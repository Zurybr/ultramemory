"""Web search tool using Tavily API."""

import os
from typing import Any
import httpx
from .base import BaseTool, ToolCategory, ToolResult

# Try to load from config file
def _load_tavily_key() -> str | None:
    """Load Tavily API key from config or env."""
    # First check env
    key = os.getenv("TAVILY_API_KEY")
    if key:
        return key

    # Try to load from config file
    try:
        import yaml
        from pathlib import Path
        config_path = Path.home() / ".config" / "ultramemory" / "config.yaml"
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
                return config.get("research", {}).get("tavily", {}).get("api_key")
    except Exception:
        pass

    return None


class WebSearchTool(BaseTool):
    """Web search tool using Tavily API."""

    name = "web_search"
    description = "Search the web for information using Tavily API"
    category = ToolCategory.WEB
    requires_auth = True

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or _load_tavily_key()
        self.base_url = "https://api.tavily.com"

    async def execute(
        self,
        query: str,
        max_results: int = 5,
        include_raw_content: bool = False,
        search_depth: str = "basic",
        include_answer: bool = True
    ) -> ToolResult:
        """Execute web search.

        Args:
            query: Search query
            max_results: Maximum number of results (1-10)
            include_raw_content: Include raw HTML content
            search_depth: "basic" or "advanced"
            include_answer: Include AI-generated answer
        """
        if not self.api_key:
            return ToolResult(
                success=False,
                data=None,
                error="TAVILY_API_KEY not set. Get one at https://tavily.com"
            )

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/search",
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "max_results": min(max_results, 10),
                        "include_raw_content": include_raw_content,
                        "search_depth": search_depth,
                        "include_answer": include_answer,
                    }
                )
                response.raise_for_status()
                data = response.json()

                return ToolResult(
                    success=True,
                    data=data,
                    metadata={
                        "query": query,
                        "results_count": len(data.get("results", [])),
                        "answer_included": include_answer and data.get("answer") is not None
                    }
                )
            except httpx.HTTPStatusError as e:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"HTTP error {e.response.status_code}: {e.response.text[:200]}"
                )
            except httpx.RequestError as e:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Request error: {str(e)}"
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
                        "description": "Search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results (1-10)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 10
                    },
                    "search_depth": {
                        "type": "string",
                        "enum": ["basic", "advanced"],
                        "default": "basic",
                        "description": "Search depth - advanced uses more credits"
                    },
                    "include_answer": {
                        "type": "boolean",
                        "default": True,
                        "description": "Include AI-generated answer"
                    }
                },
                "required": ["query"]
            }
        }
