"""Log viewing commands."""

import asyncio
from pathlib import Path
import click

from ultramemory_cli.settings import CONFIG_DIR


@click.group(name="logs")
def logs_group():
    """View logs."""
    pass


@logs_group.command(name="show")
@click.argument("service", required=False, default="all")
@click.option("--lines", "-n", default=50, help="Number of lines")
@click.option("--follow", "-f", is_flag=True, help="Follow logs")
def show_logs(service: str, lines: int, follow: bool):
    """Show logs for a service or all services."""
    logs_dir = CONFIG_DIR / "logs"

    if service == "all":
        # Show latest log file
        log_files = sorted(logs_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if log_files:
            click.echo(f"Showing logs from: {log_files[0]}")
            click.echo("=" * 40)
            content = log_files[0].read_text().splitlines()[-lines:]
            for line in content:
                click.echo(line)
        else:
            click.echo("No logs found.")
    else:
        log_file = logs_dir / f"{service}.log"
        if log_file.exists():
            content = log_file.read_text().splitlines()[-lines:]
            for line in content:
                click.echo(line)
        else:
            click.echo(f"No logs for {service}")


@logs_group.command(name="docker")
@click.argument("service", required=False, default="all")
@click.option("--lines", "-n", default=50)
def show_docker_logs(service: str, lines: int):
    """Show Docker container logs."""
    import subprocess

    if service == "all":
        result = subprocess.run(
            ["docker", "compose", "logs", "--tail", str(lines)],
            capture_output=True,
            text=True,
        )
    else:
        container_name = f"ultramemory-{service}"
        result = subprocess.run(
            ["docker", "logs", "--tail", str(lines), container_name],
            capture_output=True,
            text=True,
        )

    click.echo(result.stdout)
    if result.stderr:
        click.echo(result.stderr, err=True)
