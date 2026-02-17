"""Memory operations for CLI."""

import asyncio
from pathlib import Path

import click

from core.memory import MemorySystem
from agents.librarian import LibrarianAgent
from agents.researcher import ResearcherAgent
from agents.consolidator import ConsolidatorAgent
from agents.auto_researcher import AutoResearcherAgent
from agents.deleter import DeleterAgent


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

        # Check if content is a valid file path (but handle very long texts gracefully)
        try:
            path = Path(content)
            # Only treat as file if it exists AND path length is reasonable (< 500 chars)
            # This prevents "File name too long" errors with long text content
            if path.exists() and len(content) < 500:
                result = await librarian.add(path, meta)
            else:
                result = await librarian.add(content, meta)
        except (OSError, ValueError):
            # If Path() fails for any reason (long filenames, special chars, etc.), treat as text
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
            click.echo(f"\n🧹 Running DEEP consolidation...")
            result = await consolidator.consolidate()

            click.echo(f"\n✅ Consolidation complete:")
            click.echo(f"   Duplicates removed: {result.get('duplicates_removed', 0)}")
            click.echo(f"   Malformed entries fixed: {result.get('malformed_fixed', 0)}")
            click.echo(f"   Graph nodes synced: {result.get('nodes_synced', 0)}")
            click.echo(f"   Graph links created: {result.get('links_created', 0)}")
            click.echo(f"   Insights generated: {result.get('insights_generated', 0)}")

            # Show graph insights
            graph_insights = result.get('graph_insights', [])
            if graph_insights:
                click.echo(f"\n🔗 Graph Insights:")
                for insight in graph_insights:
                    click.echo(f"   • {insight}")

            # Show summary if available
            summary = result.get('analysis_summary', {})
            if summary:
                click.echo(f"\n📊 Analysis Summary:")
                click.echo(f"   Total docs: {summary.get('total_docs', 'N/A')}")
                click.echo(f"   Graph nodes: {summary.get('graph_nodes', 'N/A')}")
                click.echo(f"   Graph relations: {summary.get('graph_relations', 'N/A')}")

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


@memory_group.command(name="delete-all")
@click.option("--confirm", is_flag=True, help="Confirm deletion of ALL memories")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
def delete_all_command(confirm: bool, force: bool):
    """Delete ALL memories from the system.

    ⚠️ WARNING: This is irreversible!

    \b
    Examples:
        ulmemory memory delete-all --confirm       # Interactive confirmation
        ulmemory memory delete-all --confirm -f    # No prompt, just delete
        ulmemory memory delete-all                 # Preview only
    """
    async def _delete():
        memory = MemorySystem()
        deleter = DeleterAgent(memory)

        # Show count first
        count = await deleter.count()
        click.echo(f"\n📊 Total memories: {count}")

        if not confirm:
            click.echo("\n⚠️  Dry run - no memories deleted")
            click.echo("   Use --confirm to actually delete")
            return

        if not force:
            if not click.confirm(f"\n⚠️  Delete ALL {count} memories? This cannot be undone!"):
                click.echo("Cancelled.")
                return

        result = await deleter.delete_all(confirm=True)

        if result["status"] == "success":
            click.echo(f"\n✅ Deleted {result['qdrant_deleted']} memories")
        else:
            click.echo(f"\n❌ Error: {result.get('errors', 'Unknown error')}")

    asyncio.run(_delete())


@memory_group.command(name="delete")
@click.argument("query")
@click.option("--limit", "-l", default=10, help="Max memories to delete")
@click.option("--confirm", is_flag=True, help="Confirm deletion")
def delete_command(query: str, limit: int, confirm: bool):
    """Delete memories matching a search query.

    \b
    Examples:
        ulmemory memory delete "test"           # Preview matches
        ulmemory memory delete "test" --confirm # Delete matches
        ulmemory memory delete "test" -l 5      # Max 5 deletions
    """
    async def _delete():
        memory = MemorySystem()
        deleter = DeleterAgent(memory)

        if not confirm:
            # Just show what would be deleted
            from agents.researcher import ResearcherAgent
            researcher = ResearcherAgent(memory)
            results = await researcher.query(query, limit=limit)

            click.echo(f"\n🔍 Found {len(results['results'])} memories matching '{query}':")
            for i, r in enumerate(results["results"], 1):
                content = r.get("content", "")[:80]
                click.echo(f"   {i}. {content}...")

            click.echo(f"\n💡 Use --confirm to delete these memories")
        else:
            result = await deleter.delete_by_query(query, limit=limit)

            if result["status"] == "success":
                click.echo(f"\n✅ Deleted {result['deleted']} memories matching '{query}'")
            else:
                click.echo(f"\n❌ Error: {result.get('errors', 'Unknown error')}")

    asyncio.run(_delete())


@memory_group.command(name="count")
def count_command():
    """Count total memories in the system."""
    async def _count():
        memory = MemorySystem()
        deleter = DeleterAgent(memory)
        count = await deleter.count()
        click.echo(f"\n📊 Total memories: {count}")

    asyncio.run(_count())
