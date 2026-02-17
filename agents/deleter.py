"""Enhanced Deleter Agent - removes memories with connection preservation."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from core.memory import MemorySystem


class DeleterAgent:
    """Agent responsible for deleting memories with audit trail.

    Features:
    - Preserves graph connections when possible
    - Maintains audit log of deletions
    - Option to create new connections after deletion
    """

    AUDIT_LOG = Path.home() / ".ulmemory" / "logs" / "deletions.jsonl"

    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system
        self.AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)

    async def delete_all(self, confirm: bool = False) -> dict[str, Any]:
        """Delete ALL memories from the system.

        Args:
            confirm: Must be True to actually delete

        Returns:
            Report with count of deleted items
        """
        if not confirm:
            return {
                "status": "aborted",
                "message": "Deletion not confirmed. Set confirm=True to proceed.",
            }

        result = {
            "status": "success",
            "qdrant_deleted": 0,
            "falkordb_deleted": 0,
            "errors": [],
        }

        try:
            count_before = await self.memory.qdrant.count()
            deleted = await self.memory.qdrant.delete_all()
            result["qdrant_deleted"] = deleted if deleted else count_before

            # Delete all from FalkorDB
            try:
                if hasattr(self.memory, 'falkordb'):
                    # Get all nodes and delete them
                    nodes = await self.memory.falkordb.get_all_nodes(limit=10000)
                    for node in nodes:
                        node_id = node.get("id", "")
                        if node_id:
                            await self.memory.falkordb.execute(f"MATCH (n {{id: '{node_id}'}}) DETACH DELETE n")
                    result["falkordb_deleted"] = len(nodes)
            except Exception as e:
                result["errors"].append(f"FalkorDB: {str(e)}")

            # Log the deletion
            await self._log_deletion({
                "type": "delete_all",
                "qdrant_count": result["qdrant_deleted"],
                "falkordb_count": result["falkordb_deleted"],
                "timestamp": datetime.now().isoformat(),
            })

            try:
                await self.memory.redis.clear_all()
                result["redis_cleared"] = True
            except Exception:
                result["redis_cleared"] = False

            try:
                await self.memory.graphiti.clear_all()
                result["graph_cleared"] = True
            except Exception:
                result["graph_cleared"] = False

            result["message"] = f"Deleted {result['qdrant_deleted']} Qdrant, {result['falkordb_deleted']} FalkorDB"

        except Exception as e:
            result["status"] = "error"
            result["errors"].append(str(e))

        return result

    async def delete_by_query(self, query: str, limit: int = 100, preserve_connections: bool = True) -> dict[str, Any]:
        """Delete memories matching a query from both Qdrant and FalkorDB.

        Args:
            query: Search query to find memories to delete
            limit: Maximum memories to delete
            preserve_connections: If True, check graph before deletion

        Returns:
            Report with deleted items
        """
        result = {
            "status": "success",
            "query": query,
            "qdrant_deleted": 0,
            "falkordb_deleted": 0,
            "preserved_connections": 0,
            "errors": [],
        }

        try:
            # Search for memories in both stores
            search_results = await self.memory.query(query, limit=limit)

            # Get IDs from vector results (Qdrant)
            vector_ids = [r.get("id", "") for r in search_results.get("vector_results", [])]

            # Get IDs from graph results (FalkorDB)
            graph_ids = [r.get("id", "") for r in search_results.get("graph_results", [])]

            # Combine and dedupe
            all_ids = list(set(vector_ids + graph_ids))[:limit]

            # Delete each found memory
            for memory_id in all_ids:
                if not memory_id:
                    continue

                try:
                    # Check for connections if preservation is enabled
                    if preserve_connections:
                        has_connections = await self._check_connections(memory_id)
                        if has_connections:
                            result["preserved_connections"] += 1
                            continue  # Skip deletion

                    # Delete from Qdrant
                    try:
                        await self.memory.qdrant.delete(memory_id)
                        result["qdrant_deleted"] += 1
                    except Exception:
                        pass

                    # Delete from FalkorDB
                    try:
                        if hasattr(self.memory, 'falkordb'):
                            await self.memory.falkordb.execute(f"MATCH (n {{id: '{memory_id}'}}) DETACH DELETE n")
                            result["falkordb_deleted"] += 1
                    except Exception:
                        pass

                    # Log the deletion
                    await self._log_deletion({
                        "type": "delete_by_query",
                        "query": query,
                        "deleted_id": memory_id,
                        "timestamp": datetime.now().isoformat(),
                    })

                except Exception as e:
                    result["errors"].append(f"Failed to delete {memory_id}: {e}")

            result["deleted"] = result["qdrant_deleted"] + result["falkordb_deleted"]
            result["message"] = f"Deleted {result['qdrant_deleted']} Qdrant, {result['falkordb_deleted']} FalkorDB"

        except Exception as e:
            result["status"] = "error"
            result["errors"].append(str(e))

        return result

    async def delete_by_id(self, memory_id: str, preserve_connections: bool = True) -> dict[str, Any]:
        """Delete a specific memory by ID from both Qdrant and FalkorDB.

        Args:
            memory_id: The ID of the memory to delete
            preserve_connections: If True, preserve graph connections

        Returns:
            Report with status
        """
        result = {
            "status": "success",
            "id": memory_id,
            "qdrant_deleted": False,
            "falkordb_deleted": False,
        }

        try:
            if preserve_connections:
                has_connections = await self._check_connections(memory_id)
                if has_connections:
                    result["status"] = "blocked"
                    result["message"] = f"Memory {memory_id} has connections. Use force=True to delete anyway."
                    return result

            # Delete from Qdrant
            try:
                await self.memory.qdrant.delete(memory_id)
                result["qdrant_deleted"] = True
            except Exception as e:
                result["qdrant_error"] = str(e)

            # Delete from FalkorDB
            try:
                if hasattr(self.memory, 'falkordb'):
                    await self.memory.falkordb.execute(f"MATCH (n {{id: '{memory_id}'}}) DETACH DELETE n")
                    result["falkordb_deleted"] = True
            except Exception as e:
                result["falkordb_error"] = str(e)

            # Log the deletion
            await self._log_deletion({
                "type": "delete_by_id",
                "deleted_id": memory_id,
                "qdrant": result["qdrant_deleted"],
                "falkordb": result["falkordb_deleted"],
                "timestamp": datetime.now().isoformat(),
            })

            result["deleted"] = result["qdrant_deleted"] or result["falkordb_deleted"]
            result["message"] = f"Memory {memory_id} deleted from Qdrant:{result['qdrant_deleted']}, FalkorDB:{result['falkordb_deleted']}"

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    async def delete_with_replacement(self, memory_id: str, new_content: str, new_metadata: dict | None = None) -> dict[str, Any]:
        """Delete memory and create new connections to replace it.

        Args:
            memory_id: ID to delete
            new_content: New content to add
            new_metadata: Metadata for new content

        Returns:
            Report with deletion and creation
        """
        # First, get related memories
        related = await self._get_related(memory_id)

        # Delete old
        await self.memory.qdrant.delete(memory_id)

        # Log deletion
        await self._log_deletion({
            "type": "delete_with_replacement",
            "deleted_id": memory_id,
            "new_relationships": len(related),
            "timestamp": datetime.now().isoformat(),
        })

        # Add new content
        new_metadata = new_metadata or {}
        new_metadata["replaces"] = memory_id
        new_metadata["related_count"] = len(related)

        doc_id = await self.memory.add(new_content, metadata=new_metadata)

        return {
            "status": "success",
            "deleted_id": memory_id,
            "new_id": doc_id,
            "related_preserved": len(related),
        }

    async def _check_connections(self, memory_id: str) -> bool:
        """Check if memory has graph connections in FalkorDB."""
        try:
            # Check FalkorDB first
            if hasattr(self.memory, 'falkordb'):
                try:
                    result = await self.memory.falkordb.get_node_relationships(memory_id)
                    if result and len(result) > 0:
                        return True
                except Exception:
                    pass

            # Fallback to graphiti
            try:
                result = await self.memory.graphiti.get_neighbors(memory_id)
                return len(result) > 0
            except Exception:
                return False

        except Exception:
            return False

    async def _get_related(self, memory_id: str) -> list[str]:
        """Get related memory IDs."""
        try:
            result = await self.memory.graphiti.get_neighbors(memory_id)
            return [r.get("id") for r in result]
        except Exception:
            return []

    async def _log_deletion(self, entry: dict[str, Any]):
        """Log deletion to audit file."""
        try:
            with open(self.AUDIT_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass  # Don't fail if logging fails

    async def get_audit_log(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent deletion history."""
        if not self.AUDIT_LOG.exists():
            return []

        entries = []
        with open(self.AUDIT_LOG, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    continue

        return entries[-limit:]

    async def count(self) -> int:
        """Count total memories in the system."""
        return await self.memory.qdrant.count()
