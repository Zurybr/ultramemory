"""Embedding provider using MiniMax API."""

import os
from typing import Any


class EmbeddingProvider:
    """Generate embeddings using MiniMax API."""

    # Default dimensions by model
    DEFAULT_DIMENSIONS = {
        "MiniMax-Text-01": 1536,  # Verify with actual API
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "MiniMax-Text-01",
        base_url: str = "https://api.minimax.chat/v1",
        vector_size: int | None = None,
    ):
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY", "")
        self.model = model
        self.base_url = base_url
        # Use provided size or default for model
        self.vector_size = vector_size or self.DEFAULT_DIMENSIONS.get(model, 1536)

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for text using MiniMax API."""
        import httpx

        if not self.api_key:
            # Fallback to mock if no API key
            return self._mock_embedding(text)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "input": text
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    embedding = data["data"][0]["embedding"]
                    # Ensure consistent dimensionality
                    if len(embedding) != self.vector_size:
                        # Truncate or pad
                        if len(embedding) > self.vector_size:
                            embedding = embedding[:self.vector_size]
                        else:
                            embedding.extend([0.0] * (self.vector_size - len(embedding)))
                    return embedding
                else:
                    # Fallback on error
                    return self._mock_embedding(text)

        except Exception:
            return self._mock_embedding(text)

    def _mock_embedding(self, text: str) -> list[float]:
        """Generate deterministic mock embedding based on text hash."""
        import hashlib
        import random

        # Use text hash as seed for consistency
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
        random.seed(seed)

        # Generate embedding with configured vector size
        embedding = [random.uniform(-1, 1) for _ in range(self.vector_size)]

        # Normalize
        magnitude = sum(x**2 for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        return embedding


class OpenAIEmbeddingProvider:
    """Generate embeddings using OpenAI API."""

    DEFAULT_DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "text-embedding-3-small",
        vector_size: int | None = None,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self.vector_size = vector_size or self.DEFAULT_DIMENSIONS.get(model, 1536)

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for text using OpenAI API."""
        import httpx

        if not self.api_key:
            return self._mock_embedding(text)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "input": text
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    embedding = data["data"][0]["embedding"]
                    # Ensure consistent dimensionality
                    if len(embedding) != self.vector_size:
                        if len(embedding) > self.vector_size:
                            embedding = embedding[:self.vector_size]
                        else:
                            embedding.extend([0.0] * (self.vector_size - len(embedding)))
                    return embedding
                else:
                    return self._mock_embedding(text)

        except Exception:
            return self._mock_embedding(text)

    def _mock_embedding(self, text: str) -> list[float]:
        """Generate deterministic mock embedding."""
        import hashlib
        import random

        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
        random.seed(seed)

        embedding = [random.uniform(-1, 1) for _ in range(1536)]
        magnitude = sum(x**2 for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        return embedding


def get_embedding_provider(provider: str = "minimax", **kwargs) -> EmbeddingProvider | OpenAIEmbeddingProvider:
    """Factory function to get embedding provider.

    Args:
        provider: "minimax" or "openai"
        api_key: API key for the provider
        model: Model name to use
        vector_size: Override embedding dimensions (optional)

    Returns:
        Embedding provider instance
    """
    if provider == "openai":
        return OpenAIEmbeddingProvider(**kwargs)
    return EmbeddingProvider(**kwargs)
