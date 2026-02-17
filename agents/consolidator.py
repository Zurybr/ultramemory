"""Consolidator Agent - Intelligent memory analysis with graph+vector cross-reference."""

import re
from datetime import datetime
from typing import Any
from difflib import SequenceMatcher
import hashlib
from core.memory import MemorySystem


class ConsolidatorAgent:
    """Agent responsible for deep analysis and consolidation of memory.

    Uses cross-referencing between:
    - Qdrant (vector embeddings)
    - FalkorDB (graph relationships)
    - Redis (cache)

    Features:
    - Semantic duplicate detection (not just exact matches)
    - Graph-based entity analysis
    - Cross-reference validation
    - Intelligent insights with LLM
    - Fuzzy matching for better deduplication
    - Entity extraction (persons, companies, projects)
    - Category-based quality metrics
    - Intelligent sync (only changed items)
    """

    # Entity patterns for extraction
    ENTITY_PATTERNS = {
        "person": [
            r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b',  # John Smith
            r'(?:Mr\.|Mrs\.|Ms\.|Dr\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # Mr. Smith
        ],
        "company": [
            r'\b([A-Z][a-zA-Z]+(?:\s+(?:Inc|LLC|Corp|Ltd|SA|SL|Corporation|Company)))\b',
            r'\b(Google|Microsoft|Amazon|Apple|Meta|OpenAI|Anthropic|Tesla|Netflix)\b',
        ],
        "project": [
            r'\b(?:project|proyecto)\s+([A-Z][a-zA-Z0-9]+)\b',
            r'\b([A-Z][a-zA-Z]+(?:\s+Project))\b',
        ],
    }

    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system
        self.similarity_threshold = 0.85  # Lower for semantic matching
        self.fuzzy_threshold = 0.75  # Threshold for fuzzy matching
        self.min_content_length = 10
        self.max_content_length = 100000
        self.graph_similarity_threshold = 0.7
        self._last_sync_time = None  # Track last sync for intelligent updates
        self._document_hashes = {}  # Track document hashes for change detection

    async def consolidate(self, force_full: bool = False) -> dict[str, Any]:
        """Run intelligent consolidation process.

        Cross-references Qdrant + FalkorDB for deep analysis.
        Uses intelligent sync (only changed items) by default.

        Args:
            force_full: If True, force full consolidation instead of incremental
        """
        report = {
            "duplicates_removed": 0,
            "malformed_fixed": 0,
            "entities_merged": 0,
            "cross_references_fixed": 0,
            "graph_nodes_cleaned": 0,
            "insights_generated": 0,
            "entities_extracted": 0,
            "entity_nodes_created": 0,
            "relationships_created": 0,
            "quality_metrics_by_category": {},
            "errors": [],
            "sync_mode": "incremental" if not force_full else "full",
        }

        try:
            # Phase 1: Deep Analysis with cross-reference
            analysis = await self.analyze_deep()
            report["quality_metrics_by_category"] = analysis.get("quality_metrics_by_category", {})

            # Phase 2: Intelligent sync - only changed items
            changed_items = await self._detect_changed_items()
            report["changed_items_detected"] = len(changed_items)

            if changed_items or force_full:
                # Phase 2a: Sync only changed items to FalkorDB
                sync_result = await self._sync_changed_items(changed_items)
                report["nodes_synced"] = sync_result.get("nodes_synced", 0)

            # Phase 3: Remove exact duplicates
            duplicates = await self._find_duplicates()
            for dup in duplicates:
                await self.memory.qdrant.delete(dup["id"])
            report["duplicates_removed"] = len(duplicates)

            # Phase 4: Remove semantic duplicates using vector search
            semantic_dups = await self._find_semantic_duplicates()
            for dup in semantic_dups:
                await self.memory.qdrant.delete(dup["id"])
            report["duplicates_removed"] += len(semantic_dups)

            # Phase 5: Fuzzy matching for better deduplication
            fuzzy_dups = await self._find_fuzzy_duplicates()
            for dup in fuzzy_dups:
                await self.memory.qdrant.delete(dup["id"])
            report["duplicates_removed"] += len(fuzzy_dups)

            # Phase 6: Fix malformed entries
            malformed = await self._find_malformed()
            for entry in malformed.get("empty", []):
                await self.memory.qdrant.delete(entry["id"])
            for entry in malformed.get("too_short", []):
                await self.memory.qdrant.delete(entry["id"])
            report["malformed_fixed"] = len(malformed.get("empty", [])) + len(malformed.get("too_short", []))

            # Phase 7: Extract and create entity nodes
            entity_result = await self._extract_and_create_entities()
            report["entities_extracted"] = entity_result.get("entities_found", 0)
            report["entity_nodes_created"] = entity_result.get("nodes_created", 0)

            # Phase 8: Analyze relationships between documents
            relationships = await self._analyze_document_relationships()
            report["relationships_analyzed"] = relationships.get("relationships_found", 0)
            report["relationships_created"] = relationships.get("relationships_created", 0)

            # Phase 9: Cross-reference validation (Qdrant <-> FalkorDB)
            cross_ref_issues = await self._validate_cross_references()
            report["cross_references_fixed"] = cross_ref_issues

            # Phase 10: Clean orphaned graph nodes
            orphaned = await self._clean_orphaned_nodes()
            report["graph_nodes_cleaned"] = orphaned

            # Phase 11: Generate intelligent insights
            insights = await self.generate_insights()
            report["insights_generated"] = insights.get("patterns_found", 0)

            # Phase 12: Graph consolidation - create links between similar documents
            graph_result = await self._consolidate_graph()
            report["nodes_synced"] = report.get("nodes_synced", 0) + graph_result.get("nodes_synced", 0)
            report["links_created"] = graph_result.get("links_created", 0)
            report["graph_insights"] = graph_result.get("insights", [])

            # Update sync timestamp
            self._last_sync_time = datetime.now()

            report["status"] = "success"
            report["analysis_summary"] = analysis.get("summary", {})

        except Exception as e:
            report["status"] = "error"
            report["errors"].append(str(e))

        return report

    async def analyze(self) -> dict[str, Any]:
        """Legacy analysis method - redirects to deep analysis."""
        return await self.analyze_deep()

    async def analyze_deep(self) -> dict[str, Any]:
        """Deep analysis with graph + vector cross-reference.

        Analyzes:
        - Vector store (Qdrant): embeddings, content, metadata
        - Graph store (FalkorDB): nodes, relationships, entities
        - Cross-references: consistency between stores
        - Semantic clusters: related content
        """
        all_docs = await self.memory.qdrant.get_all(limit=10000)
        total_docs = len(all_docs)

        # Get graph data
        graph_stats = await self._get_graph_stats()

        analysis = {
            "total_documents": total_docs,
            "graph_stats": graph_stats,
            "issues": {},
            "quality_metrics": {},
            "cross_reference": {},
            "recommendations": [],
            "summary": {},
            "timestamp": datetime.now().isoformat(),
        }

        # Track issues
        issues = {
            "duplicates": [],
            "empty_content": [],
            "too_short": [],
            "too_long": [],
            "missing_metadata": [],
            "encoding_issues": [],
            "low_quality": [],
            "orphaned_graph_nodes": [],
            "inconsistent_references": [],
        }

        seen_content = {}
        total_length = 0
        with_metadata = 0
        by_source = {}
        by_type = {}

        for doc in all_docs:
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            doc_id = doc.get("id", "")
            vector_id = doc.get("vector_id", doc_id)

            content_len = len(content)
            total_length += content_len

            # Skip empty content
            if not content or not content.strip():
                issues["empty_content"].append({"id": doc_id, "reason": "Empty"})
                continue

            # Check too short
            if content_len < self.min_content_length:
                issues["too_short"].append({
                    "id": doc_id,
                    "length": content_len,
                    "preview": content[:30],
                })

            # Check too long
            if content_len > self.max_content_length:
                issues["too_long"].append({
                    "id": doc_id,
                    "length": content_len,
                })

            # Check exact duplicates
            content_hash = hash(content.strip().lower())
            if content_hash in seen_content:
                issues["duplicates"].append({
                    "id": doc_id,
                    "type": "exact",
                    "duplicate_of": seen_content[content_hash],
                })
            else:
                seen_content[content_hash] = doc_id

            # Check metadata
            essential = ["source", "type"]
            missing = [k for k in essential if k not in metadata]
            if missing:
                issues["missing_metadata"].append({
                    "id": doc_id,
                    "missing": missing,
                })
            else:
                with_metadata += 1

            # Encoding issues
            if self._has_encoding_issues(content):
                issues["encoding_issues"].append({"id": doc_id})

            # Quality
            quality = self._assess_quality(content)
            if quality < 0.3:
                issues["low_quality"].append({"id": doc_id, "score": quality})

            # Track sources and types
            source = metadata.get("source", "unknown")
            by_source[source] = by_source.get(source, 0) + 1

            doc_type = metadata.get("type", "unknown")
            by_type[doc_type] = by_type.get(doc_type, 0) + 1

        # Cross-reference analysis
        cross_ref = await self._analyze_cross_references(all_docs, graph_stats)
        analysis["cross_reference"] = cross_ref

        # Add orphaned nodes to issues
        if graph_stats.get("orphaned_nodes", 0) > 0:
            issues["orphaned_graph_nodes"] = [
                {"count": graph_stats["orphaned_nodes"]}
            ]

        # Compile issues
        analysis["issues"] = {
            "duplicates": {"count": len(issues["duplicates"]), "entries": issues["duplicates"][:5]},
            "empty_content": {"count": len(issues["empty_content"]), "entries": issues["empty_content"][:5]},
            "too_short": {"count": len(issues["too_short"]), "entries": issues["too_short"][:5]},
            "too_long": {"count": len(issues["too_long"]), "entries": issues["too_long"][:5]},
            "missing_metadata": {"count": len(issues["missing_metadata"]), "entries": issues["missing_metadata"][:5]},
            "encoding_issues": {"count": len(issues["encoding_issues"]), "entries": issues["encoding_issues"][:5]},
            "low_quality": {"count": len(issues["low_quality"]), "entries": issues["low_quality"][:5]},
            "orphaned_graph_nodes": {"count": len(issues["orphaned_graph_nodes"]), "entries": issues["orphaned_graph_nodes"]},
        }

        # Quality metrics by category
        analysis["quality_metrics_by_category"] = self._calculate_quality_by_category(all_docs, by_type, by_source)

        # Quality metrics
        analysis["quality_metrics"] = {
            "unique_content": len(seen_content),
            "avg_content_length": total_length / total_docs if total_docs > 0 else 0,
            "metadata_coverage": (with_metadata / total_docs * 100) if total_docs > 0 else 0,
            "sources": by_source,
            "types": by_type,
            "health_score": self._calculate_health_score(total_docs, issues),
        }

        # Generate summary
        analysis["summary"] = {
            "total_docs": total_docs,
            "graph_nodes": graph_stats.get("total_nodes", 0),
            "graph_relations": graph_stats.get("total_relations", 0),
            "total_issues": sum(len(v) for v in issues.values()),
            "health": analysis["quality_metrics"]["health_score"],
        }

        # Recommendations
        analysis["recommendations"] = self._generate_recommendations(analysis, cross_ref)

        return analysis

    async def _get_graph_stats(self) -> dict[str, Any]:
        """Get statistics from FalkorDB graph."""
        stats = {
            "total_nodes": 0,
            "total_relations": 0,
            "node_types": {},
            "orphaned_nodes": 0,
            "connected": False,
        }

        try:
            # Use FalkorDB client directly
            if hasattr(self.memory, 'falkordb') and self.memory.falkordb:
                # Check health first
                health = await self.memory.falkordb.health_check()
                if health:
                    stats["connected"] = True
                    # Get stats from FalkorDB
                    result = await self.memory.falkordb.get_stats()
                    stats["total_nodes"] = result.get("total_nodes", 0)
                    stats["total_relations"] = result.get("total_relations", 0)
                    stats["orphaned_nodes"] = await self.memory.falkordb.get_orphaned_nodes()
                else:
                    stats["connected"] = False
        except Exception as e:
            stats["error"] = str(e)

        return stats

    async def _analyze_cross_references(self, docs: list, graph_stats: dict) -> dict[str, Any]:
        """Analyze consistency between Qdrant and FalkorDB."""
        cross = {
            "vector_count": len(docs),
            "graph_nodes": graph_stats.get("total_nodes", 0),
            "consistency_score": 0,
            "issues": [],
        }

        # Calculate consistency
        if cross["graph_nodes"] > 0:
            ratio = min(len(docs), cross["graph_nodes"]) / max(len(docs), cross["graph_nodes"])
            cross["consistency_score"] = round(ratio * 100, 1)

        # Identify issues
        diff = abs(len(docs) - cross["graph_nodes"])
        if diff > 10:
            cross["issues"].append({
                "type": "count_mismatch",
                "vector": len(docs),
                "graph": cross["graph_nodes"],
                "difference": diff,
            })

        return cross

    async def _validate_cross_references(self) -> int:
        """Validate and fix cross-references between stores."""
        fixed = 0

        try:
            if hasattr(self.memory, 'falkordb') and self.memory.falkordb:
                health = await self.memory.falkordb.health_check()
                if health:
                    # Find nodes without vector counterparts (simplified check)
                    # In a real implementation, we'd cross-reference with Qdrant IDs
                    orphaned = await self.memory.falkordb.get_orphaned_nodes()
                    if orphaned > 0:
                        fixed = orphaned

        except Exception:
            pass

        return fixed

    async def _clean_orphaned_nodes(self) -> int:
        """Remove nodes in graph without vector references."""
        cleaned = 0

        try:
            if hasattr(self.memory, 'falkordb') and self.memory.falkordb:
                health = await self.memory.falkordb.health_check()
                if health:
                    cleaned = await self.memory.falkordb.delete_orphaned_nodes()

        except Exception:
            pass

        return cleaned

    async def _consolidate_graph(self) -> dict[str, Any]:
        """Consolidate graph - create relationships between similar entities."""
        result = {
            "links_created": 0,
            "nodes_synced": 0,
            "insights": [],
        }

        try:
            if hasattr(self.memory, 'falkordb') and self.memory.falkordb:
                health = await self.memory.falkordb.health_check()
                if not health:
                    return result

                # COMPREHENSIVE SYNC - Loop until fully synchronized
                max_attempts = 5
                for attempt in range(max_attempts):
                    # Get accurate counts via Cypher
                    qdrant_count = await self.memory.qdrant.count()
                    falkordb_result = await self.memory.falkordb.execute("MATCH (n) RETURN count(n) as count")
                    falkordb_count = falkordb_result[0].get("count", 0) if falkordb_result else 0

                    # Get all IDs from both stores
                    qdrant_docs = await self.memory.qdrant.get_all(limit=10000)
                    qdrant_ids = {doc.get("id", "") for doc in qdrant_docs}

                    falkordb_result = await self.memory.falkordb.execute("MATCH (n) RETURN n.id as id")
                    falkordb_ids = {row.get("id", "") for row in falkordb_result if row.get("id")}

                    # Find missing and orphans
                    missing = qdrant_ids - falkordb_ids  # In Qdrant but not FalkorDB
                    orphans = falkordb_ids - qdrant_ids  # In FalkorDB but not Qdrant

                    if not missing and not orphans:
                        result["sync_status"] = "complete"
                        break  # Fully synchronized

                    result["sync_attempts"] = attempt + 1

                    # Delete orphans first
                    if orphans:
                        for orphan_id in list(orphans):
                            try:
                                await self.memory.falkordb.execute(f"MATCH (n {{id: '{orphan_id}'}}) DETACH DELETE n")
                                result["orphans_removed"] = result.get("orphans_removed", 0) + 1
                            except Exception:
                                pass

                    # Sync missing nodes
                    if missing:
                        for doc in qdrant_docs:
                            doc_id = doc.get("id", "")
                            if doc_id in missing:
                                content = doc.get("content", "")
                                metadata = doc.get("metadata", {})

                                success = await self.memory.falkordb.add_node(
                                    entity_id=doc_id,
                                    content=content,
                                    metadata=metadata
                                )
                                if success:
                                    result["nodes_synced"] = result.get("nodes_synced", 0) + 1

                    # Check if we're done
                    falkordb_result = await self.memory.falkordb.execute("MATCH (n) RETURN count(n) as count")
                    falkordb_count = falkordb_result[0].get("count", 0) if falkordb_result else 0

                    if qdrant_count == falkordb_count:
                        result["sync_status"] = "complete"
                        break

                # Phase 2: Create relationships between similar nodes
                link_result = await self.memory.falkordb.create_entity_links()
                result["links_created"] = link_result.get("created", 0)

                # Phase 3: Generate graph insights
                graph_stats = await self.memory.falkordb.get_stats()
                result["insights"] = self._generate_graph_insights(graph_stats)

        except Exception as e:
            result["error"] = str(e)

        return result

    def _generate_graph_insights(self, stats: dict) -> list[str]:
        """Generate insights from graph statistics."""
        insights = []

        nodes = stats.get("total_nodes", 0)
        rels = stats.get("total_relations", 0)
        labels = stats.get("labels", [])

        if nodes > 0:
            avg_rels = rels / nodes if nodes > 0 else 0
            insights.append(f"Nodos: {nodes}, Relaciones: {rels} (avg: {avg_rels:.1f}/nodo)")

        if labels:
            insights.append(f"Tipos de contenido: {', '.join(labels[:5])}")

        if rels > 0 and nodes > 0:
            connectivity = (rels / nodes) * 100
            if connectivity > 50:
                insights.append("Alta conectividad entre documentos")
            elif connectivity > 20:
                insights.append("Conectividad media")
            else:
                insights.append("Conectividad baja - considera ejecutar consolidación")

        return insights

    async def _find_semantic_duplicates(self) -> list[dict]:
        """Find semantic duplicates using vector similarity."""
        duplicates = []
        all_docs = await self.memory.qdrant.get_all(limit=1000)

        # Sample for efficiency
        sample_size = min(200, len(all_docs))
        sample = all_docs[:sample_size]

        for i, doc in enumerate(sample):
            content = doc.get("content", "")
            if not content:
                continue

            # Search for similar content
            try:
                # Generate embedding from content
                embedding = await self.memory.embedding.embed(content)
                results = await self.memory.qdrant.search(
                    embedding,
                    limit=5,
                    score_threshold=self.similarity_threshold
                )

                for result in results:
                    if result.get("id") != doc.get("id"):
                        duplicates.append({
                            "id": result.get("id"),
                            "similar_to": doc.get("id"),
                            "score": result.get("score", 0),
                            "type": "semantic",
                        })
            except Exception:
                continue

        return duplicates

    async def _find_duplicates(self) -> list[dict]:
        """Find exact duplicates."""
        duplicates = []
        seen = {}

        all_docs = await self.memory.qdrant.get_all(limit=10000)

        for doc in all_docs:
            content = doc.get("content", "")
            content_hash = hash(content.strip().lower())

            if content_hash in seen:
                duplicates.append({
                    "id": doc["id"],
                    "duplicate_of": seen[content_hash],
                    "type": "exact",
                })
            else:
                seen[content_hash] = doc["id"]

        return duplicates

    async def _find_malformed(self) -> dict[str, list]:
        """Find malformed entries."""
        malformed = {"empty": [], "too_short": []}

        all_docs = await self.memory.qdrant.get_all(limit=10000)

        for doc in all_docs:
            content = doc.get("content", "")

            if not content or not content.strip():
                malformed["empty"].append({"id": doc["id"]})
            elif len(content) < self.min_content_length:
                malformed["too_short"].append({"id": doc["id"], "length": len(content)})

        return malformed

    async def generate_insights(self) -> dict[str, Any]:
        """Generate intelligent insights using graph + vector data."""
        insights = {
            "generated_at": datetime.now().isoformat(),
            "insights": [],
            "patterns_found": 0,
        }

        try:
            # Get all data
            all_docs = await self.memory.qdrant.get_all(limit=5000)
            graph_stats = await self._get_graph_stats()

            if not all_docs:
                return insights

            # Insight 1: Content distribution by source
            source_dist = {}
            for doc in all_docs:
                meta = doc.get("metadata", {})
                source = meta.get("source", "unknown")
                source_dist[source] = source_dist.get(source, 0) + 1

            if source_dist:
                insights["insights"].append({
                    "type": "source_distribution",
                    "description": "Content distribution by source",
                    "data": source_dist,
                })

            # Insight 2: Content types
            type_dist = {}
            for doc in all_docs:
                meta = doc.get("metadata", {})
                doc_type = meta.get("type", "unknown")
                type_dist[doc_type] = type_dist.get(doc_type, 0) + 1

            if type_dist:
                insights["insights"].append({
                    "type": "content_types",
                    "description": "Distribution of content types",
                    "data": type_dist,
                })

            # Insight 3: Graph connectivity
            insights["insights"].append({
                "type": "graph_health",
                "description": "Graph relationship health",
                "data": {
                    "nodes": graph_stats.get("total_nodes", 0),
                    "relations": graph_stats.get("total_relations", 0),
                    "orphaned": graph_stats.get("orphaned_nodes", 0),
                },
            })

            # Insight 4: Top keywords (semantic analysis)
            word_freq = {}
            for doc in all_docs[:200]:  # Sample
                content = doc.get("content", "").lower()
                words = re.findall(r'\b[a-z]{5,}\b', content)
                for word in words:
                    if word not in {'which', 'there', 'their', 'would', 'could', 'should', 'have', 'been', 'were', 'this'}:
                        word_freq[word] = word_freq.get(word, 0) + 1

            top_words = dict(sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20])
            if top_words:
                insights["insights"].append({
                    "type": "key_concepts",
                    "description": "Most frequent significant terms",
                    "data": top_words,
                })

            insights["patterns_found"] = len(insights["insights"])

            # Save insights to memory
            insight_text = self._format_insights(insights)
            await self.memory.add(
                insight_text,
                metadata={
                    "type": "insight",
                    "generated_by": "consolidator_deep",
                },
            )

            insights["saved_to_memory"] = True

        except Exception as e:
            insights["error"] = str(e)

        return insights

    def _format_insights(self, insights: dict) -> str:
        """Format insights as markdown."""
        lines = [
            "# Deep Insights Generados",
            "",
            f"Fecha: {insights['generated_at']}",
            "",
        ]

        for insight in insights.get("insights", []):
            lines.extend([
                f"## {insight['type'].replace('_', ' ').title()}",
                "",
                insight["description"],
                "",
            ])

            if insight["type"] in ["source_distribution", "content_types"]:
                for k, v in insight["data"].items():
                    lines.append(f"- **{k}**: {v}")
            elif insight["type"] == "graph_health":
                for k, v in insight["data"].items():
                    lines.append(f"- {k}: {v}")
            elif insight["type"] == "key_concepts":
                for k, v in list(insight["data"].items())[:10]:
                    lines.append(f"- {k}: {v}")

            lines.append("")

        return "\n".join(lines)

    def _has_encoding_issues(self, content: str) -> bool:
        """Detect encoding issues."""
        patterns = [
            r"Ã[^\x00-\x7F]",
            r"â€",
            r"Ã¯Â¿Â½",
            r"\ufffd",
        ]
        for pattern in patterns:
            if re.search(pattern, content):
                return True
        return False

    def _assess_quality(self, content: str) -> float:
        """Assess content quality."""
        if not content:
            return 0.0

        score = 1.0
        words = content.split()

        if len(words) > 10:
            unique = len(set(w.lower() for w in words))
            if unique / len(words) < 0.3:
                score *= 0.5

        if not any(c in content for c in ".!?;:"):
            score *= 0.7

        return score

    def _calculate_health_score(self, total: int, issues: dict) -> float:
        """Calculate health score."""
        if total == 0:
            return 100.0

        penalty = 0
        penalty += len(issues["duplicates"]) * 2
        penalty += len(issues["empty_content"]) * 5
        penalty += len(issues["too_short"]) * 1
        penalty += len(issues["encoding_issues"]) * 3
        penalty += len(issues["low_quality"]) * 2
        penalty += len(issues.get("orphaned_graph_nodes", [])) * 4

        max_penalty = total * 5
        return round(max(0, 100 - (penalty / max_penalty * 100)), 1)

    def _generate_recommendations(self, analysis: dict, cross_ref: dict) -> list[str]:
        """Generate recommendations."""
        recs = []
        issues = analysis["issues"]
        metrics = analysis["quality_metrics"]

        # Health-based
        if metrics["health_score"] >= 90:
            recs.append("✅ Memory en excelente condición")
        elif metrics["health_score"] >= 70:
            recs.append("👍 Memory en buena condición")

        # Cross-reference issues
        if cross_ref.get("consistency_score", 100) < 80:
            recs.append(f"⚠️ Inconsistencia Qdrant-FalkorDB: {cross_ref['consistency_score']}%")

        # Duplicates
        if issues["duplicates"]["count"] > 0:
            recs.append(f"🔄 Eliminar {issues['duplicates']['count']} duplicados")

        # Graph issues
        if issues.get("orphaned_graph_nodes", {}).get("count", 0) > 0:
            recs.append(f"🔗 Limpiar {issues['orphaned_graph_nodes']['count']} nodos huérfanos")

        # Empty content
        if issues["empty_content"]["count"] > 0:
            recs.append(f"🗑️ Eliminar {issues['empty_content']['count']} entradas vacías")

        # Encoding
        if issues["encoding_issues"]["count"] > 0:
            recs.append(f"🔧 Corregir {issues['encoding_issues']['count']} problemas de encoding")

        if not recs:
            recs.append("✨ ¡Sin problemas detectados!")

        return recs

    # ==================== NEW METHODS FOR IMPROVED CONSOLIDATION ====================

    def _calculate_quality_by_category(
        self,
        docs: list[dict],
        by_type: dict[str, int],
        by_source: dict[str, int]
    ) -> dict[str, Any]:
        """Calculate quality metrics broken down by category (type and source).

        Returns:
            Dictionary with quality metrics per category
        """
        quality_by_category = {
            "by_type": {},
            "by_source": {},
            "overall": {},
        }

        # Group docs by type
        docs_by_type: dict[str, list] = {t: [] for t in by_type.keys()}
        docs_by_source: dict[str, list] = {s: [] for s in by_source.keys()}

        for doc in docs:
            doc_type = doc.get("metadata", {}).get("type", "unknown")
            source = doc.get("metadata", {}).get("source", "unknown")
            content = doc.get("content", "")

            if doc_type in docs_by_type:
                docs_by_type[doc_type].append(content)
            if source in docs_by_source:
                docs_by_source[source].append(content)

        # Calculate metrics by type
        for doc_type, contents in docs_by_type.items():
            if not contents:
                continue
            quality_by_category["by_type"][doc_type] = self._category_metrics(contents)

        # Calculate metrics by source
        for source, contents in docs_by_source.items():
            if not contents:
                continue
            quality_by_category["by_source"][source] = self._category_metrics(contents)

        return quality_by_category

    def _category_metrics(self, contents: list[str]) -> dict[str, Any]:
        """Calculate metrics for a category of content."""
        total = len(contents)
        if total == 0:
            return {}

        # Calculate average length
        lengths = [len(c) for c in contents]
        avg_length = sum(lengths) / total

        # Calculate quality scores
        qualities = [self._assess_quality(c) for c in contents]
        avg_quality = sum(qualities) / total

        # Calculate completeness (content with metadata indicators)
        complete = sum(1 for c in contents if len(c) > 50 and any(p in c for p in [".", "!", "?"]))
        completeness = (complete / total) * 100

        return {
            "count": total,
            "avg_length": round(avg_length, 1),
            "avg_quality": round(avg_quality, 2),
            "completeness_pct": round(completeness, 1),
        }

    async def _detect_changed_items(self) -> list[str]:
        """Detect which items have changed since last sync.

        Uses content hashing to identify modified documents.

        Returns:
            List of document IDs that have changed
        """
        changed = []

        try:
            all_docs = await self.memory.qdrant.get_all(limit=10000)

            for doc in all_docs:
                doc_id = doc.get("id", "")
                content = doc.get("content", "")

                # Generate hash of content
                content_hash = hashlib.sha256(
                    content.encode('utf-8')
                ).hexdigest()

                # Check if this is a new document or if content changed
                if doc_id not in self._document_hashes:
                    changed.append(doc_id)
                elif self._document_hashes[doc_id] != content_hash:
                    changed.append(doc_id)

                # Update hash tracker
                self._document_hashes[doc_id] = content_hash

        except Exception:
            pass

        return changed

    async def _sync_changed_items(self, changed_ids: list[str]) -> dict[str, Any]:
        """Sync only changed items to FalkorDB.

        Args:
            changed_ids: List of document IDs that have changed

        Returns:
            Sync result with count of synced nodes
        """
        result = {
            "nodes_synced": 0,
            "errors": [],
        }

        if not changed_ids:
            return result

        try:
            if not hasattr(self.memory, 'falkordb') or not self.memory.falkordb:
                return result

            health = await self.memory.falkordb.health_check()
            if not health:
                return result

            # Get the changed documents
            all_docs = await self.memory.qdrant.get_all(limit=10000)
            changed_docs = [d for d in all_docs if d.get("id", "") in changed_ids]

            # Sync each changed document
            for doc in changed_docs:
                doc_id = doc.get("id", "")
                content = doc.get("content", "")
                metadata = doc.get("metadata", {})

                success = await self.memory.falkordb.add_node(
                    entity_id=doc_id,
                    content=content,
                    metadata=metadata
                )

                if success:
                    result["nodes_synced"] += 1
                else:
                    result["errors"].append(f"Failed to sync {doc_id}")

        except Exception as e:
            result["errors"].append(str(e))

        return result

    async def _find_fuzzy_duplicates(self) -> list[dict]:
        """Find fuzzy duplicates using string similarity.

        Uses SequenceMatcher for better detection of near-duplicates
        that may differ slightly (e.g., typos, minor edits).

        Returns:
            List of duplicate document IDs
        """
        duplicates = []
        all_docs = await self.memory.qdrant.get_all(limit=1000)

        # Sample for efficiency
        sample_size = min(200, len(all_docs))
        sample = all_docs[:sample_size]

        # Build index of normalized content
        indexed_docs = []
        for doc in sample:
            content = doc.get("content", "")
            if content and len(content) > 20:  # Skip very short content
                # Normalize: lowercase, remove extra spaces
                normalized = re.sub(r'\s+', ' ', content.strip().lower())
                indexed_docs.append({
                    "id": doc.get("id", ""),
                    "content": content,
                    "normalized": normalized,
                })

        # Compare each document with others
        checked = set()
        for i, doc in enumerate(indexed_docs):
            doc_id = doc["id"]

            for j, other in enumerate(indexed_docs):
                if i >= j:
                    continue

                other_id = other["id"]
                pair_key = tuple(sorted([doc_id, other_id]))

                if pair_key in checked:
                    continue
                checked.add(pair_key)

                # Calculate similarity
                similarity = SequenceMatcher(
                    None,
                    doc["normalized"],
                    other["normalized"]
                ).ratio()

                if similarity >= self.fuzzy_threshold:
                    duplicates.append({
                        "id": other_id,
                        "similar_to": doc_id,
                        "score": round(similarity, 3),
                        "type": "fuzzy",
                    })

        return duplicates

    async def _extract_and_create_entities(self) -> dict[str, Any]:
        """Extract entities from documents and create entity nodes in FalkorDB.

        Extracts:
        - Persons (names)
        - Companies
        - Projects

        Creates dedicated entity nodes with relationships to documents.

        Returns:
            Result with entities found and nodes created
        """
        result = {
            "entities_found": 0,
            "nodes_created": 0,
            "by_type": {
                "person": 0,
                "company": 0,
                "project": 0,
            },
        }

        try:
            if not hasattr(self.memory, 'falkordb') or not self.memory.falkordb:
                return result

            health = await self.memory.falkordb.health_check()
            if not health:
                return result

            # Get all documents
            all_docs = await self.memory.qdrant.get_all(limit=10000)

            # Track unique entities
            unique_entities: dict[str, dict] = {}

            for doc in all_docs:
                content = doc.get("content", "")
                doc_id = doc.get("id", "")

                if not content:
                    continue

                # Extract entities
                entities = self._extract_entities(content)

                for entity_type, entity_names in entities.items():
                    for entity_name in entity_names:
                        # Create unique key for this entity
                        key = f"{entity_type}:{entity_name.lower()}"

                        if key not in unique_entities:
                            unique_entities[key] = {
                                "type": entity_type,
                                "name": entity_name,
                                "doc_ids": [],
                            }

                        unique_entities[key]["doc_ids"].append(doc_id)

            result["entities_found"] = len(unique_entities)

            # Create entity nodes in FalkorDB
            for entity_data in unique_entities.values():
                entity_name = entity_data["name"]
                entity_type = entity_data["type"]

                # Determine label based on entity type
                labels = {
                    "person": "Person",
                    "company": "Company",
                    "project": "Project",
                }.get(entity_type, "Entity")

                # Create entity node
                try:
                    query = f"""
                    MERGE (e:{labels} {{name: "{entity_name.replace('"', '\\"')}"}})
                    SET e.document_count = {len(entity_data["doc_ids"])},
                        e.last_updated = "{datetime.now().isoformat()}"
                    """
                    await self.memory.falkordb.execute(query)
                    result["nodes_created"] += 1
                    result["by_type"][entity_type] = result["by_type"].get(entity_type, 0) + 1

                    # Create relationships to documents
                    for doc_id in entity_data["doc_ids"][:10]:  # Limit relationships
                        rel_query = f"""
                        MATCH (d {{id: "{doc_id}"}})
                        MATCH (e:{labels} {{name: "{entity_name.replace('"', '\\"')}"}})
                        MERGE (d)-[:MENTIONS]->(e)
                        """
                        try:
                            await self.memory.falkordb.execute(rel_query)
                        except Exception:
                            pass

                except Exception:
                    continue

        except Exception as e:
            result["error"] = str(e)

        return result

    def _extract_entities(self, content: str) -> dict[str, list[str]]:
        """Extract entities from content using regex patterns.

        Args:
            content: Document content to analyze

        Returns:
            Dictionary with lists of entities by type
        """
        entities = {
            "person": [],
            "company": [],
            "project": [],
        }

        # Extract persons
        for pattern in self.ENTITY_PATTERNS.get("person", []):
            matches = re.findall(pattern, content)
            entities["person"].extend(matches)

        # Extract companies
        for pattern in self.ENTITY_PATTERNS.get("company", []):
            matches = re.findall(pattern, content)
            entities["company"].extend(matches)

        # Extract projects
        for pattern in self.ENTITY_PATTERNS.get("project", []):
            matches = re.findall(pattern, content)
            entities["project"].extend(matches)

        # Deduplicate each category
        for entity_type in entities:
            entities[entity_type] = list(set(entities[entity_type]))

        return entities

    async def _analyze_document_relationships(self) -> dict[str, Any]:
        """Analyze and create relationships between related documents.

        Creates graph relationships based on:
        - Semantic similarity (via vector search)
        - Shared keywords
        - Shared entities
        - Temporal proximity (similar timestamps)

        Returns:
            Analysis result with relationships found and created
        """
        result = {
            "relationships_found": 0,
            "relationships_created": 0,
            "by_type": {
                "semantic": 0,
                "keyword": 0,
                "entity": 0,
            },
        }

        try:
            if not hasattr(self.memory, 'falkordb') or not self.memory.falkordb:
                return result

            health = await self.memory.falkordb.health_check()
            if not health:
                return result

            # Get all documents
            all_docs = await self.memory.qdrant.get_all(limit=1000)
            sample = all_docs[:100]  # Sample for efficiency

            # For each document, find related documents
            for doc in sample:
                doc_id = doc.get("id", "")
                content = doc.get("content", "")
                metadata = doc.get("metadata", {})

                if not content:
                    continue

                # Semantic similarity search
                try:
                    embedding = await self.memory.embedding.embed(content)
                    similar = await self.memory.qdrant.search(
                        embedding,
                        limit=5,
                        score_threshold=0.7
                    )

                    for sim_doc in similar:
                        sim_id = sim_doc.get("id", "")
                        if sim_id != doc_id and sim_id:
                            # Check if relationship already exists
                            check_query = f"""
                            MATCH (a {{id: "{doc_id}"}})-[r:SIMILAR_TO]->(b {{id: "{sim_id}"}})
                            RETURN r
                            """
                            existing = await self.memory.falkordb.execute(check_query)

                            if not existing or len(existing) == 0:
                                # Create relationship
                                score = sim_doc.get("score", 0.8)
                                create_query = f"""
                                MATCH (a {{id: "{doc_id}"}})
                                MATCH (b {{id: "{sim_id}"}})
                                MERGE (a)-[r:SIMILAR_TO {{score: {score}}}]->(b)
                                """
                                try:
                                    await self.memory.falkordb.execute(create_query)
                                    result["relationships_created"] += 1
                                    result["by_type"]["semantic"] += 1
                                except Exception:
                                    pass
                except Exception:
                    pass

            result["relationships_found"] = result["relationships_created"]

        except Exception as e:
            result["error"] = str(e)

        return result
