"""Memory operation tools for agents."""

from typing import Any
from .base import BaseTool, ToolCategory, ToolResult


class MemoryQueryTool(BaseTool):
    """Query memory system."""

    name = "memory_query"
    description = "Search the memory system for information"
    category = ToolCategory.MEMORY

    def __init__(self, memory):
        """Initialize with MemorySystem instance."""
        self.memory = memory

    async def execute(self, query: str, limit: int = 5) -> ToolResult:
        """Query memory.

        Args:
            query: Search query
            limit: Maximum results to return
        """
        try:
            results = await self.memory.query(query, limit)
            return ToolResult(
                success=True,
                data=results,
                metadata={"query": query, "limit": limit}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Memory query failed: {str(e)}"
            )

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for semantic search"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 5,
                        "description": "Maximum number of results"
                    }
                },
                "required": ["query"]
            }
        }


class MemoryAddTool(BaseTool):
    """Add content to memory."""

    name = "memory_add"
    description = "Add content to the memory system for later retrieval"
    category = ToolCategory.MEMORY

    def __init__(self, memory):
        """Initialize with MemorySystem instance."""
        self.memory = memory

    async def execute(
        self,
        content: str,
        metadata: dict | None = None,
        tags: list[str] | None = None
    ) -> ToolResult:
        """Add content to memory.

        Args:
            content: Content to store
            metadata: Optional metadata dict
            tags: Optional list of tags
        """
        try:
            # Merge tags into metadata
            meta = metadata or {}
            if tags:
                meta["tags"] = tags

            doc_id = await self.memory.add(content, meta)
            return ToolResult(
                success=True,
                data={"doc_id": doc_id, "content_length": len(content)},
                metadata={"tags": tags or []}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Memory add failed: {str(e)}"
            )

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Content to store in memory"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional metadata to attach"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags for categorization"
                    }
                },
                "required": ["content"]
            }
        }


class MemoryCountTool(BaseTool):
    """Count documents in memory."""

    name = "memory_count"
    description = "Count total documents in memory system"
    category = ToolCategory.MEMORY

    def __init__(self, memory):
        """Initialize with MemorySystem instance."""
        self.memory = memory

    async def execute(self) -> ToolResult:
        """Count all documents."""
        try:
            count = await self.memory.qdrant.count()
            return ToolResult(
                success=True,
                data={"count": count},
                metadata={}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Count failed: {str(e)}"
            )

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
