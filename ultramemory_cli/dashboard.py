"""Dashboard commands for all services."""

import webbrowser

import click

from ultramemory_cli.settings import settings


@click.group(name="dashboard", invoke_without_command=True)
@click.pass_context
def dashboard_group(ctx):
    """Open dashboards and view connection info for all services.

    \b
    Examples:
        ulmemory dashboard           # Show all connections
        ulmemory dashboard grafana   # Open Grafana
        ulmemory dashboard qdrant    # Open Qdrant dashboard
        ulmemory dashboard redis     # Show Redis info
        ulmemory dashboard falkordb  # Show FalkorDB info
    """
    if ctx.invoked_subcommand is None:
        # No subcommand specified, show all connections
        ctx.invoke(show_all)


@dashboard_group.command(name="all")
@click.pass_context
def show_all(ctx):
    """Show all service connections and info."""
    services = settings.services
    creds = settings.credentials

    click.echo("\n")
    click.echo("╔══════════════════════════════════════════════════════════════════════════╗")
    click.echo("║                    🔌 ULTRAMEMORY - ALL CONNECTIONS                      ║")
    click.echo("╚══════════════════════════════════════════════════════════════════════════╝")

    # API
    click.echo("\n┌──────────────────────────────────────────────────────────────────────────┐")
    click.echo("│  🚀 API REST                                                             │")
    click.echo("├──────────────────────────────────────────────────────────────────────────┤")
    click.echo(f"│  🔗 URL:       {services.get('api', 'http://localhost:8000'):<55}│")
    click.echo(f"│  📚 Docs:      {services.get('api', 'http://localhost:8000')}/docs{' ' * 49}│")
    click.echo(f"│  📊 Health:    {services.get('api', 'http://localhost:8000')}/health{' ' * 47}│")
    click.echo("└──────────────────────────────────────────────────────────────────────────┘")

    # Qdrant (Vector DB)
    click.echo("\n┌──────────────────────────────────────────────────────────────────────────┐")
    click.echo("│  🎯 QDRANT - Vector Database (Embeddings)                                │")
    click.echo("├──────────────────────────────────────────────────────────────────────────┤")
    qdrant_url = services.get('qdrant', 'http://localhost:6333')
    click.echo(f"│  🔗 URL:       {qdrant_url:<55}│")
    click.echo(f"│  📊 Dashboard: {qdrant_url}/dashboard{' ' * 42}│")
    click.echo(f"│  🔌 Puerto:    6333 (HTTP) / 6334 (gRPC){' ' * 33}│")
    qdrant_key = creds.get('qdrant', {}).get('api_key', '')
    click.echo(f"│  🔑 API Key:   {qdrant_key or '(sin autenticación)':<55}│")
    click.echo("│  📦 Colección: ultramemory                                               │")
    click.echo("└──────────────────────────────────────────────────────────────────────────┘")

    # FalkorDB (Graph DB)
    click.echo("\n┌──────────────────────────────────────────────────────────────────────────┐")
    click.echo("│  🕸️  FALKORDB - Graph Database (Temporal Knowledge)                       │")
    click.echo("├──────────────────────────────────────────────────────────────────────────┤")
    falkor_url = services.get('falkordb', 'localhost:6370')
    click.echo(f"│  🔗 Host:      {falkor_url:<55}│")
    click.echo("│  🔌 Puerto:    6370                                                      │")
    click.echo("│  📝 Protocolo: Redis-compatible                                          │")
    click.echo("│  📊 Comando:   GRAPH.QUERY                                               │")
    click.echo("└──────────────────────────────────────────────────────────────────────────┘")

    # Redis (Cache)
    click.echo("\n┌──────────────────────────────────────────────────────────────────────────┐")
    click.echo("│  ⚡ REDIS - Cache & Session Store                                         │")
    click.echo("├──────────────────────────────────────────────────────────────────────────┤")
    redis_url = services.get('redis', 'localhost:6379')
    click.echo(f"│  🔗 Host:      {redis_url:<55}│")
    click.echo("│  🔌 Puerto:    6379                                                      │")
    redis_pass = creds.get('redis', {}).get('password', '')
    click.echo(f"│  🔑 Password:  {redis_pass or '(sin password)':<55}│")
    click.echo("│  💾 DB:        0 (default)                                               │")
    click.echo("└──────────────────────────────────────────────────────────────────────────┘")

    # PostgreSQL
    click.echo("\n┌──────────────────────────────────────────────────────────────────────────┐")
    click.echo("│  🐘 POSTGRESQL - Metadata Store                                          │")
    click.echo("├──────────────────────────────────────────────────────────────────────────┤")
    pg_url = services.get('postgres', 'localhost:5432')
    pg_creds = creds.get('postgres', {})
    click.echo(f"│  🔗 Host:      {pg_url:<55}│")
    click.echo(f"│  👤 Usuario:   {pg_creds.get('user', 'postgres'):<55}│")
    click.echo(f"│  🔑 Password:  {pg_creds.get('pass', 'postgres'):<55}│")
    click.echo("│  💾 Database:  ultramemory                                               │")
    click.echo("└──────────────────────────────────────────────────────────────────────────┘")

    # Grafana
    click.echo("\n┌──────────────────────────────────────────────────────────────────────────┐")
    click.echo("│  📊 GRAFANA - Monitoring Dashboard                                       │")
    click.echo("├──────────────────────────────────────────────────────────────────────────┤")
    grafana_url = services.get('grafana', 'http://localhost:3000')
    grafana_creds = creds.get('grafana', {})
    click.echo(f"│  🔗 URL:       {grafana_url:<55}│")
    click.echo(f"│  👤 Usuario:   {grafana_creds.get('user', 'admin'):<55}│")
    click.echo(f"│  🔑 Password:  {grafana_creds.get('pass', 'admin'):<55}│")
    click.echo("└──────────────────────────────────────────────────────────────────────────┘")

    # Prometheus
    click.echo("\n┌──────────────────────────────────────────────────────────────────────────┐")
    click.echo("│  📈 PROMETHEUS - Metrics Collection                                      │")
    click.echo("├──────────────────────────────────────────────────────────────────────────┤")
    prom_url = services.get('prometheus', 'http://localhost:9090')
    click.echo(f"│  🔗 URL:       {prom_url:<55}│")
    click.echo("│  📊 Query:     /api/v1/query                                             │")
    click.echo("│  📋 Targets:   /api/v1/targets                                           │")
    click.echo("└──────────────────────────────────────────────────────────────────────────┘")

    # Quick commands
    click.echo("\n")
    click.echo("┌──────────────────────────────────────────────────────────────────────────┐")
    click.echo("│  🖥️  HERRAMIENTAS DE VISUALIZACIÓN                                       │")
    click.echo("├──────────────────────────────────────────────────────────────────────────┤")
    click.echo("│  🎯 Qdrant Dashboard:     http://localhost:6333/dashboard               │")
    click.echo("│  🕸️  FalkorDB Browser:    http://localhost:3001                         │")
    click.echo("│  ⚡ RedisInsight:          http://localhost:5540                         │")
    click.echo("│  🐘 pgAdmin (PostgreSQL): http://localhost:5050                          │")
    click.echo("│  📊 Grafana:               http://localhost:3000                         │")
    click.echo("└──────────────────────────────────────────────────────────────────────────┘")
    click.echo("")
    click.echo("┌──────────────────────────────────────────────────────────────────────────┐")
    click.echo("│  💡 COMANDOS RÁPIDOS                                                     │")
    click.echo("├──────────────────────────────────────────────────────────────────────────┤")
    click.echo("│  ulmemory dashboard qdrant       → Abrir Qdrant (embeddings)             │")
    click.echo("│  ulmemory dashboard falkor       → Abrir FalkorDB Browser (grafos)       │")
    click.echo("│  ulmemory dashboard redisinsight → Abrir RedisInsight (cache+graph)      │")
    click.echo("│  ulmemory dashboard pgadmin      → Abrir pgAdmin (PostgreSQL)            │")
    click.echo("│  ulmemory dashboard grafana      → Abrir Grafana (métricas)              │")
    click.echo("└──────────────────────────────────────────────────────────────────────────┘")
    click.echo("")


@dashboard_group.command(name="grafana")
def open_grafana():
    """Open Grafana monitoring dashboard."""
    grafana_url = settings.services.get("grafana", "http://localhost:3000")
    grafana_creds = settings.credentials.get("grafana", {})

    click.echo("\n╔══════════════════════════════════════════════════════╗")
    click.echo("║               📊 GRAFANA DASHBOARD                   ║")
    click.echo("╚══════════════════════════════════════════════════════╝")
    click.echo(f"\n  🔗 URL:      {grafana_url}")
    click.echo(f"  👤 Usuario:  {grafana_creds.get('user', 'admin')}")
    click.echo(f"  🔑 Password: {grafana_creds.get('pass', 'admin')}")
    click.echo("\n  ⚠️  Cambia las credenciales por defecto en producción!")
    click.echo("")

    webbrowser.open(grafana_url)


@dashboard_group.command(name="qdrant")
def open_qdrant():
    """Open Qdrant vector database dashboard."""
    qdrant_url = settings.services.get("qdrant", "http://localhost:6333")
    qdrant_key = settings.credentials.get("qdrant", {}).get("api_key", "")

    click.echo("\n╔══════════════════════════════════════════════════════╗")
    click.echo("║            🎯 QDRANT - VECTOR DATABASE               ║")
    click.echo("╚══════════════════════════════════════════════════════╝")
    click.echo(f"\n  🔗 API URL:       {qdrant_url}")
    click.echo(f"  📊 Dashboard:     {qdrant_url}/dashboard")
    click.echo(f"  📚 Collections:   {qdrant_url}/collections")
    click.echo(f"  🔑 API Key:       {qdrant_key or '(sin autenticación)'}")
    click.echo(f"  📦 Colección:     ultramemory")
    click.echo("\n  💡 Vector size:   1536 (OpenAI) / 768 (Gemini)")
    click.echo("")

    webbrowser.open(f"{qdrant_url}/dashboard")


@dashboard_group.command(name="redis")
def show_redis():
    """Show Redis connection info."""
    redis_url = settings.services.get("redis", "localhost:6379")
    redis_pass = settings.credentials.get("redis", {}).get("password", "")

    click.echo("\n╔══════════════════════════════════════════════════════╗")
    click.echo("║              ⚡ REDIS - CACHE STORE                  ║")
    click.echo("╚══════════════════════════════════════════════════════╝")
    click.echo(f"\n  🔗 Host:      {redis_url}")
    click.echo(f"  🔌 Puerto:    6379")
    click.echo(f"  🔑 Password:  {redis_pass or '(sin password)'}")
    click.echo(f"  💾 Database:  0 (default)")
    click.echo("\n  📝 Comandos útiles:")
    click.echo("     redis-cli -h localhost -p 6379")
    click.echo("     redis-cli -h localhost -p 6379 PING")
    click.echo("     redis-cli -h localhost -p 6379 INFO")
    click.echo("")


@dashboard_group.command(name="falkordb")
def show_falkordb():
    """Show FalkorDB graph database connection info."""
    falkor_url = settings.services.get("falkordb", "localhost:6370")

    click.echo("\n╔══════════════════════════════════════════════════════╗")
    click.echo("║           🕸️  FALKORDB - GRAPH DATABASE              ║")
    click.echo("╚══════════════════════════════════════════════════════╝")
    click.echo(f"\n  🔗 Host:      {falkor_url}")
    click.echo(f"  🔌 Puerto:    6370")
    click.echo(f"  📝 Protocolo: Redis-compatible")
    click.echo(f"  📊 Tipo:      Temporal Knowledge Graph")
    click.echo("\n  📝 Comandos útiles:")
    click.echo("     redis-cli -h localhost -p 6370")
    click.echo("     GRAPH.QUERY graph_name 'MATCH (n) RETURN n'")
    click.echo("\n  💡 FalkorDB almacena relaciones temporales y")
    click.echo("     conocimiento estructurado de la memoria.")
    click.echo("")


@dashboard_group.command(name="api")
def open_api():
    """Open API documentation."""
    api_url = settings.services.get("api", "http://localhost:8000")

    click.echo("\n╔══════════════════════════════════════════════════════╗")
    click.echo("║               🚀 API REST DOCUMENTATION              ║")
    click.echo("╚══════════════════════════════════════════════════════╝")
    click.echo(f"\n  🔗 API URL:   {api_url}")
    click.echo(f"  📚 Swagger:   {api_url}/docs")
    click.echo(f"  📖 ReDoc:     {api_url}/redoc")
    click.echo(f"  ❤️  Health:    {api_url}/health")
    click.echo(f"  📊 OpenAPI:   {api_url}/openapi.json")
    click.echo("")

    webbrowser.open(f"{api_url}/docs")


@dashboard_group.command(name="prometheus")
def open_prometheus():
    """Open Prometheus metrics dashboard."""
    prom_url = settings.services.get("prometheus", "http://localhost:9090")

    click.echo("\n╔══════════════════════════════════════════════════════╗")
    click.echo("║            📈 PROMETHEUS - METRICS                   ║")
    click.echo("╚══════════════════════════════════════════════════════╝")
    click.echo(f"\n  🔗 URL:       {prom_url}")
    click.echo(f"  📊 Query:     {prom_url}/graph")
    click.echo(f"  📋 Targets:   {prom_url}/targets")
    click.echo(f"  ⚠️  Alerts:    {prom_url}/alerts")
    click.echo("")

    webbrowser.open(prom_url)


@dashboard_group.command(name="pgadmin")
def open_pgadmin():
    """Open pgAdmin for PostgreSQL visualization."""
    pgadmin_url = "http://localhost:5050"

    click.echo("\n╔══════════════════════════════════════════════════════╗")
    click.echo("║            🐘 PGADMIN - POSTGRESQL GUI               ║")
    click.echo("╚══════════════════════════════════════════════════════╝")
    click.echo(f"\n  🔗 URL:       {pgadmin_url}")
    click.echo(f"  👤 Email:     admin@ultramemory.local")
    click.echo(f"  🔑 Password:  admin")
    click.echo("\n  📝 Para conectar a PostgreSQL:")
    click.echo("     Host: postgres (o localhost desde host)")
    click.echo("     Port: 5432")
    click.echo("     User: postgres")
    click.echo("     Pass: postgres")
    click.echo("")

    webbrowser.open(pgadmin_url)


@dashboard_group.command(name="redisinsight")
def open_redisinsight():
    """Open RedisInsight for Redis and FalkorDB visualization."""
    redisinsight_url = "http://localhost:5540"

    click.echo("\n╔══════════════════════════════════════════════════════╗")
    click.echo("║          ⚡ REDISINSIGHT - REDIS & FALKORDB           ║")
    click.echo("╚══════════════════════════════════════════════════════╝")
    click.echo(f"\n  🔗 URL:       {redisinsight_url}")
    click.echo("\n  📝 Conexiones a agregar:")
    click.echo("\n  1️⃣  Redis (Cache):")
    click.echo("     Host: host.docker.internal (o localhost)")
    click.echo("     Port: 6379")
    click.echo("     Name: Ultramemory Redis")
    click.echo("\n  2️⃣  FalkorDB (Graph):")
    click.echo("     Host: host.docker.internal (o localhost)")
    click.echo("     Port: 6370")
    click.echo("     Name: Ultramemory FalkorDB")
    click.echo("\n  💡 RedisInsight soporta ambas bases de datos!")
    click.echo("")

    webbrowser.open(redisinsight_url)


@dashboard_group.command(name="falkor")
def open_falkordb_browser():
    """Open FalkorDB Browser for graph visualization."""
    falkor_url = "http://localhost:3001"

    click.echo("\n╔══════════════════════════════════════════════════════╗")
    click.echo("║          🕸️  FALKORDB BROWSER - GRAPH VISUALIZER      ║")
    click.echo("╚══════════════════════════════════════════════════════╝")
    click.echo(f"\n  🔗 URL:       {falkor_url}")
    click.echo("\n  📊 Funcionalidades:")
    click.echo("     • Visualizar grafos de conocimiento")
    click.echo("     • Ejecutar queries Cypher")
    click.echo("     • Explorar nodos y relaciones")
    click.echo("     • Ver datos temporales")
    click.echo("\n  💡 Ya conectado automáticamente a FalkorDB!")
    click.echo("")

    webbrowser.open(falkor_url)


# Default command shows all
@dashboard_group.command(name="connections")
@click.pass_context
def show_connections(ctx):
    """Show all database and service connections (alias for 'all')."""
    ctx.invoke(show_all)
