"""Core memory module integrating Graphiti, Qdrant, and Redis."""

from typing import Any
from .graphiti_client import GraphitiClient
from .qdrant_client import QdrantClientWrapper
from .redis_client import RedisClientWrapper


class MemorySystem:
    """Hybrid memory system combining Graphiti, Qdrant, and Redis."""

    def __init__(
        self,
        graphiti_url: str = "http://localhost:8001",
        qdrant_url: str = "http://localhost:6333",
        redis_url: str = "redis://localhost:6379",
        embedding_model: str = "text-embedding-3-small",
    ):
        self.graphiti = GraphitiClient(graphiti_url)
        self.qdrant = QdrantClientWrapper(qdrant_url)
        self.redis = RedisClientWrapper(redis_url)
        self.embedding_model = embedding_model

    async def add(self, content: str, metadata: dict[str, Any] | None = None) -> str:
        """Add content to memory system."""
        # 1. Generate embedding
        embedding = await self._generate_embedding(content)

        # 2. Add to Qdrant (vector search)
        doc_id = await self.qdrant.add(embedding, content, metadata or {})

        # 3. Add to Graphiti (temporal graph)
        episode_id = await self.graphiti.add_episode(content, metadata or {})

        # 4. Cache in Redis
        await self.redis.set(f"doc:{doc_id}", content, ex=3600)

        return doc_id

    async def query(self, query_text: str, limit: int = 5) -> dict[str, Any]:
        """Query memory system."""
        # 1. Generate embedding for query
        embedding = await self._generate_embedding(query_text)

        # 2. Search Qdrant
        results = await self.qdrant.search(embedding, limit)

        # 3. Search Graphiti for temporal context
        graph_results = await self.graphiti.search(query_text, limit)

        return {
            "vector_results": results,
            "graph_results": graph_results,
        }

    async def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for text (placeholder - to be implemented with LangChain)."""
        # Will be implemented with LangChain
        import random
        # Return a mock embedding of 1536 dimensions (OpenAI embedding size)
        return [random.random() for _ in range(1536)]

    async def close(self):
        """Close all connections."""
        await self.graphiti.close()
        await self.redis.close()
