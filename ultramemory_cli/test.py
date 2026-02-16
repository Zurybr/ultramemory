"""Test command."""

import click


@click.command(name="test")
def test_command():
    """Test connections."""
    click.echo("Testing connections...")
