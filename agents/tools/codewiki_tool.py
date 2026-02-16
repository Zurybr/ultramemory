"""CodeWiki tool for repository research."""

import asyncio
import shutil
from pathlib import Path
from typing import Any
from .base import BaseTool, ToolCategory, ToolResult


class CodeWikiTool(BaseTool):
    """Tool to query CodeWiki for repository documentation."""

    name = "codewiki"
    description = "Research GitHub repositories using CodeWiki AI documentation"
    category = ToolCategory.WEB
    requires_auth = False

    def __init__(self, codewiki_path: str | None = None):
        self.codewiki_path = codewiki_path or self._find_codewiki()

    def _find_codewiki(self) -> str | None:
        """Find codewiki executable."""
        # Check in skill directory
        skill_path = Path.home() / ".claude" / "skills" / "codewiki" / "codewiki"
        if skill_path.exists():
            return str(skill_path)

        # Check in PATH
        codewiki = shutil.which("codewiki")
        if codewiki:
            return codewiki

        # Check common locations
        paths = [
            Path.home() / ".local" / "bin" / "codewiki",
            Path("/usr/local/bin/codewiki"),
        ]
        for p in paths:
            if p.exists():
                return str(p)

        return None

    async def execute(
        self,
        action: str,
        repo: str | None = None,
        query: str | None = None,
    ) -> ToolResult:
        """Execute CodeWiki action.

        Args:
            action: One of: search, intro, info, ask, doc, full, featured
            repo: Repository in format "owner/repo"
            query: Query for search or ask actions
        """
        if not self.codewiki_path:
            return ToolResult(
                success=False,
                data=None,
                error="CodeWiki CLI not found. Install from skills/codewiki/"
            )

        try:
            # Build command
            cmd = [self.codewiki_path]

            if action == "search" and query:
                cmd.extend(["search", query])
            elif action == "featured":
                cmd.append("featured")
            elif action == "intro" and repo:
                cmd.extend(["intro", repo])
            elif action == "ask" and repo and query:
                cmd.extend(["ask", repo, query])
            elif action == "doc" and repo:
                cmd.extend(["doc", repo])
            elif action == "full" and repo:
                cmd.extend(["full", repo])
            elif action == "info" and repo:
                cmd.extend(["info", repo])
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Invalid action '{action}' or missing parameters"
                )

            result = await self._run_command(cmd)

            return ToolResult(
                success=True,
                data={"action": action, "repo": repo, "output": result},
                metadata={"action": action, "repo": repo, "query": query}
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"CodeWiki error: {str(e)}"
            )

    async def _run_command(self, cmd: list[str]) -> str:
        """Run command asynchronously."""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Command failed"
            raise Exception(error_msg)

        return stdout.decode()

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["search", "intro", "info", "ask", "doc", "full", "featured"],
                        "description": "Action to perform"
                    },
                    "repo": {
                        "type": "string",
                        "description": "Repository in format 'owner/repo'"
                    },
                    "query": {
                        "type": "string",
                        "description": "Query for search or ask actions"
                    }
                },
                "required": ["action"]
            }
        }


class MultiSourceResearchTool(BaseTool):
    """Tool that combines multiple research sources."""

    name = "multi_research"
    description = "Research across web (Tavily), repositories (CodeWiki), and memory"
    category = ToolCategory.SEARCH
    requires_auth = False

    def __init__(
        self,
        web_tool=None,
        codewiki_tool=None,
        memory_tool=None
    ):
        self.web_tool = web_tool
        self.codewiki_tool = codewiki_tool
        self.memory_tool = memory_tool

    async def execute(
        self,
        query: str,
        sources: list[str] | None = None,
        max_results: int = 5
    ) -> ToolResult:
        """Execute multi-source research.

        Args:
            query: Research query
            sources: List of sources ["web", "codewiki", "memory"]
            max_results: Max results per source
        """
        sources = sources or ["web", "memory"]
        results = {
            "query": query,
            "sources_queried": [],
            "web": [],
            "codewiki": [],
            "memory": [],
            "errors": [],
        }

        # Web search (Tavily)
        if "web" in sources and self.web_tool:
            results["sources_queried"].append("web")
            web_result = await self.web_tool.execute(query=query, max_results=max_results)
            if web_result.success:
                results["web"] = web_result.data.get("results", [])
                if web_result.data.get("answer"):
                    results["web_answer"] = web_result.data.get("answer")
            else:
                results["errors"].append(f"web: {web_result.error}")

        # CodeWiki search
        if "codewiki" in sources and self.codewiki_tool:
            results["sources_queried"].append("codewiki")
            cw_search = await self.codewiki_tool.execute(action="search", query=query)
            if cw_search.success:
                results["codewiki"] = self._parse_codewiki_results(cw_search.data.get("output", ""))
            else:
                results["errors"].append(f"codewiki: {cw_search.error}")

        # Memory search
        if "memory" in sources and self.memory_tool:
            results["sources_queried"].append("memory")
            mem_result = await self.memory_tool.execute(query=query, limit=max_results)
            if mem_result.success:
                results["memory"] = mem_result.data.get("vector_results", [])
            else:
                results["errors"].append(f"memory: {mem_result.error}")

        # Calculate totals
        total = sum(len(results.get(s, [])) for s in ["web", "codewiki", "memory"])

        return ToolResult(
            success=True,
            data=results,
            metadata={
                "sources": sources,
                "total_results": total,
                "errors_count": len(results["errors"])
            }
        )

    def _parse_codewiki_results(self, output: str) -> list[dict]:
        """Parse CodeWiki search output."""
        results = []
        for line in output.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Try to parse "owner/repo - description" format
            if " - " in line:
                parts = line.split(" - ", 1)
                repo = parts[0].strip()
                desc = parts[1].strip() if len(parts) > 1 else ""
                if "/" in repo:
                    results.append({"repo": repo, "description": desc})
            elif "/" in line:
                # Just repo name
                results.append({"repo": line, "description": ""})
        return results[:5]

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Research query"
                    },
                    "sources": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["web", "codewiki", "memory"]
                        },
                        "default": ["web", "memory"],
                        "description": "Sources to query"
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 5,
                        "description": "Max results per source"
                    }
                },
                "required": ["query"]
            }
        }
