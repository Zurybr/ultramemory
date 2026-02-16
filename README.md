# Ultramemory

**Sistema de Memoria Híbrida Multi-Agente para AI**

Ultramemory es un sistema de memoria híbrida que combina almacenamiento vectorial, grafos temporales y caché de baja latencia, diseñado para agentes de IA con soporte multi-LLM.

## 🚀 Características

- **Memoria Híbrida**: Vector DB (Qdrant) + Graph DB (FalkorDB) + Cache (Redis)
- **Multi-Agente**: Librarian, Researcher, Consolidator, Auto-Researcher
- **Multi-LLM**: OpenAI, Google Gemini, MiniMax, Kimi, Groq, Ollama
- **CLI Completo**: 20+ comandos para gestión de memoria
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

### Comandos Principales

```bash
# Gestión de servicios
ulmemory up        # Iniciar servicios
ulmemory down      # Detener servicios
ulmemory restart   # Reiniciar servicios
ulmemory status    # Estado detallado
ulmemory health    # Health check rápido

# Memoria
ulmemory memory add "Contenido a recordar"
ulmemory memory query "búsqueda"
ulmemory memory consolidate

# Agentes
ulmemory agent list
ulmemory agent create
ulmemory agent launch <nombre>

# Configuración
ulmemory config show
ulmemory config set <key> <value>

# Utilidades
ulmemory logs [servicio]
ulmemory metrics
ulmemory dashboard
ulmemory test
```

### Configuración de LLM

Edita el archivo de configuración:

```bash
~/.config/ultramemory/config.yaml
```

Ejemplo con MiniMax:

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
```

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI (Click/Typer)                        │
├─────────────────────────────────────────────────────────────┤
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
├── agents/           # Agentes del sistema
│   ├── librarian.py  # Agente de inserción
│   ├── researcher.py # Agente de consulta
│   ├── consolidator.py
│   └── auto_researcher.py
├── core/             # Núcleo del sistema
│   ├── memory.py     # Sistema de memoria híbrida
│   ├── qdrant_client.py
│   ├── graphiti_client.py
│   └── redis_client.py
├── services/         # Servicios API
├── ultramemory_cli/  # CLI commands
├── docker/           # Configuración Docker
├── tests/            # Tests
├── docker-compose.yml
├── Dockerfile.api
├── pyproject.toml
└── install-cli.sh
```

## 🐛 Troubleshooting

### Error: "externally-managed-environment"

El script de instalación crea automáticamente un virtual environment. Si tienes problemas:

```bash
rm -rf ~/.ulmemory/venv
./install-cli.sh
```

### Puerto ocupado

Si algún puerto está en uso:

```bash
# Verificar qué usa el puerto
lsof -i :6333  # Qdrant
lsof -i :6379  # Redis
lsof -i :5432  # PostgreSQL

# Detener el contenedor conflictivo
docker stop <container_name>
```

### CLI no encontrado

```bash
# Agregar manualmente al PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
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
