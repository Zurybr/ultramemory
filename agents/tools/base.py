"""Base tool interface for agent capabilities."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class ToolCategory(Enum):
    """Categories of tools available to agents."""
    SEARCH = "search"
    MEMORY = "memory"
    WEB = "web"
    SKILL = "skill"
    LLM = "llm"
    UTILITY = "utility"


@dataclass
class ToolResult:
    """Result from tool execution."""
    success: bool
    data: Any
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    """Abstract base class for all agent tools."""

    name: str = "base_tool"
    description: str = "Base tool class"
    category: ToolCategory = ToolCategory.UTILITY
    requires_auth: bool = False

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass

    @abstractmethod
    def get_schema(self) -> dict[str, Any]:
        """Return JSON schema for tool parameters."""
        pass

    def validate_params(self, **kwargs) -> bool:
        """Validate parameters against schema."""
        return True
