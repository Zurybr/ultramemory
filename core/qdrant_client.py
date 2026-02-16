"""Qdrant client wrapper for vector search."""

from typing import Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid


class QdrantClientWrapper:
    """Wrapper for Qdrant client."""

    def __init__(self, url: str = "http://localhost:6333", api_key: str | None = None):
        self.client = QdrantClient(url=url, api_key=api_key)
        self.collection_name = "ultramemory"

    async def ensure_collection(self, vector_size: int = 1536):
        """Ensure collection exists."""
        collections = self.client.get_collections().collections
        if self.collection_name not in [c.name for c in collections]:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

    async def add(self, embedding: list[float], content: str, metadata: dict[str, Any]) -> str:
        """Add a vector to Qdrant."""
        point_id = str(uuid.uuid4())

        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={"content": content, "metadata": metadata},
                )
            ],
        )

        return point_id

    async def search(self, query_embedding: list[float], limit: int = 5) -> list[dict[str, Any]]:
        """Search vectors."""
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=limit,
        )

        return [
            {
                "id": r.id,
                "score": r.score,
                "content": r.payload.get("content"),
                "metadata": r.payload.get("metadata", {}),
            }
            for r in results.points
        ]

    async def delete(self, point_id: str):
        """Delete a vector."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=[point_id],
        )

    async def health(self) -> bool:
        """Check if Qdrant is healthy."""
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False

    async def get_all(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Get all points from collection."""
        try:
            result, _ = self.client.scroll(
                collection_name=self.collection_name,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
            return [
                {
                    "id": str(point.id),
                    "content": point.payload.get("content", ""),
                    "metadata": point.payload.get("metadata", {}),
                }
                for point in result
            ]
        except Exception:
            return []

    async def count(self) -> int:
        """Count total points in collection."""
        try:
            result = self.client.count(collection_name=self.collection_name)
            return result.count
        except Exception:
            return 0
