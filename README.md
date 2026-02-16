# Ultramemory

**Sistema de Memoria Híbrida Multi-Agente para AI**

Ultramemory es un sistema de memoria híbrida que combina almacenamiento vectorial, grafos temporales y caché de baja latencia, diseñado para agentes de IA con soporte multi-LLM.

## 🚀 Características

- **Memoria Híbrida**: Vector DB (Qdrant) + Graph DB (FalkorDB) + Cache (Redis)
- **Multi-Agente**: Librarian, Researcher, Consolidator, Auto-Researcher
- **Multi-LLM**: OpenAI, Google Gemini, MiniMax, Kimi, Groq, Ollama
- **CLI Completo**: 30+ comandos para gestión de memoria
- **Scheduler Integrado**: Automatiza tareas con cron
- **Análisis de Memoria**: Detecta duplicados, contenido mal indexado, problemas de calidad
- **Docker Compose**: Setup completo con 7 servicios
- **Monitoreo**: Grafana + Prometheus incluidos

## 📋 Requisitos

- Docker & Docker Compose
- Python 3.11+
- Git

## 🔧 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/Zurybr/ultramemory.git
cd ultramemory
```

### 2. Ejecutar el script de instalación

```bash
./install-cli.sh
```

Este script:
- Crea un virtual environment en `~/.ulmemory/venv`
- Instala todas las dependencias
- Crea el comando `ulmemory` en `~/.local/bin`
- Agrega `~/.local/bin` a tu PATH

### 3. Reiniciar la terminal

```bash
source ~/.bashrc  # o ~/.zshrc
```

### 4. Iniciar los servicios

```bash
ulmemory up
```

Esto inicia todos los servicios Docker:
- **PostgreSQL** (puerto 5432) - Metadata
- **Redis** (puerto 6379) - Cache
- **Qdrant** (puerto 6333) - Vector DB
- **FalkorDB** (puerto 6370) - Graph DB
- **API** (puerto 8000) - REST API
- **Prometheus** (puerto 9090) - Métricas
- **Grafana** (puerto 3000) - Dashboard

## 📖 Uso

### Gestión de Servicios

```bash
ulmemory up        # Iniciar servicios
ulmemory down      # Detener servicios
ulmemory restart   # Reiniciar servicios
ulmemory status    # Estado detallado
ulmemory health    # Health check rápido
ulmemory test      # Probar conexiones
```

### Operaciones de Memoria

```bash
# Agregar contenido
ulmemory memory add "Contenido a recordar"
ulmemory memory add "/path/to/file.txt"           # Archivo
ulmemory memory add "texto" -m "type=nota" -m "priority=high"  # Con metadata

# Buscar en memoria
ulmemory memory query "búsqueda semántica"
ulmemory memory query "term" --limit 10

# Contar memorias
ulmemory memory count

# Analizar memoria (detecta problemas)
ulmemory memory analyze

# Consolidar y limpiar
ulmemory memory consolidate

# Eliminar memorias
ulmemory memory delete "query"                     # Preview eliminación
ulmemory memory delete "query" --confirm           # Eliminar por búsqueda
ulmemory memory delete-all                         # Preview eliminar todo
ulmemory memory delete-all --confirm -f            # Eliminar TODO (cuidado!)

# Investigación automática
ulmemory memory research --topics "AI,ML" --output ./researches
```

### Indexar Repositorios GitHub

El comando `code-index` permite indexar repositorios GitHub completos en memoria vectorial, con metadata rico (commits, autor, categoría) y soporte para actualización incremental.

```bash
# Indexar repositorio (usa categoría guardada o 'personal')
ulmemory code-index owner/repo
ulmemory code-index https://github.com/owner/repo

# Especificar categoría
ulmemory code-index owner/repo -c opensource
ulmemory code-index owner/repo -c personal
ulmemory code-index owner/repo -c trabajo

# Opciones adicionales
ulmemory code-index owner/repo -f              # Forzar re-index completo
ulmemory code-index owner/repo -l 50           # Limitar archivos (default: 100)
ulmemory code-index owner/repo -e "vendor"     # Excluir patrones

# Ejemplos prácticos
ulmemory code-index kubernetes/kubernetes -c opensource -l 20
ulmemory code-index myorg/myrepo -c trabajo -f
```

**Categorías disponibles**:
- `lefarma` - Proyectos LeFarma
- `e6labs` - Proyectos E6 Labs
- `personal` - Proyectos personales (default)
- `opensource` - Proyectos open source
- `hobby` - Proyectos hobby
- `trabajo` - Proyectos laborales
- `dependencias` - Librerías dependencias

**Características**:
- ✅ Indexación incremental (solo re-indexa archivos cambiados)
- ✅ Metadata rico (commit SHA, fecha, autor)
- ✅ CodeWiki para repos públicos
- ✅ Persistencia de categorías en `~/.ulmemory/settings.json`
- ✅ Soporta 25+ extensiones de código

### Agentes

```bash
# Listar agentes disponibles
ulmemory agent list

# Ejecutar un agente directamente
ulmemory agent run consolidator                     # Limpiar memoria
ulmemory agent run researcher "query de búsqueda"   # Buscar
ulmemory agent run librarian "/path/to/docs"        # Indexar archivos
ulmemory agent run auto-researcher "topic:AI"       # Investigar
ulmemory agent run deleter "all"                    # Eliminar todas las memorias
ulmemory agent run deleter "query"                  # Eliminar por búsqueda

# Crear agente personalizado
ulmemory agent create

# Gestionar agentes personalizados
ulmemory agent launch <nombre>
ulmemory agent config <nombre>
```

### Scheduler (Tareas Programadas)

El scheduler permite automatizar la ejecución de agentes usando expresiones cron.

```bash
# Crear tarea programada
ulmemory schedule add consolidator --cron "0 3 * * *" --name "limpieza-diaria"
ulmemory schedule add researcher --cron "0 */6 * * *" --args "topic:updates"
ulmemory schedule add auto-researcher --cron "0 9 * * 1" --args "topic:AI"

# Listar tareas
ulmemory schedule list

# Ver detalles de una tarea
ulmemory schedule show 1

# Editar tarea
ulmemory schedule edit 1 --cron "30 2 * * *" --name "nuevo-nombre"

# Habilitar/Deshabilitar
ulmemory schedule disable 1
ulmemory schedule enable 1

# Ejecutar tarea inmediatamente
ulmemory schedule run 1

# Ver logs de una tarea
ulmemory schedule logs 1

# Eliminar tarea
ulmemory schedule remove 1
```

#### Formato Cron

```
┌───────────── minuto (0-59)
│ ┌───────────── hora (0-23)
│ │ ┌───────────── día del mes (1-31)
│ │ │ ┌───────────── mes (1-12)
│ │ │ │ ┌───────────── día de la semana (0-6, 0=domingo)
│ │ │ │ │
* * * * *
```

#### Ejemplos de Programación

| Cron | Descripción |
|------|-------------|
| `0 3 * * *` | Cada día a las 3:00am |
| `30 2 * * *` | Cada día a las 2:30am |
| `0 */6 * * *` | Cada 6 horas |
| `0 9 * * 1` | Cada lunes a las 9:00am |
| `0 4 * * 0` | Cada domingo a las 4:00am |
| `0 2 1 * *` | El día 1 de cada mes a las 2:00am |

### Configuración

```bash
ulmemory config show              # Ver configuración actual
ulmemory config set <key> <value> # Establecer valor
```

### Utilidades

```bash
ulmemory logs show [servicio]     # Ver logs de servicios
ulmemory logs docker [contenedor] # Ver logs de Docker
ulmemory metrics                  # Mostrar métricas
ulmemory dashboard                # Abrir Grafana
```

## 🔍 Análisis de Memoria

El comando `ulmemory memory analyze` realiza un análisis completo:

### Métricas Analizadas

- **Health Score**: Puntuación de salud (0-100)
- **Total documentos**: Cantidad de entradas
- **Contenido único**: Entradas sin duplicar
- **Longitud promedio**: Caracteres por entrada
- **Cobertura de metadata**: Porcentaje con metadata completo

### Problemas Detectados

| Problema | Descripción |
|----------|-------------|
| Duplicados | Contenido idéntico |
| Contenido vacío | Entradas sin texto |
| Muy corto | <10 caracteres |
| Muy largo | >100KB |
| Sin metadata | Faltan campos esenciales |
| Problemas de encoding | Mojibake/ caracteres corruptos |
| Baja calidad | Contenido repetitivo/sin estructura |

### Recomendaciones

El sistema genera recomendaciones automáticas basadas en los problemas encontrados.

## 🧹 Consolidación

El comando `ulmemory memory consolidate` limpia la memoria:

- Elimina duplicados exactos
- Borra contenido vacío
- Remueve entradas muy cortas (<10 chars)
- Fusiona entidades relacionadas

## 🤖 Agentes del Sistema

| Agente | Función | Uso |
|--------|---------|-----|
| **Librarian** | Inserta contenido en memoria | `ulmemory agent run librarian "texto"` |
| **Researcher** | Busca en memoria | `ulmemory agent run researcher "query"` |
| **Consolidator** | Limpia y optimiza | `ulmemory agent run consolidator` |
| **Auto-Researcher** | Investigación automática | `ulmemory agent run auto-researcher "topic"` |
| **Deleter** | Elimina memorias | `ulmemory agent run deleter "all"` |

## 📁 Tipos de Archivo Soportados

El Librarian puede indexar automáticamente:

| Tipo | Extensiones |
|------|-------------|
| Texto | `.txt`, `.md` |
| Datos | `.csv`, `.xlsx`, `.xls` |
| Documentos | `.pdf` |
| Web | `.html`, URLs |

## ⚙️ Configuración de LLM

Edita el archivo: `~/.config/ultramemory/config.yaml`

```yaml
llm:
  default_provider: "minimax"
  providers:
    minimax:
      api_key: "tu-api-key"
      model: "MiniMax-Text-01"
    google:
      api_key: "tu-gemini-api-key"
      model: "gemini-1.5-flash"
    openai:
      api_key: "tu-openai-api-key"
      model: "gpt-4"
```

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI (Click)                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ memory  │ │  agent  │ │schedule │ │ config  │           │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘           │
├───────┴──────────┴──────────┴──────────┴───────────────────┤
│                     Agent Layer                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │Librarian │ │Researcher│ │Consolida.│ │Auto-Res. │       │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘       │
├───────┴────────────┴────────────┴────────────┴──────────────┤
│                    Memory System                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │   Qdrant    │ │  FalkorDB   │ │    Redis    │           │
│  │  (Vector)   │ │   (Graph)   │ │   (Cache)   │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
├─────────────────────────────────────────────────────────────┤
│                    LLM Providers                             │
│  OpenAI │ Google │ MiniMax │ Kimi │ Groq │ Ollama          │
└─────────────────────────────────────────────────────────────┘
```

## 🔌 API Endpoints

Una vez iniciados los servicios:

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Qdrant Dashboard**: http://localhost:6333/dashboard
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

## 📁 Estructura del Proyecto

```
ultramemory/
├── agents/              # Agentes del sistema
│   ├── librarian.py     # Agente de inserción
│   ├── researcher.py    # Agente de consulta
│   ├── consolidator.py  # Agente de limpieza
│   └── auto_researcher.py
├── core/                # Núcleo del sistema
│   ├── memory.py        # Sistema de memoria híbrida
│   ├── qdrant_client.py
│   ├── graphiti_client.py
│   └── redis_client.py
├── services/            # Servicios API
├── ultramemory_cli/     # CLI commands
│   ├── main.py          # Entry point
│   ├── memory.py        # Comandos de memoria
│   ├── agents.py        # Comandos de agentes
│   ├── scheduler.py     # Comandos de scheduler
│   └── ...
├── skills/              # Skills para automatización
│   └── ulmemory-cli/
│       └── SKILL.md
├── docker/              # Configuración Docker
├── tests/               # Tests
├── docker-compose.yml
├── Dockerfile.api
├── pyproject.toml
└── install-cli.sh
```

## 🐛 Troubleshooting

### Error: "externally-managed-environment"

El script de instalación crea automáticamente un virtual environment:

```bash
rm -rf ~/.ulmemory/venv
./install-cli.sh
```

### Puerto ocupado

```bash
lsof -i :6333  # Qdrant
lsof -i :6379  # Redis
lsof -i :5432  # PostgreSQL
docker stop <container_name>
```

### CLI no encontrado

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Tareas programadas no ejecutan

```bash
# Verificar crontab
crontab -l

# Ver logs
ulmemory schedule logs <id>
cat /tmp/ulmemory-task-<id>.log
```

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE) para más detalles.

## 🤝 Contribuir

1. Fork el repositorio
2. Crea una rama (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📧 Contacto

- **Repositorio**: https://github.com/Zurybr/ultramemory
- **Issues**: https://github.com/Zurybr/ultramemory/issues
