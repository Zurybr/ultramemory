"""Memory operations for CLI."""

import asyncio
from pathlib import Path

import click

from core.memory import MemorySystem
from agents.librarian import LibrarianAgent
from agents.researcher import ResearcherAgent
from agents.consolidator import ConsolidatorAgent
from agents.auto_researcher import AutoResearcherAgent


@click.group(name="memory")
def memory_group():
    """Memory operations (add, query, consolidate)."""
    pass


@memory_group.command(name="add")
@click.argument("content")
@click.option("--metadata", "-m", multiple=True, help="Metadata as key=value pairs")
def add_command(content: str, metadata: tuple):
    """Add content to memory.

    CONTENT can be text, file path, or URL.
    """
    # Parse metadata
    meta = {}
    for item in metadata:
        if "=" in item:
            key, value = item.split("=", 1)
            meta[key] = value

    async def _add():
        memory = MemorySystem()
        librarian = LibrarianAgent(memory)

        path = Path(content)
        if path.exists():
            result = await librarian.add(path, meta)
        else:
            result = await librarian.add(content, meta)

        click.echo(f"Added: {result['chunks_created']} chunks created")

    asyncio.run(_add())


@memory_group.command(name="query")
@click.argument("query")
@click.option("--limit", "-l", default=5, help="Number of results")
def query_command(query: str, limit: int):
    """Query memory system."""
    async def _query():
        memory = MemorySystem()
        researcher = ResearcherAgent(memory)

        result = await researcher.query(query, limit)

        click.echo(f"\nFound {len(result['results'])} results:\n")
        for i, r in enumerate(result["results"], 1):
            click.echo(f"{i}. {r.get('content', '')[:200]}...")
            click.echo(f"   Score: {r.get('score', 'N/A')}\n")

    asyncio.run(_query())


@memory_group.command(name="consolidate")
def consolidate_command():
    """Run consolidation agent."""
    async def _consolidate():
        memory = MemorySystem()
        consolidator = ConsolidatorAgent(memory)

        result = await consolidator.consolidate()

        click.echo(f"Consolidation complete:")
        click.echo(f"  Duplicates removed: {result.get('duplicates_removed', 0)}")
        click.echo(f"  Entities merged: {result.get('entities_merged', 0)}")

    asyncio.run(_consolidate())


@memory_group.command(name="research")
@click.option("--topics", "-t", multiple=True, help="Topics to research")
@click.option("--output", "-o", default="./researches", help="Output directory")
def research_command(topics: tuple, output: str):
    """Run auto-researcher agent."""
    async def _research():
        memory = MemorySystem()
        researcher = AutoResearcherAgent(memory)

        topic_list = list(topics)
        result = await researcher.research(topic_list, output)

        click.echo(f"Research complete. Output: {result['output_dir']}")

    asyncio.run(_research())
