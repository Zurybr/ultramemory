"""Graphiti client for temporal graph memory."""

import httpx
from typing import Any


class GraphitiClient:
    """Client for Graphiti API."""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def add_episode(self, content: str, metadata: dict[str, Any]) -> str:
        """Add an episode to the graph."""
        response = await self.client.post(
            f"{self.base_url}/episodes",
            json={"content": content, "metadata": metadata},
        )
        response.raise_for_status()
        return response.json()["episode_id"]

    async def search(self, query: str, limit: int = 5, time_range: str | None = None) -> list[dict[str, Any]]:
        """Search the graph."""
        params = {"query": query, "limit": limit}
        if time_range:
            params["time_range"] = time_range
            
        response = await self.client.post(
            f"{self.base_url}/search",
            json=params,
        )
        response.raise_for_status()
        return response.json()["results"]

    async def get_history(self, entity_name: str, time_range: str | None = None) -> list[dict[str, Any]]:
        """Get entity history within time range."""
        params = {"entity_name": entity_name}
        if time_range:
            params["time_range"] = time_range

        response = await self.client.get(
            f"{self.base_url}/entities/history",
            params=params,
        )
        response.raise_for_status()
        return response.json()["history"]

    async def consolidate(self) -> dict[str, Any]:
        """Trigger graph consolidation."""
        response = await self.client.post(f"{self.base_url}/consolidate")
        response.raise_for_status()
        return response.json()

    async def health(self) -> bool:
        """Check if Graphiti is healthy."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        """Close the client."""
        await self.client.aclose()
