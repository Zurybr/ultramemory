---
name: ulmemory-cli
description: Use when working with Ultramemory hybrid memory system, storing/retrieving information, managing multi-agent memory operations, web research with Tavily, or scheduling automated tasks
---

# Ulmemory CLI

## Overview

CLI para el sistema de memoria híbrida Ultramemory que combina almacenamiento vectorial (Qdrant), grafos temporales (FalkorDB) y caché (Redis) con soporte multi-LLM, investigación web (Tavily), CodeWiki y scheduler integrado.

## When to Use

- Almacenar información para recuperación semántica
- Buscar/recuperar memories previas
- **Investigar en web con Tavily API**
- **Investigar repositorios GitHub con CodeWiki**
- Gestionar servicios Docker del sistema
- Crear/configurar agentes personalizados con skills
- Programar tareas automáticas de limpieza/investigación
- Analizar salud de la memoria

## 🆕 Novedades v0.3.0

### Sistema de Agentes Completos
- **ConsultantAgent**: Búsqueda ordenada por relevancia/fecha/fuente
- **ProactiveAgent**: Ejecuta tareas del heartbeat.md cada 30 min
- **TerminalAgent**: Dashboard interactivo y diagnóstico
- **PRDGeneratorAgent**: Convierte investigaciones en PRDs ejecutables
- **Heartbeat System**: Gestión de tareas desde archivo markdown

### Scheduler Automático
```bash
ulmemory schedule add-proactive        # Cada 30 min
ulmemory schedule add-researcher        # Cada hora
ulmemory schedule add-consolidator     # Diario 5am
```

---

## 🆕 Novedades v0.2.0

### Web Search Integration
```bash
# Buscar en memoria + web
ulmemory agent run researcher "AI agents" --web

# Especificar fuentes
ulmemory agent run researcher "topic" --sources web,memory,codewiki

# Deep research con expansión de queries
ulmemory agent run researcher "topic" --deep
```

### Agent Skills System
```bash
ulmemory agent skills                    # Ver skills disponibles
ulmemory agent skills researcher         # Ver skills de un agente
ulmemory agent add-skill mi-agente web_search
ulmemory agent edit mi-agente --schedule "0 9 * * *"
```

### Enhanced Auto-Researcher
```bash
# Investigación profunda con web + codewiki
ulmemory agent run auto-researcher "topic:AI,topic:ML" --deep
```

## Quick Reference

### Gestión de Servicios

| Comando | Descripción |
|---------|-------------|
| `ulmemory up` | Iniciar todos los servicios Docker |
| `ulmemory down` | Detener servicios |
| `ulmemory restart` | Reiniciar servicios |
| `ulmemory status` | Estado detallado de agentes y servicios |
| `ulmemory health` | Health check rápido |
| `ulmemory test` | Probar conexiones |

### Memoria

| Comando | Descripción |
|---------|-------------|
| `ulmemory memory add "texto"` | Agregar contenido a memoria |
| `ulmemory memory add "texto" -m "key=value"` | Agregar con metadata |
| `ulmemory memory add /path/to/file` | Indexar archivo (PDF, CSV, MD, etc.) |
| `ulmemory memory query "búsqueda"` | Buscar en memoria vectorial |
| `ulmemory memory query "term" --limit 10` | Buscar con límite |
| `ulmemory memory count` | Contar memorias totales |
| `ulmemory memory analyze` | Análisis completo de salud |
| `ulmemory memory consolidate` | Limpiar duplicados y mal indexados |
| `ulmemory memory delete "query" --confirm` | Eliminar por búsqueda |
| `ulmemory memory delete-all --confirm -f` | Eliminar TODAS las memorias |
| `ulmemory memory research --topics "AI,ML"` | Investigación automática |

### Code Index (Repos GitHub)

| Comando | Descripción |
|---------|-------------|
| `ulmemory code-index owner/repo` | Indexar repo (usa categoría guardada o personal) |
| `ulmemory code-index owner/repo -c opensource` | Indexar con categoría específica |
| `ulmemory code-index owner/repo -f` | Forzar re-index completo |
| `ulmemory code-index owner/repo -l 50` | Limitar archivos a indexar |
| `ulmemory code-index owner/repo -e "vendor"` | Excluir patrones adicionales |

**Categorías disponibles**: `lefarma`, `e6labs`, `personal`, `opensource`, `hobby`, `trabajo`, `dependencias`

### Agentes (Enhanced)

| Comando | Descripción |
|---------|-------------|
| `ulmemory agent list` | Listar agentes disponibles |
| `ulmemory agent skills` | Listar skills disponibles |
| `ulmemory agent skills <name>` | Ver skills de un agente |
| `ulmemory agent run researcher "query"` | Buscar en memoria |
| `ulmemory agent run researcher "query" --web` | **Memory + Web (Tavily)** |
| `ulmemory agent run researcher "query" --sources web,memory,codewiki` | **Multi-source** |
| `ulmemory agent run researcher "query" --deep` | **Deep research** |
| `ulmemory agent run librarian "texto"` | Agregar a memoria |
| `ulmemory agent run auto-researcher "topic"` | Investigar tema |
| `ulmemory agent run auto-researcher "topic" --deep` | **Deep research + web** |
| `ulmemory agent run consolidator` | Ejecutar limpieza de memoria |
| `ulmemory agent run deleter "all"` | Eliminar todas las memorias |
| `ulmemory agent create` | Crear agente personalizado |
| `ulmemory agent add-skill <agent> <skill>` | **Agregar skill a agente** |
| `ulmemory agent remove-skill <agent> <skill>` | **Remover skill** |
| `ulmemory agent edit <agent> --schedule "cron"` | **Editar configuración** |
| `ulmemory agent launch <nombre>` | Lanzar agente custom |
| `ulmemory agent config <nombre>` | Configurar agente |

### Nuevos Agentes v0.3.0

| Comando | Descripción |
|---------|-------------|
| `ulmemory agent consultant "query" --order date` | **Búsqueda ordenada** (relevance/date/source) |
| `ulmemory agent proactive` | **Ejecutar tareas del heartbeat** |
| `ulmemory agent terminal dashboard` | **Dashboard interactivo** |
| `ulmemory agent terminal diagnose` | **Diagnóstico del sistema** |
| `ulmemory agent terminal guide` | **Guía interactiva** |
| `ulmemory agent heartbeat list` | **Ver tareas pendientes** |
| `ulmemory agent heartbeat add "tarea #tag"` | **Agregar tarea** |
| `ulmemory agent heartbeat complete "tarea"` | **Completar tarea** |
| `ulmemory agent prd generate "research.md"` | **Generar PRD** |
| `ulmemory agent prd list` | **Listar PRDs** |

### Scheduler (Tareas Programadas)

| Comando | Descripción |
|---------|-------------|
| `ulmemory schedule add <agente> --cron "0 3 * * *"` | Crear tarea programada |
| `ulmemory schedule list` | Listar todas las tareas |
| `ulmemory schedule show <id>` | Ver detalles de tarea |
| `ulmemory schedule edit <id> --cron "..."` | Editar horario |
| `ulmemory schedule enable <id>` | Habilitar tarea |
| `ulmemory schedule disable <id>` | Deshabilitar tarea |
| `ulmemory schedule run <id>` | Ejecutar tarea ahora |
| `ulmemory schedule logs <id>` | Ver logs de tarea |
| `ulmemory schedule history <id>` | **Ver historial de ejecuciones** |
| `ulmemory schedule remove <id>` | Eliminar tarea |

### Nuevos Schedules v0.3.0

| Comando | Descripción |
|---------|-------------|
| `ulmemory schedule add-proactive` | **Agente proactivo cada 30 min** |
| `ulmemory schedule add-researcher` | **Investigador hourly (default)** |
| `ulmemory schedule add-researcher --cron "0 */6 * * *"` | Investigador cada 6 horas |
| `ulmemory schedule add-consolidator` | **Consolidator daily 5am** |
| `ulmemory schedule add-consolidator --hour 8` | Consolidator daily 8am |

### Configuración

| Comando | Descripción |
|---------|-------------|
| `ulmemory config show` | Ver configuración actual |
| `ulmemory config set <key> <value>` | Establecer valor |

### Utilidades

| Comando | Descripción |
|---------|-------------|
| `ulmemory logs show [servicio]` | Ver logs de servicios |
| `ulmemory logs docker [contenedor]` | Ver logs de Docker |
| `ulmemory metrics` | Mostrar métricas de Prometheus |
| `ulmemory dashboard` | Abrir dashboard de Grafana |
| `ulmemory version` | **Mostrar versión** |

## 🔍 Research Skills

### Web Search (Tavily)
```bash
# Requiere API key de Tavily (gratuita)
export TAVILY_API_KEY="tvly-xxx"

# O en config.yaml:
# research:
#   tavily:
#     api_key: "tvly-xxx"
```

### CodeWiki Integration
```bash
# Buscar repositorios relacionados
ulmemory agent run researcher "RAG frameworks" --sources codewiki

# Auto-researcher incluye CodeWiki automáticamente
ulmemory agent run auto-researcher "vector databases"
```

### Multi-Source Research
```bash
# Combinar todas las fuentes
ulmemory agent run researcher "LLM agents" --sources web,memory,codewiki

# Deep research con expansión automática de queries
ulmemory agent run researcher "RAG systems" --deep
```

## 📋 Available Skills

| Skill | Descripción | Categoría |
|-------|-------------|-----------|
| `web_search` | Búsqueda web con Tavily API | Research |
| `codewiki` | Investigación de repos GitHub | Research |
| `deep_research` | Research multi-fuente con expansión | Research |
| `memory_query` | Búsqueda en memoria interna | Memory |
| `memory_add` | Agregar contenido a memoria | Memory |
| `memory_count` | Contar documentos | Memory |

## Flujo de Uso Típico

```bash
# 1. Iniciar servicios
ulmemory up

# 2. Indexar documentos
ulmemory memory add ./docs/

# 3. Buscar en memoria + web
ulmemory agent run researcher "importante" --web

# 4. Deep research
ulmemory agent run researcher "AI memory systems" --deep --sources web,codewiki

# 5. Analizar salud
ulmemory memory analyze

# 6. Limpiar si es necesario
ulmemory memory consolidate

# 7. Programar mantenimiento diario
ulmemory schedule add consolidator --cron "0 3 * * *" --name "limpieza-diaria"

# 8. Programar research semanal
ulmemory schedule add auto-researcher --cron "0 9 * * 1" --args "topic:AI" --name "research-semanal"
```

## Scheduler - Automatización

### Crear Tareas Programadas

```bash
# Limpieza diaria a las 3am
ulmemory schedule add consolidator --cron "0 3 * * *" --name "limpieza-diaria"

# Investigación semanal los lunes a las 9am
ulmemory schedule add auto-researcher --cron "0 9 * * 1" --args "topic:AI,topic:ML" --name "research-semanal"

# Búsqueda cada 6 horas
ulmemory schedule add researcher --cron "0 */6 * * *" --args "updates"
```

### Formato Cron

```
┌───────────── minuto (0-59)
│ ┌───────────── hora (0-23)
│ │ ┌───────────── día del mes (1-31)
│ │ │ ┌───────────── mes (1-12)
│ │ │ │ ┌───────────── día de la semana (0-6, 0=domingo)
│ │ │ │ │
* * * * *
```

### Gestionar Tareas

```bash
# Ver todas las tareas
ulmemory schedule list

# Ver historial de ejecuciones
ulmemory schedule history 1

# Editar horario
ulmemory schedule edit 1 --cron "0 4 * * *"

# Ejecutar inmediatamente
ulmemory schedule run 1
```

## Análisis de Memoria

El comando `ulmemory memory analyze` detecta:

### Métricas
- **Health Score**: 0-100 (🟢 ≥90, 🟡 ≥70, 🔴 <70)
- **Total documentos**: Cantidad de entradas
- **Contenido único**: Sin duplicados
- **Longitud promedio**: Caracteres por entrada
- **Cobertura de metadata**: % con metadata completo

### Problemas Detectados
| Problema | Criterio |
|----------|----------|
| Duplicados | Contenido idéntico |
| Vacío | Sin texto |
| Muy corto | <10 caracteres |
| Muy largo | >100KB |
| Sin metadata | Faltan campos |
| Encoding | Mojibake/caracteres corruptos |
| Baja calidad | Repetitivo/sin estructura |

## Tipos de Archivo Soportados

| Tipo | Extensiones |
|------|-------------|
| Texto | `.txt`, `.md` |
| Datos | `.csv`, `.xlsx`, `.xls` |
| Documentos | `.pdf` |
| Web | `.html`, URLs |

## Puertos de Servicios

| Servicio | Puerto | URL |
|----------|--------|-----|
| API | 8000 | http://localhost:8000 |
| API Docs | 8000 | http://localhost:8000/docs |
| Qdrant | 6333 | http://localhost:6333/dashboard |
| Redis | 6379 | localhost:6379 |
| FalkorDB | 6370 | localhost:6370 |
| Grafana | 3000 | http://localhost:3000 |
| Prometheus | 9090 | http://localhost:9090 |

## Configuración

### LLM y APIs
Archivo: `~/.config/ultramemory/config.yaml`

```yaml
llm:
  default_provider: "minimax"
  providers:
    minimax:
      api_key: "sk-cp-xxx"
      model: "MiniMax-Text-01"
    google:
      api_key: "AIza-xxx"
      model: "gemini-1.5-flash"
    openai:
      api_key: "sk-xxx"
      model: "gpt-4"

# Research Tools
research:
  tavily:
    api_key: "tvly-xxx"
    enabled: true
  codewiki:
    enabled: true
    cli_path: "~/.claude/skills/codewiki/codewiki"

# Agent Configuration
agents:
  researcher:
    enabled: true
    sources: ["memory", "web", "codewiki"]
  auto_researcher:
    enabled: true
    sources: ["web", "codewiki"]
```

## Common Mistakes

| Error | Solución |
|-------|----------|
| `Connection refused` | Ejecutar `ulmemory up` primero |
| `CLI not found` | Verificar PATH incluye `~/.local/bin` |
| Puerto ocupado | `lsof -i :PUERTO` y detener conflicto |
| Tarea no ejecuta | Verificar crontab con `crontab -l` |
| Health score bajo | Ejecutar `ulmemory memory consolidate` |
| `TAVILY_API_KEY not set` | Configurar API key en config.yaml |
| Web search no funciona | Verificar API key de Tavily |

## Ejemplo de Uso Programático

```python
import asyncio
from core.memory import MemorySystem
from agents.researcher import ResearcherAgent
from agents.tools import registry, WebSearchTool

async def main():
    memory = MemorySystem()

    # Enhanced researcher with web search
    researcher = ResearcherAgent(
        memory,
        enable_web_search=True,
        tavily_api_key="tvly-xxx"
    )

    # Multi-source research
    result = await researcher.research(
        "AI agents",
        sources=["web", "memory", "codewiki"]
    )

    print(f"Web results: {len(result.web_results)}")
    print(f"Memory results: {len(result.memory_results)}")
    print(f"CodeWiki repos: {len(result.codewiki_results)}")

    if result.web_answer:
        print(f"AI Answer: {result.web_answer}")

    # Deep research
    deep_result = await researcher.deep_research(
        "vector databases",
        max_depth=3,
        save_to_memory=True
    )
    print(f"Total sources: {deep_result['total_sources']}")

asyncio.run(main())
```

## Archivos de Configuración

| Archivo | Ubicación |
|---------|-----------|
| Config general | `~/.ulmemory/settings.json` |
| LLM config | `~/.config/ultramemory/config.yaml` |
| Tareas programadas | `~/.ulmemory/schedules/tasks.json` |
| Agentes custom | `~/.config/ultramemory/agents/` |
| Logs de tareas | `/tmp/ulmemory-task-<id>.log` |

## 🔗 API Keys

| Servicio | Variable | Obtener |
|----------|----------|---------|
| Web Search | `TAVILY_API_KEY` | https://tavily.com (gratis) |
| OpenAI | `OPENAI_API_KEY` | https://platform.openai.com |
| Google | `GOOGLE_API_KEY` | https://ai.google.dev |
| MiniMax | Config file | https://minimax.chat |
