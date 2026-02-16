"""Auto-Researcher Agent - automatic research on configured topics."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from core.memory import MemorySystem


class AutoResearcherAgent:
    """Agent that automatically researches configured topics."""

    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system
        self.http_client = httpx.AsyncClient(timeout=60.0)

    async def research(self, topics: list[str], output_dir: str = "./researches") -> dict[str, Any]:
        """Run research on given topics.

        Args:
            topics: List of topics to research
            output_dir: Directory to save research outputs

        Returns:
            Report with research results
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        results = []

        for topic in topics:
            try:
                # 1. Search for information (placeholder - implement with search API)
                info = await self._search_topic(topic)

                # 2. Save to file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{topic.replace(' ', '_')}.md"
                filepath = output_path / filename

                content = self._format_research(topic, info)
                filepath.write_text(content, encoding="utf-8")

                # 3. Add to memory
                await self.memory.add(
                    content,
                    metadata={
                        "type": "research",
                        "topic": topic,
                        "timestamp": timestamp,
                    },
                )

                results.append({"topic": topic, "status": "success", "file": str(filepath)})

            except Exception as e:
                results.append({"topic": topic, "status": "error", "error": str(e)})

        return {
            "status": "success",
            "topics_processed": len(topics),
            "results": results,
            "output_dir": str(output_path),
        }

    async def _search_topic(self, topic: str) -> dict[str, Any]:
        """Search for information on a topic.

        This is a placeholder. In production, integrate with:
        - Tavily, SerpAPI, or other search APIs
        - arXiv, PubMed for academic research
        """
        # Placeholder - returns mock data
        return {
            "summary": f"Research summary for {topic}",
            "key_findings": [
                "Finding 1",
                "Finding 2",
            ],
            "sources": [],
        }

    def _format_research(self, topic: str, info: dict[str, Any]) -> str:
        """Format research as markdown."""
        lines = [
            f"# Research: {topic}",
            "",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Summary",
            "",
            info.get("summary", "No summary available."),
            "",
            "## Key Findings",
            "",
        ]

        for finding in info.get("key_findings", []):
            lines.append(f"- {finding}")

        lines.extend([
            "",
            "## Sources",
            "",
        ])

        for source in info.get("sources", []):
            lines.append(f"- {source}")

        return "\n".join(lines)

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()
