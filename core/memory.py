"""Core memory module integrating FalkorDB, Graphiti, Qdrant, and Redis."""

import os
from datetime import datetime
from typing import Any
from .graphiti_client import GraphitiClient
from .falkordb_client import FalkorDBClient
from .qdrant_client import QdrantClientWrapper
from .redis_client import RedisClientWrapper
from .embedding_provider import get_embedding_provider


class MemorySystem:
    """Hybrid memory system combining FalkorDB, Graphiti, Qdrant, and Redis."""

    def __init__(
        self,
        graphiti_url: str = "http://localhost:8001",
        qdrant_url: str = "http://localhost:6333",
        redis_url: str = "redis://localhost:6379",
        falkordb_url: str = "redis://localhost:6370",
        embedding_model: str = "text-embedding-3-small",
    ):
        self.graphiti = GraphitiClient(graphiti_url)
        self.falkordb = FalkorDBClient(host="localhost", port=6370)
        self.qdrant = QdrantClientWrapper(qdrant_url)
        self.redis = RedisClientWrapper(redis_url)
        self.embedding_model = embedding_model

        # Initialize embedding provider based on config
        embedding_provider = os.getenv("EMBEDDING_PROVIDER", "minimax")
        api_key = os.getenv(f"{embedding_provider.upper()}_API_KEY", "")

        self.embedding = get_embedding_provider(embedding_provider, api_key=api_key)

    async def add(self, content: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Add content to memory system - stores in both Qdrant (embedding) and FalkorDB (graph).

        Returns:
            dict with doc_id and status for each store
        """
        metadata = metadata or {}
        metadata["created_at"] = datetime.now().isoformat()

        results = {
            "qdrant_id": None,
            "falkordb_id": None,
            "status": "partial",
            "errors": []
        }

        # 0. Ensure Qdrant collection exists
        await self.qdrant.ensure_collection()

        # 1. Generate embedding
        embedding = await self._generate_embedding(content)

        # 2. Add to Qdrant (vector search)
        try:
            doc_id = await self.qdrant.add(embedding, content, metadata)
            results["qdrant_id"] = doc_id
        except Exception as e:
            results["errors"].append(f"Qdrant: {str(e)}")

        # 3. Add to FalkorDB (graph) - with same ID for cross-reference
        try:
            # Extract labels from metadata
            labels = metadata.get("labels", ["Document"])
            if isinstance(labels, str):
                labels = [labels]

            # Use same ID as Qdrant for cross-referencing
            entity_id = results["qdrant_id"] or f"doc_{hash(content) % 1000000}"

            await self.falkordb.add_node(
                entity_id=entity_id,
                content=content,
                metadata=metadata,
                labels=labels
            )
            results["falkordb_id"] = entity_id
        except Exception as e:
            results["errors"].append(f"FalkorDB: {str(e)}")

        # 4. Add to Graphiti (temporal graph) - optional
        try:
            await self.graphiti.add_episode(content, metadata)
        except Exception:
            pass

        # 5. Cache in Redis - optional
        try:
            doc_id = results["qdrant_id"] or "unknown"
            await self.redis.set(f"doc:{doc_id}", content, ex=3600)
        except Exception:
            pass

        # Set status
        if results["qdrant_id"] and results["falkordb_id"]:
            results["status"] = "full"
        elif results["qdrant_id"] or results["falkordb_id"]:
            results["status"] = "partial"

        return results

    async def query(self, query_text: str, limit: int = 5) -> dict[str, Any]:
        """Query memory system - searches both Qdrant (vector) and FalkorDB (graph).

        Returns:
            dict with vector_results and graph_results
        """
        # 1. Generate embedding for query
        embedding = await self._generate_embedding(query_text)

        # 2. Search Qdrant (semantic/vector search)
        vector_results = []
        try:
            vector_results = await self.qdrant.search(embedding, limit)
        except Exception as e:
            pass

        # 3. Search FalkorDB (graph-based search)
        graph_results = []
        try:
            # Check FalkorDB health first
            if await self.falkordb.health_check():
                # Search by keywords
                graph_results = await self.falkordb.search_nodes(query_text, limit)
        except Exception:
            pass

        # 4. Search Graphiti for temporal context - optional
        temporal_results = []
        try:
            temporal_results = await self.graphiti.search(query_text, limit)
        except Exception:
            pass

        return {
            "vector_results": vector_results,
            "graph_results": graph_results,
            "temporal_results": temporal_results,
            "query": query_text,
        }

    async def get_stats(self) -> dict[str, Any]:
        """Get statistics from all stores."""
        stats = {
            "qdrant": {"documents": 0},
            "falkordb": {"nodes": 0, "relations": 0},
            "redis": {"cached": 0},
        }

        try:
            docs = await self.qdrant.get_all(limit=10000)
            stats["qdrant"]["documents"] = len(docs)
        except Exception:
            pass

        try:
            graph_stats = await self.falkordb.get_stats()
            stats["falkordb"] = graph_stats
        except Exception:
            pass

        return stats

    async def sync_graph(self) -> dict[str, Any]:
        """Sync Qdrant documents to FalkorDB graph."""
        synced = 0
        errors = []

        try:
            # Get all documents from Qdrant
            docs = await self.qdrant.get_all(limit=1000)

            for doc in docs:
                try:
                    doc_id = doc.get("id", "")
                    content = doc.get("content", "")
                    metadata = doc.get("metadata", {})

                    # Check if node exists in FalkorDB
                    existing = await self.falkordb.get_node(doc_id)
                    if not existing:
                        # Add to graph
                        await self.falkordb.add_node(
                            entity_id=doc_id,
                            content=content,
                            metadata=metadata
                        )
                        synced += 1
                except Exception as e:
                    errors.append(str(e))

            return {"synced": synced, "total": len(docs), "errors": errors}
        except Exception as e:
            return {"synced": 0, "error": str(e)}

    async def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for text using configured provider."""
        try:
            return await self.embedding.embed(text)
        except Exception:
            # Fallback to mock if embedding fails
            import random
            return [random.random() for _ in range(1536)]

    async def close(self):
        """Close all connections."""
        await self.graphiti.close()
        await self.falkordb.close()
        await self.redis.close()
