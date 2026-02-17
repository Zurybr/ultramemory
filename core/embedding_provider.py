"""Embedding provider using MiniMax API."""

import os
from typing import Any


class EmbeddingProvider:
    """Generate embeddings using MiniMax API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "MiniMax-Text-01",
        base_url: str = "https://api.minimax.chat/v1"
    ):
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY", "")
        self.model = model
        self.base_url = base_url

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
                    return data["data"][0]["embedding"]
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

        # Generate 1536-dimensional embedding (OpenAI standard)
        embedding = [random.uniform(-1, 1) for _ in range(1536)]

        # Normalize
        magnitude = sum(x**2 for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        return embedding


class OpenAIEmbeddingProvider:
    """Generate embeddings using OpenAI API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "text-embedding-3-small"
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model

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
                    return data["data"][0]["embedding"]
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
    """Factory function to get embedding provider."""
    if provider == "openai":
        return OpenAIEmbeddingProvider(**kwargs)
    return EmbeddingProvider(**kwargs)
