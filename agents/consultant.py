"""Consultant Agent - ordered information retrieval."""

from typing import Any
from core.memory import MemorySystem


class ConsultantAgent:
    """Agent for ordered, structured information retrieval.

    Features:
    - Ordered search results by relevance, date, or source
    - Context-aware retrieval
    - Supports complex queries
    - Returns structured text output
    """

    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system

    async def query(
        self,
        query: str,
        order_by: str = "relevance",
        max_results: int = 10,
        include_context: bool = True,
    ) -> dict[str, Any]:
        """Query memory with ordering.

        Args:
            query: Search query
            order_by: "relevance", "date", or "source"
            max_results: Maximum results to return
            include_context: Include surrounding context

        Returns:
            Structured results with ordered items
        """
        # Get raw results
        raw_results = await self.memory.qdrant.search(
            query_embedding=await self.memory.embedding.embed(query),
            limit=max_results * 2,  # Get more for sorting
        )

        # Sort results
        sorted_results = self._sort_results(raw_results, order_by)

        # Limit to max_results
        sorted_results = sorted_results[:max_results]

        # Format output
        formatted = []
        for i, item in enumerate(sorted_results, 1):
            content = item.get("content", item.get("payload", {}).get("content", ""))
            metadata = item.get("metadata", item.get("payload", {}).get("metadata", {}))

            entry = {
                "rank": i,
                "content": content[:500],  # Limit content length
                "score": item.get("score", 0),
                "source": metadata.get("source", "unknown"),
                "type": metadata.get("content_type", metadata.get("type", "text")),
            }

            if include_context:
                entry["full_content"] = content

            formatted.append(entry)

        return {
            "query": query,
            "total_found": len(raw_results),
            "returned": len(formatted),
            "order_by": order_by,
            "results": formatted,
        }

    def _sort_results(self, results: list[dict], order_by: str) -> list[dict]:
        """Sort results by specified criteria."""
        if order_by == "relevance":
            return sorted(results, key=lambda x: x.get("score", 0), reverse=True)

        elif order_by == "date":
            # Sort by timestamp in metadata
            def get_date(item):
                metadata = item.get("metadata", item.get("payload", {}).get("metadata", {}))
                return metadata.get("timestamp", "")
            return sorted(results, key=get_date, reverse=True)

        elif order_by == "source":
            def get_source(item):
                metadata = item.get("metadata", item.get("payload", {}).get("metadata", {}))
                return metadata.get("source", "zzz")
            return sorted(results, key=get_source)

        return results

    async def query_structured(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Query with structured filters.

        Args:
            query: Search query
            filters: Dict with filters (type, source, date_range, tags)

        Returns:
            Filtered and structured results
        """
        filters = filters or {}

        # Base search
        results = await self.memory.qdrant.search(
            query_embedding=await self.memory.embedding.embed(query),
            limit=filters.get("limit", 20),
        )

        # Apply filters
        filtered = []
        for item in results:
            metadata = item.get("metadata", item.get("payload", {}).get("metadata", {}))

            # Filter by type
            if filters.get("type") and metadata.get("content_type") != filters["type"]:
                continue

            # Filter by source
            if filters.get("source") and metadata.get("source") != filters["source"]:
                continue

            # Filter by tags
            if filters.get("tags"):
                item_tags = metadata.get("tags", [])
                if not any(tag in item_tags for tag in filters["tags"]):
                    continue

            filtered.append(item)

        return {
            "query": query,
            "filters_applied": filters,
            "results": filtered,
            "count": len(filtered),
        }

    def format_as_text(self, results: dict[str, Any]) -> str:
        """Format query results as readable text.

        Args:
            results: Results from query()

        Returns:
            Formatted text string
        """
        lines = [
            f"=== Resultados para: {results['query']} ===",
            f"Ordenado por: {results['order_by']}",
            f"Total: {results['returned']} de {results['total_found']}",
            "",
        ]

        for item in results["results"]:
            lines.extend([
                f"[{item['rank']}] (score: {item['score']:.2f})",
                f"Fuente: {item['source']} | Tipo: {item['type']}",
                "",
                item["content"],
                "",
                "-" * 40,
                "",
            ])

        return "\n".join(lines)
