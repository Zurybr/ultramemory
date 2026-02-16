"""Proactive Agent - executes tasks from heartbeat."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from core.memory import MemorySystem
from agents.heartbeat_reader import HeartbeatReader


class ProactiveAgent:
    """Agent that executes tasks from heartbeat.md.

    Runs every 30 minutes and checks for pending tasks.
    Supports task types: research, report, cleanup, notify
    """

    def __init__(self, memory_system: MemorySystem, heartbeat_path: Path | None = None):
        self.memory = memory_system
        self.heartbeat = HeartbeatReader(heartbeat_path)

    async def check_and_execute(self, max_tasks: int = 3) -> dict[str, Any]:
        """Check heartbeat and execute pending tasks.

        Args:
            max_tasks: Maximum tasks to execute per run

        Returns:
            Report of executed tasks
        """
        pending = self.heartbeat.get_pending_tasks()

        if not pending:
            return {
                "status": "no_tasks",
                "executed": 0,
                "message": "No pending tasks in heartbeat",
            }

        results = []
        tasks_to_execute = pending[:max_tasks]

        for task in tasks_to_execute:
            try:
                result = await self._execute_task(task)
                results.append({
                    "task": task["title"],
                    "status": "success",
                    "result": result,
                })

                # Mark as completed
                self.heartbeat.mark_completed(task["title"])

            except Exception as e:
                results.append({
                    "task": task["title"],
                    "status": "error",
                    "error": str(e),
                })

        return {
            "status": "completed",
            "executed": len(results),
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }

    async def _execute_task(self, task: dict[str, Any]) -> dict[str, Any]:
        """Execute a single task based on its tags."""
        title = task["title"]
        tags = task.get("tags", [])

        # Determine task type from tags
        if "research" in tags:
            return await self._do_research(title)
        elif "report" in tags:
            return await self._do_report(title)
        elif "cleanup" in tags or "maintenance" in tags:
            return await self._do_cleanup(title)
        elif "notify" in tags:
            return await self._do_notify(title)
        else:
            # Default: log task
            return {"message": f"Task noted: {title}"}

    async def _do_research(self, task_title: str) -> dict[str, Any]:
        """Execute research task."""
        # Extract topic from title (remove "Investigar" prefix if present)
        topic = task_title.replace("Investigar", "").replace("investigar", "").strip()

        from agents.researcher import ResearcherAgent

        agent = ResearcherAgent(self.memory, enable_web_search=True)

        # Run research
        result = await agent.deep_research(topic, max_depth=2, save_to_memory=True)

        return {
            "topic": topic,
            "sources_found": result.get("total_sources", 0),
            "saved": result.get("synthesis_saved", False),
        }

    async def _do_report(self, task_title: str) -> dict[str, Any]:
        """Execute report generation task."""
        # Generate activity report
        count = await self.memory.qdrant.count()

        report = f"""# Reporte de Actividad

Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Estado de Memoria
- Total de entradas: {count}

## Tareas Completadas
- Reporte generado
"""

        # Save to memory
        doc_id = await self.memory.add(
            report,
            metadata={
                "type": "report",
                "report_type": "activity",
            },
        )

        return {
            "document_id": doc_id,
            "total_memories": count,
        }

    async def _do_cleanup(self, task_title: str) -> dict[str, Any]:
        """Execute cleanup task."""
        from agents.consolidator import ConsolidatorAgent

        agent = ConsolidatorAgent(self.memory)
        result = await agent.consolidate()

        return result

    async def _do_notify(self, task_title: str) -> dict[str, Any]:
        """Execute notification task."""
        # For now, just add a notification to memory
        await self.memory.add(
            f"Notificación: {task_title}",
            metadata={"type": "notification", "source": "proactive"},
        )

        return {"notified": True, "message": task_title}

    async def add_task(
        self,
        title: str,
        tags: list[str] | None = None,
        priority: str = "normal",
    ):
        """Add a task to heartbeat."""
        self.heartbeat.add_task(title, tags, priority)
