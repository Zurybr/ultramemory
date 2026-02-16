"""Metrics viewing commands."""

import json
import click
import httpx
import asyncio

from ultramemory_cli.settings import settings


@click.command(name="metrics")
@click.option("--agent", "-a", help="Specific agent metrics")
def show_metrics(agent: str | None):
    """Show metrics from Prometheus."""
    prometheus_url = settings.services.get("prometheus", "http://localhost:9090")

    queries = {
        "api_requests": 'rate(ultramemory_api_requests_total[5m])',
        "memory_usage": 'ultramemory_memory_chunks_total',
        "agent_runs": 'rate(ultramemory_agent_runs_total[5m])',
    }

    async def _fetch():
        async with httpx.AsyncClient() as client:
            for name, query in queries.items():
                if agent and name != f"{agent}_runs":
                    continue

                try:
                    response = await client.get(
                        f"{prometheus_url}/api/v1/query",
                        params={"query": query},
                        timeout=10,
                    )
                    if response.status_code == 200:
                        data = response.json()
                        click.echo(f"{name}: {data.get('status')}")
                except Exception as e:
                    click.echo(f"Error fetching {name}: {e}")

    asyncio.run(_fetch())
