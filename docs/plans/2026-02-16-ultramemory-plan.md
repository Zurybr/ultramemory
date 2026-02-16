# Ultramemory Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a hybrid memory system with CLI for multi-agent management (Librarian, Researcher, Consolidator, Auto-Researcher) using Graphiti, Qdrant, Redis, PostgreSQL orchestrated with LangGraph.

**Architecture:** Three-tier architecture: CLI (Python/Click) → FastAPI → LangGraph agents → Memory layer (Graphiti + Qdrant + Redis) + Data layer (PostgreSQL)

**Tech Stack:** Python, Click, FastAPI, LangGraph, Graphiti, Qdrant, Redis/Valkey, PostgreSQL, Grafana, Prometheus

---

## Phase 1: Project Scaffolding

### Task 1: Create project structure

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `LICENSE`
- Create: `.gitignore`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "ultramemory"
version = "0.1.0"
description = "Hybrid memory system with multi-agent CLI for AI agents"
authors = [{name = "Brandom Ledema"}]
requires-python = ">=3.11"
dependencies = [
    "click>=8.1.0",
    "typer>=0.12.0",
    "fastapi>=0.110.0",
    "uvicorn>=0.27.0",
    "langgraph>=0.2.0",
    "langchain>=0.2.0",
    "langchain-openai>=0.1.0",
    "langchain-google-genai>=0.1.0",
    "qdrant-client>=1.7.0",
    "redis>=5.0.0",
    "psycopg2-binary>=2.9.0",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.1.0",
    "python-dotenv>=1.0.0",
    "pyyaml>=6.0.0",
    "httpx>=0.27.0",
    "python-multipart>=0.0.9",
    "pymupdf>=1.23.0",
    "pandas>=2.2.0",
    "openpyxl>=3.1.0",
    "beautifulsoup4>=4.12.0",
    "requests>=2.31.0",
    "pillow>=10.2.0",
    "moviepy>=1.0.3",
]

[project.scripts]
ulmemory = "ultramemory_cli.main:app"

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
```

**Step 2: Create .gitignore**

```
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/
.ulmemory/
*.log
.coverage
htmlcov/
.pytest_cache/
.mypy_cache/
.DS_Store
```

**Step 3: Create basic README.md**

```markdown
# Ultramemory

Hybrid memory system with multi-agent CLI for AI agents.

## Quick Start

```bash
git clone https://github.com/brandom/ultramemory
cd ultramemory
./install-cli.sh
ulmemory up
```
```

**Step 4: Commit**

```bash
git init
git add .
git commit -m "chore: initial project scaffolding"
```

---

### Task 2: Create .env.example and docker-compose.yml

**Files:**
- Create: `.env.example`
- Create: `docker-compose.yml`
- Create: `docker/grafana/dashboard.json`
- Create: `docker/prometheus/prometheus.yml`

**Step 1: Create .env.example**

```bash
# Ultramemory Configuration

# LLM Provider (openai, google, minimax, kimi, groq, ollama)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o

# Embedding Provider
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small

# API Keys
OPENAI_API_KEY=
GOOGLE_API_KEY=
MINIMAX_API_KEY=
KIMI_API_KEY=
GROQ_API_KEY=

# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=ultramemory

# Redis
REDIS_PASSWORD=

# Qdrant
QDRANT_API_KEY=

# Grafana
GRAFANA_USER=admin
GRAFANA_PASSWORD=admin

# Researcher Config
RESEARCHER_TOPICS=
RESEARCHER_SCHEDULE=daily
RESEARCHER_OUTPUT_DIR=./researches
```

**Step 2: Create docker-compose.yml**

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: ultramemory-postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-ultramemory}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: ultramemory-redis
    command: redis-server --requirepass ${REDIS_PASSWORD:-}
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  qdrant:
    image: qdrant/qdrant:v1.16.0
    container_name: ultramemory-qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      QDRANT__SERVICE__API_KEY: ${QDRANT_API_KEY:-}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  falkordb:
    image: ghcr.io/falkordb/falkordb:latest
    container_name: ultramemory-falkordb
    ports:
      - "6370:6379"
    volumes:
      - falkordb_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    container_name: ultramemory-api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@postgres:5432/${POSTGRES_DB:-ultramemory}
      - REDIS_URL=redis://:${REDIS_PASSWORD:-}@redis:6379
      - QDRANT_URL=http://qdrant:6333
      - FALKORDB_URL=redis://falkordb:6379
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      qdrant:
        condition: service_healthy
      falkordb:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  prometheus:
    image: prom/prometheus:latest
    container_name: ultramemory-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./docker/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:9090/-/healthy"]
      interval: 10s
      timeout: 5s
      retries: 5

  grafana:
    image: grafana/grafana:latest
    container_name: ultramemory-grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_USER: ${GRAFANA_USER:-admin}
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./docker/grafana/dashboard.json:/var/lib/grafana/dashboards/ultramemory.json
    depends_on:
      - prometheus

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
  falkordb_data:
  prometheus_data:
  grafana_data:
```

**Step 3: Create prometheus config**

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'ultramemory-api'
    static_configs:
      - targets: ['api:8000']
```

**Step 4: Create Grafana dashboard placeholder**

```json
{
  "dashboard": {
    "title": "Ultramemory",
    "tags": ["ultramemory"],
    "timezone": "browser",
    "panels": []
  }
}
```

**Step 5: Commit**

```bash
git add .env.example docker-compose.yml docker/
git commit -m "chore: add docker-compose and config templates"
```

---

## Phase 2: CLI Core

### Task 3: Install CLI script

**Files:**
- Create: `install-cli.sh`
- Modify: `pyproject.toml` (add console_scripts)

**Step 1: Create install-cli.sh**

```bash
#!/bin/bash
set -e

echo "Installing Ultramemory CLI..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3.11+ is required"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Error: Python $REQUIRED_VERSION or higher is required"
    exit 1
fi

# Create config directory
CONFIG_DIR="$HOME/.ulmemory"
mkdir -p "$CONFIG_DIR"
mkdir -p "$CONFIG_DIR/agents"
mkdir -p "$CONFIG_DIR/logs"

echo "Config directory: $CONFIG_DIR"

# Install package in editable mode
echo "Installing ultramemory package..."
pip install -e .

# Create default settings if not exists
if [ ! -f "$CONFIG_DIR/settings.json" ]; then
    cat > "$CONFIG_DIR/settings.json" << 'EOF'
{
  "mode": "local",
  "services": {
    "api": "http://localhost:8000",
    "graphiti": "http://localhost:8001",
    "qdrant": "http://localhost:6333",
    "redis": "localhost:6379",
    "falkordb": "localhost:6370",
    "postgres": "localhost:5432",
    "grafana": "http://localhost:3000",
    "prometheus": "http://localhost:9090"
  },
  "credentials": {
    "postgres": {"user": "postgres", "pass": "postgres"},
    "grafana": {"user": "admin", "pass": "admin"},
    "qdrant": {"api_key": ""},
    "redis": {"password": ""}
  },
  "llm_provider": "openai",
  "embedding_provider": "openai",
  "researcher_topics": [],
  "researcher_schedule": "daily",
  "researcher_output_dir": "./researches"
}
EOF
    echo "Default settings created at $CONFIG_DIR/settings.json"
fi

echo ""
echo "Installation complete!"
echo "Run 'ulmemory --help' to get started"
```

**Step 2: Make executable**

```bash
chmod +x install-cli.sh
```

**Step 3: Commit**

```bash
git add install-cli.sh
git commit -m "feat: add install-cli.sh script"
```

---

### Task 4: CLI Structure - Main app and config

**Files:**
- Create: `ultramemory_cli/__init__.py`
- Create: `ultramemory_cli/main.py`
- Create: `ultramemory_cli/config.py`
- Create: `ultramemory_cli/settings.py`

**Step 1: Create ultramemory_cli/__init__.py**

```python
"""Ultramemory CLI - Hybrid memory system with multi-agent management."""

__version__ = "0.1.0"
```

**Step 2: Create ultramemory_cli/settings.py**

```python
"""Settings management for Ultramemory CLI."""

import json
import os
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".ulmemory"
SETTINGS_FILE = CONFIG_DIR / "settings.json"


class Settings:
    """Manage CLI settings."""

    def __init__(self):
        self._settings: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load settings from file."""
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE) as f:
                self._settings = json.load(f)
        else:
            self._settings = self._default_settings()
            self.save()

    def _default_settings(self) -> dict[str, Any]:
        """Return default settings."""
        return {
            "mode": "local",
            "services": {
                "api": "http://localhost:8000",
                "graphiti": "http://localhost:8001",
                "qdrant": "http://localhost:6333",
                "redis": "localhost:6379",
                "falkordb": "localhost:6370",
                "postgres": "localhost:5432",
                "grafana": "http://localhost:3000",
                "prometheus": "http://localhost:9090",
            },
            "credentials": {
                "postgres": {"user": "postgres", "pass": "postgres"},
                "grafana": {"user": "admin", "pass": "admin"},
                "qdrant": {"api_key": ""},
                "redis": {"password": ""},
            },
            "llm_provider": "openai",
            "embedding_provider": "openai",
            "researcher_topics": [],
            "researcher_schedule": "daily",
            "researcher_output_dir": "./researches",
        }

    def save(self) -> None:
        """Save settings to file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self._settings, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """Get setting by key (supports dot notation)."""
        keys = key.split(".")
        value = self._settings
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def set(self, key: str, value: Any) -> None:
        """Set setting by key (supports dot notation)."""
        keys = key.split(".")
        target = self._settings
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value

    def get_all(self) -> dict[str, Any]:
        """Get all settings."""
        return self._settings.copy()

    @property
    def mode(self) -> str:
        return self._settings.get("mode", "local")

    @mode.setter
    def mode(self, value: str):
        self._settings["mode"] = value
        self.save()

    @property
    def services(self) -> dict[str, str]:
        return self._settings.get("services", {})

    @property
    def credentials(self) -> dict[str, Any]:
        return self._settings.get("credentials", {})


settings = Settings()
```

**Step 3: Create ultramemory_cli/config.py**

```python
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
```

**Step 4: Create ultramemory_cli/main.py**

```python
"""Main CLI application for Ultramemory."""

import subprocess
import sys
from pathlib import Path

import click

from .settings import settings


@click.group()
@click.version_option(version="0.1.0")
def app():
    """Ultramemory - Hybrid memory system with multi-agent CLI."""
    pass


# Service Management Commands
@app.command(name="up")
@click.argument("path", default=".", required=False)
def up(path: str):
    """Start Ultramemory services."""
    click.echo("Starting Ultramemory services...")

    # Check if docker is available
    try:
        subprocess.run(["docker", "compose", "version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        click.echo("Error: docker compose not found. Please install Docker.", err=True)
        sys.exit(1)

    compose_file = Path(path) / "docker-compose.yml"
    if not compose_file.exists():
        click.echo(f"Error: docker-compose.yml not found in {path}", err=True)
        sys.exit(1)

    result = subprocess.run(["docker", "compose", "-f", str(compose_file), "up", "-d"], cwd=path)
    if result.returncode == 0:
        click.echo("Services started successfully!")
        health()
    else:
        click.echo("Failed to start services.", err=True)
        sys.exit(1)


@app.command(name="down")
@click.argument("path", default=".", required=False)
def down(path: str):
    """Stop Ultramemory services."""
    compose_file = Path(path) / "docker-compose.yml"
    result = subprocess.run(["docker", "compose", "-f", str(compose_file), "down"], cwd=path)
    if result.returncode == 0:
        click.echo("Services stopped.")
    else:
        click.echo("Failed to stop services.", err=True)


@app.command(name="restart")
@click.argument("path", default=".", required=False)
def restart(path: str):
    """Restart Ultramemory services."""
    compose_file = Path(path) / "docker-compose.yml"
    subprocess.run(["docker", "compose", "-f", str(compose_file), "restart"], cwd=path)
    click.echo("Services restarted.")
    health()


@app.command(name="health")
def health():
    """Check health of all services."""
    import httpx

    services = settings.services
    results = {}

    for name, url in services.items():
        if name in ["redis", "falkordb", "postgres"]:
            # These don't have HTTP health endpoints, skip
            continue
        try:
            health_url = url + "/health" if not url.endswith("/health") else url
            response = httpx.get(health_url, timeout=5)
            results[name] = "✓ UP" if response.status_code == 200 else f"✗ {response.status_code}"
        except Exception as e:
            results[name] = f"✗ DOWN"

    click.echo("Service Health:")
    for name, status in results.items():
        click.echo(f"  {name}: {status}")


@app.command(name="status")
def status():
    """Show detailed status of agents and services."""
    health()

    click.echo("\nAgent Status:")
    click.echo("  librarian: " + ("✓ registered" if settings.get("agents.librarian") else "○ not registered"))
    click.echo("  researcher: " + ("✓ registered" if settings.get("agents.researcher") else "○ not registered"))
    click.echo("  consolidator: " + ("✓ registered" if settings.get("agents.consolidator") else "○ not registered"))
    click.echo("  auto-researcher: " + ("✓ registered" if settings.get("agents.auto_researcher") else "○ not registered"))

    # Custom agents
    custom_agents = settings.get("agents.custom", {})
    if custom_agents:
        click.echo("\nCustom Agents:")
        for name in custom_agents:
            click.echo(f"  {name}: ✓ registered")


# Import subcommands
from .config import config_group
from .memory import memory_group
from .agents import agent_group
from .logs import logs_group
from .test import test_command
from .metrics import metrics_command
from .dashboard import dashboard_command

app.add_command(config_group, name="config")
app.add_command(memory_group, name="memory")
app.add_command(agent_group, name="agent")
app.add_command(logs_group, name="logs")
app.add_command(test_command, name="test")
app.add_command(metrics_command, name="metrics")
app.add_command(dashboard_command, name="dashboard")


if __name__ == "__main__":
    app()
```

**Step 5: Create placeholder modules (will be implemented in later tasks)**

```python
# ultramemory_cli/memory.py
import click

@click.group(name="memory")
def memory_group():
    """Memory operations (add, query, consolidate)."""
    pass
```

```python
# ultramemory_cli/agents.py
import click

@click.group(name="agent")
def agent_group():
    """Agent management commands."""
    pass
```

```python
# ultramemory_cli/logs.py
import click

@click.group(name="logs")
def logs_group():
    """View logs."""
    pass
```

```python
# ultramemory_cli/test.py
import click

@click.command(name="test")
def test_command():
    """Test connections."""
    click.echo("Testing connections...")
```

```python
# ultramemory_cli/metrics.py
import click

@click.command(name="metrics")
def metrics_command():
    """Show metrics."""
    click.echo("Metrics coming soon...")
```

```python
# ultramemory_cli/dashboard.py
import click

@click.command(name="dashboard")
def dashboard_command():
    """Open Grafana dashboard."""
    import webbrowser
    import settings
    webbrowser.open(settings.services.get("grafana", "http://localhost:3000"))
```

**Step 6: Commit**

```bash
git add ultramemory_cli/
git commit -m "feat: add CLI core structure"
```

---

## Phase 3: Memory Layer (Graphiti, Qdrant, Redis)

### Task 5: Core memory integration

**Files:**
- Create: `core/__init__.py`
- Create: `core/memory.py`
- Create: `core/graphiti_client.py`
- Create: `core/qdrant_client.py`
- Create: `core/redis_client.py`

**Step 1: Create core/memory.py**

```python
"""Core memory module integrating Graphiti, Qdrant, and Redis."""

from typing import Any
from .graphiti_client import GraphitiClient
from .qdrant_client import QdrantClientWrapper
from .redis_client import RedisClientWrapper


class MemorySystem:
    """Hybrid memory system combining Graphiti, Qdrant, and Redis."""

    def __init__(
        self,
        graphiti_url: str = "http://localhost:8001",
        qdrant_url: str = "http://localhost:6333",
        redis_url: str = "redis://localhost:6379",
        embedding_model: str = "text-embedding-3-small",
    ):
        self.graphiti = GraphitiClient(graphiti_url)
        self.qdrant = QdrantClientWrapper(qdrant_url)
        self.redis = RedisClientWrapper(redis_url)
        self.embedding_model = embedding_model

    async def add(self, content: str, metadata: dict[str, Any] | None = None) -> str:
        """Add content to memory system."""
        # 1. Generate embedding
        embedding = await self._generate_embedding(content)

        # 2. Add to Qdrant (vector search)
        doc_id = await self.qdrant.add(embedding, content, metadata or {})

        # 3. Add to Graphiti (temporal graph)
        episode_id = await self.graphiti.add_episode(content, metadata or {})

        # 4. Cache in Redis
        await self.redis.set(f"doc:{doc_id}", content, ex=3600)

        return doc_id

    async def query(self, query_text: str, limit: int = 5) -> list[dict[str, Any]]:
        """Query memory system."""
        # 1. Generate embedding for query
        embedding = await self._generate_embedding(query_text)

        # 2. Search Qdrant
        results = await self.qdrant.search(embedding, limit)

        # 3. Search Graphiti for temporal context
        graph_results = await self.graphiti.search(query_text, limit)

        return {
            "vector_results": results,
            "graph_results": graph_results,
        }

    async def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for text (placeholder - to be implemented with LangChain)."""
        # Will be implemented with LangChain
        pass
```

**Step 2: Create core/graphiti_client.py**

```python
"""Graphiti client for temporal graph memory."""

import httpx
from typing import Any


class GraphitiClient:
    """Client for Graphiti API."""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def add_episode(self, content: str, metadata: dict[str, Any]) -> str:
        """Add an episode to the graph."""
        response = await self.client.post(
            f"{self.base_url}/episodes",
            json={"content": content, "metadata": metadata},
        )
        response.raise_for_status()
        return response.json()["episode_id"]

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search the graph."""
        response = await self.client.post(
            f"{self.base_url}/search",
            json={"query": query, "limit": limit},
        )
        response.raise_for_status()
        return response.json()["results"]

    async def get_history(self, entity_name: str, time_range: str | None = None) -> list[dict[str, Any]]:
        """Get entity history within time range."""
        params = {"entity_name": entity_name}
        if time_range:
            params["time_range"] = time_range

        response = await self.client.get(
            f"{self.base_url}/entities/history",
            params=params,
        )
        response.raise_for_status()
        return response.json()["history"]

    async def consolidate(self) -> dict[str, Any]:
        """Trigger graph consolidation."""
        response = await self.client.post(f"{self.base_url}/consolidate")
        response.raise_for_status()
        return response.json()

    async def health(self) -> bool:
        """Check if Graphiti is healthy."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        """Close the client."""
        await self.client.aclose()
```

**Step 3: Create core/qdrant_client.py**

```python
"""Qdrant client wrapper for vector search."""

from typing import Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid


class QdrantClientWrapper:
    """Wrapper for Qdrant client."""

    def __init__(self, url: str = "http://localhost:6333", api_key: str | None = None):
        self.client = QdrantClient(url=url, api_key=api_key)
        self.collection_name = "ultramemory"

    async def ensure_collection(self, vector_size: int = 1536):
        """Ensure collection exists."""
        collections = self.client.get_collections().collections
        if self.collection_name not in [c.name for c in collections]:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

    async def add(self, embedding: list[float], content: str, metadata: dict[str, Any]) -> str:
        """Add a vector to Qdrant."""
        point_id = str(uuid.uuid4())

        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={"content": content, "metadata": metadata},
                )
            ],
        )

        return point_id

    async def search(self, query_embedding: list[float], limit: int = 5) -> list[dict[str, Any]]:
        """Search vectors."""
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
        )

        return [
            {
                "id": r.id,
                "score": r.score,
                "content": r.payload.get("content"),
                "metadata": r.payload.get("metadata", {}),
            }
            for r in results
        ]

    async def delete(self, point_id: str):
        """Delete a vector."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=[point_id],
        )

    async def health(self) -> bool:
        """Check if Qdrant is healthy."""
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False
```

**Step 4: Create core/redis_client.py**

```python
"""Redis client wrapper for caching and pub/sub."""

import json
from typing import Any
import redis.asyncio as redis


class RedisClientWrapper:
    """Wrapper for Redis client."""

    def __init__(self, url: str = "redis://localhost:6379", password: str | None = None):
        if password:
            url = url.replace("redis://", f"redis://:{password}@")
        self.redis = redis.from_url(url, decode_responses=True)

    async def set(self, key: str, value: Any, ex: int | None = None):
        """Set a value."""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await self.redis.set(key, value, ex=ex)

    async def get(self, key: str) -> Any | None:
        """Get a value."""
        value = await self.redis.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    async def delete(self, key: str):
        """Delete a key."""
        await self.redis.delete(key)

    async def keys(self, pattern: str = "*") -> list[str]:
        """Get keys matching pattern."""
        return await self.redis.keys(pattern)

    async def publish(self, channel: str, message: Any):
        """Publish a message."""
        if isinstance(message, (dict, list)):
            message = json.dumps(message)
        await self.redis.publish(channel, message)

    async def subscribe(self, channel: str):
        """Subscribe to a channel."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        return pubsub

    async def health(self) -> bool:
        """Check if Redis is healthy."""
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False

    async def close(self):
        """Close the connection."""
        await self.redis.close()
```

**Step 5: Commit**

```bash
git add core/
git commit -m "feat: add core memory layer (Graphiti, Qdrant, Redis clients)"
```

---

## Phase 4: Agents Implementation

### Task 6: Librarian Agent (add)

**Files:**
- Create: `agents/librarian.py`
- Modify: `ultramemory_cli/memory.py`

**Step 1: Create agents/librarian.py**

```python
"""Librarian Agent - inserts information into memory."""

from typing import Any
from pathlib import Path

from core.memory import MemorySystem
from core.document_processor import DocumentProcessor


class LibrarianAgent:
    """Agent responsible for organizing and inserting information into memory."""

    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system
        self.processor = DocumentProcessor()

    async def add(self, content: str | Path, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Add content to memory.

        Args:
            content: Text, file path, or URL
            metadata: Optional metadata for the content

        Returns:
            Result with document_id and chunks created
        """
        # 1. Process content (detect type, extract text)
        processed = await self.processor.process(content)

        # 2. Chunk if needed
        chunks = self.processor.chunk(processed["text"])

        # 3. Add each chunk to memory
        results = []
        for i, chunk in enumerate(chunks):
            doc_id = await self.memory.add(
                chunk,
                metadata={
                    **(metadata or {}),
                    "source": str(content),
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
            )
            results.append({"chunk": i + 1, "doc_id": doc_id})

        return {
            "status": "success",
            "chunks_created": len(chunks),
            "document_id": results[0]["doc_id"] if results else None,
        }

    async def add_from_directory(self, directory: Path, extensions: list[str] | None = None) -> dict[str, Any]:
        """Add all files from a directory."""
        if extensions is None:
            extensions = [".txt", ".pdf", ".md", ".html", ".xlsx", ".csv"]

        results = []
        for ext in extensions:
            for file_path in directory.rglob(f"*{ext}"):
                try:
                    result = await self.add(file_path)
                    results.append({"file": str(file_path), "status": "success", **result})
                except Exception as e:
                    results.append({"file": str(file_path), "status": "error", "error": str(e)})

        return {
            "status": "success",
            "files_processed": len(results),
            "results": results,
        }
```

**Step 2: Create core/document_processor.py**

```python
"""Document processor for various file types."""

import re
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import pandas as pd
from bs4 import BeautifulSoup
import requests


class DocumentProcessor:
    """Process various document types into plain text."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    async def process(self, content: str | Path) -> dict[str, Any]:
        """Process content and extract text.

        Args:
            content: Text string, file path, or URL

        Returns:
            Dict with 'text', 'type', and 'metadata'
        """
        content_str = str(content)

        # URL
        if content_str.startswith(("http://", "https://")):
            return await self._process_url(content_str)

        # File path
        path = Path(content)
        if path.exists() and path.is_file():
            return await self._process_file(path)

        # Plain text
        return {"text": content_str, "type": "text", "metadata": {}}

    async def _process_url(self, url: str) -> dict[str, Any]:
        """Process URL and extract text."""
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove scripts and styles
        for tag in soup(["script", "style"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)

        return {"text": text, "type": "url", "metadata": {"url": url}}

    async def _process_file(self, path: Path) -> dict[str, Any]:
        """Process file based on extension."""
        ext = path.suffix.lower()

        if ext == ".pdf":
            return await self._process_pdf(path)
        elif ext in [".txt", ".md"]:
            return {"text": path.read_text(encoding="utf-8"), "type": "text", "metadata": {"filename": path.name}}
        elif ext in [".xlsx", ".xls"]:
            return await self._process_excel(path)
        elif ext == ".csv":
            return await self._process_csv(path)
        elif ext == ".html":
            return await self._process_html(path)
        else:
            return {"text": str(path), "type": "unknown", "metadata": {"filename": path.name}}

    async def _process_pdf(self, path: Path) -> dict[str, Any]:
        """Process PDF file."""
        text_parts = []
        with fitz.open(path) as doc:
            for page in doc:
                text_parts.append(page.get_text())

        return {"text": "\n".join(text_parts), "type": "pdf", "metadata": {"filename": path.name}}

    async def _process_excel(self, path: Path) -> dict[str, Any]:
        """Process Excel file."""
        dfs = pd.read_excel(path, sheet_name=None)
        text_parts = []

        for sheet_name, df in dfs.items():
            text_parts.append(f"## Sheet: {sheet_name}\n")
            text_parts.append(df.to_csv(index=False))

        return {"text": "\n".join(text_parts), "type": "excel", "metadata": {"filename": path.name}}

    async def _process_csv(self, path: Path) -> dict[str, Any]:
        """Process CSV file."""
        df = pd.read_csv(path)
        return {"text": df.to_csv(index=False), "type": "csv", "metadata": {"filename": path.name}}

    async def _process_html(self, path: Path) -> dict[str, Any]:
        """Process HTML file."""
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")

        for tag in soup(["script", "style"]):
            tag.decompose()

        return {"text": soup.get_text(separator="\n", strip=True), "type": "html", "metadata": {"filename": path.name}}

    def chunk(self, text: str) -> list[str]:
        """Split text into overlapping chunks."""
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []

        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                last_period = text.rfind(".", start, end)
                last_newline = text.rfind("\n", start, end)
                break_point = max(last_period, last_newline)

                if break_point > start:
                    end = break_point + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - self.chunk_overlap

        return chunks
```

**Step 3: Update ultramemory_cli/memory.py**

```python
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
```

**Step 4: Commit**

```bash
git add agents/ core/document_processor.py
git commit -m "feat: add Librarian agent and document processor"
```

---

### Task 7: Researcher Agent (query)

**Files:**
- Create: `agents/researcher.py`
- Modify: `ultramemory_cli/memory.py`

**Step 1: Create agents/researcher.py**

```python
"""Researcher Agent - queries information from memory."""

from typing import Any
from core.memory import MemorySystem


class ResearcherAgent:
    """Agent responsible for searching and retrieving information from memory."""

    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system

    async def query(self, query_text: str, limit: int = 5) -> dict[str, Any]:
        """Query the memory system.

        Args:
            query_text: The search query
            limit: Maximum number of results

        Returns:
            List of relevant documents with scores
        """
        # 1. Search vector store
        vector_results = await self.memory.qdrant.search(
            await self.memory._generate_embedding(query_text),
            limit=limit,
        )

        # 2. Search temporal graph
        graph_results = await self.memory.graphiti.search(query_text, limit=limit)

        # 3. Combine and rank results
        combined_results = self._combine_results(vector_results, graph_results)

        return {
            "query": query_text,
            "results": combined_results[:limit],
            "total_found": len(combined_results),
        }

    def _combine_results(self, vector_results: list, graph_results: list) -> list[dict[str, Any]]:
        """Combine and deduplicate results from different sources."""
        seen_ids = set()
        combined = []

        # Priority to vector results
        for r in vector_results:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                combined.append({
                    **r,
                    "source": "vector",
                })

        for r in graph_results:
            if r.get("episode_id") not in seen_ids:
                seen_ids.add(r.get("episode_id"))
                combined.append({
                    "id": r.get("episode_id"),
                    "content": r.get("content"),
                    "score": r.get("score", 0.5),
                    "metadata": r.get("metadata", {}),
                    "source": "graph",
                })

        # Re-rank by score
        combined.sort(key=lambda x: x.get("score", 0), reverse=True)

        return combined

    async def query_by_time(self, query_text: str, time_range: str) -> dict[str, Any]:
        """Query with time-based context.

        Args:
            query_text: The search query
            time_range: Time range (e.g., "last week", "2024-01")

        Returns:
            Results within time context
        """
        # Search with time filter
        graph_results = await self.memory.graphiti.search(query_text, time_range=time_range)

        return {
            "query": query_text,
            "time_range": time_range,
            "results": graph_results,
        }
```

**Step 2: Commit**

```bash
git add agents/researcher.py
git commit -m "feat: add Researcher agent for querying memory"
```

---

### Task 8: Consolidator Agent

**Files:**
- Create: `agents/consolidator.py`

**Step 1: Create agents/consolidator.py**

```python
"""Consolidator Agent - reorganizes and deduplicates memory."""

from typing import Any
from core.memory import MemorySystem


class ConsolidatorAgent:
    """Agent responsible for consolidating and deduplicating memory."""

    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system
        self.similarity_threshold = 0.95

    async def consolidate(self) -> dict[str, Any]:
        """Run consolidation process.

        Returns:
            Report with actions taken
        """
        report = {
            "duplicates_removed": 0,
            "entities_merged": 0,
            "reindexed": 0,
            "errors": [],
        }

        try:
            # 1. Find duplicates
            duplicates = await self._find_duplicates()
            report["duplicates_removed"] = len(duplicates)

            # 2. Remove duplicates
            for dup in duplicates:
                await self.memory.qdrant.delete(dup["id"])

            # 3. Merge related entities in graph
            merged = await self._merge_entities()
            report["entities_merged"] = merged

            # 4. Trigger graph consolidation
            await self.memory.graphiti.consolidate()

            report["status"] = "success"

        except Exception as e:
            report["status"] = "error"
            report["errors"].append(str(e))

        return report

    async def _find_duplicates(self) -> list[dict[str, Any]]:
        """Find duplicate entries in memory."""
        # Get all documents (in production, use pagination)
        # For now, sample-based approach
        duplicates = []

        # This is a simplified version - in production, use more sophisticated
        # similarity detection across all documents
        return duplicates

    async def _merge_entities(self) -> int:
        """Merge related entities in the graph."""
        # Graph consolidation handles this internally
        return 0

    async def analyze(self) -> dict[str, Any]:
        """Analyze memory for issues without making changes."""
        return {
            "total_documents": "N/A",  # Implement count
            "potential_duplicates": 0,
            "orphaned_nodes": 0,
            "recommendations": [
                "Consider running consolidation during off-peak hours",
            ],
        }
```

**Step 2: Commit**

```bash
git add agents/consolidator.py
git commit -m "feat: add Consolidator agent for memory maintenance"
```

---

### Task 9: Auto-Researcher Agent

**Files:**
- Create: `agents/auto_researcher.py`

**Step 1: Create agents/auto_researcher.py**

```python
"""Auto-Researcher Agent - automatic research on configured topics."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from core.memory import MemorySystem


class AutoResearcherAgent:
    """Agent that automatically researches configured topics."""

    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system
        self.http_client = httpx.AsyncClient(timeout=60.0)

    async def research(self, topics: list[str], output_dir: str = "./researches") -> dict[str, Any]:
        """Run research on given topics.

        Args:
            topics: List of topics to research
            output_dir: Directory to save research outputs

        Returns:
            Report with research results
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        results = []

        for topic in topics:
            try:
                # 1. Search for information (placeholder - implement with search API)
                info = await self._search_topic(topic)

                # 2. Save to file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{topic.replace(' ', '_')}.md"
                filepath = output_path / filename

                content = self._format_research(topic, info)
                filepath.write_text(content, encoding="utf-8")

                # 3. Add to memory
                await self.memory.add(
                    content,
                    metadata={
                        "type": "research",
                        "topic": topic,
                        "timestamp": timestamp,
                    },
                )

                results.append({"topic": topic, "status": "success", "file": str(filepath)})

            except Exception as e:
                results.append({"topic": topic, "status": "error", "error": str(e)})

        return {
            "status": "success",
            "topics_processed": len(topics),
            "results": results,
            "output_dir": str(output_path),
        }

    async def _search_topic(self, topic: str) -> dict[str, Any]:
        """Search for information on a topic.

        This is a placeholder. In production, integrate with:
        - Tavily, SerpAPI, or other search APIs
        - arXiv, PubMed for academic research
        """
        # Placeholder - returns mock data
        return {
            "summary": f"Research summary for {topic}",
            "key_findings": [
                "Finding 1",
                "Finding 2",
            ],
            "sources": [],
        }

    def _format_research(self, topic: str, info: dict[str, Any]) -> str:
        """Format research as markdown."""
        lines = [
            f"# Research: {topic}",
            "",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Summary",
            "",
            info.get("summary", "No summary available."),
            "",
            "## Key Findings",
            "",
        ]

        for finding in info.get("key_findings", []):
            lines.append(f"- {finding}")

        lines.extend([
            "",
            "## Sources",
            "",
        ])

        for source in info.get("sources", []):
            lines.append(f"- {source}")

        return "\n".join(lines)

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()
```

**Step 2: Commit**

```bash
git add agents/auto_researcher.py
git commit -m "feat: add Auto-Researcher agent for continuous learning"
```

---

### Task 10: Custom Agent System

**Files:**
- Modify: `ultramemory_cli/agents.py`
- Create: `agents/custom_agent.py`

**Step 1: Create agents/custom_agent.py**

```python
"""Custom agent framework."""

import json
from pathlib import Path
from typing import Any

from core.memory import MemorySystem


class CustomAgent:
    """Dynamically created agent from MD + Skill + System Prompt."""

    def __init__(
        self,
        name: str,
        md_path: Path,
        skill_path: Path | None = None,
        system_prompt: str | None = None,
    ):
        self.name = name
        self.md_path = md_path
        self.skill_path = skill_path
        self.system_prompt = system_prompt or self._load_md()
        self.skills = self._load_skills() if skill_path else []

    def _load_md(self) -> str:
        """Load agent documentation."""
        if self.md_path.exists():
            return self.md_path.read_text(encoding="utf-8")
        return ""

    def _load_skills(self) -> list[dict[str, Any]]:
        """Load agent skills."""
        if self.skill_path and self.skill_path.exists():
            return json.loads(self.skill_path.read_text(encoding="utf-8"))
        return []

    async def run(self, input_data: Any, memory: MemorySystem) -> dict[str, Any]:
        """Run the custom agent."""
        # Placeholder - implement based on skills defined
        return {
            "status": "success",
            "output": f"Agent {self.name} executed",
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize agent config."""
        return {
            "name": self.name,
            "md_path": str(self.md_path),
            "skill_path": str(self.skill_path) if self.skill_path else None,
            "system_prompt": self.system_prompt,
            "skills": self.skills,
        }
```

**Step 2: Update ultramemory_cli/agents.py**

```python
"""Agent management commands."""

import asyncio
import json
from pathlib import Path

import click

from agents.custom_agent import CustomAgent
from core.memory import MemorySystem
from ultramemory_cli.settings import settings, CONFIG_DIR


@click.group(name="agent")
def agent_group():
    """Agent management commands."""
    pass


@agent_group.command(name="create")
def create_agent():
    """Create a new custom agent interactively."""
    click.echo("Creating new agent...")
    click.echo("=" * 40)

    # Questions
    name = click.prompt("Agent name")

    purpose = click.prompt("Purpose (what does it do?)")

    click.echo("\nInput types (comma-separated):")
    click.echo("  text, file, url, all")
    input_types = click.prompt("Input types", default="text")

    click.echo("\nOutput types (comma-separated):")
    click.echo("  text, json, markdown, all")
    output_types = click.prompt("Output types", default="text")

    click.echo("\nLLM Provider:")
    llm_provider = click.prompt("Provider", default=settings.get("llm_provider", "openai"))

    click.echo("\nSchedule (if daemon):")
    click.echo("  manual, hourly, daily, weekly, cron")
    schedule = click.prompt("Schedule", default="manual")

    # Create agent files
    agents_dir = CONFIG_DIR / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    agent_dir = agents_dir / name
    agent_dir.mkdir(parents=True, exist_ok=True)

    # Write MD
    md_content = f"""# {name}

## Purpose
{purpose}

## Input Types
{input_types}

## Output Types
{output_types}

## LLM Provider
{llm_provider}

## Schedule
{schedule}
"""
    (agent_dir / "README.md").write_text(md_content, encoding="utf-8")

    # Write skills JSON
    skills = {
        "input_types": [t.strip() for t in input_types.split(",")],
        "output_types": [t.strip() for t in output_types.split(",")],
        "llm_provider": llm_provider,
        "schedule": schedule,
    }
    (agent_dir / "skills.json").write_text(json.dumps(skills, indent=2), encoding="utf-8")

    # Save to settings
    custom_agents = settings.get("agents.custom", {})
    custom_agents[name] = {
        "path": str(agent_dir),
        "created": str(Path(__file__).stat().st_mtime),
    }
    settings.set("agents.custom", custom_agents)

    click.echo(f"\nAgent '{name}' created at {agent_dir}")


@agent_group.command(name="list")
def list_agents():
    """List all agents."""
    click.echo("System Agents:")
    click.echo("  - librarian (Bibliotecario)")
    click.echo("  - researcher (Investigador)")
    click.echo("  - consolidator (Consolidador)")
    click.echo("  - auto-researcher (Researcher automático)")

    custom_agents = settings.get("agents.custom", {})
    if custom_agents:
        click.echo("\nCustom Agents:")
        for name, info in custom_agents.items():
            click.echo(f"  - {name}")


@agent_group.command(name="launch")
@click.argument("name")
@click.argument("input_data", required=False)
def launch_agent(name: str, input_data: str | None):
    """Launch a custom agent once."""
    custom_agents = settings.get("agents.custom", {})

    if name not in custom_agents:
        click.echo(f"Error: Agent '{name}' not found", err=True)
        return

    agent_path = Path(custom_agents[name]["path"])

    agent = CustomAgent(
        name=name,
        md_path=agent_path / "README.md",
        skill_path=agent_path / "skills.json" if (agent_path / "skills.json").exists() else None,
    )

    async def _run():
        memory = MemorySystem()
        result = await agent.run(input_data, memory)
        click.echo(f"Result: {result}")

    asyncio.run(_run())


@agent_group.command(name="config")
@click.argument("name")
def config_agent(name: str):
    """Configure a custom agent."""
    custom_agents = settings.get("agents.custom", {})

    if name not in custom_agents:
        click.echo(f"Error: Agent '{name}' not found", err=True)
        return

    agent_path = Path(custom_agents[name]["path"])

    click.echo(f"Configuring agent: {name}")
    click.echo(f"Location: {agent_path}")

    # Edit skills
    if (agent_path / "skills.json").exists():
        skills = json.loads((agent_path / "skills.json").read_text())
        click.echo(f"\nCurrent skills: {json.dumps(skills, indent=2)}")

        if click.confirm("Edit skills?"):
            # Re-ask questions (simplified)
            new_schedule = click.prompt("Schedule", default=skills.get("schedule", "manual"))
            skills["schedule"] = new_schedule
            (agent_path / "skills.json").write_text(json.dumps(skills, indent=2))
            click.echo("Skills updated.")
```

**Step 3: Commit**

```bash
git add agents/custom_agent.py ultramemory_cli/agents.py
git commit -m "feat: add custom agent system with CLI management"
```

---

## Phase 5: FastAPI Service

### Task 11: FastAPI endpoints

**Files:**
- Create: `services/__init__.py`
- Create: `services/main.py`
- Create: `services/models.py`

**Step 1: Create services/models.py**

```python
"""Pydantic models for API."""

from typing import Any
from pydantic import BaseModel


class AddRequest(BaseModel):
    """Request to add content to memory."""

    content: str
    metadata: dict[str, Any] | None = None


class AddResponse(BaseModel):
    """Response from adding content."""

    status: str
    chunks_created: int
    document_id: str | None


class QueryRequest(BaseModel):
    """Request to query memory."""

    query: str
    limit: int = 5


class QueryResponse(BaseModel):
    """Response from querying memory."""

    query: str
    results: list[dict[str, Any]]
    total_found: int


class ConsolidateResponse(BaseModel):
    """Response from consolidation."""

    status: str
    duplicates_removed: int
    entities_merged: int


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    services: dict[str, bool]
```

**Step 2: Create services/main.py**

```python
"""FastAPI service for Ultramemory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from core.memory import MemorySystem
from agents.librarian import LibrarianAgent
from agents.researcher import ResearcherAgent
from agents.consolidator import ConsolidatorAgent
from .models import (
    AddRequest,
    AddResponse,
    QueryRequest,
    QueryResponse,
    ConsolidateResponse,
    HealthResponse,
)


memory: MemorySystem | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager."""
    global memory
    memory = MemorySystem()
    yield
    await memory.close()


app = FastAPI(
    title="Ultramemory API",
    description="Hybrid memory system API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    services = {
        "qdrant": await memory.qdrant.health(),
        "redis": await memory.redis.health(),
        "graphiti": await memory.graphiti.health(),
    }

    return HealthResponse(
        status="healthy" if all(services.values()) else "degraded",
        services=services,
    )


@app.post("/memory/add", response_model=AddResponse)
async def add_content(request: AddRequest):
    """Add content to memory."""
    librarian = LibrarianAgent(memory)

    try:
        result = await librarian.add(request.content, request.metadata)
        return AddResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/query", response_model=QueryResponse)
async def query_memory(request: QueryRequest):
    """Query memory."""
    researcher = ResearcherAgent(memory)

    try:
        result = await researcher.query(request.query, request.limit)
        return QueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/consolidate", response_model=ConsolidateResponse)
async def consolidate_memory():
    """Run consolidation."""
    consolidator = ConsolidatorAgent(memory)

    try:
        result = await consolidator.consolidate()
        return ConsolidateResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/list")
async def list_agents():
    """List available agents."""
    return {
        "system": ["librarian", "researcher", "consolidator", "auto-researcher"],
        "custom": [],  # Load from settings
    }
```

**Step 3: Create Dockerfile.api**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install -e .

COPY core/ ./core/
COPY agents/ ./agents/
COPY services/ ./services/
COPY ultramemory_cli/ ./ultramemory_cli/

ENV PYTHONPATH=/app

CMD ["uvicorn", "services.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 4: Commit**

```bash
git add services/ Dockerfile.api
git commit -m "feat: add FastAPI service with endpoints"
```

---

## Phase 6: Logging, Metrics, Utils

### Task 12: Logs, metrics, dashboard

**Files:**
- Modify: `ultramemory_cli/main.py`
- Modify: `ultramemory_cli/logs.py`
- Modify: `ultramemory_cli/metrics.py`
- Modify: `ultramemory_cli/dashboard.py`

**Step 1: Update logs.py**

```python
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
```

**Step 2: Update metrics.py**

```python
"""Metrics viewing commands."""

import json
import click
import httpx

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


import asyncio
```

**Step 3: Update dashboard.py**

```python
"""Dashboard command."""

import asyncio
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
```

**Step 4: Commit**

```bash
git add ultramemory_cli/
git commit -m "feat: add logging, metrics, and dashboard commands"
```

---

## Phase 7: Testing

### Task 13: Add tests

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_document_processor.py`
- Create: `tests/test_memory.py`

**Step 1: Create tests/test_document_processor.py**

```python
"""Tests for document processor."""

import pytest
from pathlib import Path
import tempfile

from core.document_processor import DocumentProcessor


@pytest.fixture
def processor():
    return DocumentProcessor(chunk_size=100, chunk_overlap=20)


def test_chunk_small_text(processor):
    """Test that small text is not chunked."""
    text = "This is a short text."
    chunks = processor.chunk(text)

    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_long_text(processor):
    """Test that long text is chunked."""
    text = "A" * 200 + ". " + "B" * 200 + "."
    chunks = processor.chunk(text)

    assert len(chunks) > 1


def test_chunk_with_overlap(processor):
    """Test that chunks overlap."""
    text = "This is sentence one. This is sentence two. " * 50
    chunks = processor.chunk(text)

    if len(chunks) > 1:
        # Check overlap exists
        assert any(chunks[i].endswith(chunks[i+1][:10]) for i in range(len(chunks) - 1))


@pytest.fixture
def temp_text_file():
    """Create a temporary text file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Test content for the file.")
        return Path(f.name)


@pytest.mark.asyncio
async def test_process_text(processor):
    """Test processing plain text."""
    result = await processor.process("Hello world")

    assert result["type"] == "text"
    assert result["text"] == "Hello world"


@pytest.mark.asyncio
async def test_process_file(processor, temp_text_file):
    """Test processing a file."""
    result = await processor.process(temp_text_file)

    assert result["type"] == "text"
    assert "Test content" in result["text"]
```

**Step 2: Create tests/test_memory.py**

```python
"""Tests for memory system."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from core.memory import MemorySystem


@pytest.fixture
def memory_system():
    return MemorySystem()


@pytest.mark.asyncio
async def test_memory_add(memory_system):
    """Test adding content to memory."""
    memory_system._generate_embedding = AsyncMock(return_value=[0.1] * 1536)
    memory_system.qdrant.add = AsyncMock(return_value="test-id")
    memory_system.graphiti.add_episode = AsyncMock(return_value="episode-id")
    memory_system.redis.set = AsyncMock()

    result = await memory_system.add("Test content")

    assert result == "test-id"
    memory_system.qdrant.add.assert_called_once()
    memory_system.graphiti.add_episode.assert_called_once()


@pytest.mark.asyncio
async def test_memory_query(memory_system):
    """Test querying memory."""
    memory_system._generate_embedding = AsyncMock(return_value=[0.1] * 1536)
    memory_system.qdrant.search = AsyncMock(return_value=[
        {"id": "1", "score": 0.9, "content": "Test"}
    ])
    memory_system.graphiti.search = AsyncMock(return_value=[])

    result = await memory_system.query("Test query")

    assert "vector_results" in result
    assert "graph_results" in result
```

**Step 3: Commit**

```bash
git add tests/
git commit -m "test: add basic tests"
```

---

## Phase 8: GitHub Repository

### Task 14: Push to GitHub

**Step 1: Check if gh is authenticated**

```bash
gh auth status
```

**Step 2: Create GitHub repo**

```bash
gh repo create ultramemory --public --source=. --description "Hybrid memory system with multi-agent CLI for AI agents"
```

**Step 3: Push**

```bash
git branch -M main
git push -u origin main
```

---

## Summary

**Plan complete and saved to `docs/plans/2026-02-16-ultramemory-design.md`.**

### Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
