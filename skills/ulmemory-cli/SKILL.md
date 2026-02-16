---
name: ulmemory-cli
description: Use when working with Ultramemory hybrid memory system, storing/retrieving information, managing multi-agent memory operations, or scheduling automated tasks
---

# Ulmemory CLI

## Overview

CLI para el sistema de memoria híbrida Ultramemory que combina almacenamiento vectorial (Qdrant), grafos temporales (FalkorDB) y caché (Redis) con soporte multi-LLM y scheduler integrado.

## When to Use

- Almacenar información para recuperación semántica
- Buscar/recuperar memories previas
- Gestionar servicios Docker del sistema
- Crear/configurar agentes personalizados
- Programar tareas automáticas de limpieza/investigación
- Analizar salud de la memoria

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
| `ulmemory memory analyze` | Análisis completo de salud |
| `ulmemory memory consolidate` | Limpiar duplicados y mal indexados |
| `ulmemory memory research --topics "AI,ML"` | Investigación automática |

### Agentes

| Comando | Descripción |
|---------|-------------|
| `ulmemory agent list` | Listar agentes disponibles |
| `ulmemory agent run consolidator` | Ejecutar limpieza de memoria |
| `ulmemory agent run researcher "query"` | Buscar en memoria |
| `ulmemory agent run librarian "texto"` | Agregar a memoria |
| `ulmemory agent run librarian /path/to/docs` | Indexar directorio |
| `ulmemory agent run auto-researcher "topic"` | Investigar tema |
| `ulmemory agent create` | Crear agente personalizado |
| `ulmemory agent launch <nombre>` | Lanzar agente custom |
| `ulmemory agent config <nombre>` | Configurar agente |

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
| `ulmemory schedule remove <id>` | Eliminar tarea |

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

## Flujo de Uso Típico

```bash
# 1. Iniciar servicios
ulmemory up

# 2. Indexar documentos
ulmemory memory add ./docs/

# 3. Buscar información
ulmemory memory query "importante"

# 4. Analizar salud
ulmemory memory analyze

# 5. Limpiar si es necesario
ulmemory memory consolidate

# 6. Programar mantenimiento diario
ulmemory schedule add consolidator --cron "0 3 * * *" --name "limpieza-diaria"
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

### Ejemplos de Cron

| Expresión | Significado |
|-----------|-------------|
| `0 3 * * *` | Cada día a las 3:00am |
| `30 2 * * *` | Cada día a las 2:30am |
| `0 */6 * * *` | Cada 6 horas |
| `0 9 * * 1` | Cada lunes a las 9:00am |
| `0 4 * * 0` | Cada domingo a las 4:00am |
| `0 2 1 * *` | Día 1 de cada mes a las 2:00am |

### Gestionar Tareas

```bash
# Ver todas las tareas
ulmemory schedule list

# Ver detalles
ulmemory schedule show 1

# Editar horario
ulmemory schedule edit 1 --cron "0 4 * * *"

# Deshabilitar temporalmente
ulmemory schedule disable 1

# Ejecutar inmediatamente
ulmemory schedule run 1

# Ver logs
ulmemory schedule logs 1
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

## Consolidación

El comando `ulmemory memory consolidate`:
- Elimina duplicados exactos
- Borra contenido vacío
- Remueve entradas muy cortas
- Fusiona entidades relacionadas

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
    openai:
      api_key: "sk-xxx"
      model: "gpt-4"
```

## Common Mistakes

| Error | Solución |
|-------|----------|
| `Connection refused` | Ejecutar `ulmemory up` primero |
| `CLI not found` | Verificar PATH incluye `~/.local/bin` |
| Puerto ocupado | `lsof -i :PUERTO` y detener conflicto |
| Tarea no ejecuta | Verificar crontab con `crontab -l` |
| Health score bajo | Ejecutar `ulmemory memory consolidate` |

## Ejemplo de Uso Programático

```python
import asyncio
from core.memory import MemorySystem
from agents.librarian import LibrarianAgent
from agents.researcher import ResearcherAgent
from agents.consolidator import ConsolidatorAgent

async def main():
    memory = MemorySystem()
    librarian = LibrarianAgent(memory)
    researcher = ResearcherAgent(memory)
    consolidator = ConsolidatorAgent(memory)

    # Indexar
    await librarian.add("Información importante")

    # Buscar
    results = await researcher.query("importante", limit=5)
    print(results)

    # Analizar
    analysis = await consolidator.analyze()
    print(f"Health: {analysis['quality_metrics']['health_score']}")

    # Limpiar
    await consolidator.consolidate()

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
