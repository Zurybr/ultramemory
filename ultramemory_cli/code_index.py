"""Code index command for CLI."""

import asyncio

import click

from core.memory import MemorySystem
from agents.code_indexer import CodeIndexerAgent, CategoryManager
from .settings import settings


def get_memory_system() -> MemorySystem:
    """Create MemorySystem with settings from config."""
    services = settings.services
    qdrant_url = services.get("qdrant", "http://localhost:6333")
    redis_url = services.get("redis", "localhost:6379")
    falkordb_url = services.get("falkordb", "localhost:6370")
    graphiti_url = services.get("graphiti", "http://localhost:8001")

    # Convert redis host:port to redis:// URL
    if ":" in redis_url and not redis_url.startswith("redis://"):
        host, port = redis_url.rsplit(":", 1)
        redis_url = f"redis://{host}:{port}"

    return MemorySystem(
        qdrant_url=qdrant_url,
        redis_url=redis_url,
        falkordb_url=falkordb_url,
        graphiti_url=graphiti_url,
    )


VALID_CATEGORIES = ["lefarma", "e6labs", "personal", "opensource", "hobby", "trabajo", "dependencias"]


@click.command(name="code-index")
@click.argument("repo_url")
@click.option(
    "-c", "--category",
    type=click.Choice(VALID_CATEGORIES),
    help="Repository category"
)
@click.option(
    "-f", "--force",
    is_flag=True,
    help="Force re-index of all files (ignore existing)"
)
@click.option(
    "-e", "--exclude",
    multiple=True,
    help="Additional exclude patterns"
)
@click.option(
    "-l", "--limit",
    default=None,
    type=int,
    help="Max files to index (no limit by default)"
)
def code_index_command(
    repo_url: str,
    category: str | None,
    force: bool,
    exclude: tuple,
    limit: int
):
    """Index a GitHub repository into memory.

    REPO_URL: GitHub repository URL or owner/repo format

    \b
    Examples:
        ulmemory code-index owner/repo
        ulmemory code-index https://github.com/owner/repo
        ulmemory code-index owner/repo -c opensource
        ulmemory code-index owner/repo -f --limit 50

    \b
    Categories:
        lefarma     - LeFarma project repositories
        e6labs      - E6 Labs project repositories
        personal    - Personal projects
        opensource  - Open source projects
        hobby       - Hobby projects
        trabajo     - Work-related projects
        dependencias - Dependency libraries
    """
    async def _index():
        # Initialize category with provided value
        selected_category = category

        # Validate repo URL
        try:
            from core.github_client import GitHubClient
            gh = GitHubClient()
            owner, repo = gh.parse_repo_url(repo_url)
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            return

        # Get category (default: personal)
        repo_full_name = f"{owner}/{repo}"
        category_mgr = CategoryManager(settings)

        if selected_category is None:
            # Check saved preference
            saved_category = category_mgr.get_category(repo_full_name)
            if saved_category:
                selected_category = saved_category
                click.echo(f"Using saved category: {selected_category}")
            else:
                # Default to personal without prompting
                selected_category = "personal"
                click.echo(f"Category not set, using default: {selected_category}")

        # Confirm indexing
        click.echo(f"\n{'='*50}")
        click.echo(f"Indexing: {repo_full_name}")
        click.echo(f"Category: {selected_category}")
        click.echo(f"Force re-index: {force}")
        click.echo(f"Max files: {limit if limit else 'No limit (all files)'}")
        click.echo(f"{'='*50}\n")

        # Run indexing
        try:
            memory = get_memory_system()
            indexer = CodeIndexerAgent(memory)

            result = await indexer.index(
                repo_url=repo_url,
                category=selected_category,
                force=force,
                exclude_patterns=list(exclude) if exclude else None,
                limit=limit
            )

            # Show results
            click.echo(f"\n{'='*50}")
            click.echo(f"Indexing complete!")
            click.echo(f"  Repository: {result['repo']}")
            click.echo(f"  Category: {result['category']}")
            click.echo(f"  Files indexed: {result['files_indexed']}")
            click.echo(f"  Files skipped: {result['files_skipped']}")
            click.echo(f"  Total files: {result['total_files']}")

            if result.get("codewiki_available"):
                click.echo(f"  CodeWiki: Available")

            if result['errors']:
                click.echo(f"\nErrors ({len(result['errors'])}):")
                for err in result['errors'][:5]:
                    click.echo(f"    - {err['file']}: {err['error']}")

            # Save category preference
            category_mgr.set_category(repo_full_name, selected_category)
            click.echo(f"\nCategory saved: {selected_category}")

        except Exception as e:
            click.echo(f"Error during indexing: {e}", err=True)
            raise

    asyncio.run(_index())
