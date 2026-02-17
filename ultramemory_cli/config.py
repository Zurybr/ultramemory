"""Configuration command for Ultramemory CLI."""

import json
from pathlib import Path

import click

from .settings import settings, CONFIG_DIR


@click.group(name="config")
def config_group():
    """Manage Ultramemory configuration."""
    pass


@config_group.command()
def show():
    """Show current configuration."""
    config = settings.get_all()
    # Hide sensitive data
    if "credentials" in config:
        for service in config["credentials"]:
            if "pass" in config["credentials"][service]:
                config["credentials"][service]["pass"] = "***"
            if "api_key" in config["credentials"][service]:
                config["credentials"][service]["api_key"] = "***"
    click.echo(json.dumps(config, indent=2))


@config_group.command()
def edit():
    """Edit configuration interactively."""
    click.echo("Configuration Editor")
    click.echo("=" * 40)

    # Mode selection
    click.echo("\n1. Connection Mode")
    click.echo("   current: " + settings.mode)
    mode = click.prompt("   Select mode", type=click.Choice(["local", "remote"]), default=settings.mode)
    settings.set("mode", mode)

    # Services configuration
    click.echo("\n2. Services Configuration")
    services = settings.services

    for service_name, default_url in [
        ("api", "http://localhost:8000"),
        ("graphiti", "http://localhost:8001"),
        ("qdrant", "http://localhost:6333"),
        ("redis", "localhost:6379"),
        ("falkordb", "localhost:6370"),
        ("postgres", "localhost:5432"),
        ("grafana", "http://localhost:3000"),
        ("prometheus", "http://localhost:9090"),
    ]:
        current = services.get(service_name, default_url)
        click.echo(f"\n   {service_name}:")
        click.echo(f"   current: {current}")
        new_url = click.prompt(f"   new value (Enter to keep)", default=current)
        settings.set(f"services.{service_name}", new_url)

    # Credentials (only for remote mode)
    if mode == "remote":
        click.echo("\n3. Credentials")
        creds = settings.credentials

        for service in ["postgres", "grafana", "qdrant", "redis"]:
            click.echo(f"\n   {service}:")
            if service in ["postgres", "grafana"]:
                user = click.prompt("     user", default=creds.get(service, {}).get("user", ""))
                password = click.prompt("     password", hide_input=True, default=creds.get(service, {}).get("pass", ""))
                settings.set(f"credentials.{service}", {"user": user, "pass": password})
            elif service == "qdrant":
                api_key = click.prompt("     API key", default=creds.get(service, {}).get("api_key", ""))
                settings.set(f"credentials.{service}", {"api_key": api_key})

    # LLM Provider
    click.echo("\n4. LLM Provider")
    current_llm = settings.get("llm_provider", "openai")
    click.echo(f"   current: {current_llm}")
    llm = click.prompt("   provider", type=click.Choice(["openai", "google", "minimax", "kimi", "groq", "ollama"]), default=current_llm)
    settings.set("llm_provider", llm)

    api_key_var = f"{llm.upper()}_API_KEY"
    api_key = click.prompt(f"   {api_key_var}", default="")
    if api_key:
        settings.set(f"credentials.{llm}.api_key", api_key)

    # Embedding Provider
    click.echo("\n5. Embedding Provider")
    current_emb = settings.get("embedding_provider", "openai")
    click.echo(f"   current: {current_emb}")
    emb = click.prompt("   provider", type=click.Choice(["openai", "google", "minimax", "kimi", "sentence-transformers"]), default=current_emb)
    settings.set("embedding_provider", emb)

    # Vector size (dimensionality)
    click.echo("\n6. Embedding Vector Size")
    current_size = settings.get("embedding_vector_size", 1536)
    click.echo(f"   current: {current_size}")
    click.echo("   Common values: 1536 (OpenAI), 3072 (OpenAI large), 1024 (many models)")
    vector_size = click.prompt("   vector dimensions", default=str(current_size))
    try:
        settings.set("embedding_vector_size", int(vector_size))
    except ValueError:
        click.echo("   Invalid number, keeping current value")

    settings.save()
    click.echo("\nConfiguration saved!")


@config_group.command()
def env():
    """Generate .env file from settings."""
    config = settings.get_all()

    env_content = []
    env_content.append("# Ultramemory Configuration")
    env_content.append(f"LLM_PROVIDER={config.get('llm_provider', 'openai')}")
    env_content.append(f"EMBEDDING_PROVIDER={config.get('embedding_provider', 'openai')}")

    creds = config.get("credentials", {})
    if "openai" in creds and "api_key" in creds["openai"]:
        env_content.append(f"OPENAI_API_KEY={creds['openai']['api_key']}")
    if "google" in creds and "api_key" in creds["google"]:
        env_content.append(f"GOOGLE_API_KEY={creds['google']['api_key']}")
    if "minimax" in creds and "api_key" in creds["minimax"]:
        env_content.append(f"MINIMAX_API_KEY={creds['minimax']['api_key']}")
    if "kimi" in creds and "api_key" in creds["kimi"]:
        env_content.append(f"KIMI_API_KEY={creds['kimi']['api_key']}")

    pg = creds.get("postgres", {})
    env_content.append(f"POSTGRES_USER={pg.get('user', 'postgres')}")
    env_content.append(f"POSTGRES_PASSWORD={pg.get('pass', 'postgres')}")

    redis_cred = creds.get("redis", {})
    env_content.append(f"REDIS_PASSWORD={redis_cred.get('password', '')}")

    grafana_cred = creds.get("grafana", {})
    env_content.append(f"GRAFANA_USER={grafana_cred.get('user', 'admin')}")
    env_content.append(f"GRAFANA_PASSWORD={grafana_cred.get('pass', 'admin')}")

    env_content.append(f"RESEARCHER_SCHEDULE={config.get('researcher_schedule', 'daily')}")
    env_content.append(f"RESEARCHER_OUTPUT_DIR={config.get('researcher_output_dir', './researches')}")

    # Write .env
    env_path = Path(".env")
    env_path.write_text("\n".join(env_content))
    click.echo(f".env file generated at {env_path}")


@config_group.command()
def reset():
    """Reset configuration to defaults."""
    if click.confirm("Reset all configuration to defaults?"):
        settings._settings = settings._default_settings()
        settings.save()
        click.echo("Configuration reset to defaults.")
