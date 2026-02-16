"""Dashboard command."""

import webbrowser

import click

from ultramemory_cli.settings import settings


@click.command(name="dashboard")
@click.option("--port", "-p", default=3000, help="Grafana port")
def open_dashboard(port: int):
    """Open Grafana dashboard."""
    grafana_url = settings.services.get("grafana", f"http://localhost:{port}")

    # Get credentials from settings
    grafana_creds = settings.credentials.get("grafana", {})
    username = grafana_creds.get("user", "admin")
    password = grafana_creds.get("pass", "admin")

    click.echo("\n╔══════════════════════════════════════════════════════╗")
    click.echo("║               📊 GRAFANA DASHBOARD                   ║")
    click.echo("╚══════════════════════════════════════════════════════╝")
    click.echo(f"\n  🔗 URL:      {grafana_url}")
    click.echo(f"  👤 Usuario:  {username}")
    click.echo(f"  🔑 Password: {password}")
    click.echo("\n  ⚠️  Cambia las credenciales por defecto en producción!")
    click.echo("")

    webbrowser.open(grafana_url)
