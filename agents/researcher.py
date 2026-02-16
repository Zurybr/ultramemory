"""Researcher Agent - queries information from memory."""

from typing import Any
from core.memory import MemorySystem


class ResearcherAgent:
    """Agent responsible for searching and retrieving information from memory."""

    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system

    async def query(self, query_text: str, limit: int = 5) -> dict[str, Any]:
        """Query the memory system.

        Args:
            query_text: The search query
            limit: Maximum number of results

        Returns:
            List of relevant documents with scores
        """
        # 1. Search vector store
        vector_results = await self.memory.qdrant.search(
            await self.memory._generate_embedding(query_text),
            limit=limit,
        )

        # 2. Search temporal graph
        graph_results = await self.memory.graphiti.search(query_text, limit=limit)

        # 3. Combine and rank results
        combined_results = self._combine_results(vector_results, graph_results)

        return {
            "query": query_text,
            "results": combined_results[:limit],
            "total_found": len(combined_results),
        }

    def _combine_results(self, vector_results: list, graph_results: list) -> list[dict[str, Any]]:
        """Combine and deduplicate results from different sources."""
        seen_ids = set()
        combined = []

        # Priority to vector results
        for r in vector_results:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                combined.append({
                    **r,
                    "source": "vector",
                })

        for r in graph_results:
            if r.get("episode_id") not in seen_ids:
                seen_ids.add(r.get("episode_id"))
                combined.append({
                    "id": r.get("episode_id"),
                    "content": r.get("content"),
                    "score": r.get("score", 0.5),
                    "metadata": r.get("metadata", {}),
                    "source": "graph",
                })

        # Re-rank by score
        combined.sort(key=lambda x: x.get("score", 0), reverse=True)

        return combined

    async def query_by_time(self, query_text: str, time_range: str) -> dict[str, Any]:
        """Query with time-based context.

        Args:
            query_text: The search query
            time_range: Time range (e.g., "last week", "2024-01")

        Returns:
            Results within time context
        """
        # Search with time filter
        graph_results = await self.memory.graphiti.search(query_text, time_range=time_range)

        return {
            "query": query_text,
            "time_range": time_range,
            "results": graph_results,
        }
