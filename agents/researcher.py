"""Enhanced Researcher Agent with multi-source research capabilities."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from core.memory import MemorySystem
from agents.tools.base import ToolResult
from agents.tools.web_search import WebSearchTool
from agents.tools.memory_tools import MemoryQueryTool, MemoryAddTool
from agents.tools.codewiki_tool import CodeWikiTool, MultiSourceResearchTool


# Research todo list configuration
RESEARCH_TODO_PATH = Path.home() / ".ulmemory" / "research" / "todo.md"
RESEARCH_OUTPUT_DIR = Path.home() / ".ulmemory" / "research" / "reports"

# Ensure directories exist
RESEARCH_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ResearchResult:
    """Structured research result from multiple sources."""
    query: str
    memory_results: list[dict[str, Any]] = field(default_factory=list)
    web_results: list[dict[str, Any]] = field(default_factory=list)
    codewiki_results: list[dict[str, Any]] = field(default_factory=list)
    web_answer: str | None = None
    sources: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total_results(self) -> int:
        return len(self.memory_results) + len(self.web_results) + len(self.codewiki_results)


class ResearcherAgent:
    """Enhanced researcher agent with web (Tavily), CodeWiki, and memory search."""

    def __init__(
        self,
        memory_system: MemorySystem,
        enable_web_search: bool = True,
        enable_codewiki: bool = True,
        tavily_api_key: str | None = None,
    ):
        self.memory = memory_system
        self.enable_web_search = enable_web_search
        self.enable_codewiki = enable_codewiki

        # Initialize individual tools
        self.memory_tool = MemoryQueryTool(memory_system)
        self.memory_add_tool = MemoryAddTool(memory_system)
        self.web_tool = WebSearchTool(api_key=tavily_api_key) if enable_web_search else None
        self.codewiki_tool = CodeWikiTool() if enable_codewiki else None

        # Initialize multi-source tool
        self.multi_tool = MultiSourceResearchTool(
            web_tool=self.web_tool,
            codewiki_tool=self.codewiki_tool,
            memory_tool=self.memory_tool,
        )

    async def query(self, query_text: str, limit: int = 5, use_cache: bool = True) -> dict[str, Any]:
        """Query memory system (legacy interface for backward compatibility).

        Args:
            query_text: The search query
            limit: Maximum number of results
            use_cache: Whether to use cache (default: True)

        Returns:
            Dict with query, results, total_found, cache_hit
        """
        result = await self.memory_tool.execute(query=query_text, limit=limit)
        if result.success:
            return {
                "query": query_text,
                "results": result.data.get("vector_results", []),
                "graph_results": result.data.get("graph_results", []),
                "temporal_results": result.data.get("temporal_results", []),
                "total_found": len(result.data.get("vector_results", [])),
                "cache_hit": result.data.get("cache_hit", False),
            }
        return {
            "query": query_text,
            "results": [],
            "graph_results": [],
            "temporal_results": [],
            "total_found": 0,
            "cache_hit": False,
            "error": result.error,
        }

    async def warmup_memory_cache(self, queries: list[str] | None = None):
        """Warm up memory cache with common queries.

        Args:
            queries: List of queries to pre-cache. Uses defaults if None
        """
        if self.memory.warmup_cache:
            await self.memory.warmup_cache(queries)

    async def get_query_stats(self) -> dict[str, Any]:
        """Get query and cache statistics."""
        stats = await self.memory.get_cache_stats()
        history = await self.memory.get_query_history(limit=10)
        frequent = await self.memory.get_frequent_queries(limit=10)
        return {
            "cache_stats": stats,
            "recent_queries": [h.get("query") for h in history],
            "frequent_query_hashes": [h[0] for h in frequent],
        }

    async def research(
        self,
        query: str,
        sources: list[str] | None = None,
        max_results_per_source: int = 5
    ) -> ResearchResult:
        """Comprehensive research across memory and web.

        Args:
            query: Research query
            sources: List of sources ["memory", "web", "codewiki"]. Default: all available
            max_results_per_source: Max results per source

        Returns:
            ResearchResult with combined findings from all sources
        """
        # Default to all available sources
        if sources is None:
            sources = ["memory"]
            if self.enable_web_search and self.web_tool and self.web_tool.api_key:
                sources.append("web")
            if self.enable_codewiki and self.codewiki_tool and self.codewiki_tool.codewiki_path:
                sources.append("codewiki")

        result = await self.multi_tool.execute(
            query=query,
            sources=sources,
            max_results=max_results_per_source
        )

        if result.success:
            data = result.data
            return ResearchResult(
                query=query,
                memory_results=data.get("memory", []),
                web_results=data.get("web", []),
                codewiki_results=data.get("codewiki", []),
                web_answer=data.get("web_answer"),
                sources=self._extract_all_sources(data),
                errors=data.get("errors", []),
            )

        return ResearchResult(
            query=query,
            errors=[result.error] if result.error else [],
        )

    def _extract_all_sources(self, data: dict) -> list[str]:
        """Extract all source URLs/references from results."""
        sources = []

        # Web sources
        for r in data.get("web", []):
            if url := r.get("url"):
                sources.append(url)

        # CodeWiki repos
        for r in data.get("codewiki", []):
            if repo := r.get("repo"):
                sources.append(f"https://github.com/{repo}")

        return sources

    async def deep_research(
        self,
        topic: str,
        sub_queries: list[str] | None = None,
        max_depth: int = 3,
        save_to_memory: bool = True
    ) -> dict[str, Any]:
        """Deep research with automatic query expansion.

        Args:
            topic: Main research topic
            sub_queries: Optional sub-queries to explore
            max_depth: Maximum depth of research (max sub-queries)
            save_to_memory: Save results to memory

        Returns:
            Comprehensive research report
        """
        # Generate sub-queries if not provided
        if not sub_queries:
            sub_queries = self._generate_sub_queries(topic)

        results = {
            "topic": topic,
            "main_research": None,
            "sub_research": [],
            "synthesis": None,
            "total_sources": 0,
        }

        # Main research
        main_result = await self.research(topic)
        results["main_research"] = {
            "memory_count": len(main_result.memory_results),
            "web_count": len(main_result.web_results),
            "codewiki_count": len(main_result.codewiki_results),
            "sources": main_result.sources,
            "web_answer": main_result.web_answer,
            "errors": main_result.errors,
        }
        results["total_sources"] += len(main_result.sources)

        # Sub-research
        for sub_q in sub_queries[:max_depth]:
            sub_result = await self.research(sub_q)
            results["sub_research"].append({
                "query": sub_q,
                "memory_count": len(sub_result.memory_results),
                "web_count": len(sub_result.web_results),
                "codewiki_count": len(sub_result.codewiki_results),
                "sources": sub_result.sources,
            })
            results["total_sources"] += len(sub_result.sources)

        # Save to memory if requested
        if save_to_memory:
            synthesis = self._create_synthesis(topic, results)
            await self.memory_add_tool.execute(
                content=synthesis,
                metadata={"type": "deep_research", "topic": topic}
            )
            results["synthesis_saved"] = True

        return results

    def _generate_sub_queries(self, topic: str) -> list[str]:
        """Generate sub-queries for deep research."""
        prefixes = [
            "what is",
            "how does",
            "best practices for",
            "latest developments in",
            "tutorials for",
            "examples of",
        ]
        return [f"{prefix} {topic}" for prefix in prefixes]

    def _create_synthesis(self, topic: str, results: dict) -> str:
        """Create synthesis markdown from results."""
        lines = [
            f"# Deep Research: {topic}",
            "",
            "## Overview",
            "",
            f"Total sources found: {results['total_sources']}",
            "",
            "## Main Research",
            "",
        ]

        if answer := results["main_research"].get("web_answer"):
            lines.append(f"**Answer:** {answer}")
            lines.append("")

        lines.append("### Sources")
        for source in results["main_research"].get("sources", []):
            lines.append(f"- {source}")

        lines.extend(["", "## Sub-Research Topics", ""])

        for sub in results.get("sub_research", []):
            lines.append(f"### {sub['query']}")
            lines.append(f"- Sources: {len(sub['sources'])}")
            lines.append("")

        return "\n".join(lines)

    async def query_by_time(self, query_text: str, time_range: str) -> dict[str, Any]:
        """Query with time-based context.

        Args:
            query_text: The search query
            time_range: Time range (e.g., "last week", "2024-01")

        Returns:
            Results within time context
        """
        # Search with time filter via Graphiti
        try:
            graph_results = await self.memory.graphiti.search(query_text, time_range=time_range)
            return {
                "query": query_text,
                "time_range": time_range,
                "results": graph_results,
            }
        except Exception as e:
            return {
                "query": query_text,
                "time_range": time_range,
                "results": [],
                "error": str(e),
            }

    # === Research Todo List Methods ===

    def load_todo_list(self) -> list[str]:
        """Load research todo list from file."""
        RESEARCH_TODO_PATH.parent.mkdir(parents=True, exist_ok=True)

        if not RESEARCH_TODO_PATH.exists():
            return []

        content = RESEARCH_TODO_PATH.read_text(encoding="utf-8")
        topics = []

        for line in content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("-"):
                topics.append(line)
            elif line.startswith("-"):
                # Also support - topic format
                topic = line.lstrip("- ").strip()
                if topic:
                    topics.append(topic)

        return topics

    def save_todo_list(self, topics: list[str]):
        """Save research todo list (removes first item as it's being processed)."""
        RESEARCH_TODO_PATH.parent.mkdir(parents=True, exist_ok=True)

        remaining = topics[1:]  # Remove first (being processed)
        content = "# Research Todo List\n\n" + "\n".join(f"- {t}" for t in remaining)

        RESEARCH_TODO_PATH.write_text(content, encoding="utf-8")

    async def research_with_sources(
        self,
        query: str,
        include_scientific: bool = True,
        include_github: bool = True,
    ) -> dict[str, Any]:
        """Research with specific sources.

        Args:
            query: Research query
            include_scientific: Include scientific papers (arXiv, etc)
            include_github: Include GitHub repositories

        Returns:
            Combined results from all sources
        """
        results = {
            "query": query,
            "sources_used": [],
            "web": [],
            "github": [],
            "scientific": [],
            "memory": [],
        }

        # Memory search
        mem_result = await self.memory_tool.execute(query=query, limit=10)
        if mem_result.success:
            results["memory"] = mem_result.data.get("vector_results", [])
            results["sources_used"].append("memory")

        # Web search
        if self.web_tool and self.web_tool.api_key:
            web_result = await self.web_tool.execute(
                query=query,
                max_results=10,
                search_depth="advanced"
            )
            if web_result.success:
                results["web"] = web_result.data.get("results", [])
                results["sources_used"].append("web")

        # GitHub search (via CodeWiki)
        if include_github and self.codewiki_tool:
            try:
                github_result = await self.codewiki_tool.execute(
                    action="search",
                    query=query,
                )
                if github_result.success:
                    results["github"] = github_result.data.get("results", [])
                    results["sources_used"].append("github")
            except Exception:
                pass  # Optional source

        return results
