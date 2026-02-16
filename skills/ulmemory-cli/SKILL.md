---
name: ulmemory-cli
description: Use when working with Ultramemory hybrid memory system, storing/retrieving information, or managing multi-agent memory operations
---

# Ulmemory CLI

## Overview

CLI para el sistema de memoria híbrida Ultramemory que combina almacenamiento vectorial (Qdrant), grafos temporales (FalkorDB) y caché (Redis) con soporte multi-LLM.

## When to Use

- Almacenar información para recuperación semántica
- Buscar/recuperar memories previas
- Gestionar servicios Docker del sistema
- Crear/configurar agentes personalizados

## Quick Reference

### Gestión de Servicios

| Comando | Descripción |
|---------|-------------|
| `ulmemory up` | Iniciar todos los servicios Docker |
| `ulmemory down` | Detener servicios |
| `ulmemory restart` | Reiniciar servicios |
| `ulmemory status` | Estado detallado de agentes y servicios |
| `ulmemory health` | Health check rápido |

### Memoria

| Comando | Descripción |
|---------|-------------|
| `ulmemory memory add "texto"` | Agregar contenido a memoria |
| `ulmemory memory add "texto" -m "key=value"` | Agregar con metadata |
| `ulmemory memory query "búsqueda"` | Buscar en memoria vectorial |
| `ulmemory memory consolidate` | Consolidar y optimizar memoria |

### Agentes

| Comando | Descripción |
|---------|-------------|
| `ulmemory agent list` | Listar agentes disponibles |
| `ulmemory agent create` | Crear agente personalizado |
| `ulmemory agent launch <nombre>` | Lanzar agente |
| `ulmemory agent config <nombre>` | Configurar agente |

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
| `ulmemory test` | Probar conexiones |

## Flujo de Uso Típico

```bash
# 1. Iniciar servicios
ulmemory up

# 2. Agregar información
ulmemory memory add "Nota importante: el servidor usa PostgreSQL 16"

# 3. Recuperar información
ulmemory memory query "base de datos"

# 4. Detener cuando no se use
ulmemory down
```

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

## Configuración de LLM

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
```

## Common Mistakes

| Error | Solución |
|-------|----------|
| `Connection refused` | Ejecutar `ulmemory up` primero |
| `CLI not found` | Verificar PATH incluye `~/.local/bin` |
| Puerto ocupado | `lsof -i :PUERTO` y detener conflicto |

## Ejemplo de Uso Programático

```python
import asyncio
from core.memory import MemorySystem
from agents.librarian import LibrarianAgent
from agents.researcher import ResearcherAgent

async def main():
    memory = MemorySystem()
    librarian = LibrarianAgent(memory)
    researcher = ResearcherAgent(memory)

    # Agregar
    await memory.add("Información importante")

    # Buscar
    results = await researcher.query("importante", limit=5)
    print(results)

asyncio.run(main())
```
