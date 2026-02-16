# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ultramemory is a **hybrid memory system for AI agents** that combines:
- **Vector storage** (Qdrant) - semantic search
- **Temporal graphs** (FalkorDB) - relationship tracking
- **Cache** (Redis) - low-latency access
- **Multi-LLM support** - OpenAI, Google Gemini, MiniMax, Kimi, Groq, Ollama

The project provides a CLI (`ulmemory`) with 30+ commands for memory management, agent execution, and automated scheduling.

## Common Commands

### Development
```bash
# Install CLI
./install-cli.sh

# Start services (requires Docker)
ulmemory up

# Test connections
ulmemory test

# Run CLI
~/.ulmemory/venv/bin/python -m ultramemory_cli.main [command]

# Run tests
~/.ulmemory/venv/bin/python -m pytest tests/ -v
```

### Key CLI Commands
```bash
ulmemory up                  # Start all Docker services
ulmemory down                # Stop services
ulmemory memory add "text"   # Add to memory
ulmemory memory query "term"  # Search memory
ulmemory agent run researcher "query" --web  # Research with web
ulmemory code-index owner/repo  # Index GitHub repo
ulmemory schedule add-proactive # Schedule heartbeat check (every 30min)
```

## Architecture

### Core Components

| Directory | Purpose |
|-----------|---------|
| `core/` | MemorySystem, clients for Qdrant, Redis, FalkorDB, GitHub |
| `agents/` | 12 specialized agents (Librarian, Researcher, Consolidator, etc.) |
| `ultramemory_cli/` | CLI commands using Click |
| `services/` | REST API (FastAPI) |
| `docker/` | Prometheus, Grafana configs |

### Memory System Flow

```
add(content)
  → generate embedding
  → store in Qdrant (vector)
  → store in FalkorDB (graph)
  → cache in Redis (optional)

query(text)
  → generate embedding
  → search Qdrant
  → search FalkorDB (temporal)
  → merge results
```

### Agents

All agents inherit from no base class - they're standalone classes. Key agents:
- `LibrarianAgent` - inserts content (text, files, URLs, images)
- `ResearcherAgent` - multi-source search (memory + web + codewiki)
- `ConsolidatorAgent` - deduplication, cleanup, insights generation
- `ProactiveAgent` - reads heartbeat.md, executes pending tasks
- `TerminalAgent` - interactive dashboard
- `CodeIndexerAgent` - indexes GitHub repos

## Configuration

- CLI config: `~/.config/ultramemory/config.yaml`
- User data: `~/.ulmemory/`
  - `heartbeat.md` - task list for ProactiveAgent
  - `research/todo.md` - research topics queue
  - `research/reports/` - saved investigations
  - `prds/` - generated PRD documents

## Environment Variables

Set in `~/.config/ultramemory/config.yaml` or as env vars:
- `TAVILY_API_KEY` - web search
- `OPENAI_API_KEY`, `GOOGLE_API_KEY`, etc. - LLM providers

## Docker Services

7 services via docker-compose:
- PostgreSQL (5432) - metadata
- Redis (6379) - cache
- Qdrant (6333) - vector DB
- FalkorDB (6370) - graph DB
- API (8000) - REST API
- Prometheus (9090) - metrics
- Grafana (3000) - dashboards
