"""FalkorDB client for graph operations."""

import re
import hashlib
from typing import Any
import redis


class FalkorDBClient:
    """Client for FalkorDB graph database.

    FalkorDB uses Redis protocol, so we connect via redis-py.
    """

    def __init__(self, host: str = "localhost", port: int = 6370, db: int = 0):
        self.host = host
        self.port = port
        self.db = db
        self._client = None

    def _get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True
            )
        return self._client

    async def execute(self, query: str) -> list[dict]:
        """Execute a Cypher query."""
        client = self._get_client()
        try:
            result = client.execute_command("GRAPH.QUERY", "default", query)
            if result:
                if len(result) >= 2:
                    header = result[0]
                    rows = result[1]
                    return [dict(zip(header, row)) for row in rows]
            return []
        except Exception:
            try:
                result = client.execute_command("GRAPH.QUERY", query)
                return result if result else []
            except Exception:
                return []

    async def add_node(
        self,
        entity_id: str,
        content: str,
        metadata: dict[str, Any],
        labels: list[str] | None = None
    ) -> bool:
        """Add a node to the graph with metadata."""
        try:
            # Skip binary content - can't store in graph
            if self._is_binary_content(content):
                # Still create node but with placeholder content
                content_preview = "[Binary content - not stored in graph]"
            else:
                # Clean content for graph storage (truncate if too long)
                # Remove control characters and escape properly
                clean_chars = []
                for char in content[:500]:
                    code = ord(char)
                    if code < 32 and code not in (9, 10, 13):  # Keep tab, newline, carriage return
                        clean_chars.append(' ')  # Replace control chars with space
                    elif code > 127:
                        clean_chars.append('?')  # Replace non-ASCII with ?
                    else:
                        clean_chars.append(char)
                content_preview = ''.join(clean_chars)
                content_preview = content_preview.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")

            # Extract labels from metadata or use defaults
            if labels is None:
                labels = metadata.get("labels", ["Document"])
            if isinstance(labels, str):
                labels = [labels]
            if not labels:
                labels = ["Document"]

            # Build Cypher query using MERGE instead of CREATE
            label_str = ":".join(labels)
            props = {
                "id": entity_id,
                "content": content_preview,
                "source": metadata.get("source", "unknown"),
                "type": metadata.get("type", "document"),
                "created_at": metadata.get("created_at", ""),
            }

            # Add extracted keywords for non-binary content
            keywords = []
            if not self._is_binary_content(content):
                keywords = self._extract_keywords(content)
            if keywords:
                props["keywords"] = ",".join(keywords[:10])

            # Build safe property string
            props_list = []
            for k, v in props.items():
                # Escape special characters
                v_str = str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
                props_list.append(f'{k}:"{v_str}"')
            props_str = ", ".join(props_list)

            query = f"MERGE (n:{label_str} {{{props_str}}})"
            result = await self.execute(query)
            return True
        except Exception:
            return False

    def _is_binary_content(self, content: str) -> bool:
        """Check if content appears to be binary."""
        if not content:
            return False

        # Check first 1000 characters for binary indicators
        sample = content[:1000]

        # Check for null bytes
        if '\\x00' in sample or '\\0' in sample:
            return True

        # Check for high proportion of non-printable/non-ASCII characters
        try:
            # Count non-ASCII and control characters
            non_printable = 0
            for char in sample:
                code = ord(char)
                # Control chars (0-31 except \t, \n, \r) and non-ASCII (>127)
                if code < 32 and code not in (9, 10, 13):  # not tab, newline, carriage return
                    non_printable += 1
                elif code > 127:
                    non_printable += 1

            # If more than 10% are non-printable, treat as binary
            if len(sample) > 0 and non_printable / len(sample) > 0.1:
                return True
        except Exception:
            pass

        # Check for common binary file signatures
        binary_headers = ['MZ', 'PK\\x03\\x04', '\\xff\\xd8\\xff', 'GIF87', 'GIF89', '%PDF', '\\x89PNG']
        for header in binary_headers:
            if sample.startswith(header):
                return True

        return False

    async def add_relationship(
        self,
        from_id: str,
        to_id: str,
        rel_type: str = "RELATED_TO",
        properties: dict | None = None
    ) -> bool:
        """Add a relationship between two nodes."""
        try:
            props = properties or {}
            props_str = ""
            if props:
                props_str = "{" + ", ".join(f'{k}:"{v}"' for k, v in props.items()) + "}"

            query = f"""
                MATCH (a {{id: '{from_id}'}}), (b {{id: '{to_id}'}})
                CREATE (a)-[r:{rel_type} {props_str}]->(b)
            """
            await self.execute(query)
            return True
        except Exception:
            return False

    async def find_similar_nodes(
        self,
        content: str,
        limit: int = 5
    ) -> list[dict]:
        """Find similar nodes based on keywords/content."""
        try:
            keywords = self._extract_keywords(content)
            if not keywords:
                return []

            # Search for nodes with matching keywords
            keyword_conditions = " OR ".join([f'n.keywords CONTAINS "{kw}"' for kw in keywords[:5]])
            query = f"""
                MATCH (n)
                WHERE {keyword_conditions}
                RETURN n.id as id, n.content as content, n.source as source, n.type as type
                LIMIT {limit}
            """
            results = await self.execute(query)
            return results
        except Exception:
            return []

    async def get_node(self, entity_id: str) -> dict | None:
        """Get a node by ID."""
        try:
            query = f"MATCH (n {{id: '{entity_id}'}}) RETURN n"
            results = await self.execute(query)
            return results[0] if results else None
        except Exception:
            return None

    async def get_node_relationships(self, entity_id: str) -> list[dict]:
        """Get all relationships for a node."""
        try:
            query = f"""
                MATCH (n {{id: '{entity_id}'}})-[r]->(m)
                RETURN type(r) as type, m.id as target, m.content as content
            """
            return await self.execute(query)
        except Exception:
            return []

    async def search_nodes(
        self,
        query_text: str,
        limit: int = 10
    ) -> list[dict]:
        """Search nodes by content or properties."""
        try:
            # Simple text search in content
            query = f"""
                MATCH (n)
                WHERE n.content CONTAINS '{query_text}' OR n.source CONTAINS '{query_text}'
                RETURN n.id as id, n.content as content, n.source as source, n.type as type
                LIMIT {limit}
            """
            return await self.execute(query)
        except Exception:
            return []

    async def get_all_nodes(self, limit: int = 1000) -> list[dict]:
        """Get all nodes in the graph."""
        try:
            query = f"""
                MATCH (n)
                RETURN n.id as id, n.content as content, n.source as source, n.type as type, labels(n) as labels
                LIMIT {limit}
            """
            return await self.execute(query)
        except Exception:
            return []

    async def get_stats(self) -> dict[str, Any]:
        """Get graph statistics."""
        try:
            result = await self.execute("MATCH (n) RETURN count(n) as count")
            nodes_count = result[0].get("count", 0) if result else 0

            result = await self.execute("MATCH ()-[r]->() RETURN count(r) as count")
            rels_count = result[0].get("count", 0) if result else 0

            result = await self.execute("CALL db.labels()")
            labels = [r.get("label") for r in result] if result else []

            result = await self.execute("CALL db.relationshipTypes()")
            rel_types = [r.get("relationshipType") for r in result] if result else []

            return {
                "total_nodes": nodes_count,
                "total_relations": rels_count,
                "labels": labels,
                "relationship_types": rel_types,
                "connected": True,
            }
        except Exception as e:
            return {
                "total_nodes": 0,
                "total_relations": 0,
                "labels": [],
                "relationship_types": [],
                "connected": False,
                "error": str(e),
            }

    async def get_orphaned_nodes(self) -> int:
        """Get count of orphaned nodes."""
        try:
            result = await self.execute("""
                MATCH (n)
                WHERE NOT (n)-[]->() AND NOT ()-[]->(n)
                RETURN count(n) as count
            """)
            return result[0].get("count", 0) if result else 0
        except Exception:
            return 0

    async def delete_orphaned_nodes(self, limit: int = 1000) -> int:
        """Delete orphaned nodes."""
        try:
            result = await self.execute(f"""
                MATCH (n)
                WHERE NOT (n)-[]->() AND NOT ()-[]->(n)
                WITH n LIMIT {limit}
                DETACH DELETE n
                RETURN count(n) as count
            """)
            return result[0].get("count", 0) if result else 0
        except Exception:
            return 0

    async def create_entity_links(self, threshold: float = 0.3) -> dict[str, Any]:
        """Create relationships between similar entities based on keywords."""
        created = 0
        try:
            # Get all nodes
            nodes = await self.get_all_nodes(limit=500)
            if len(nodes) < 2:
                return {"created": 0, "message": "Not enough nodes"}

            # Build keyword index
            keyword_index = {}
            for node in nodes:
                node_id = node.get("id", "")
                content = node.get("content", "")
                keywords = self._extract_keywords(content)

                for kw in keywords:
                    if kw not in keyword_index:
                        keyword_index[kw] = []
                    keyword_index[kw].append(node_id)

            # Create relationships between nodes with shared keywords
            seen_pairs = set()
            for kw, node_ids in keyword_index.items():
                for i, id1 in enumerate(node_ids):
                    for id2 in node_ids[i+1:]:
                        pair = tuple(sorted([id1, id2]))
                        if pair not in seen_pairs:
                            seen_pairs.add(pair)
                            success = await self.add_relationship(
                                id1, id2, "SIMILAR_TO",
                                {"keyword": kw, "weight": "0.5"}
                            )
                            if success:
                                created += 1

            return {"created": created, "total_nodes": len(nodes)}
        except Exception as e:
            return {"created": 0, "error": str(e)}

    async def health_check(self) -> bool:
        """Check if FalkorDB is accessible."""
        try:
            client = self._get_client()
            client.ping()
            return True
        except Exception:
            return False

    async def close(self):
        """Close connection."""
        if self._client:
            self._client.close()
            self._client = None

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from text."""
        # Simple keyword extraction
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        # Filter common words
        stopwords = {'this', 'that', 'with', 'from', 'have', 'been', 'were',
                     'they', 'their', 'which', 'would', 'could', 'should',
                     'there', 'where', 'when', 'what', 'more', 'also'}
        keywords = [w for w in words if w not in stopwords]
        # Return unique keywords
        return list(set(keywords))
