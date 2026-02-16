# Ultramemory Agent Enhancement Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enhance Ultramemory agents with Claude Code skills integration, web research capabilities, and improved CLI management.

**Architecture:** Plugin-based tool system for agents, integration with web search APIs (Tavily), enhanced scheduler with full CRUD, and skill-based configuration.

**Tech Stack:** Python 3.11+, Click, httpx, Tavily API, async/await patterns

---

## Phase 1: Core Tool System for Agents

### Task 1.1: Create Base Tool Interface

**Files:**
- Create: `agents/tools/__init__.py`
- Create: `agents/tools/base.py`
- Create: `agents/tools/registry.py`

**Step 1: Write the tool base module**

```python
# agents/tools/base.py
"""Base tool interface for agent capabilities."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class ToolCategory(Enum):
    """Categories of tools available to agents."""
    SEARCH = "search"
    MEMORY = "memory"
    WEB = "web"
    SKILL = "skill"
    LLM = "llm"
    UTILITY = "utility"


@dataclass
class ToolResult:
    """Result from tool execution."""
    success: bool
    data: Any
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    """Abstract base class for all agent tools."""

    name: str = "base_tool"
    description: str = "Base tool class"
    category: ToolCategory = ToolCategory.UTILITY
    requires_auth: bool = False

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass

    @abstractmethod
    def get_schema(self) -> dict[str, Any]:
        """Return JSON schema for tool parameters."""
        pass

    def validate_params(self, **kwargs) -> bool:
        """Validate parameters against schema."""
        return True
```

**Step 2: Write the tool registry**

```python
# agents/tools/registry.py
"""Tool registry for managing available tools."""

from typing import Any
from .base import BaseTool, ToolCategory


class ToolRegistry:
    """Registry for all available tools."""

    _instance = None
    _tools: dict[str, BaseTool] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self, category: ToolCategory | None = None) -> list[BaseTool]:
        """List all tools, optionally filtered by category."""
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return tools

    def get_schemas(self) -> list[dict[str, Any]]:
        """Get schemas for all tools."""
        return [t.get_schema() for t in self._tools.values()]


# Global registry
registry = ToolRegistry()
```

**Step 3: Create the __init__.py**

```python
# agents/tools/__init__.py
"""Agent tools package."""

from .base import BaseTool, ToolCategory, ToolResult
from .registry import ToolRegistry, registry

__all__ = ["BaseTool", "ToolCategory", "ToolResult", "ToolRegistry", "registry"]
```

**Step 4: Verify module imports**

Run: `cd /home/zurybr/workspace/ultramemory && python -c "from agents.tools import registry; print('OK')"`
Expected: `OK`

---

### Task 1.2: Create Web Search Tool (Tavily Integration)

**Files:**
- Create: `agents/tools/web_search.py`
- Modify: `agents/tools/__init__.py`

**Step 1: Write the web search tool**

```python
# agents/tools/web_search.py
"""Web search tool using Tavily API."""

import os
from typing import Any
import httpx
from .base import BaseTool, ToolCategory, ToolResult


class WebSearchTool(BaseTool):
    """Web search tool using Tavily API."""

    name = "web_search"
    description = "Search the web for information using Tavily API"
    category = ToolCategory.WEB
    requires_auth = True

    def __init__(self):
        self.api_key = os.getenv("TAVILY_API_KEY")
        self.base_url = "https://api.tavily.com"

    async def execute(
        self,
        query: str,
        max_results: int = 5,
        include_raw_content: bool = False,
        search_depth: str = "basic"
    ) -> ToolResult:
        """Execute web search.

        Args:
            query: Search query
            max_results: Maximum number of results
            include_raw_content: Include raw HTML content
            search_depth: "basic" or "advanced"
        """
        if not self.api_key:
            return ToolResult(
                success=False,
                data=None,
                error="TAVILY_API_KEY not set. Get one at https://tavily.com"
            )

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/search",
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "max_results": max_results,
                        "include_raw_content": include_raw_content,
                        "search_depth": search_depth,
                    }
                )
                response.raise_for_status()
                data = response.json()

                return ToolResult(
                    success=True,
                    data=data,
                    metadata={"query": query, "results_count": len(data.get("results", []))}
                )
            except httpx.HTTPError as e:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"HTTP error: {str(e)}"
                )

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results",
                        "default": 5
                    },
                    "search_depth": {
                        "type": "string",
                        "enum": ["basic", "advanced"],
                        "default": "basic"
                    }
                },
                "required": ["query"]
            }
        }
```

**Step 2: Update __init__.py**

```python
# Add to agents/tools/__init__.py
from .web_search import WebSearchTool
__all__.append("WebSearchTool")
```

**Step 3: Test the tool**

Run: `cd /home/zurybr/workspace/ultramemory && python -c "from agents.tools import WebSearchTool; t = WebSearchTool(); print(t.name, t.description)"`
Expected: `web_search Search the web for information using Tavily API`

---

### Task 1.3: Create Memory Tool Wrapper

**Files:**
- Create: `agents/tools/memory_tools.py`

**Step 1: Write memory tools**

```python
# agents/tools/memory_tools.py
"""Memory operation tools for agents."""

from typing import Any
from core.memory import MemorySystem
from .base import BaseTool, ToolCategory, ToolResult


class MemoryQueryTool(BaseTool):
    """Query memory system."""

    name = "memory_query"
    description = "Search the memory system for information"
    category = ToolCategory.MEMORY

    def __init__(self, memory: MemorySystem):
        self.memory = memory

    async def execute(self, query: str, limit: int = 5) -> ToolResult:
        """Query memory."""
        try:
            results = await self.memory.query(query, limit)
            return ToolResult(
                success=True,
                data=results,
                metadata={"query": query, "limit": limit}
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            }
        }


class MemoryAddTool(BaseTool):
    """Add content to memory."""

    name = "memory_add"
    description = "Add content to the memory system"
    category = ToolCategory.MEMORY

    def __init__(self, memory: MemorySystem):
        self.memory = memory

    async def execute(self, content: str, metadata: dict | None = None) -> ToolResult:
        """Add to memory."""
        try:
            doc_id = await self.memory.add(content, metadata)
            return ToolResult(
                success=True,
                data={"doc_id": doc_id},
                metadata={"content_length": len(content)}
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Content to store"},
                    "metadata": {"type": "object", "description": "Optional metadata"}
                },
                "required": ["content"]
            }
        }
```

---

## Phase 2: Enhanced Researcher Agent

### Task 2.1: Refactor ResearcherAgent with Tools

**Files:**
- Modify: `agents/researcher.py`

**Step 1: Update researcher.py**

```python
# agents/researcher.py (complete rewrite)
"""Enhanced Researcher Agent with tool support."""

from typing import Any
from dataclasses import dataclass
from core.memory import MemorySystem
from agents.tools.base import ToolResult
from agents.tools.web_search import WebSearchTool
from agents.tools.memory_tools import MemoryQueryTool


@dataclass
class ResearchResult:
    """Structured research result."""
    query: str
    memory_results: list[dict[str, Any]]
    web_results: list[dict[str, Any]]
    synthesis: str | None = None
    sources: list[str] | None = None


class ResearcherAgent:
    """Enhanced researcher agent with web and memory search capabilities."""

    def __init__(self, memory_system: MemorySystem, enable_web_search: bool = True):
        self.memory = memory_system
        self.enable_web_search = enable_web_search

        # Initialize tools
        self.memory_tool = MemoryQueryTool(memory_system)
        self.web_tool = WebSearchTool() if enable_web_search else None

    async def query(self, query_text: str, limit: int = 5) -> dict[str, Any]:
        """Query memory system (legacy interface)."""
        result = await self.memory_tool.execute(query=query_text, limit=limit)
        return {
            "query": query_text,
            "results": result.data.get("vector_results", []) if result.success else [],
            "total_found": len(result.data.get("vector_results", [])) if result.success else 0,
        }

    async def research(
        self,
        query: str,
        sources: list[str] = None,
        max_results_per_source: int = 5
    ) -> ResearchResult:
        """Comprehensive research across memory and web.

        Args:
            query: Research query
            sources: List of sources ["memory", "web"]. Default: all
            max_results_per_source: Max results per source

        Returns:
            ResearchResult with combined findings
        """
        sources = sources or ["memory", "web"]
        memory_results = []
        web_results = []

        # Memory search
        if "memory" in sources:
            mem_result = await self.memory_tool.execute(query, max_results_per_source)
            if mem_result.success:
                memory_results = mem_result.data.get("vector_results", [])

        # Web search
        if "web" in sources and self.web_tool:
            web_result = await self.web_tool.execute(
                query=query,
                max_results=max_results_per_source,
                search_depth="advanced"
            )
            if web_result.success:
                web_results = web_result.data.get("results", [])

        return ResearchResult(
            query=query,
            memory_results=memory_results,
            web_results=web_results,
            sources=self._extract_sources(memory_results, web_results)
        )

    def _extract_sources(
        self,
        memory_results: list[dict],
        web_results: list[dict]
    ) -> list[str]:
        """Extract source URLs from results."""
        sources = []
        for r in web_results:
            if url := r.get("url"):
                sources.append(url)
        return sources

    async def deep_research(
        self,
        topic: str,
        sub_queries: list[str] | None = None,
        max_depth: int = 3
    ) -> dict[str, Any]:
        """Deep research with automatic query expansion.

        Args:
            topic: Main research topic
            sub_queries: Optional sub-queries to explore
            max_depth: Maximum depth of research

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
        }

        # Main research
        main_result = await self.research(topic)
        results["main_research"] = {
            "memory_results": main_result.memory_results,
            "web_results": main_result.web_results,
        }

        # Sub-research
        for sub_q in sub_queries[:max_depth]:
            sub_result = await self.research(sub_q)
            results["sub_research"].append({
                "query": sub_q,
                "memory_results": sub_result.memory_results,
                "web_results": sub_result.web_results,
            })

        return results

    def _generate_sub_queries(self, topic: str) -> list[str]:
        """Generate sub-queries for deep research."""
        # Simple heuristics for query expansion
        prefixes = ["what is", "how does", "latest developments in", "best practices for"]
        return [f"{prefix} {topic}" for prefix in prefixes]
```

**Step 2: Test the updated researcher**

Run: `cd /home/zurybr/workspace/ultramemory && python -c "from agents.researcher import ResearcherAgent; print('OK')"`
Expected: `OK`

---

### Task 2.2: Update Auto-Researcher with Web Search

**Files:**
- Modify: `agents/auto_researcher.py`

**Step 1: Replace auto_researcher.py**

```python
# agents/auto_researcher.py (enhanced version)
"""Auto-Researcher Agent with real web search capabilities."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from core.memory import MemorySystem
from agents.tools.web_search import WebSearchTool


class AutoResearcherAgent:
    """Agent that automatically researches topics with web search."""

    def __init__(self, memory_system: MemorySystem, use_web: bool = True):
        self.memory = memory_system
        self.web_tool = WebSearchTool() if use_web else None

    async def research(
        self,
        topics: list[str],
        output_dir: str = "./researches",
        depth: str = "basic"
    ) -> dict[str, Any]:
        """Run research on given topics.

        Args:
            topics: List of topics to research
            output_dir: Directory to save research outputs
            depth: "basic" or "deep" research
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        results = []

        for topic in topics:
            try:
                # Web search
                info = await self._search_topic(topic, depth)

                # Save to file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{topic.replace(' ', '_')[:50]}.md"
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
                    },
                )

                results.append({
                    "topic": topic,
                    "status": "success",
                    "file": str(filepath),
                    "sources": info.get("sources", []),
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
        }

    async def _search_topic(self, topic: str, depth: str = "basic") -> dict[str, Any]:
        """Search for information on a topic."""
        if not self.web_tool:
            return self._fallback_search(topic)

        result = await self.web_tool.execute(
            query=topic,
            max_results=10 if depth == "deep" else 5,
            search_depth="advanced" if depth == "deep" else "basic"
        )

        if result.success:
            data = result.data
            return {
                "summary": self._extract_summary(data),
                "key_findings": self._extract_findings(data),
                "sources": [r.get("url", "") for r in data.get("results", [])],
                "raw_results": data.get("results", []),
            }

        return self._fallback_search(topic)

    def _fallback_search(self, topic: str) -> dict[str, Any]:
        """Fallback when web search unavailable."""
        return {
            "summary": f"Web search unavailable. Manual research needed for: {topic}",
            "key_findings": ["Enable TAVILY_API_KEY for web search"],
            "sources": [],
        }

    def _extract_summary(self, data: dict) -> str:
        """Extract summary from search results."""
        if answer := data.get("answer"):
            return answer
        results = data.get("results", [])
        if results:
            return results[0].get("content", "")[:500]
        return "No summary available."

    def _extract_findings(self, data: dict) -> list[str]:
        """Extract key findings from results."""
        findings = []
        for r in data.get("results", [])[:5]:
            if content := r.get("content"):
                # Extract first sentence or 200 chars
                finding = content.split(".")[0][:200]
                findings.append(finding)
        return findings

    def _format_research(self, topic: str, info: dict[str, Any]) -> str:
        """Format research as markdown."""
        lines = [
            f"# Research: {topic}",
            "",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Source:** Auto-Researcher (Tavily)",
            "",
            "## Summary",
            "",
            info.get("summary", "No summary available."),
            "",
            "## Key Findings",
            "",
        ]

        for i, finding in enumerate(info.get("key_findings", []), 1):
            lines.append(f"{i}. {finding}")

        lines.extend([
            "",
            "## Sources",
            "",
        ])

        for source in info.get("sources", []):
            if source:
                lines.append(f"- {source}")

        return "\n".join(lines)
```

---

## Phase 3: Enhanced Agent CLI Management

### Task 3.1: Add Skill Configuration to Agent CLI

**Files:**
- Modify: `ultramemory_cli/agents.py`

**Step 1: Add skill management commands**

Add these new commands to `ultramemory_cli/agents.py`:

```python
# Add to existing agents.py

@agent_group.command(name="skills")
@click.argument("name", required=False)
def list_skills(name: str | None):
    """List available skills for agents.

    Without argument: list all available skills
    With agent name: list skills assigned to that agent
    """
    if name:
        # Show skills for specific agent
        custom_agents = settings.get("agents.custom", {})
        if name not in custom_agents:
            click.echo(f"Error: Agent '{name}' not found", err=True)
            return

        agent_path = Path(custom_agents[name]["path"])
        skills_file = agent_path / "skills.json"

        if skills_file.exists():
            skills = json.loads(skills_file.read_text())
            click.echo(f"\nSkills for agent '{name}':")
            click.echo(json.dumps(skills, indent=2))
        else:
            click.echo(f"No skills configured for agent '{name}'")
    else:
        # List all available skill types
        click.echo("\n📋 Available Skill Categories:")
        click.echo("  - web_search: Search the web for information")
        click.echo("  - memory_query: Search internal memory")
        click.echo("  - memory_add: Add content to memory")
        click.echo("  - deep_research: Comprehensive research with web search")
        click.echo("\n💡 Use 'ulmemory agent add-skill <agent> <skill>' to add")


@agent_group.command(name="add-skill")
@click.argument("name")
@click.argument("skill")
@click.option("--config", "-c", help="JSON config for the skill")
def add_skill(name: str, skill: str, config: str | None):
    """Add a skill to an agent.

    Example:
        ulmemory agent add-skill my-agent web_search
        ulmemory agent add-skill my-agent deep_research -c '{"max_depth": 5}'
    """
    custom_agents = settings.get("agents.custom", {})

    if name not in custom_agents:
        click.echo(f"Error: Agent '{name}' not found", err=True)
        return

    agent_path = Path(custom_agents[name]["path"])
    skills_file = agent_path / "skills.json"

    # Load existing skills
    if skills_file.exists():
        skills = json.loads(skills_file.read_text())
    else:
        skills = {"tools": [], "config": {}}

    # Add tool
    if skill not in skills.get("tools", []):
        skills.setdefault("tools", []).append(skill)

    # Add config if provided
    if config:
        try:
            skill_config = json.loads(config)
            skills.setdefault("config", {})[skill] = skill_config
        except json.JSONDecodeError:
            click.echo("Error: Invalid JSON config", err=True)
            return

    # Save
    skills_file.write_text(json.dumps(skills, indent=2))
    click.echo(f"✅ Added skill '{skill}' to agent '{name}'")


@agent_group.command(name="remove-skill")
@click.argument("name")
@click.argument("skill")
def remove_skill(name: str, skill: str):
    """Remove a skill from an agent."""
    custom_agents = settings.get("agents.custom", {})

    if name not in custom_agents:
        click.echo(f"Error: Agent '{name}' not found", err=True)
        return

    agent_path = Path(custom_agents[name]["path"])
    skills_file = agent_path / "skills.json"

    if not skills_file.exists():
        click.echo(f"No skills configured for agent '{name}'")
        return

    skills = json.loads(skills_file.read_text())

    if skill in skills.get("tools", []):
        skills["tools"].remove(skill)
        skills.get("config", {}).pop(skill, None)
        skills_file.write_text(json.dumps(skills, indent=2))
        click.echo(f"✅ Removed skill '{skill}' from agent '{name}'")
    else:
        click.echo(f"Skill '{skill}' not found in agent '{name}'")


@agent_group.command(name="edit")
@click.argument("name")
@click.option("--schedule", "-s", help="New schedule (cron expression)")
@click.option("--provider", "-p", help="New LLM provider")
@click.option("--name", "-n", "new_name", help="Rename agent")
def edit_agent(name: str, schedule: str | None, provider: str | None, new_name: str | None):
    """Edit agent configuration.

    Examples:
        ulmemory agent edit my-agent --schedule "0 */6 * * *"
        ulmemory agent edit my-agent --provider openai
        ulmemory agent edit my-agent --name new-name
    """
    custom_agents = settings.get("agents.custom", {})

    if name not in custom_agents:
        click.echo(f"Error: Agent '{name}' not found", err=True)
        return

    agent_path = Path(custom_agents[name]["path"])
    skills_file = agent_path / "skills.json"

    if skills_file.exists():
        skills = json.loads(skills_file.read_text())
    else:
        skills = {}

    changed = False

    if schedule:
        skills["schedule"] = schedule
        changed = True
        click.echo(f"✅ Schedule updated: {schedule}")

    if provider:
        skills["llm_provider"] = provider
        changed = True
        click.echo(f"✅ Provider updated: {provider}")

    if new_name:
        # Rename agent directory
        new_path = agent_path.parent / new_name
        agent_path.rename(new_path)

        # Update settings
        custom_agents[new_name] = custom_agents.pop(name)
        custom_agents[new_name]["path"] = str(new_path)
        settings.set("agents.custom", custom_agents)

        click.echo(f"✅ Agent renamed: {name} -> {new_name}")
        agent_path = new_path
        changed = True

    if changed:
        (agent_path / "skills.json").write_text(json.dumps(skills, indent=2))
    else:
        click.echo("No changes made. Use --schedule, --provider, or --name")
```

**Step 2: Test the new commands**

Run: `cd /home/zurybr/workspace/ultramemory && python -m ultramemory_cli.main agent skills`
Expected: List of skill categories

---

## Phase 4: Enhanced Scheduler

### Task 4.1: Add History and Status to Scheduler

**Files:**
- Modify: `ultramemory_cli/scheduler.py`

**Step 1: Add history command**

Add this command to scheduler.py:

```python
@schedule_group.command(name="history")
@click.argument("task_id", type=int)
@click.option("--limit", "-l", default=10, help="Number of entries to show")
def history_command(task_id: int, limit: int):
    """Show execution history for a task."""
    history_file = SCHEDULES_DIR / f"task_{task_id}_history.json"

    if not history_file.exists():
        click.echo(f"No history found for task #{task_id}")
        return

    history = json.loads(history_file.read_text())

    click.echo(f"\n📜 Execution History for Task #{task_id}:\n")

    for entry in history[-limit:]:
        status = "✅" if entry.get("success") else "❌"
        timestamp = entry.get("timestamp", "unknown")
        duration = entry.get("duration", "N/A")
        click.echo(f"  {status} {timestamp} (duration: {duration}s)")


def _record_execution(task_id: int, success: bool, duration: float):
    """Record task execution in history."""
    history_file = SCHEDULES_DIR / f"task_{task_id}_history.json"

    if history_file.exists():
        history = json.loads(history_file.read_text())
    else:
        history = []

    history.append({
        "timestamp": datetime.now().isoformat(),
        "success": success,
        "duration": round(duration, 2),
    })

    # Keep last 100 entries
    history = history[-100:]
    history_file.write_text(json.dumps(history, indent=2))
```

---

## Phase 5: Update CLI Main Entry

### Task 5.1: Add Version and Validate Commands

**Files:**
- Modify: `ultramemory_cli/main.py`

**Step 1: Add version command**

```python
# Add to main.py

__version__ = "0.2.0"

@app.command(name="version")
def version():
    """Show Ultramemory version."""
    click.echo(f"Ultramemory v{__version__}")


@app.command(name="validate")
def validate():
    """Validate system configuration and connections."""
    issues = []

    # Check Docker
    try:
        subprocess.run(["docker", "version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        issues.append("❌ Docker not running or not installed")

    # Check config
    config_file = Path.home() / ".config" / "ultramemory" / "config.yaml"
    if not config_file.exists():
        issues.append("⚠️  Config file not found. Run 'ulmemory config init'")

    # Check API keys
    if not os.getenv("TAVILY_API_KEY"):
        issues.append("⚠️  TAVILY_API_KEY not set (web search disabled)")

    if issues:
        click.echo("Validation Issues:\n")
        for issue in issues:
            click.echo(f"  {issue}")
    else:
        click.echo("✅ All validations passed!")
```

---

## Phase 6: Update Skill Documentation

### Task 6.1: Update SKILL.md

**Files:**
- Modify: `skills/ulmemory-cli/SKILL.md`

**Step 1: Update with new commands**

```markdown
# Ulmemory CLI

## Overview
CLI para el sistema de memoria híbrida Ultramemory...

## New Features (v0.2.0)

### Agent Skills Management
| Comando | Descripción |
|---------|-------------|
| `ulmemory agent skills` | List all available skills |
| `ulmemory agent skills <name>` | Show skills for specific agent |
| `ulmemory agent add-skill <agent> <skill>` | Add skill to agent |
| `ulmemory agent remove-skill <agent> <skill>` | Remove skill from agent |
| `ulmemory agent edit <name> --schedule "cron"` | Edit agent schedule |

### Enhanced Research
| Comando | Descripción |
|---------|-------------|
| `ulmemory agent run researcher "query"` | Search memory only |
| `ulmemory agent run researcher "query" --web` | Memory + Web search |
| `ulmemory agent run auto-researcher "topic" --deep` | Deep web research |

### Scheduler History
| Comando | Descripción |
|---------|-------------|
| `ulmemory schedule history <id>` | View execution history |
| `ulmemory schedule status <id>` | Detailed task status |

## Environment Variables
- `TAVILY_API_KEY`: Required for web search (get at https://tavily.com)

## Configuration
Edit `~/.config/ultramemory/config.yaml` to add API keys...
```

---

## Phase 7: Testing and Validation

### Task 7.1: Create Test Suite

**Files:**
- Create: `tests/test_tools.py`
- Create: `tests/test_researcher.py`

**Step 1: Write tool tests**

```python
# tests/test_tools.py
"""Tests for agent tools."""

import pytest
from agents.tools import registry, WebSearchTool, ToolCategory


def test_tool_registry():
    """Test tool registration."""
    tool = WebSearchTool()
    registry.register(tool)

    assert registry.get("web_search") == tool
    assert tool.category == ToolCategory.WEB


def test_web_search_schema():
    """Test web search tool schema."""
    tool = WebSearchTool()
    schema = tool.get_schema()

    assert schema["name"] == "web_search"
    assert "query" in schema["parameters"]["properties"]
    assert schema["parameters"]["required"] == ["query"]


@pytest.mark.asyncio
async def test_web_search_no_key():
    """Test web search without API key."""
    tool = WebSearchTool()
    tool.api_key = None

    result = await tool.execute(query="test")
    assert result.success is False
    assert "TAVILY_API_KEY" in result.error
```

**Step 2: Write researcher tests**

```python
# tests/test_researcher.py
"""Tests for enhanced researcher."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from agents.researcher import ResearcherAgent, ResearchResult


@pytest.fixture
def mock_memory():
    memory = MagicMock()
    memory.query = AsyncMock(return_value={"vector_results": []})
    return memory


@pytest.mark.asyncio
async def test_researcher_query(mock_memory):
    """Test basic query."""
    agent = ResearcherAgent(mock_memory, enable_web_search=False)
    result = await agent.query("test query")

    assert result["query"] == "test query"
    assert "results" in result


@pytest.mark.asyncio
async def test_researcher_research(mock_memory):
    """Test research method."""
    agent = ResearcherAgent(mock_memory, enable_web_search=False)
    result = await agent.research("test", sources=["memory"])

    assert isinstance(result, ResearchResult)
    assert result.query == "test"
```

**Step 3: Run tests**

Run: `cd /home/zurybr/workspace/ultramemory && python -m pytest tests/ -v`
Expected: All tests pass

---

## Phase 8: Documentation Update

### Task 8.1: Update README.md

**Files:**
- Modify: `README.md`

**Step 1: Add new features section**

Add after line 16:

```markdown
## 🆕 Novedades v0.2.0

### Web Search Integration
El Researcher ahora puede buscar en internet usando Tavily API:
```bash
# Configurar API key
export TAVILY_API_KEY="tu-api-key"

# Buscar en memoria + web
ulmemory agent run researcher "topic" --web
```

### Agent Skills System
Sistema de skills para personalizar agentes:
```bash
ulmemory agent skills                    # Ver skills disponibles
ulmemory agent add-skill mi-agente web_search
ulmemory agent edit mi-agente --schedule "0 9 * * *"
```

### Enhanced Scheduler
Historial de ejecución y mejor gestión:
```bash
ulmemory schedule history 1              # Ver historial
ulmemory schedule edit 1 --cron "0 */6 * * *"
```

## 📦 Requisitos de API

| Servicio | Variable | Obtener |
|----------|----------|---------|
| Web Search | `TAVILY_API_KEY` | https://tavily.com |
| OpenAI | `OPENAI_API_KEY` | https://platform.openai.com |
| Google | `GOOGLE_API_KEY` | https://ai.google.dev |
```

---

## Phase 9: Git Commit and Push

### Task 9.1: Commit Changes

**Step 1: Stage all changes**

```bash
git add agents/tools/
git add agents/researcher.py
git add agents/auto_researcher.py
git add ultramemory_cli/agents.py
git add ultramemory_cli/scheduler.py
git add ultramemory_cli/main.py
git add tests/test_tools.py
git add tests/test_researcher.py
git add skills/ulmemory-cli/SKILL.md
git add README.md
git add docs/plans/2026-02-16-agent-enhancement-plan.md
```

**Step 2: Create commit**

```bash
git commit -m "$(cat <<'EOF'
feat: Enhance agents with web search and skills system

- Add tool system with BaseTool interface and registry
- Integrate Tavily API for web search in Researcher
- Add agent skills management CLI commands
- Add scheduler execution history
- Update documentation and skill file

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

**Step 3: Push to remote**

```bash
git push origin main
```

---

## Phase 10: Document in Ultramemory

### Task 10.1: Store Implementation Insights

```bash
ulmemory memory add "Ultramemory enhancement completed: Added tool system with BaseTool interface, WebSearchTool with Tavily integration, enhanced ResearcherAgent with web+memory search, agent skills management CLI (add-skill, remove-skill, edit), scheduler execution history. Key patterns: async tools with ToolResult dataclass, registry singleton, skill-based agent configuration." -m "type=feature,project=ultramemory,version=0.2.0"
```

---

## Execution Summary

| Phase | Description | Files |
|-------|-------------|-------|
| 1 | Core Tool System | `agents/tools/` (3 files) |
| 2 | Enhanced Researcher | `agents/researcher.py`, `agents/auto_researcher.py` |
| 3 | Agent CLI | `ultramemory_cli/agents.py` |
| 4 | Scheduler | `ultramemory_cli/scheduler.py` |
| 5 | Main CLI | `ultramemory_cli/main.py` |
| 6 | Skill Doc | `skills/ulmemory-cli/SKILL.md` |
| 7 | Tests | `tests/test_tools.py`, `tests/test_researcher.py` |
| 8 | README | `README.md` |
| 9 | Git | Commit and push |
| 10 | Memory | Store insights |

---

**Plan complete. Ready for execution with superpowers:subagent-driven-development or superpowers:executing-plans.**
