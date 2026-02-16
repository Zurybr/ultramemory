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
    """Run consolidation agent to remove duplicates and optimize memory."""
    async def _consolidate():
        memory = MemorySystem()
        consolidator = ConsolidatorAgent(memory)

        # First analyze
        click.echo("🔍 Analyzing memory before consolidation...\n")
        analysis = await consolidator.analyze()

        health = analysis['quality_metrics']['health_score']
        click.echo(f"   Health Score: {health}/100")
        click.echo(f"   Total documents: {analysis['total_documents']}")
        click.echo(f"   Duplicates: {analysis['issues']['duplicates']['count']}")
        click.echo(f"   Empty content: {analysis['issues']['empty_content']['count']}")
        click.echo(f"   Too short: {analysis['issues']['too_short']['count']}")

        # Check if consolidation needed
        needs_consolidation = (
            analysis['issues']['duplicates']['count'] > 0 or
            analysis['issues']['empty_content']['count'] > 0 or
            analysis['issues']['too_short']['count'] > 0
        )

        if needs_consolidation:
            click.echo(f"\n🧹 Running consolidation...")
            result = await consolidator.consolidate()

            click.echo(f"\n✅ Consolidation complete:")
            click.echo(f"   Duplicates removed: {result.get('duplicates_removed', 0)}")
            click.echo(f"   Malformed entries fixed: {result.get('malformed_fixed', 0)}")

            if result.get('errors'):
                click.echo(f"   ⚠️  Errors: {result.get('errors')}")
        else:
            click.echo(f"\n✨ Memory is clean! No consolidation needed.")

    asyncio.run(_consolidate())


@memory_group.command(name="analyze")
def analyze_command():
    """Comprehensive memory analysis - finds duplicates, malformed entries, and quality issues."""
    async def _analyze():
        memory = MemorySystem()
        consolidator = ConsolidatorAgent(memory)

        click.echo("🔍 Analyzing memory...\n")
        result = await consolidator.analyze()

        # Health Score
        health = result['quality_metrics']['health_score']
        if health >= 90:
            health_color = "🟢"
        elif health >= 70:
            health_color = "🟡"
        else:
            health_color = "🔴"

        click.echo(f"📊 Memory Analysis Report")
        click.echo(f"{'='*50}")
        click.echo(f"\n{health_color} Health Score: {health}/100")
        click.echo(f"\n📈 Statistics:")
        click.echo(f"   Total documents: {result['total_documents']}")
        click.echo(f"   Unique content: {result['quality_metrics']['unique_content']}")
        click.echo(f"   Avg content length: {result['quality_metrics']['avg_content_length']:.0f} chars")
        click.echo(f"   Metadata coverage: {result['quality_metrics']['metadata_coverage']:.1f}%")

        # Issues summary
        click.echo(f"\n🔍 Issues Found:")
        issues = result['issues']
        issue_counts = [
            ("  Duplicates", issues['duplicates']['count']),
            ("  Empty content", issues['empty_content']['count']),
            ("  Too short (<10 chars)", issues['too_short']['count']),
            ("  Too long (>100KB)", issues['too_long']['count']),
            ("  Missing metadata", issues['missing_metadata']['count']),
            ("  Encoding issues", issues['encoding_issues']['count']),
            ("  Low quality", issues['low_quality']['count']),
        ]

        has_issues = False
        for name, count in issue_counts:
            if count > 0:
                click.echo(f"  ⚠️  {name}: {count}")
                has_issues = True

        if not has_issues:
            click.echo("  ✅ No issues found!")

        # Recommendations
        click.echo(f"\n💡 Recommendations:")
        for rec in result.get('recommendations', []):
            click.echo(f"   {rec}")

    asyncio.run(_analyze())


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
