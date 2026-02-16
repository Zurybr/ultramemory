"""Consolidator Agent - reorganizes and deduplicates memory."""

from typing import Any
from core.memory import MemorySystem


class ConsolidatorAgent:
    """Agent responsible for consolidating and deduplicating memory."""

    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system
        self.similarity_threshold = 0.95

    async def consolidate(self) -> dict[str, Any]:
        """Run consolidation process.

        Returns:
            Report with actions taken
        """
        report = {
            "duplicates_removed": 0,
            "entities_merged": 0,
            "reindexed": 0,
            "errors": [],
        }

        try:
            # 1. Find duplicates
            duplicates = await self._find_duplicates()
            report["duplicates_removed"] = len(duplicates)

            # 2. Remove duplicates
            for dup in duplicates:
                await self.memory.qdrant.delete(dup["id"])

            # 3. Merge related entities in graph
            merged = await self._merge_entities()
            report["entities_merged"] = merged

            # 4. Trigger graph consolidation
            await self.memory.graphiti.consolidate()

            report["status"] = "success"

        except Exception as e:
            report["status"] = "error"
            report["errors"].append(str(e))

        return report

    async def _find_duplicates(self) -> list[dict[str, Any]]:
        """Find duplicate entries in memory.

        Uses exact content matching to find duplicates.
        Returns list of duplicate IDs to remove (keeps first occurrence).
        """
        duplicates = []
        seen_content = {}

        # Get all documents
        all_docs = await self.memory.qdrant.get_all(limit=10000)

        for doc in all_docs:
            content = doc.get("content", "")
            content_hash = hash(content)

            if content_hash in seen_content:
                # Found duplicate - mark for deletion
                duplicates.append({
                    "id": doc["id"],
                    "content": content[:50] + "..." if len(content) > 50 else content,
                    "duplicate_of": seen_content[content_hash],
                })
            else:
                # First occurrence - keep it
                seen_content[content_hash] = doc["id"]

        return duplicates

    async def _merge_entities(self) -> int:
        """Merge related entities in the graph."""
        # Graph consolidation handles this internally
        return 0

    async def analyze(self) -> dict[str, Any]:
        """Analyze memory for issues without making changes."""
        total_docs = await self.memory.qdrant.count()
        all_docs = await self.memory.qdrant.get_all(limit=10000)

        # Count potential duplicates
        seen_content = set()
        potential_duplicates = 0
        for doc in all_docs:
            content_hash = hash(doc.get("content", ""))
            if content_hash in seen_content:
                potential_duplicates += 1
            else:
                seen_content.add(content_hash)

        return {
            "total_documents": total_docs,
            "potential_duplicates": potential_duplicates,
            "orphaned_nodes": 0,
            "unique_content": len(seen_content),
            "recommendations": [
                "Run consolidation to remove duplicates" if potential_duplicates > 0 else "Memory is healthy",
                "Consider running consolidation during off-peak hours",
            ],
        }
