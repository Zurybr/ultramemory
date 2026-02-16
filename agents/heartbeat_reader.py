"""Heartbeat system for proactive task execution."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any


HEARTBEAT_PATH = Path.home() / ".ulmemory" / "heartbeat.md"


class HeartbeatReader:
    """Lee y parsea el archivo heartbeat.md para tareas pendientes."""

    def __init__(self, heartbeat_path: Path | None = None):
        self.path = heartbeat_path or HEARTBEAT_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def read(self) -> dict[str, Any]:
        """Lee el heartbeat y retorna tareas pendientes."""
        if not self.path.exists():
            return {"tasks": [], "last_updated": None}

        content = self.path.read_text(encoding="utf-8")
        return self._parse_heartbeat(content)

    def _parse_heartbeat(self, content: str) -> dict[str, Any]:
        """Parsea el contenido del heartbeat."""
        tasks = []
        lines = content.split("\n")
        current_task = None

        for line in lines:
            # Buscar inicio de tarea: - [ ] o - [x]
            task_match = re.match(r'^-\s*\[([ x])\]\s*(.+)$', line)
            if task_match:
                if current_task:
                    tasks.append(current_task)

                status = task_match.group(1) == "x"
                raw_title = task_match.group(2).strip()

                # Extract tags from title
                tag_match = re.findall(r'#(\w+)', raw_title)
                tags = tag_match
                # Remove tags from title
                title = re.sub(r'#\w+', '', raw_title).strip()

                current_task = {
                    "title": title,
                    "completed": status,
                    "tags": tags,
                    "priority": "normal",
                    "created": None,
                }

        if current_task:
            tasks.append(current_task)

        return {
            "tasks": tasks,
            "last_updated": datetime.now().isoformat(),
            "pending_count": sum(1 for t in tasks if not t["completed"]),
        }

    def get_pending_tasks(self, tags: list[str] | None = None) -> list[dict[str, Any]]:
        """Obtiene tareas pendientes, opcionalmente filtradas por tags."""
        data = self.read()
        pending = [t for t in data["tasks"] if not t["completed"]]

        if tags:
            pending = [t for t in pending if any(tag in t["tags"] for tag in tags)]

        return pending

    def mark_completed(self, task_title: str) -> bool:
        """Marca una tarea como completada."""
        if not self.path.exists():
            return False

        content = self.path.read_text(encoding="utf-8")
        lines = content.split("\n")
        new_lines = []

        for line in lines:
            if f"- [ ] {task_title}" in line or f"- [ ]  {task_title}" in line:
                line = line.replace("- [ ]", "- [x]")
            new_lines.append(line)

        self.path.write_text("\n".join(new_lines), encoding="utf-8")
        return True

    def add_task(self, title: str, tags: list[str] | None = None, priority: str = "normal"):
        """Agrega una nueva tarea al heartbeat."""
        if not self.path.exists():
            header = "# Heartbeat - Tareas Pendientes\n\n"
            self.path.write_text(header, encoding="utf-8")

        tags_str = " ".join(f"#{tag}" for tag in (tags or []))
        task_line = f"- [ ] {title} {tags_str}\n"

        with open(self.path, "a", encoding="utf-8") as f:
            f.write(task_line)
