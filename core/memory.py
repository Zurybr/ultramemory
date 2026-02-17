"""Core memory module integrating FalkorDB, Graphiti, Qdrant, and Redis."""

import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime
from typing import Any
from .graphiti_client import GraphitiClient
from .falkordb_client import FalkorDBClient
from .qdrant_client import QdrantClientWrapper
from .redis_client import RedisClientWrapper
from .embedding_provider import get_embedding_provider


# Common queries for cache warm-up
COMMON_QUERIES = [
    "project",
    "architecture",
    "bug",
    "feature",
    "api",
    "config",
    "memory",
    "research",
    "documentation",
]

# Stopwords for keyword extraction
STOPWORDS = {
    'this', 'that', 'with', 'from', 'have', 'been', 'were', 'they', 'their',
    'which', 'would', 'could', 'should', 'there', 'where', 'when', 'what',
    'more', 'also', 'just', 'only', 'very', 'into', 'over', 'such', 'after',
    'before', 'about', 'above', 'below', 'between', 'under', 'again', 'then',
    'once', 'here', 'some', 'any', 'each', 'most', 'other', 'these', 'those',
    'being', 'having', 'doing', 'because', 'while', 'through', 'during'
}


class MemorySystem:
    """Hybrid memory system combining FalkorDB, Graphiti, Qdrant, and Redis."""

    # Redis cache keys
    RECENT_CACHE_PREFIX = "recent:"
    RECENT_CACHE_LIST = "recent:docs"
    RECENT_CACHE_MAX = 100
    CACHE_TTL_SECONDS = 3600  # 1 hour

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
        vector_size = int(os.getenv("EMBEDDING_VECTOR_SIZE", "1536"))

        self.embedding = get_embedding_provider(
            embedding_provider,
            api_key=api_key,
            vector_size=vector_size
        )

    async def add(self, content: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Add content to memory system - stores in both Qdrant (embedding) and FalkorDB (graph).

        Enhanced with:
        - Automatic metadata extraction (keywords, entities, language, source_type)
        - Entity extraction for FalkorDB relationships
        - Improved Redis caching with recent content tracking
        - Context-aware embeddings

        Returns:
            dict with doc_id and status for each store
        """
        metadata = metadata or {}
        now = datetime.now()

        # 0. Enrich metadata automatically
        metadata = self._enrich_metadata(content, metadata, now)

        results = {
            "qdrant_id": None,
            "falkordb_id": None,
            "status": "partial",
            "errors": [],
            "metadata_enriched": True
        }

        # 1. Ensure Qdrant collection exists
        await self.qdrant.ensure_collection()

        # 2. Generate context-aware embedding
        embedding = await self._generate_embedding_with_context(content, metadata)

        # 3. Add to Qdrant (vector search)
        try:
            doc_id = await self.qdrant.add(embedding, content, metadata)
            results["qdrant_id"] = doc_id
        except Exception as e:
            results["errors"].append(f"Qdrant: {str(e)}")

        # 4. Add to FalkorDB (graph) - with entity relationships
        entity_id = None
        try:
            # Extract labels from metadata
            labels = metadata.get("labels", ["Document"])
            if isinstance(labels, str):
                labels = [labels]
            if not labels:
                labels = ["Document"]

            # Add entity type labels if available
            entity_labels = metadata.get("entity_labels", [])
            if entity_labels:
                labels.extend(entity_labels[:3])

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

        # 5. Add to Graphiti (temporal graph) - optional
        try:
            await self.graphiti.add_episode(content, metadata)
        except Exception:
            pass

        # 6. Cache in Redis - improved caching
        try:
            doc_id = results["qdrant_id"] or "unknown"
            await self.redis.set(f"doc:{doc_id}", content, ex=self.CACHE_TTL_SECONDS)

            # Cache entities for this document
            await self._cache_entities(doc_id, content)

            # Cache keywords for faster graph queries
            keywords = metadata.get("keywords", [])
            if keywords:
                await self.redis.set(
                    f"keywords:{doc_id}",
                    ",".join(keywords[:10]) if isinstance(keywords, list) else str(keywords),
                    ex=self.CACHE_TTL_SECONDS
                )

            # Add to recent documents list
            await self._add_to_recent_cache(doc_id, content, metadata)
        except Exception:
            pass

        # Set status
        if results["qdrant_id"] and results["falkordb_id"]:
            results["status"] = "full"
        elif results["qdrant_id"] or results["falkordb_id"]:
            results["status"] = "partial"

        return results

    def _enrich_metadata(
        self,
        content: str,
        metadata: dict[str, Any],
        timestamp: datetime
    ) -> dict[str, Any]:
        """Enrich metadata with automatic extraction.

        Extracts:
        - timestamp (created_at, updated_at)
        - source_type (text, url, file, etc.)
        - keywords (top keywords from content)
        - entities (people, organizations, locations)
        - language (detected language)
        - content_hash (for deduplication)
        - word_count, char_count (content stats)
        """
        # Base timestamp
        metadata["created_at"] = timestamp.isoformat()
        metadata["updated_at"] = timestamp.isoformat()

        # Extract keywords
        keywords = self._extract_keywords(content)
        if keywords:
            metadata["keywords"] = keywords[:15]  # Limit to top 15

        # Extract entities (people, organizations, locations)
        entities = self._extract_named_entities(content)
        if entities:
            metadata["entities"] = entities
            # Add entity types as labels
            entity_labels = []
            if entities.get("people"):
                entity_labels.extend([f"Person:{p}" for p in entities["people"][:3]])
            if entities.get("organizations"):
                entity_labels.extend([f"Org:{o}" for o in entities["organizations"][:3]])
            if entities.get("locations"):
                entity_labels.extend([f"Location:{l}" for l in entities["locations"][:3]])
            if entity_labels:
                metadata["entity_labels"] = entity_labels

        # Detect language (simple heuristic)
        language = self._detect_language(content)
        if language:
            metadata["language"] = language

        # Source type detection
        if "source_type" not in metadata:
            metadata["source_type"] = self._infer_source_type(
                metadata.get("source", ""),
                content
            )

        # Content hash for deduplication
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        metadata["content_hash"] = content_hash

        # Content statistics
        metadata["word_count"] = len(content.split())
        metadata["char_count"] = len(content)

        return metadata

    def _extract_keywords(self, text: str, max_keywords: int = 15) -> list[str]:
        """Extract top keywords from text using frequency analysis.

        Args:
            text: Content to extract keywords from
            max_keywords: Maximum number of keywords to return

        Returns:
            List of top keywords
        """
        if not text:
            return []

        # Normalize text
        text_lower = text.lower()

        # Extract words (4+ characters)
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text_lower)

        # Filter stopwords and count frequencies
        filtered_words = [w for w in words if w not in STOPWORDS]

        # Get frequency count
        word_freq = Counter(filtered_words)

        # Return top keywords
        return [word for word, _ in word_freq.most_common(max_keywords)]

    def _extract_named_entities(self, content: str) -> dict[str, list[str]]:
        """Extract named entities from content.

        Simple pattern-based entity extraction:
        - People: Capitalized words following common name patterns
        - Organizations: Words like Inc, Corp, LLC, etc.
        - Locations: Capitalized words with common location indicators

        Args:
            content: Text to extract entities from

        Returns:
            Dict with entity types and their values
        """
        entities = {
            "people": [],
            "organizations": [],
            "locations": []
        }

        if not content:
            return entities

        # Organizations: detect company suffixes
        org_patterns = [
            r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+(Inc\.?|Corp\.?|LLC|Ltd\.?|GmbH|SA|SL)\b',
            r'\b(Google|Microsoft|Amazon|Apple|Meta|Twitter|OpenAI|Anthropic|Nvidia|Intel)\b',
        ]
        for pattern in org_patterns:
            matches = re.findall(pattern, content)
            entities["organizations"].extend([m[0] if isinstance(m, tuple) else m for m in matches[:3]])

        # Locations: common patterns
        location_patterns = [
            r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+(City|Country|State|Province|Region|Area)\b',
            r'\b(USA|UK|US|EU|Asia|Europe|America)\b',
        ]
        for pattern in location_patterns:
            matches = re.findall(pattern, content)
            entities["locations"].extend([m[0] if isinstance(m, tuple) else m for m in matches[:3]])

        # People: Capitalized names (simple heuristic - 2-3 capitalized words)
        people_pattern = r'\b([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'
        potential_names = re.findall(people_pattern, content)
        # Filter out common non-name patterns
        for name in potential_names[:5]:
            if name.lower() not in STOPWORDS and len(name) > 3:
                entities["people"].append(name)

        # Deduplicate
        entities["organizations"] = list(set(entities["organizations"]))[:3]
        entities["locations"] = list(set(entities["locations"]))[:3]
        entities["people"] = list(set(entities["people"]))[:3]

        return entities

    def _detect_language(self, content: str) -> str | None:
        """Detect language using simple character analysis.

        Args:
            content: Text to analyze

        Returns:
            Language code (es, en, etc.) or None
        """
        if not content:
            return None

        # Simple heuristics based on character patterns
        # Spanish indicators
        spanish_indicators = [' que ', ' de ', ' la ', ' el ', ' en ', ' con ', ' para ',
                              ' esta ', ' son ', ' los ', ' las ', ' una ', ' por ', ' mas ']
        spanish_count = sum(1 for ind in spanish_indicators if ind in content.lower())

        # English indicators
        english_indicators = [' the ', ' is ', ' are ', ' was ', ' were ', ' and ', ' or ',
                              ' with ', ' for ', ' that ', ' this ', ' have ', ' has ']
        english_count = sum(1 for ind in english_indicators if ind in content.lower())

        if spanish_count > english_count + 2:
            return "es"
        elif english_count > spanish_count + 2:
            return "en"

        return None

    def _infer_source_type(self, source: str, content: str) -> str:
        """Infer source type from source URL or content.

        Args:
            source: Source URL or path
            content: Content text

        Returns:
            Source type (url, file, text, api, etc.)
        """
        if not source:
            return "text"

        source_lower = source.lower()

        # URL patterns
        if source_lower.startswith(("http://", "https://")):
            if "github" in source_lower:
                return "github"
            elif "notion" in source_lower or "confluence" in source_lower:
                return "wiki"
            elif any(ext in source_lower for ext in [".pdf", ".doc", ".md"]):
                return "document"
            return "url"

        # File patterns
        if "/" in source or "\\" in source:
            if any(ext in source_lower for ext in [".pdf", ".docx", ".xlsx", ".pptx"]):
                return "document"
            elif any(ext in source_lower for ext in [".md", ".txt", ".rst"]):
                return "text_file"
            elif any(ext in source_lower for ext in [".py", ".js", ".ts", ".java", ".go"]):
                return "code"
            elif any(ext in source_lower for ext in [".json", ".yaml", ".yml", ".toml"]):
                return "config"
            return "file"

        return "text"

    async def _generate_embedding_with_context(
        self,
        content: str,
        metadata: dict[str, Any]
    ) -> list[float]:
        """Generate embedding with enhanced context.

        Enhances the embedding by adding contextual information:
        - Keywords from metadata
        - Entity types
        - Source type
        - Language

        Args:
            content: Original text content
            metadata: Enriched metadata

        Returns:
            Embedding vector
        """
        # Build enhanced context string
        context_parts = [content]

        # Add keywords for better semantic matching
        keywords = metadata.get("keywords", [])
        if keywords:
            keyword_context = " ".join(keywords[:5])
            context_parts.append(f"Keywords: {keyword_context}")

        # Add entity types
        entities = metadata.get("entities", {})
        if entities:
            entity_parts = []
            if entities.get("people"):
                entity_parts.extend(entities["people"][:2])
            if entities.get("organizations"):
                entity_parts.extend(entities["organizations"][:2])
            if entity_parts:
                context_parts.append(f"Entities: {', '.join(entity_parts)}")

        # Add language context
        language = metadata.get("language")
        if language:
            context_parts.append(f"Language: {language}")

        # Combine with separator
        enhanced_text = " | ".join(context_parts)

        # Generate embedding
        try:
            return await self.embedding.embed(enhanced_text)
        except Exception:
            # Fallback to original content
            return await self._generate_embedding(content)

    async def _add_to_recent_cache(
        self,
        doc_id: str,
        content: str,
        metadata: dict[str, Any]
    ) -> None:
        """Add document to recent cache list in Redis.

        Maintains a sorted list of recent documents for quick access.

        Args:
            doc_id: Document ID
            content: Document content
            metadata: Document metadata
        """
        try:
            # Get current timestamp as score
            import time
            score = time.time()

            # Add to sorted set with timestamp as score
            await self.redis._client.zadd(
                self.RECENT_CACHE_LIST,
                {doc_id: score}
            )

            # Trim to keep only recent items
            await self.redis._client.zremrangebyrank(
                self.RECENT_CACHE_LIST,
                0,
                -self.RECENT_CACHE_MAX - 1
            )

            # Store content
            await self.redis.set(
                f"{self.RECENT_CACHE_PREFIX}{doc_id}",
                content[:5000],  # Limit cached content size
                ex=self.CACHE_TTL_SECONDS
            )
        except Exception:
            pass

    async def query(self, query_text: str, limit: int = 5, use_cache: bool = True) -> dict[str, Any]:
        """Query memory system - searches both Qdrant (vector) and FalkorDB (graph).

        Args:
            query_text: Query string to search for
            limit: Maximum number of results per source
            use_cache: Whether to use cache for this query (default: True)

        Returns:
            dict with vector_results, graph_results, temporal_results, query, and cache_info
        """
        # Check cache first
        if use_cache:
            cached = await self._get_cached_result(query_text)
            if cached:
                # Add cache info
                cached["cache_hit"] = True
                return cached

        # 1. Generate embedding for query
        embedding = await self._generate_embedding(query_text)

        # 2. Search Qdrant (semantic/vector search)
        vector_results = []
        try:
            vector_results = await self.qdrant.search(embedding, limit)
        except Exception:
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

        results = {
            "vector_results": vector_results,
            "graph_results": graph_results,
            "temporal_results": temporal_results,
            "query": query_text,
            "cache_hit": False,
        }

        # Cache results and track query
        if use_cache:
            await self._cache_query_result(query_text, results, ttl=self.CACHE_TTL_SECONDS)
            await self._add_to_query_history(query_text)

            # Prefetch related documents in background
            await self.prefetch_related_documents(results)

        return results

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

    # === Query Cache Methods ===

    def _get_query_cache_key(self, query_text: str) -> str:
        """Generate cache key for query results."""
        normalized = query_text.lower().strip()
        query_hash = hashlib.md5(normalized.encode()).hexdigest()[:12]
        return f"query_cache:{query_hash}"

    def _get_query_hash_key(self, query_text: str) -> str:
        """Generate hash key for tracking query frequency."""
        normalized = query_text.lower().strip()
        return f"query_hash:{hashlib.md5(normalized.encode()).hexdigest()}"

    async def _cache_query_result(self, query_text: str, results: dict[str, Any], ttl: int = 3600):
        """Cache query results in Redis.

        Args:
            query_text: Original query text
            results: Query results to cache
            ttl: Time-to-live in seconds (default: 1 hour)
        """
        try:
            cache_key = self._get_query_cache_key(query_text)
            cache_data = {
                "query": query_text,
                "timestamp": datetime.now().isoformat(),
                "results": results,
            }
            await self.redis.set(cache_key, json.dumps(cache_data), ex=ttl)

            # Track query frequency for analytics
            hash_key = self._get_query_hash_key(query_text)
            await self.redis.redis.incr(hash_key)
            await self.redis.redis.expire(hash_key, 86400)
        except Exception:
            pass  # Cache failures are non-critical

    async def _get_cached_result(self, query_text: str) -> dict[str, Any] | None:
        """Get cached query result if available.

        Args:
            query_text: Query text to look up

        Returns:
            Cached results or None if not found/expired
        """
        try:
            cache_key = self._get_query_cache_key(query_text)
            cached = await self.redis.get(cache_key)
            if cached and isinstance(cached, dict):
                return cached.get("results")
            elif cached:
                try:
                    data = json.loads(cached) if isinstance(cached, str) else cached
                    return data.get("results") if isinstance(data, dict) else None
                except (json.JSONDecodeError, AttributeError):
                    return None
            return None
        except Exception:
            return None

    # === Query History Methods ===

    async def _add_to_query_history(self, query_text: str):
        """Add query to recent history (stores up to 100 recent queries)."""
        try:
            history_key = "query_history"
            history_data = await self.redis.get(history_key)
            history = json.loads(history_data) if history_data else []

            history.append({
                "query": query_text.lower().strip(),
                "timestamp": datetime.now().isoformat(),
            })
            history = history[-100:]  # Keep only last 100

            await self.redis.set(history_key, json.dumps(history), ex=86400)
        except Exception:
            pass

    async def get_query_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent query history."""
        try:
            history_key = "query_history"
            history_data = await self.redis.get(history_key)
            if history_data:
                history = json.loads(history_data) if isinstance(history_data, str) else history_data
                return history[-limit:]
            return []
        except Exception:
            return []

    async def get_frequent_queries(self, limit: int = 10) -> list[tuple[str, int]]:
        """Get most frequent queries."""
        try:
            keys = await self.redis.keys("query_hash:*")
            frequencies = []
            for key in keys:
                try:
                    count = await self.redis.redis.get(key)
                    if count:
                        query_hash = key.replace("query_hash:", "")
                        frequencies.append((query_hash, int(count)))
                except Exception:
                    continue
            frequencies.sort(key=lambda x: x[1], reverse=True)
            return frequencies[:limit]
        except Exception:
            return []

    # === Entity Extraction & Caching ===

    def _extract_entities(self, text: str) -> list[str]:
        """Extract entities from text (camelCase, paths, keywords)."""
        entities = set()

        # Extract camelCase words
        camel_pattern = re.findall(r'[a-z]+[A-Z][a-zA-Z]+', text)
        entities.update([e.lower() for e in camel_pattern])

        # Extract paths
        path_pattern = re.findall(r'/\w+(?:/\w+)*', text)
        entities.update([p.strip('/').replace('/', ':') for p in path_pattern])

        # Extract keywords
        keywords = re.findall(r'(?:class|function|method|var|const|import|export)\s+(\w+)', text)
        entities.update([k.lower() for k in keywords])

        # Extract capitalized words
        caps_pattern = re.findall(r'\b[A-Z][a-z]+(?:\w+)*\b', text)
        entities.update([w.lower() for w in caps_pattern if len(w) > 2])

        return list(entities)

    async def _cache_entities(self, doc_id: str, content: str, ttl: int = 86400):
        """Cache extracted entities from document."""
        try:
            entities = self._extract_entities(content)
            if entities:
                entity_key = f"doc_entities:{doc_id}"
                await self.redis.set(entity_key, json.dumps(entities), ex=ttl)

                # Create reverse index: entity -> doc_ids
                for entity in entities:
                    entity_doc_key = f"entity_docs:{entity}"
                    existing = await self.redis.get(entity_doc_key)
                    doc_ids = json.loads(existing) if existing else []
                    if doc_id not in doc_ids:
                        doc_ids.append(doc_id)
                        doc_ids = doc_ids[-100:]
                    await self.redis.set(entity_doc_key, json.dumps(doc_ids), ex=ttl)
        except Exception:
            pass

    async def get_entities_for_doc(self, doc_id: str) -> list[str]:
        """Get cached entities for a document."""
        try:
            entity_key = f"doc_entities:{doc_id}"
            entities = await self.redis.get(entity_key)
            if entities:
                return json.loads(entities) if isinstance(entities, str) else entities
            return []
        except Exception:
            return []

    async def get_related_docs(self, doc_id: str, limit: int = 5) -> list[str]:
        """Get documents related via entity sharing."""
        try:
            entities = await self.get_entities_for_doc(doc_id)
            related_docs = Counter()
            for entity in entities:
                entity_doc_key = f"entity_docs:{entity}"
                doc_ids = await self.redis.get(entity_doc_key)
                if doc_ids:
                    docs = json.loads(doc_ids) if isinstance(doc_ids, str) else doc_ids
                    for d in docs:
                        if d != doc_id:
                            related_docs[d] += 1
            related = sorted(related_docs.items(), key=lambda x: x[1], reverse=True)
            return [doc_id for doc_id, _ in related[:limit]]
        except Exception:
            return []

    # === Prefetching Methods ===

    async def prefetch_related_documents(self, results: dict[str, Any], limit: int = 3):
        """Prefetch and cache related documents for results."""
        try:
            doc_ids = []
            for r in results.get("vector_results", []):
                if doc_id := r.get("id"):
                    doc_ids.append(doc_id)
            for r in results.get("graph_results", []):
                if doc_id := r.get("id"):
                    doc_ids.append(doc_id)

            for doc_id in doc_ids[:10]:
                related = await self.get_related_docs(doc_id, limit=limit)
                for rel_id in related:
                    prefetch_key = f"prefetch:{rel_id}"
                    await self.redis.set(prefetch_key, "1", ex=1800)
        except Exception:
            pass

    # === Cache Warm-up Methods ===

    async def warmup_cache(self, queries: list[str] | None = None, limit: int = 3):
        """Warm up cache with common queries."""
        if queries is None:
            queries = COMMON_QUERIES

        for query in queries:
            cached = await self._get_cached_result(query)
            if cached:
                continue
            try:
                results = await self.query(query, limit=limit)
                await self._cache_query_result(query, results, ttl=7200)
            except Exception:
                pass

    async def invalidate_query_cache(self, query_text: str | None = None):
        """Invalidate query cache."""
        try:
            if query_text:
                cache_key = self._get_query_cache_key(query_text)
                await self.redis.delete(cache_key)
            else:
                keys = await self.redis.keys("query_cache:*")
                for key in keys:
                    await self.redis.delete(key)
        except Exception:
            pass

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        stats = {
            "query_cache_entries": 0,
            "entity_cache_entries": 0,
            "prefetch_entries": 0,
            "history_entries": 0,
            "frequent_queries": 0,
        }
        try:
            stats["query_cache_entries"] = len(await self.redis.keys("query_cache:*"))
            stats["entity_cache_entries"] = len(await self.redis.keys("doc_entities:*"))
            stats["prefetch_entries"] = len(await self.redis.keys("prefetch:*"))
            stats["history_entries"] = len(await self.redis.keys("query_history"))
            stats["frequent_queries"] = len(await self.redis.keys("query_hash:*"))
        except Exception:
            pass
        return stats

    async def close(self):
        """Close all connections."""
        await self.graphiti.close()
        await self.falkordb.close()
        await self.redis.close()
