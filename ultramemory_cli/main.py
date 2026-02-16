"""Main CLI application for Ultramemory."""

import subprocess
import sys
from pathlib import Path

import click
import httpx

from .settings import settings


@click.group()
@click.version_option(version="0.1.0")
def app():
    """Ultramemory - Hybrid memory system with multi-agent CLI."""
    pass


# Service Management Commands
@app.command(name="up")
@click.argument("path", default=".", required=False)
def up(path: str):
    """Start Ultramemory services."""
    click.echo("Starting Ultramemory services...")

    # Check if docker is available
    try:
        subprocess.run(["docker", "compose", "version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        click.echo("Error: docker compose not found. Please install Docker.", err=True)
        sys.exit(1)

    compose_file = Path(path) / "docker-compose.yml"
    if not compose_file.exists():
        click.echo(f"Error: docker-compose.yml not found in {path}", err=True)
        sys.exit(1)

    result = subprocess.run(["docker", "compose", "-f", str(compose_file), "up", "-d"], cwd=path)
    if result.returncode == 0:
        click.echo("Services started successfully!")
        health()
    else:
        click.echo("Failed to start services.", err=True)
        sys.exit(1)


@app.command(name="down")
@click.argument("path", default=".", required=False)
def down(path: str):
    """Stop Ultramemory services."""
    compose_file = Path(path) / "docker-compose.yml"
    result = subprocess.run(["docker", "compose", "-f", str(compose_file), "down"], cwd=path)
    if result.returncode == 0:
        click.echo("Services stopped.")
    else:
        click.echo("Failed to stop services.", err=True)


@app.command(name="restart")
@click.argument("path", default=".", required=False)
def restart(path: str):
    """Restart Ultramemory services."""
    compose_file = Path(path) / "docker-compose.yml"
    subprocess.run(["docker", "compose", "-f", str(compose_file), "restart"], cwd=path)
    click.echo("Services restarted.")
    health()


@app.command(name="health")
def health():
    """Check health of all services."""
    services = settings.services
    results = {}

    for name, url in services.items():
        if name in ["redis", "falkordb", "postgres"]:
            # These don't have HTTP health endpoints, skip
            continue
        try:
            health_url = url + "/health" if not url.endswith("/health") else url
            response = httpx.get(health_url, timeout=5)
            results[name] = "✓ UP" if response.status_code == 200 else f"✗ {response.status_code}"
        except Exception as e:
            results[name] = "✗ DOWN"

    click.echo("Service Health:")
    for name, status in results.items():
        click.echo(f"  {name}: {status}")


@app.command(name="status")
def status():
    """Show detailed status of agents and services."""
    health()

    click.echo("\nAgent Status:")
    click.echo("  librarian: " + ("✓ registered" if settings.get("agents.librarian") else "○ not registered"))
    click.echo("  researcher: " + ("✓ registered" if settings.get("agents.researcher") else "○ not registered"))
    click.echo("  consolidator: " + ("✓ registered" if settings.get("agents.consolidator") else "○ not registered"))
    click.echo("  auto-researcher: " + ("✓ registered" if settings.get("agents.auto_researcher") else "○ not registered"))

    # Custom agents
    custom_agents = settings.get("agents.custom", {})
    if custom_agents:
        click.echo("\nCustom Agents:")
        for name in custom_agents:
            click.echo(f"  {name}: ✓ registered")


# Import subcommands
from .config import config_group
from .memory import memory_group
from .agents import agent_group
from .logs import logs_group
from .test import test_command
from .metrics import show_metrics as metrics_command
from .dashboard import open_dashboard as dashboard_command

app.add_command(config_group, name="config")
app.add_command(memory_group, name="memory")
app.add_command(agent_group, name="agent")
app.add_command(logs_group, name="logs")
app.add_command(test_command, name="test")
app.add_command(metrics_command, name="metrics")
app.add_command(dashboard_command, name="dashboard")


if __name__ == "__main__":
    app()
