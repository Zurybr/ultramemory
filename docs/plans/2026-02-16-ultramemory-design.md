# Ultramemory Design

**Date**: 2026-02-16
**Status**: Approved

## 1. Arquitectura

### Stack Tecnológico

| Capa | Tecnología |
|------|------------|
| Memoria Principal | Graphiti + FalkorDB |
| Vector Store | Qdrant |
| Cache/Temp | Redis |
| Orquestación | LangGraph |
| BD Principal | PostgreSQL |
| API | FastAPI |
| CLI | Python + Click/Typer |
| Monitoreo | Grafana + Prometheus |

### Flujo de Datos

```
User CLI → FastAPI → LangGraph → Graphiti → FalkorDB
                              ↓
                         Qdrant (embeddings)
                              ↓
                         Redis (cache)
                              ↓
                         PostgreSQL (metadatos)
```

## 2. Agentes del Sistema

### 2.1 Bibliotecario (Librarian)
- **Propósito**: Insertar información bien organizada, chunkificada y etiquetada
- **Input**: Texto, paths a archivos/carpetas, URLs
- **Proceso**:
  1. Detectar tipo de contenido
  2. Chunkificar (tamaño configurable)
  3. Generar embeddings
  4. Insertar en Graphiti + Qdrant
  5. Etiquetar y categorizar
- **CLI**: `ulmemory add <texto/path>`

### 2.2 Investigador (Researcher)
- **Propósito**: Buscar y recuperar información
- **Input**: Query del usuario
- **Proceso**:
  1. Embeddings del query
  2. Buscar en Qdrant + Graphiti
  3. Razonar respuesta con contexto
  4. Devolver resultado
- **CLI**: `ulmemory query "<pregunta>"`

### 2.3 Consolidador (Consolidator)
- **Propósito**: Reorganizar, indexar y consolidar (agente nocturno)
- **Trigger**: Manual (`ulmemory consolidate`) o schedule
- **Proceso**:
  1. Detectar duplicados
  2. Resolver contradicciones
  3. Reindexar
  4. Consolidar grafos
  5. Reporte de cambios

### 2.4 Researcher (Auto-mejora)
- **Propósito**: Investigar temas automáticamente
- **Input**: Lista de temas + schedule (configurable)
- **Proceso**:
  1. Buscar información
  2. Dejar investigaciones en carpeta configurable
  3. Formato: MD/PDF
- **CLI**: `ulmemory researcher`

## 3. Agentes Personalizables

### Estructura de un Agente
Cada agente personalizado se define con:
- **MD**: Documentación/instrucciones del agente
- **Skill**: Capacidades que tiene
- **System Prompt**: Cómo se comporta

### CLI para Agentes
- `ulmemory agent create` - Cuestionario interactivo
- `ulmemory agent list` - Listar agentes
- `ulmemory agent config <nombre>` - Configurar agente
- `ulmemory agent launch <nombre>` - Ejecutar una vez
- `ulmemory agent daemon <nombre>` - Ejecutar como daemon
- `ulmemory agent cron <nombre>` - Configurar schedule

### Cuestionario para Crear Agente
1. Nombre del agente
2. Propósito (qué hace)
3. Input que acepta (texto, archivos, URLs)
4. Output que produce
5. Qué herramientas LLM usa
6. Frecuencia de ejecución (si es daemon)

## 4. CLI

### Instalación
```bash
git clone https://github.com/brandom/ultramemory
cd ultramemory
./install-cli.sh
```

### Gestión de Servicios
| Comando | Descripción |
|---------|-------------|
| `ulmemory up` | Levantar servicios (docker-compose) |
| `ulmemory down` | Bajar servicios |
| `ulmemory restart` | Reiniciar servicios |
| `ulmemory health` | Verificar estado de todos los servicios |
| `ulmemory status` | Ver estado detallado de agentes |

### Memoria
| Comando | Descripción |
|---------|-------------|
| `ulmemory add <texto/path>` | Agent bibliotecario - insertar |
| `ulmemory query "<pregunta>"` | Agent investigador - buscar |
| `ulmemory consolidate` | Agent consolidador - reorganizar |
| `ulmemory researcher` | Agent researcher - investigar |

### Configuración
| Comando | Descripción |
|---------|-------------|
| `ulmemory config` | Configurar servicios remotos (interactivo) |
| `ulmemory env` | Generar .env desde config |
| `ulmemory test` | Probar conexiones |

### Utilidades
| Comando | Descripción |
|---------|-------------|
| `ulmemory logs` | Ver logs |
| `ulmemory logs <servicio>` | Ver logs de servicio específico |
| `ulmemory metrics` | Ver métricas |
| `ulmemory dashboard` | Abrir Grafana |

## 5. Configuración

### Estructura del Proyecto
```
ultramemory/
├── .env.example          # Template de configuración
├── install-cli.sh        # Script de instalación
├── docker-compose.yml    # Servicios
├── cli/                  # Código CLI
│   └── ultramemory_cli/
├── core/                 # Nucleo (Graphiti, LangGraph)
├── agents/               # Agentes del sistema
├── services/             # FastAPI + endpoints
├── config/               # Templates
└── docs/                 # Documentación
```

### Configuración CLI (~/.ulmemory/)
```
~/.ulmemory/
├── settings.json         # URLs, credenciales, preferencias
├── agents/               # Agentes personalizados (MD + skills + prompts)
└── logs/                # Logs locales
```

### settings.json (estructura)
```json
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
    "openai": {"api_key": ""},
    "minimax": {"api_key": ""},
    "kimi": {"api_key": ""}
  },
  "llm_provider": "openai",
  "embedding_provider": "openai",
  "researcher_topics": [],
  "researcher_schedule": "daily"
}
```

### Configuración Interactiva
El comando `ulmemory config` pregunta servicio por servicio:
- URL + puerto (placeholder: localhost + puerto default)
- Usuario (opcional)
- Contraseña (opcional)
- Enter para aceptar valores por defecto

## 6. Procesamiento de Documentos

### Tipos Soportados

| Tipo | Librería |
|------|----------|
| Texto | Built-in |
| PDF | PyMuPDF |
| Excel/CSV | pandas + openpyxl |
| HTML | BeautifulSoup |
| Web/URLs | requests + BeautifulSoup |
| Markdown | Built-in |
| Imágenes | Pillow |
| Videos | ffmpeg |

### Compatibilidad LLM
- OpenAI: GPT-4, GPT-4o, etc.
- Google: Gemini 1.5, 2.0
- MiniMax: MiniMax 2.5 CodePlan
- Kimi: Kimi 2.5 CodePlan
- Groq
- Ollama
- Custom (endpoint compatible OpenAI)

### Compatibilidad Embeddings
- OpenAI (text-embedding-3)
- Google (embedding-001, 004)
- MiniMax
- Kimi
- sentence-transformers (local)
- Ollama

## 7. Monitoreo

- **Logs**: Archivos en carpeta logs/
- **Grafana**: Dashboard visual
- **Prometheus**: Métricas
- **Dashboard Custom**: Métricas propias de agentes
