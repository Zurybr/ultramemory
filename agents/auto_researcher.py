"""Auto-Researcher Agent with real web search and CodeWiki capabilities."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from core.memory import MemorySystem
from agents.tools.web_search import WebSearchTool
from agents.tools.codewiki_tool import CodeWikiTool


class AutoResearcherAgent:
    """Agent that automatically researches topics with Tavily web search and CodeWiki."""

    def __init__(
        self,
        memory_system: MemorySystem,
        use_web: bool = True,
        use_codewiki: bool = True,
        tavily_api_key: str | None = None,
    ):
        self.memory = memory_system
        self.web_tool = WebSearchTool(api_key=tavily_api_key) if use_web else None
        self.codewiki_tool = CodeWikiTool() if use_codewiki else None

    async def research(
        self,
        topics: list[str],
        output_dir: str = "./researches",
        depth: str = "basic",
        sources: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run research on given topics.

        Args:
            topics: List of topics to research
            output_dir: Directory to save research outputs
            depth: "basic" or "deep" research (deep uses more API credits)
            sources: List of sources ["web", "codewiki"]. Default: all available
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Determine available sources
        sources = sources or []
        if self.web_tool and self.web_tool.api_key:
            sources.append("web")
        if self.codewiki_tool and self.codewiki_tool.codewiki_path:
            sources.append("codewiki")

        if not sources:
            sources = ["fallback"]

        results = []

        for topic in topics:
            try:
                info = await self._search_topic(topic, depth, sources)

                # Save to file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_topic = topic.replace(" ", "_").replace("/", "-")[:50]
                filename = f"{timestamp}_{safe_topic}.md"
                filepath = output_path / filename

                content = self._format_research(topic, info)
                filepath.write_text(content, encoding="utf-8")

                # Add to memory
                await self.memory.add(
                    content,
                    metadata={
                        "type": "research",
                        "topic": topic,
                        "timestamp": timestamp,
                        "source": "auto-researcher",
                        "sources_queried": sources,
                    },
                )

                results.append({
                    "topic": topic,
                    "status": "success",
                    "file": str(filepath),
                    "web_sources": len(info.get("web_sources", [])),
                    "codewiki_sources": len(info.get("codewiki_repos", [])),
                })

            except Exception as e:
                results.append({
                    "topic": topic,
                    "status": "error",
                    "error": str(e)
                })

        return {
            "status": "success",
            "topics_processed": len(topics),
            "results": results,
            "output_dir": str(output_path),
            "sources_used": sources,
        }

    async def _search_topic(
        self,
        topic: str,
        depth: str = "basic",
        sources: list[str] = None
    ) -> dict[str, Any]:
        """Search for information on a topic using available sources."""
        sources = sources or []
        info = {
            "summary": "",
            "key_findings": [],
            "web_sources": [],
            "codewiki_repos": [],
            "web_answer": None,
        }

        # Web search via Tavily
        if "web" in sources and self.web_tool:
            max_results = 10 if depth == "deep" else 5
            search_depth = "advanced" if depth == "deep" else "basic"

            result = await self.web_tool.execute(
                query=topic,
                max_results=max_results,
                search_depth=search_depth,
                include_answer=True
            )

            if result.success:
                data = result.data
                info["web_answer"] = data.get("answer")
                info["web_sources"] = [
                    {"url": r.get("url"), "title": r.get("title", "")}
                    for r in data.get("results", [])
                ]
                info["key_findings"].extend(
                    r.get("content", "")[:200]
                    for r in data.get("results", [])[:3]
                    if r.get("content")
                )

        # CodeWiki search for repositories
        if "codewiki" in sources and self.codewiki_tool:
            cw_result = await self.codewiki_tool.execute(action="search", query=topic)

            if cw_result.success:
                output = cw_result.data.get("output", "")
                info["codewiki_repos"] = self._parse_codewiki_output(output)

        # Fallback if no sources available
        if not info["summary"] and not info["web_sources"] and not info["codewiki_repos"]:
            info["summary"] = f"No external sources available for: {topic}"
            info["key_findings"] = ["Enable TAVILY_API_KEY for web search"]

        # Generate summary
        if info["web_answer"]:
            info["summary"] = info["web_answer"]
        elif info["key_findings"]:
            info["summary"] = info["key_findings"][0] if info["key_findings"] else ""

        return info

    def _parse_codewiki_output(self, output: str) -> list[dict]:
        """Parse CodeWiki search output into structured data."""
        repos = []
        for line in output.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "/" in line:
                parts = line.split(" - ", 1)
                repo = parts[0].strip()
                desc = parts[1].strip() if len(parts) > 1 else ""
                repos.append({"repo": repo, "description": desc})
        return repos[:5]

    def _format_research(self, topic: str, info: dict[str, Any]) -> str:
        """Format research as markdown."""
        lines = [
            f"# Research: {topic}",
            "",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Source:** Auto-Researcher (Tavily + CodeWiki)",
            "",
            "## Summary",
            "",
            info.get("summary") or "No summary available.",
            "",
        ]

        # Web answer if available
        if info.get("web_answer"):
            lines.extend([
                "## AI Answer",
                "",
                info["web_answer"],
                "",
            ])

        # Key findings
        if info.get("key_findings"):
            lines.extend(["## Key Findings", ""])
            for i, finding in enumerate(info["key_findings"][:5], 1):
                lines.append(f"{i}. {finding[:300]}")
            lines.append("")

        # Web sources
        if info.get("web_sources"):
            lines.extend(["## Web Sources", ""])
            for source in info["web_sources"]:
                url = source.get("url", "")
                title = source.get("title", url)
                lines.append(f"- [{title}]({url})")
            lines.append("")

        # CodeWiki repos
        if info.get("codewiki_repos"):
            lines.extend(["## Related Repositories (CodeWiki)", ""])
            for repo in info["codewiki_repos"]:
                name = repo.get("repo", "")
                desc = repo.get("description", "")
                lines.append(f"- [{name}](https://github.com/{name}) - {desc}")
            lines.append("")

        return "\n".join(lines)

    async def close(self):
        """Close any open connections."""
        pass
