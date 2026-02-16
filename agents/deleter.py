"""Deleter Agent - removes memories from the system."""

from typing import Any

from core.memory import MemorySystem


class DeleterAgent:
    """Agent responsible for deleting memories from the system."""

    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system

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
            # Get count before deletion
            count_before = await self.memory.qdrant.count()

            # Delete all from Qdrant
            deleted = await self.memory.qdrant.delete_all()
            result["qdrant_deleted"] = deleted if deleted else count_before

            # Clear Redis cache
            try:
                await self.memory.redis.clear_all()
                result["redis_cleared"] = True
            except Exception:
                result["redis_cleared"] = False

            # Clear Graphiti graph
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

    async def delete_by_query(self, query: str, limit: int = 100) -> dict[str, Any]:
        """Delete memories matching a semantic query.

        Args:
            query: Search query to find memories to delete
            limit: Maximum memories to delete

        Returns:
            Report with deleted items
        """
        result = {
            "status": "success",
            "query": query,
            "deleted": 0,
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
                    await self.memory.qdrant.delete(item["id"])
                    result["deleted"] += 1
                except Exception as e:
                    result["errors"].append(f"Failed to delete {item['id']}: {e}")

            result["message"] = f"Deleted {result['deleted']} memories matching '{query}'"

        except Exception as e:
            result["status"] = "error"
            result["errors"].append(str(e))

        return result

    async def delete_by_id(self, memory_id: str) -> dict[str, Any]:
        """Delete a specific memory by ID.

        Args:
            memory_id: The ID of the memory to delete

        Returns:
            Report with status
        """
        result = {
            "status": "success",
            "id": memory_id,
            "deleted": False,
        }

        try:
            await self.memory.qdrant.delete(memory_id)
            result["deleted"] = True
            result["message"] = f"Memory {memory_id} deleted"
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    async def count(self) -> int:
        """Count total memories in the system."""
        return await self.memory.qdrant.count()
