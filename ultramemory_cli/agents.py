"""Agent management commands."""

import asyncio
import json
from pathlib import Path

import click

from agents.custom_agent import CustomAgent
from core.memory import MemorySystem
from ultramemory_cli.settings import settings, CONFIG_DIR


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
    }
    (agent_dir / "skills.json").write_text(json.dumps(skills, indent=2), encoding="utf-8")

    # Save to settings
    custom_agents = settings.get("agents.custom", {})
    custom_agents[name] = {
        "path": str(agent_dir),
        "created": str(Path(__file__).stat().st_mtime),
    }
    settings.set("agents.custom", custom_agents)

    click.echo(f"\nAgent '{name}' created at {agent_dir}")


@agent_group.command(name="list")
def list_agents():
    """List all agents."""
    click.echo("System Agents:")
    click.echo("  - librarian (Bibliotecario)")
    click.echo("  - researcher (Investigador)")
    click.echo("  - consolidator (Consolidador)")
    click.echo("  - auto-researcher (Researcher automático)")

    custom_agents = settings.get("agents.custom", {})
    if custom_agents:
        click.echo("\nCustom Agents:")
        for name, info in custom_agents.items():
            click.echo(f"  - {name}")


@agent_group.command(name="launch")
@click.argument("name")
@click.argument("input_data", required=False)
def launch_agent(name: str, input_data: str | None):
    """Launch a custom agent once."""
    custom_agents = settings.get("agents.custom", {})

    if name not in custom_agents:
        click.echo(f"Error: Agent '{name}' not found", err=True)
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
        click.echo(f"Error: Agent '{name}' not found", err=True)
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
