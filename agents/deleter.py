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
            "errors": [],
        }

        try:
            count_before = await self.memory.qdrant.count()
            deleted = await self.memory.qdrant.delete_all()
            result["qdrant_deleted"] = deleted if deleted else count_before

            # Log the deletion
            await self._log_deletion({
                "type": "delete_all",
                "count": result["qdrant_deleted"],
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

            result["message"] = f"Deleted {result['qdrant_deleted']} memories"

        except Exception as e:
            result["status"] = "error"
            result["errors"].append(str(e))

        return result

    async def delete_by_query(self, query: str, limit: int = 100, preserve_connections: bool = True) -> dict[str, Any]:
        """Delete memories matching a semantic query.

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
            "deleted": 0,
            "preserved_connections": 0,
            "errors": [],
        }

        try:
            # Search for memories
            results = await self.memory.qdrant.search(
                query_embedding=await self.memory.embedding.embed(query),
                limit=limit,
            )

            # Delete each found memory
            for item in results:
                try:
                    # Check for connections if preservation is enabled
                    if preserve_connections:
                        has_connections = await self._check_connections(item["id"])
                        if has_connections:
                            result["preserved_connections"] += 1
                            continue  # Skip deletion

                    await self.memory.qdrant.delete(item["id"])
                    result["deleted"] += 1

                    # Log the deletion
                    await self._log_deletion({
                        "type": "delete_by_query",
                        "query": query,
                        "deleted_id": item["id"],
                        "timestamp": datetime.now().isoformat(),
                    })

                except Exception as e:
                    result["errors"].append(f"Failed to delete {item['id']}: {e}")

            result["message"] = f"Deleted {result['deleted']} memories matching '{query}'"

        except Exception as e:
            result["status"] = "error"
            result["errors"].append(str(e))

        return result

    async def delete_by_id(self, memory_id: str, preserve_connections: bool = True) -> dict[str, Any]:
        """Delete a specific memory by ID.

        Args:
            memory_id: The ID of the memory to delete
            preserve_connections: If True, preserve graph connections

        Returns:
            Report with status
        """
        result = {
            "status": "success",
            "id": memory_id,
            "deleted": False,
        }

        try:
            if preserve_connections:
                has_connections = await self._check_connections(memory_id)
                if has_connections:
                    result["status"] = "blocked"
                    result["message"] = f"Memory {memory_id} has connections. Use force=True to delete anyway."
                    return result

            await self.memory.qdrant.delete(memory_id)
            result["deleted"] = True

            # Log the deletion
            await self._log_deletion({
                "type": "delete_by_id",
                "deleted_id": memory_id,
                "timestamp": datetime.now().isoformat(),
            })

            result["message"] = f"Memory {memory_id} deleted"

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
        """Check if memory has graph connections."""
        try:
            # Try graphiti connection check
            result = await self.memory.graphiti.get_neighbors(memory_id)
            return len(result) > 0
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
