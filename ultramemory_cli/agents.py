"""Agent management commands with skill support and web research."""

import asyncio
import json
import os
from pathlib import Path

import click

from agents.custom_agent import CustomAgent
from core.memory import MemorySystem
from ultramemory_cli.settings import settings, CONFIG_DIR


# Load Tavily API key from config
def _get_tavily_key() -> str | None:
    """Get Tavily API key from config or env."""
    key = os.getenv("TAVILY_API_KEY")
    if key:
        return key
    try:
        import yaml
        config_path = Path.home() / ".config" / "ultramemory" / "config.yaml"
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
                return config.get("research", {}).get("tavily", {}).get("api_key")
    except Exception:
        pass
    return None


@click.group(name="agent")
def agent_group():
    """Agent management commands."""
    pass


@agent_group.command(name="create")
def create_agent():
    """Create a new custom agent interactively."""
    click.echo("Creating new agent...")
    click.echo("=" * 40)

    # Questions
    name = click.prompt("Agent name")

    purpose = click.prompt("Purpose (what does it do?)")

    click.echo("\nInput types (comma-separated):")
    click.echo("  text, file, url, all")
    input_types = click.prompt("Input types", default="text")

    click.echo("\nOutput types (comma-separated):")
    click.echo("  text, json, markdown, all")
    output_types = click.prompt("Output types", default="text")

    click.echo("\nLLM Provider:")
    llm_provider = click.prompt("Provider", default=settings.get("llm_provider", "openai"))

    click.echo("\nSchedule (if daemon):")
    click.echo("  manual, hourly, daily, weekly, cron")
    schedule = click.prompt("Schedule", default="manual")

    click.echo("\nSkills (comma-separated):")
    click.echo("  web_search, memory_query, memory_add, codewiki, deep_research")
    skills_input = click.prompt("Skills", default="")

    # Create agent files
    agents_dir = CONFIG_DIR / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    agent_dir = agents_dir / name
    agent_dir.mkdir(parents=True, exist_ok=True)

    # Write MD
    md_content = f"""# {name}

## Purpose
{purpose}

## Input Types
{input_types}

## Output Types
{output_types}

## LLM Provider
{llm_provider}

## Schedule
{schedule}
"""
    (agent_dir / "README.md").write_text(md_content, encoding="utf-8")

    # Write skills JSON
    skills = {
        "input_types": [t.strip() for t in input_types.split(",")],
        "output_types": [t.strip() for t in output_types.split(",")],
        "llm_provider": llm_provider,
        "schedule": schedule,
        "tools": [s.strip() for s in skills_input.split(",") if s.strip()],
    }
    (agent_dir / "skills.json").write_text(json.dumps(skills, indent=2), encoding="utf-8")

    # Save to settings
    custom_agents = settings.get("agents.custom", {})
    custom_agents[name] = {
        "path": str(agent_dir),
        "created": str(Path(__file__).stat().st_mtime),
    }
    settings.set("agents.custom", custom_agents)

    click.echo(f"\n✅ Agent '{name}' created at {agent_dir}")


@agent_group.command(name="list")
def list_agents():
    """List all agents."""
    click.echo("\n🤖 System Agents:")
    click.echo("  - librarian    (Bibliotecario - add content)")
    click.echo("  - researcher   (Investigador - search memory + web)")
    click.echo("  - consolidator (Consolidador - cleanup)")
    click.echo("  - auto-researcher (Researcher automático - web + codewiki)")
    click.echo("  - deleter      (Eliminador - delete memories)")

    custom_agents = settings.get("agents.custom", {})
    if custom_agents:
        click.echo("\n📋 Custom Agents:")
        for name, info in custom_agents.items():
            click.echo(f"  - {name}")


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

        if name in ["researcher", "auto-researcher"]:
            click.echo(f"\n📋 Built-in skills for '{name}':")
            click.echo("  - memory_query (search internal memory)")
            click.echo("  - web_search (Tavily API)")
            click.echo("  - codewiki (GitHub repo research)")
            click.echo("  - deep_research (multi-source research)")
            return

        if name not in custom_agents:
            click.echo(f"❌ Agent '{name}' not found", err=True)
            return

        agent_path = Path(custom_agents[name]["path"])
        skills_file = agent_path / "skills.json"

        if skills_file.exists():
            skills = json.loads(skills_file.read_text())
            click.echo(f"\n📋 Skills for agent '{name}':")
            click.echo(json.dumps(skills, indent=2))
        else:
            click.echo(f"No skills configured for agent '{name}'")
    else:
        # List all available skill types
        click.echo("\n📋 Available Skill Categories:")
        click.echo("")
        click.echo("  🔍 Research Skills:")
        click.echo("    - web_search      Search the web (Tavily API)")
        click.echo("    - codewiki        Research GitHub repos")
        click.echo("    - deep_research   Multi-source comprehensive research")
        click.echo("")
        click.echo("  💾 Memory Skills:")
        click.echo("    - memory_query    Search internal memory")
        click.echo("    - memory_add      Add content to memory")
        click.echo("    - memory_count    Count documents")
        click.echo("")
        click.echo("💡 Usage:")
        click.echo("  ulmemory agent add-skill <agent> <skill>")
        click.echo("  ulmemory agent skills <agent>")


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
        click.echo(f"❌ Agent '{name}' not found", err=True)
        click.echo("Create it first with: ulmemory agent create")
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
            click.echo("❌ Invalid JSON config", err=True)
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
        click.echo(f"❌ Agent '{name}' not found", err=True)
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
        click.echo(f"⚠️  Skill '{skill}' not found in agent '{name}'")


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
        click.echo(f"❌ Agent '{name}' not found", err=True)
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


@agent_group.command(name="launch")
@click.argument("name")
@click.argument("input_data", required=False)
def launch_agent(name: str, input_data: str | None):
    """Launch a custom agent once."""
    custom_agents = settings.get("agents.custom", {})

    if name not in custom_agents:
        click.echo(f"❌ Agent '{name}' not found", err=True)
        return

    agent_path = Path(custom_agents[name]["path"])

    agent = CustomAgent(
        name=name,
        md_path=agent_path / "README.md",
        skill_path=agent_path / "skills.json" if (agent_path / "skills.json").exists() else None,
    )

    async def _run():
        memory = MemorySystem()
        result = await agent.run(input_data, memory)
        click.echo(f"Result: {result}")

    asyncio.run(_run())


@agent_group.command(name="config")
@click.argument("name")
def config_agent(name: str):
    """Configure a custom agent."""
    custom_agents = settings.get("agents.custom", {})

    if name not in custom_agents:
        click.echo(f"❌ Agent '{name}' not found", err=True)
        return

    agent_path = Path(custom_agents[name]["path"])

    click.echo(f"Configuring agent: {name}")
    click.echo(f"Location: {agent_path}")

    # Edit skills
    if (agent_path / "skills.json").exists():
        skills = json.loads((agent_path / "skills.json").read_text())
        click.echo(f"\nCurrent skills: {json.dumps(skills, indent=2)}")

        if click.confirm("Edit skills?"):
            # Re-ask questions (simplified)
            new_schedule = click.prompt("Schedule", default=skills.get("schedule", "manual"))
            skills["schedule"] = new_schedule
            (agent_path / "skills.json").write_text(json.dumps(skills, indent=2))
            click.echo("Skills updated.")


@agent_group.command(name="run")
@click.argument("name")
@click.argument("args", required=False, default="")
@click.option("--web", "-w", is_flag=True, help="Enable web search for researcher")
@click.option("--deep", "-d", is_flag=True, help="Deep research mode")
@click.option("--sources", "-s", help="Comma-separated sources: web,memory,codewiki")
def run_agent(name: str, args: str, web: bool, deep: bool, sources: str | None):
    """Run an agent (system or custom).

    System agents: librarian, researcher, consolidator, auto-researcher, deleter
    Custom agents: any agent created with 'ulmemory agent create'

    \b
    Examples:
        ulmemory agent run consolidator
        ulmemory agent run librarian "/path/to/file.txt"
        ulmemory agent run researcher "search query"
        ulmemory agent run researcher "query" --web --sources web,memory
        ulmemory agent run auto-researcher "topic:AI" --deep
        ulmemory agent run deleter "all"
    """
    tavily_key = _get_tavily_key()

    async def _run():
        memory = MemorySystem()

        # System agents
        if name == "consolidator":
            from agents.consolidator import ConsolidatorAgent
            agent = ConsolidatorAgent(memory)
            result = await agent.consolidate()
            click.echo(f"✅ Consolidation complete:")
            click.echo(f"   Duplicates removed: {result.get('duplicates_removed', 0)}")
            click.echo(f"   Malformed fixed: {result.get('malformed_fixed', 0)}")

        elif name == "librarian":
            from agents.librarian import LibrarianAgent
            agent = LibrarianAgent(memory)
            if args:
                path = Path(args)
                if path.exists():
                    result = await agent.add(path)
                else:
                    result = await agent.add(args)
                click.echo(f"✅ Added: {result['chunks_created']} chunks")
            else:
                click.echo("❌ Librarian requires input (text or file path)")

        elif name == "researcher":
            from agents.researcher import ResearcherAgent
            agent = ResearcherAgent(
                memory,
                enable_web_search=web or bool(tavily_key),
                tavily_api_key=tavily_key
            )
            if args:
                # Determine sources
                source_list = None
                if sources:
                    source_list = [s.strip() for s in sources.split(",")]
                elif web:
                    source_list = ["web", "memory"]

                if source_list or deep:
                    # Use enhanced research
                    result = await agent.research(args, sources=source_list)
                    click.echo(f"\n🔍 Research Results for: {args}")
                    click.echo(f"   Sources queried: {', '.join(result.sources) if result.sources else 'memory only'}")
                    click.echo(f"   Total results: {result.total_results}")

                    if result.web_answer:
                        click.echo(f"\n💡 AI Answer:\n   {result.web_answer[:500]}...")

                    if result.web_results:
                        click.echo(f"\n🌐 Web Results ({len(result.web_results)}):")
                        for i, r in enumerate(result.web_results[:3], 1):
                            click.echo(f"   {i}. {r.get('title', r.get('url', 'Unknown'))[:60]}")

                    if result.memory_results:
                        click.echo(f"\n💾 Memory Results ({len(result.memory_results)}):")
                        for i, r in enumerate(result.memory_results[:3], 1):
                            content = r.get('content', r.get('payload', {}).get('content', ''))[:60]
                            click.echo(f"   {i}. {content}...")

                    if result.errors:
                        click.echo(f"\n⚠️  Errors: {result.errors}")
                else:
                    # Legacy memory-only search
                    result = await agent.query(args)
                    click.echo(f"\nFound {len(result['results'])} results:")
                    for i, r in enumerate(result["results"], 1):
                        content = r.get('content', r.get('payload', {}).get('content', ''))[:100]
                        click.echo(f"{i}. {content}...")
                        click.echo(f"   Score: {r.get('score', 'N/A')}\n")
            else:
                click.echo("❌ Researcher requires a query")
                click.echo("💡 Try: ulmemory agent run researcher \"your query\" --web")

        elif name == "auto-researcher":
            from agents.auto_researcher import AutoResearcherAgent
            agent = AutoResearcherAgent(
                memory,
                use_web=bool(tavily_key),
                tavily_api_key=tavily_key
            )
            topics = [t.strip() for t in args.split(",") if t.strip()] if args else ["general"]
            depth = "deep" if deep else "basic"
            result = await agent.research(topics, depth=depth)

            click.echo(f"\n✅ Research Complete!")
            click.echo(f"   Output: {result['output_dir']}")
            click.echo(f"   Sources used: {', '.join(result.get('sources_used', []))}")

            for r in result.get("results", []):
                status = "✅" if r["status"] == "success" else "❌"
                click.echo(f"   {status} {r['topic']}")
                if r["status"] == "success":
                    click.echo(f"      Web sources: {r.get('web_sources', 0)}")
                    click.echo(f"      CodeWiki repos: {r.get('codewiki_sources', 0)}")

        elif name == "deleter":
            from agents.deleter import DeleterAgent
            agent = DeleterAgent(memory)
            count = await agent.count()
            if args == "all":
                click.echo(f"⚠️  Deleting ALL {count} memories...")
                result = await agent.delete_all(confirm=True)
                click.echo(f"✅ Deleted: {result.get('qdrant_deleted', 0)} memories")
            elif args:
                click.echo(f"🔍 Deleting memories matching '{args}'...")
                result = await agent.delete_by_query(args)
                click.echo(f"✅ Deleted: {result.get('deleted', 0)} memories")
            else:
                click.echo(f"📊 Total memories: {count}")
                click.echo("💡 Use 'deleter all' to delete all, or 'deleter <query>' to delete by search")

        else:
            # Try custom agent
            custom_agents = settings.get("agents.custom", {})
            if name in custom_agents:
                agent_path = Path(custom_agents[name]["path"])
                agent = CustomAgent(
                    name=name,
                    md_path=agent_path / "README.md",
                    skill_path=agent_path / "skills.json" if (agent_path / "skills.json").exists() else None,
                )
                result = await agent.run(args, memory)
                click.echo(f"✅ Result: {result}")
            else:
                click.echo(f"❌ Agent '{name}' not found")
                click.echo("Available agents: librarian, researcher, consolidator, auto-researcher, deleter")
                if custom_agents:
                    click.echo(f"Custom agents: {', '.join(custom_agents.keys())}")

    asyncio.run(_run())


# === New Agents Commands ===

@agent_group.command(name="consultant")
@click.argument("query")
@click.option("--order", "-o", default="relevance", help="Order by: relevance, date, source")
@click.option("--limit", "-l", default=10, type=int)
def run_consultant(query: str, order: str, limit: int):
    """Run consultant agent for ordered search."""

    async def _run():
        memory = MemorySystem()
        from agents.consultant import ConsultantAgent
        agent = ConsultantAgent(memory)

        result = await agent.query(query, order_by=order, max_results=limit)
        formatted = agent.format_as_text(result)
        click.echo(formatted)

    asyncio.run(_run())


@agent_group.command(name="proactive")
def run_proactive():
    """Run proactive agent to check heartbeat."""

    async def _run():
        memory = MemorySystem()
        from agents.proactive import ProactiveAgent
        agent = ProactiveAgent(memory)

        result = await agent.check_and_execute()

        click.echo(f"\n🤖 Proactive Agent Results:")
        click.echo(f"   Status: {result['status']}")
        click.echo(f"   Executed: {result.get('executed', 0)}")

        for r in result.get("results", []):
            status = "✅" if r["status"] == "success" else "❌"
            click.echo(f"   {status} {r['task']}")

    asyncio.run(_run())


@agent_group.command(name="terminal")
@click.argument("action", default="dashboard")
@click.option("--topic", "-t", help="Topic for research guide")
def run_terminal(action: str, topic: str):
    """Run terminal agent for interactive CLI."""

    async def _run():
        memory = MemorySystem()
        from agents.terminal import TerminalAgent
        agent = TerminalAgent(memory)

        if action == "dashboard":
            result = await agent.show_dashboard()
        elif action == "diagnose":
            result = await agent.diagnose()
        elif action == "guide" and topic:
            result = await agent.guide_research(topic)
        elif action == "guide":
            result = await agent.guide_research()
        elif action == "prds":
            result = await agent.guide_prd_review()
        else:
            result = await agent.show_dashboard()

        click.echo(result)

    asyncio.run(_run())


@agent_group.command(name="heartbeat")
@click.argument("action")
@click.argument("task", required=False)
def manage_heartbeat(action: str, task: str | None):
    """Manage heartbeat tasks."""

    from agents.heartbeat_reader import HeartbeatReader

    hb = HeartbeatReader()

    if action == "list":
        data = hb.read()
        click.echo("\n📋 Tareas Pendientes:")
        for i, t in enumerate(data["tasks"], 1):
            status = "✅" if t["completed"] else "⬜"
            tags = " ".join(f"#{tag}" for tag in t.get("tags", []))
            click.echo(f"   {status} {i}. {t['title']} {tags}")

    elif action == "add" and task:
        import re
        tags = re.findall(r'#(\w+)', task)
        title = re.sub(r'#\w+', '', task).strip()

        hb.add_task(title, tags)
        click.echo(f"✅ Tarea agregada: {title}")

    elif action == "complete" and task:
        hb.mark_completed(task)
        click.echo(f"✅ Tarea completada: {task}")

    else:
        click.echo("Usage: ulmemory agent heartbeat <list|add|complete> [task]")


@agent_group.command(name="prd")
@click.argument("action")
@click.argument("research_file", required=False)
@click.option("--title", "-t", help="PRD title")
def manage_prd(action: str, research_file: str | None, title: str | None):
    """Manage PRD generation."""

    from agents.prd_generator import PRDGeneratorAgent

    async def _run():
        memory = MemorySystem()
        agent = PRDGeneratorAgent(memory)

        if action == "generate" and research_file:
            result = agent.generate_prd(research_file, title)
            click.echo(f"✅ PRD generado: {result.get('prd_file')}")

        elif action == "list":
            prds = agent.list_prds()
            click.echo("\n📄 PRDs:")
            for prd in prds:
                click.echo(f"   - {prd['title']} [{prd.get('status', 'draft')}]")

        else:
            click.echo("Usage: ulmemory agent prd <generate|list> [research_file]")

    asyncio.run(_run())
