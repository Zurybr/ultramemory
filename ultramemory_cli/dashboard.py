"""Dashboard command."""

import webbrowser

import click

from ultramemory_cli.settings import settings


@click.command(name="dashboard")
@click.option("--port", "-p", default=3000, help="Grafana port")
def open_dashboard(port: int):
    """Open Grafana dashboard."""
    grafana_url = settings.services.get("grafana", f"http://localhost:{port}")

    click.echo(f"Opening dashboard at: {grafana_url}")
    webbrowser.open(grafana_url)
