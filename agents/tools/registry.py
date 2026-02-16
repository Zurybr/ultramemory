"""Tool registry for managing available tools."""

from typing import Any
from .base import BaseTool, ToolCategory


class ToolRegistry:
    """Registry for all available tools."""

    _instance = None
    _tools: dict[str, BaseTool] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
        return cls._instance

    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> bool:
        """Unregister a tool by name."""
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self, category: ToolCategory | None = None) -> list[BaseTool]:
        """List all tools, optionally filtered by category."""
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return tools

    def get_schemas(self) -> list[dict[str, Any]]:
        """Get schemas for all tools."""
        return [t.get_schema() for t in self._tools.values()]

    def get_names(self) -> list[str]:
        """Get all registered tool names."""
        return list(self._tools.keys())

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()


# Global registry instance
registry = ToolRegistry()
