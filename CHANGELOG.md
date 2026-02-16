# Changelog

Todos los cambios notables de este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhera a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-02-16

### ✨ Added - Funcionalidades Nuevas

#### Sistema de Memoria Híbrida
- **Vector Database (Qdrant)**: Almacenamiento y búsqueda vectorial para similitud semántica
- **Graph Database (FalkorDB)**: Almacenamiento de grafos temporales para relaciones
- **Cache (Redis)**: Caché de baja latencia para acceso rápido
- **Memory System**: Integración de las tres capas de memoria

#### Agentes del Sistema
- **Librarian Agent**: Agente responsable de insertar contenido en la memoria
- **Researcher Agent**: Agente para consultas y búsquedas en la memoria
- **Consolidator Agent**: Agente de mantenimiento y optimización
- **Auto-Researcher Agent**: Agente de aprendizaje continuo automático

#### Multi-LLM Support
- **OpenAI**: Soporte para GPT-4 y modelos de OpenAI
- **Google Gemini**: Integración con Gemini 1.5 Flash/Pro
- **MiniMax**: Soporte para MiniMax-Text-01 y modelos MiniMax
- **Kimi**: Integración con Kimi AI
- **Groq**: Soporte para inferencia rápida con Groq
- **Ollama**: Soporte para modelos locales vía Ollama

#### CLI Completo (20+ comandos)
- `ulmemory up`: Iniciar todos los servicios Docker
- `ulmemory down`: Detener todos los servicios
- `ulmemory restart`: Reiniciar servicios
- `ulmemory status`: Estado detallado de agentes y servicios
- `ulmemory health`: Health check rápido
- `ulmemory memory add`: Agregar contenido a la memoria
- `ulmemory memory query`: Buscar en la memoria
- `ulmemory memory consolidate`: Consolidar memoria
- `ulmemory agent list`: Listar agentes
- `ulmemory agent create`: Crear agente personalizado
- `ulmemory agent launch`: Lanzar agente
- `ulmemory agent config`: Configurar agente
- `ulmemory config show`: Mostrar configuración
- `ulmemory config set`: Establecer valor de configuración
- `ulmemory logs`: Ver logs de servicios
- `ulmemory metrics`: Mostrar métricas de Prometheus
- `ulmemory dashboard`: Abrir dashboard de Grafana
- `ulmemory test`: Probar conexiones

#### Docker Compose Setup
- **7 servicios** configurados automáticamente:
  - PostgreSQL 16 (metadata)
  - Redis 7 (cache)
  - Qdrant v1.16.0 (vector DB)
  - FalkorDB (graph DB)
  - API FastAPI
  - Prometheus (métricas)
  - Grafana (dashboards)

#### Procesamiento de Documentos
- Soporte para PDF (PyMuPDF)
- Soporte para Excel/CSV (pandas, openpyxl)
- Soporte para HTML (BeautifulSoup)
- Soporte para imágenes (Pillow)
- Soporte para videos (MoviePy)

### 🔧 Fixed - Correcciones

#### CLI
- **Click double-import issue**: Arreglado problema donde Python cargaba el módulo como `__main__` y `ultramemory_cli.main` causando dos objetos `app` diferentes
- **Entry point**: Cambiado de `app` a `main()` para evitar conflictos de importación
- **Health call issue**: Removidas llamadas directas a `health()` desde `status()`, `up()` y `restart()` que causaban errores de argumentos en Click

#### Qdrant
- **API method**: Actualizado de `search()` deprecado a `query_points()` para Qdrant v1.16+
- **Collection creation**: Agregado `ensure_collection()` antes de insertar datos
- **API key**: Removido requisito de API key para desarrollo local

#### Docker Compose
- **Redis password**: Arreglado manejo de password vacío en Redis
- **Qdrant healthcheck**: Cambiado de curl a TCP check (curl no disponible en imagen)
- **FalkorDB image**: Cambiado de GHCR a Docker Hub para evitar error "denied"

#### Error Handling
- **Graphiti optional**: Agregado try/except para que Graphiti sea opcional
- **Redis optional**: Agregado try/except para que Redis sea opcional
- **Graceful degradation**: El sistema funciona sin servicios opcionales

### 📚 Documentation

- **README.md completo**: Instrucciones detalladas de instalación y uso
- **Arquitectura diagram**: Diagrama ASCII de la arquitectura del sistema
- **Troubleshooting**: Sección de solución de problemas comunes
- **API endpoints**: Documentación de endpoints disponibles

### 🛠️ Technical Details

#### Stack Tecnológico
- Python 3.11+
- Click/Typer para CLI
- FastAPI para API REST
- Qdrant Client para vector DB
- Redis Client para cache
- LangChain/LangGraph para orquestación
- Pydantic para validación

#### Estructura de Paquetes
```
ultramemory/
├── agents/           # 4 agentes del sistema
├── core/             # Memoria híbrida + clientes
├── services/         # API REST
├── ultramemory_cli/  # 9 módulos CLI
├── docker/           # Configuración Docker
└── tests/            # Tests
```

---

## Próximas Versiones

### [0.2.0] - Planificado

- [ ] Integración real con Graphiti para grafos temporales
- [ ] Embeddings reales con Gemini/OpenAI (actualmente mock)
- [ ] Agentes personalizados con archivo MD
- [ ] Scheduler para tareas programadas
- [ ] Web UI para gestión visual
- [ ] API de webhooks para integraciones

### [0.3.0] - Planificado

- [ ] Soporte para más proveedores LLM
- [ ] Sistema de plugins
- [ ] Backup/restore automático
- [ ] Clustering para alta disponibilidad
- [ ] API GraphQL además de REST

---

## Cómo Contribuir

Ver [README.md](README.md) para instrucciones de contribución.

## Licencia

MIT License - Ver [LICENSE](LICENSE) para más detalles.
