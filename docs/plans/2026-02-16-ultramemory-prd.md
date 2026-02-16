# Ultramemory - Product Requirements Document

**Version:** 1.0
**Date:** 2026-02-16
**Status:** Draft

---

## 1. Executive Summary

### Problem Statement
Users need a unified hybrid memory system that combines vector search, temporal graph reasoning, and caching to enable AI agents to maintain context across interactions. Existing solutions are fragmented, requiring manual integration of multiple technologies.

### Proposed Solution
**Ultramemory** is a hybrid memory system with multi-agent CLI management that provides:
- Three-tier memory: Vector (Qdrant), Graph (Graphiti + FalkorDB), Cache (Redis)
- Four system agents: Librarian (insert), Researcher (query), Consolidator (nightly maintenance), Auto-Researcher (continuous learning)
- Full CLI for service management, configuration, and agent control
- Extensible custom agent system

### Success Criteria
1. **Add operation**: Insert content with metadata in <5 seconds for files up to 10MB
2. **Query operation**: Retrieve relevant context in <2 seconds
3. **Consolidation**: Deduplicate and reorganize memory nightly without service interruption
4. **Multi-format support**: Process PDF, Excel, CSV, HTML, Markdown, text, URLs
5. **Multi-LLM**: Support OpenAI, Google Gemini, MiniMax, Kimi, Groq, Ollama
6. **CLI可用性**: All operations accessible via CLI with local and remote modes

---

## 2. User Experience & Functionality

### User Personas

| Persona | Use Case |
|---------|----------|
| **Developer** | Build AI agents with persistent memory |
| **Researcher** | Store and query research materials |
| **Data Engineer** | Process documents and maintain knowledge base |
| **Power User** | Create custom agents for specific workflows |

### User Stories

#### Story 1: Service Management
> As a user, I want to start/stop all services with one command so that I can quickly set up the environment.

**Acceptance Criteria:**
- [ ] `ulmemory up` starts all docker-compose services
- [ ] `ulmemory down` stops all services
- [ ] `ulmemory health` shows status of all services
- [ ] Services start in correct dependency order

#### Story 2: Add Content
> As a user, I want to add text, files, or URLs to memory with one command so that I can build my knowledge base.

**Acceptance Criteria:**
- [ ] `ulmemory add "plain text"` stores text with auto-generated metadata
- [ ] `ulmemory add ./document.pdf` processes PDF and stores chunks
- [ ] `ulmemory add ./folder/` processes all supported files in directory
- [ ] `ulmemory add https://example.com` fetches and stores web content
- [ ] Chunk size configurable (default: 1000 chars, overlap: 200)
- [ ] Each chunk stored with source, timestamp, chunk_index metadata

#### Story 3: Query Content
> As a user, I want to ask questions and get relevant answers from memory so that I can retrieve stored knowledge.

**Acceptance Criteria:**
- [ ] `ulmemory query "what do you know about X"` returns ranked results
- [ ] Results include source citation and relevance score
- [ ] Hybrid search combines vector and graph results
- [ ] Time-range queries supported (e.g., "what did we know in January?")

#### Story 4: Consolidation
> As a user, I want to run consolidation manually or on schedule so that memory stays organized.

**Acceptance Criteria:**
- [ ] `ulmemory consolidate` triggers deduplication
- [ ] Detects near-duplicate content (similarity > 95%)
- [ ] Merges related graph entities
- [ ] Generates consolidation report

#### Story 5: Configuration
> As a user, I want to configure remote servers and credentials so that I can manage a distributed deployment.

**Acceptance Criteria:**
- [ ] `ulmemory config` launches interactive configuration
- [ ] Each service: URL + port + optional credentials
- [ ] Defaults to localhost with Enter to accept
- [ ] Settings stored in `~/.ulmemory/settings.json`
- [ ] `ulmemory env` generates .env from settings

#### Story 6: Custom Agents
> As a user, I want to create custom agents with MD + skills + prompts so that I can extend the system.

**Acceptance Criteria:**
- [ ] `ulmemory agent create` launches questionnaire
- [ ] Questions: name, purpose, input types, output types, LLM provider, schedule
- [ ] Creates agent folder in `~/.ulmemory/agents/<name>/`
- [ ] Files: README.md (documentation), skills.json (capabilities)
- [ ] `ulmemory agent launch <name>` runs agent once
- [ ] `ulmemory agent daemon <name>` runs as background service
- [ ] `ulmemory agent cron <name>` configures schedule

#### Story 7: Auto-Researcher
> As a user, I want the system to automatically research configured topics so that it continuously improves itself.

**Acceptance Criteria:**
- [ ] Topics configurable via `ulmemory config`
- [ ] Schedule configurable (hourly, daily, weekly, cron)
- [ ] Output directory configurable
- [ ] Saves research as Markdown files
- [ ] Automatically adds research to memory

#### Story 8: Monitoring
> As a user, I want to view logs and metrics so that I can monitor system health.

**Acceptance Criteria:**
- [ ] `ulmemory logs` shows application logs
- [ ] `ulmemory logs <service>` shows specific service logs
- [ ] `ulmemory logs docker <service>` shows Docker container logs
- [ ] `ulmemory metrics` shows Prometheus metrics
- [ ] `ulmemory dashboard` opens Grafana

### Non-Goals
- [ ] No web UI (CLI-only for v1)
- [ ] No authentication system (handled by deployment)
- [ ] No multi-tenancy (single user per instance)
- [ ] No real-time sync between instances

---

## 3. AI System Requirements

### Tool Requirements

| Component | Technology | Purpose |
|-----------|------------|---------|
| Memory Layer | Graphiti + FalkorDB | Temporal graph reasoning |
| Vector Store | Qdrant | Semantic search |
| Cache | Redis | Low-latency temporary storage |
| Database | PostgreSQL | Metadata and configuration |
| Orchestration | LangGraph | Multi-agent workflow |
| LLM Abstraction | LangChain | Multi-provider support |
| Document Processing | PyMuPDF, pandas, BeautifulSoup | Multi-format ingestion |

### Embedding Providers

| Provider | Model | Dimensions |
|----------|-------|------------|
| OpenAI | text-embedding-3-small | 1536 |
| OpenAI | text-embedding-3-large | 3072 |
| Google | embedding-001 | 768 |
| Google | text-embedding-004 | 768 |
| MiniMax | custom | TBD |
| Kimi | custom | TBD |
| Local | sentence-transformers | variable |

### LLM Providers

| Provider | Models |
|----------|--------|
| OpenAI | GPT-4, GPT-4o |
| Google | Gemini 1.5, 2.0 |
| MiniMax | MiniMax 2.5 CodePlan |
| Kimi | Kimi 2.5 CodePlan |
| Groq | Llama, Mixtral |
| Ollama | Local models |

### Evaluation Strategy

| Operation | Metric | Target |
|-----------|--------|--------|
| Add | Latency | <5s for 10MB file |
| Query | Latency | <2s |
| Query | Recall@5 | >=80% |
| Consolidation | Deduplication rate | >90% |
| CLI | Command success | >99% |

---

## 4. Technical Specifications

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI (Python/Click)                       │
│  ulmemory add | query | consolidate | config | agent ...       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI (Port 8000)                         │
│  /memory/add | /memory/query | /memory/consolidate | /health   │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐     ┌─────────────────┐     ┌───────────────┐
│   LangGraph   │     │    LangGraph    │     │   LangGraph   │
│   Librarian   │     │   Researcher    │     │ Consolidator  │
└───────────────┘     └─────────────────┘     └───────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Memory Layer                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐     │
│  │  Graphiti   │◄──►│   Qdrant    │◄──►│     Redis       │     │
│  │ +FalkorDB  │    │  (vectors)  │    │     (cache)     │     │
│  └─────────────┘    └─────────────┘    └─────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    PostgreSQL                                ││
│  │  (users, metadata, configs, logs, agent state)              ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Integration Points

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| API | 8000 | HTTP | Main API |
| Graphiti | 8001 | HTTP | Temporal graph |
| Qdrant | 6333 | HTTP/gRPC | Vector search |
| Redis | 6379 | Redis | Cache/PubSub |
| FalkorDB | 6370 | Redis | Graph storage |
| PostgreSQL | 5432 | PostgreSQL | Relational data |
| Grafana | 3000 | HTTP | Visualization |
| Prometheus | 9090 | HTTP | Metrics |

### Security & Privacy

- All service credentials stored in `~/.ulmemory/settings.json`
- API keys never logged or exposed
- Local mode: all services on localhost
- Remote mode: HTTPS required for production
- No data leaves the configured endpoints

---

## 5. Risks & Roadmap

### Technical Risks

| Risk | Mitigation |
|------|------------|
| Graphiti API stability | Version pinned in docker-compose |
| Qdrant memory usage | Monitor and alert on vector count |
| Redis connection limits | Connection pooling |
| LLM provider rate limits | Queue with retry logic |

### Phased Rollout

| Phase | Features |
|-------|----------|
| **v0.1 (MVP)** | Docker-compose setup, CLI core, Librarian, Researcher, basic query |
| **v0.2** | Consolidator agent, custom agents |
| **v0.3** | Auto-Researcher, scheduling |
| **v1.0** | Monitoring (Grafana), full documentation, tests |

### Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Runtime |
| Docker | latest | Containerization |
| docker-compose | latest | Orchestration |
| Graphiti | latest | Graph memory |
| Qdrant | 1.16.0 | Vector store |
| Redis | 7-alpine | Cache |
| FalkorDB | latest | Graph DB |
| PostgreSQL | 16-alpine | Relational |

---

## 6. CLI Command Reference

### Service Management
```bash
ulmemory up [path]           # Start services
ulmemory down [path]         # Stop services
ulmemory restart [path]      # Restart services
ulmemory health              # Check service health
ulmemory status              # Detailed status
```

### Memory Operations
```bash
ulmemory add <content|path>  # Add to memory
ulmemory query "<question>"  # Query memory
ulmemory consolidate         # Run consolidation
ulmemory research            # Run auto-researcher
```

### Configuration
```bash
ulmemory config              # Interactive config
ulmemory config show         # Show config
ulmemory config edit         # Edit config
ulmemory config env          # Generate .env
ulmemory config reset        # Reset to defaults
```

### Agent Management
```bash
ulmemory agent create        # Create custom agent
ulmemory agent list          # List agents
ulmemory agent launch <name> # Run once
ulmemory agent daemon <name> # Run as daemon
ulmemory agent cron <name>   # Configure schedule
ulmemory agent config <name> # Configure agent
```

### Utilities
```bash
ulmemory logs                # View logs
ulmemory logs <service>      # Service logs
ulmemory logs docker <svc>   # Docker logs
ulmemory metrics             # Show metrics
ulmemory dashboard          # Open Grafana
ulmemory test                # Test connections
```

---

## 7. File Structure

```
ultramemory/
├── .env.example              # Configuration template
├── .gitignore
├── LICENSE
├── README.md
├── install-cli.sh            # CLI installation script
├── pyproject.toml           # Python package config
├── docker-compose.yml        # All services
├── docker/
│   ├── prometheus/
│   │   └── prometheus.yml
│   └── grafana/
│       └── dashboard.json
├── ultramemory_cli/
│   ├── __init__.py
│   ├── main.py              # CLI entry point
│   ├── config.py             # Config commands
│   ├── memory.py             # Memory commands
│   ├── agents.py             # Agent commands
│   ├── logs.py              # Log commands
│   ├── metrics.py            # Metrics commands
│   ├── dashboard.py          # Dashboard command
│   └── settings.py           # Settings manager
├── core/
│   ├── __init__.py
│   ├── memory.py             # Memory system
│   ├── graphiti_client.py    # Graphiti wrapper
│   ├── qdrant_client.py      # Qdrant wrapper
│   ├── redis_client.py       # Redis wrapper
│   └── document_processor.py # File processing
├── agents/
│   ├── __init__.py
│   ├── librarian.py          # Insert agent
│   ├── researcher.py         # Query agent
│   ├── consolidator.py       # Maintenance agent
│   ├── auto_researcher.py    # Auto-learning agent
│   └── custom_agent.py       # Custom agent framework
├── services/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   └── models.py            # Pydantic models
├── tests/
│   ├── __init__.py
│   ├── test_document_processor.py
│   └── test_memory.py
└── docs/
    └── plans/
        ├── 2026-02-16-ultramemory-design.md
        └── 2026-02-16-ultramemory-plan.md
```

---

## 8. Acceptance Criteria Summary

| Feature | Priority | Status |
|---------|----------|--------|
| Docker-compose setup | P0 | |
| CLI installation | P0 | |
| ulmemory up/down/health | P0 | |
| ulmemory add (text/file/URL) | P0 | |
| ulmemory query | P0 | |
| ulmemory config (interactive) | P0 | |
| ulmemory consolidate | P1 | |
| Custom agent creation | P1 | |
| ulmemory agent launch/daemon/cron | P1 | |
| Auto-Researcher | P2 | |
| Grafana + Prometheus | P2 | |
| Tests | P2 | |
