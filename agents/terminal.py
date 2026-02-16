"""Terminal Agent - interactive CLI guide."""

import asyncio
from pathlib import Path
from typing import Any

from core.memory import MemorySystem


class TerminalAgent:
    """Interactive terminal agent for manual operations.

    Provides guided workflows for:
    - Viewing research status
    - Reviewing PRDs
    - Manual agent execution
    - System diagnostics
    """

    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system

    async def show_dashboard(self) -> str:
        """Show system dashboard."""
        # Count memories
        count = await self.memory.qdrant.count()

        # Count research files
        research_dir = Path.home() / ".ulmemory" / "research" / "reports"
        research_count = len(list(research_dir.glob("*.md"))) if research_dir.exists() else 0

        # Count PRDs
        prd_dir = Path.home() / ".ulmemory" / "prds"
        prd_count = len(list(prd_dir.glob("*.md"))) if prd_dir.exists() else 0

        # Get recent activities
        recent = await self.memory.qdrant.search(
            query_embedding=await self.memory.embedding.embed("recent activity"),
            limit=5,
        )

        dashboard = f"""
╔══════════════════════════════════════════════════════════════╗
║                    ULTRAMEMORY DASHBOARD                     ║
╚══════════════════════════════════════════════════════════════╝

📊 ESTADÍSTICAS
   ├─ Memorias totales: {count}
   ├─ Investigaciones: {research_count}
   └─ PRDs generados: {prd_count}

📋 OPERACIONES DISPONIBLES
   ├─ ulmemory agent run researcher "query" --web
   ├─ ulmemory agent run consolidator
   ├─ ulmemory schedule list
   └─ ulmemory memory query "término"

🔔 PRÓXIMAS ACCIONES
   ├─ Revisar heartbeat: ~/.ulmemory/heartbeat.md
   ├─ Ver investigaciones: ~/.ulmemory/research/reports/
   └─ Revisar PRDs: ~/.ulmemory/prds/

💡 AYUDA
   └─ ulmemory --help
"""
        return dashboard

    async def guide_research(self, topic: str | None = None) -> str:
        """Guide user through research workflow."""
        if not topic:
            return """
🔍 GUÍA DE INVESTIGACIÓN

Para investigar un tema:

1. Define el tema de investigación
2. Ejecuta: ulmemory agent run researcher "tu tema" --web --deep
3. Revisa los resultados en ~/.ulmemory/research/reports/

¿Quieres investigar un tema específico?
Ejemplo: "AI agent frameworks" o "memory patterns"
"""

        return f"""
🎯 INVESTIGACIÓN: {topic}

Ejecutando investigación...

```bash
ulmemory agent run researcher "{topic}" --web --deep
```

Después de ejecutar, los resultados se guardarán en:
~/.ulmemory/research/reports/

Para generar un PRD desde la investigación:
```bash
ulmemory agent run prd-generator "ruta/a/investigacion.md"
```
"""

    async def guide_prd_review(self) -> str:
        """Guide user through PRD review."""
        import json

        index_file = Path.home() / ".ulmemory" / "prds" / "index.json"

        if not index_file.exists():
            return "No hay PRDs generados aún."

        prds = json.loads(index_file.read_text())

        lines = ["📄 PRDs GENERADOS\n"]

        for prd in prds:
            status_emoji = {
                "draft": "📝",
                "in_progress": "🔄",
                "completed": "✅",
            }.get(prd.get("status", "draft"), "📝")

            lines.append(f"{status_emoji} {prd['title']}")
            lines.append(f"   Estado: {prd.get('status', 'draft')}")
            lines.append(f"   Archivo: {prd['prd_file']}")
            lines.append("")

        lines.extend([
            "\n📋 OPERACIONES CON PRDs",
            "",
            "Para marcar como en progreso:",
            "  ulmemory agent run prd-generator --update 'título' --status in_progress",
            "",
            "Para marcar como completado:",
            "  ulmemory agent run prd-generator --update 'título' --status completed",
        ])

        return "\n".join(lines)

    async def diagnose(self) -> str:
        """Run system diagnostics."""
        issues = []
        checks = []

        # Check memory count
        try:
            count = await self.memory.qdrant.count()
            checks.append(f"✅ Memoria: {count} entradas")
        except Exception as e:
            issues.append(f"❌ Error en memoria: {e}")
            checks.append("❌ Memoria: Error")

        # Check config
        config = Path.home() / ".config" / "ultramemory" / "config.yaml"
        if config.exists():
            checks.append("✅ Config: Archivo existe")
        else:
            issues.append("⚠️ Config: No encontrado")
            checks.append("⚠️ Config: No existe")

        # Check research directory
        research_dir = Path.home() / ".ulmemory" / "research"
        if research_dir.exists():
            checks.append("✅ Research: Directorio existe")
        else:
            issues.append("⚠️ Research: No existe, se creará")
            checks.append("⚠️ Research: No existe")

        # Check heartbeat
        heartbeat = Path.home() / ".ulmemory" / "heartbeat.md"
        if heartbeat.exists():
            checks.append("✅ Heartbeat: Archivo existe")
        else:
            issues.append("⚠️ Heartbeat: No existe, se creará")
            checks.append("⚠️ Heartbeat: No existe")

        output = ["🔧 DIAGNÓSTICO DEL SISTEMA\n"]

        for check in checks:
            output.append(f"   {check}")

        if issues:
            output.append("\n⚠️ ACCIONES REQUERIDAS:")
            for issue in issues:
                output.append(f"   {issue}")
        else:
            output.append("\n✅ Sistema operativo")

        return "\n".join(output)
