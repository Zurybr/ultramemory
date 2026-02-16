"""Consolidator Agent - reorganizes and deduplicates memory."""

import re
from datetime import datetime
from typing import Any
from core.memory import MemorySystem


class ConsolidatorAgent:
    """Agent responsible for consolidating, analyzing and cleaning memory."""

    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system
        self.similarity_threshold = 0.95
        self.min_content_length = 10
        self.max_content_length = 100000

    async def consolidate(self) -> dict[str, Any]:
        """Run consolidation process.

        Returns:
            Report with actions taken
        """
        report = {
            "duplicates_removed": 0,
            "malformed_fixed": 0,
            "entities_merged": 0,
            "reindexed": 0,
            "errors": [],
        }

        try:
            # 1. Find and remove duplicates
            duplicates = await self._find_duplicates()
            for dup in duplicates:
                await self.memory.qdrant.delete(dup["id"])
            report["duplicates_removed"] = len(duplicates)

            # 2. Find and fix malformed entries
            malformed = await self._find_malformed()
            for entry in malformed.get("empty", []):
                await self.memory.qdrant.delete(entry["id"])
            for entry in malformed.get("too_short", []):
                await self.memory.qdrant.delete(entry["id"])
            report["malformed_fixed"] = len(malformed.get("empty", [])) + len(malformed.get("too_short", []))

            # 3. Merge related entities in graph
            merged = await self._merge_entities()
            report["entities_merged"] = merged

            # 4. Trigger graph consolidation
            try:
                await self.memory.graphiti.consolidate()
            except Exception:
                pass  # Optional service

            report["status"] = "success"

        except Exception as e:
            report["status"] = "error"
            report["errors"].append(str(e))

        return report

    async def analyze(self) -> dict[str, Any]:
        """Comprehensive memory analysis.

        Analyzes:
        - Duplicates (exact and near)
        - Malformed entries (empty, too short, encoding issues)
        - Missing metadata
        - Orphaned references
        - Content quality issues
        """
        all_docs = await self.memory.qdrant.get_all(limit=10000)
        total_docs = len(all_docs)

        # Initialize analysis results
        analysis = {
            "total_documents": total_docs,
            "issues": {},
            "quality_metrics": {},
            "recommendations": [],
        }

        # Track for duplicate detection
        seen_content = {}
        issues = {
            "duplicates": [],
            "empty_content": [],
            "too_short": [],
            "too_long": [],
            "missing_metadata": [],
            "encoding_issues": [],
            "low_quality": [],
        }

        # Quality metrics
        total_length = 0
        with_metadata = 0
        by_source = {}

        for doc in all_docs:
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            doc_id = doc.get("id", "")

            # Length tracking
            content_len = len(content)
            total_length += content_len

            # 1. Check for empty content
            if not content or not content.strip():
                issues["empty_content"].append({
                    "id": doc_id,
                    "reason": "Empty content",
                })
                continue

            # 2. Check for too short content
            if content_len < self.min_content_length:
                issues["too_short"].append({
                    "id": doc_id,
                    "length": content_len,
                    "preview": content[:30],
                })

            # 3. Check for too long content (might need re-chunking)
            if content_len > self.max_content_length:
                issues["too_long"].append({
                    "id": doc_id,
                    "length": content_len,
                })

            # 4. Check for duplicates
            content_hash = hash(content.strip().lower())
            if content_hash in seen_content:
                issues["duplicates"].append({
                    "id": doc_id,
                    "duplicate_of": seen_content[content_hash],
                    "preview": content[:50],
                })
            else:
                seen_content[content_hash] = doc_id

            # 5. Check for missing essential metadata
            essential_metadata = ["source", "chunk_index", "type"]
            missing = [k for k in essential_metadata if k not in metadata]
            if missing:
                issues["missing_metadata"].append({
                    "id": doc_id,
                    "missing_fields": missing,
                })
            else:
                with_metadata += 1

            # 6. Check for encoding issues (mojibake)
            if self._has_encoding_issues(content):
                issues["encoding_issues"].append({
                    "id": doc_id,
                    "preview": content[:50],
                })

            # 7. Check for low quality content
            quality_score = self._assess_quality(content)
            if quality_score < 0.3:
                issues["low_quality"].append({
                    "id": doc_id,
                    "score": quality_score,
                    "preview": content[:50],
                })

            # Track by source
            source = metadata.get("source", "unknown")
            by_source[source] = by_source.get(source, 0) + 1

        # Compile analysis
        analysis["issues"] = {
            "duplicates": {
                "count": len(issues["duplicates"]),
                "entries": issues["duplicates"][:10],  # Limit for display
            },
            "empty_content": {
                "count": len(issues["empty_content"]),
                "entries": issues["empty_content"][:10],
            },
            "too_short": {
                "count": len(issues["too_short"]),
                "entries": issues["too_short"][:10],
            },
            "too_long": {
                "count": len(issues["too_long"]),
                "entries": issues["too_long"][:10],
            },
            "missing_metadata": {
                "count": len(issues["missing_metadata"]),
                "entries": issues["missing_metadata"][:10],
            },
            "encoding_issues": {
                "count": len(issues["encoding_issues"]),
                "entries": issues["encoding_issues"][:10],
            },
            "low_quality": {
                "count": len(issues["low_quality"]),
                "entries": issues["low_quality"][:10],
            },
        }

        # Quality metrics
        analysis["quality_metrics"] = {
            "unique_content": len(seen_content),
            "avg_content_length": total_length / total_docs if total_docs > 0 else 0,
            "metadata_coverage": (with_metadata / total_docs * 100) if total_docs > 0 else 0,
            "sources": by_source,
            "health_score": self._calculate_health_score(total_docs, issues),
        }

        # Generate recommendations
        analysis["recommendations"] = self._generate_recommendations(analysis)

        return analysis

    def _has_encoding_issues(self, content: str) -> bool:
        """Detect potential encoding issues."""
        # Common mojibake patterns
        patterns = [
            r"Ã[^\x00-\x7F]",  # UTF-8 interpreted as Latin-1
            r"â€",  # Smart quotes gone wrong
            r"Ã¢â‚¬",  # Em dash issues
            r"\ufffd",  # Replacement character
        ]
        for pattern in patterns:
            if re.search(pattern, content):
                return True
        return False

    def _assess_quality(self, content: str) -> float:
        """Assess content quality (0-1 scale)."""
        if not content:
            return 0.0

        score = 1.0

        # Penalize very repetitive content
        words = content.split()
        if len(words) > 10:
            unique_words = len(set(w.lower() for w in words))
            repetition_ratio = unique_words / len(words)
            if repetition_ratio < 0.3:
                score *= 0.5

        # Penalize lack of structure
        has_punctuation = any(c in content for c in ".!?;:")
        if not has_punctuation:
            score *= 0.7

        # Penalize excessive special characters
        special_ratio = sum(1 for c in content if not c.isalnum() and not c.isspace()) / len(content)
        if special_ratio > 0.3:
            score *= 0.6

        return score

    def _calculate_health_score(self, total: int, issues: dict) -> float:
        """Calculate overall memory health score (0-100)."""
        if total == 0:
            return 100.0

        # Weight different issues
        penalty = 0
        penalty += len(issues["duplicates"]) * 2
        penalty += len(issues["empty_content"]) * 5
        penalty += len(issues["too_short"]) * 1
        penalty += len(issues["encoding_issues"]) * 3
        penalty += len(issues["low_quality"]) * 2

        max_penalty = total * 5
        health = max(0, 100 - (penalty / max_penalty * 100))

        return round(health, 1)

    def _generate_recommendations(self, analysis: dict) -> list[str]:
        """Generate actionable recommendations."""
        recs = []
        issues = analysis["issues"]
        metrics = analysis["quality_metrics"]

        if metrics["health_score"] >= 90:
            recs.append("✅ Memory is in excellent condition")
        elif metrics["health_score"] >= 70:
            recs.append("👍 Memory is in good condition, minor cleanup recommended")
        else:
            recs.append("⚠️ Memory needs attention")

        if issues["duplicates"]["count"] > 0:
            recs.append(f"🔄 Run consolidation to remove {issues['duplicates']['count']} duplicates")

        if issues["empty_content"]["count"] > 0:
            recs.append(f"🗑️ Remove {issues['empty_content']['count']} empty entries")

        if issues["too_short"]["count"] > 0:
            recs.append(f"📏 Review {issues['too_short']['count']} very short entries")

        if issues["encoding_issues"]["count"] > 0:
            recs.append(f"🔧 Fix {issues['encoding_issues']['count']} encoding issues")

        if issues["low_quality"]["count"] > 0:
            recs.append(f"📉 Consider removing {issues['low_quality']['count']} low quality entries")

        if metrics["metadata_coverage"] < 80:
            recs.append(f"🏷️ Improve metadata coverage ({metrics['metadata_coverage']:.0f}%)")

        if not recs:
            recs.append("✨ No issues found!")

        return recs

    async def _find_duplicates(self) -> list[dict[str, Any]]:
        """Find duplicate entries in memory."""
        duplicates = []
        seen_content = {}

        all_docs = await self.memory.qdrant.get_all(limit=10000)

        for doc in all_docs:
            content = doc.get("content", "")
            content_hash = hash(content.strip().lower())

            if content_hash in seen_content:
                duplicates.append({
                    "id": doc["id"],
                    "content": content[:50] + "..." if len(content) > 50 else content,
                    "duplicate_of": seen_content[content_hash],
                })
            else:
                seen_content[content_hash] = doc["id"]

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

    async def _merge_entities(self) -> int:
        """Merge related entities in the graph."""
        # Graph consolidation handles this internally
        return 0

    # === Insight Generation Methods ===

    async def generate_insights(self) -> dict[str, Any]:
        """Generate insights from memory connections.

        Analyzes relationships and generates actionable insights.
        """
        insights = {
            "generated_at": datetime.now().isoformat(),
            "insights": [],
            "patterns_found": 0,
        }

        try:
            # Get all documents
            all_docs = await self.memory.qdrant.get_all(limit=5000)

            if not all_docs:
                return insights

            # Find common topics (simple frequency analysis)
            topics = {}
            for doc in all_docs:
                content = doc.get("content", "")
                metadata = doc.get("metadata", {})

                # Extract tags if present
                tags = metadata.get("tags", [])
                for tag in tags:
                    topics[tag] = topics.get(tag, 0) + 1

            # Get top topics
            top_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:10]

            if top_topics:
                insights["patterns_found"] = len(top_topics)
                insights["insights"].append({
                    "type": "common_topics",
                    "description": "Most frequent topics in memory",
                    "data": [{"topic": t, "count": c} for t, c in top_topics],
                })

            # Find connected concepts (simple co-occurrence)
            if len(all_docs) > 10:
                # Sample some documents to find patterns
                sample = all_docs[:100]
                word_freq = {}

                for doc in sample:
                    content = doc.get("content", "").lower()
                    words = content.split()
                    unique_words = set(words)

                    for word in unique_words:
                        if len(word) > 5:  # Skip short words
                            word_freq[word] = word_freq.get(word, 0) + 1

                top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]

                if top_words:
                    insights["insights"].append({
                        "type": "key_concepts",
                        "description": "Most frequent significant terms",
                        "data": [{"term": w, "frequency": f} for w, f in top_words],
                    })

            # Save insights to memory
            insight_text = self._format_insights(insights)
            await self.memory.add(
                insight_text,
                metadata={
                    "type": "insight",
                    "generated_by": "consolidator",
                },
            )

            insights["saved_to_memory"] = True

        except Exception as e:
            insights["error"] = str(e)

        return insights

    def _format_insights(self, insights: dict) -> str:
        """Format insights as markdown."""
        lines = [
            "# Insights Generados",
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

            if insight["type"] == "common_topics":
                for item in insight["data"][:5]:
                    lines.append(f"- **{item['topic']}**: {item['count']} ocurrencias")
            elif insight["type"] == "key_concepts":
                for item in insight["data"][:10]:
                    lines.append(f"- {item['term']}: {item['frequency']} menciones")

            lines.append("")

        return "\n".join(lines)
