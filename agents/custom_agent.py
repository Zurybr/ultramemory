"""Custom agent framework."""

import json
from pathlib import Path
from typing import Any

from core.memory import MemorySystem


class CustomAgent:
    """Dynamically created agent from MD + Skill + System Prompt."""

    def __init__(
        self,
        name: str,
        md_path: Path,
        skill_path: Path | None = None,
        system_prompt: str | None = None,
    ):
        self.name = name
        self.md_path = md_path
        self.skill_path = skill_path
        self.system_prompt = system_prompt or self._load_md()
        self.skills = self._load_skills() if skill_path else []

    def _load_md(self) -> str:
        """Load agent documentation."""
        if self.md_path.exists():
            return self.md_path.read_text(encoding="utf-8")
        return ""

    def _load_skills(self) -> list[dict[str, Any]]:
        """Load agent skills."""
        if self.skill_path and self.skill_path.exists():
            return json.loads(self.skill_path.read_text(encoding="utf-8"))
        return []

    async def run(self, input_data: Any, memory: MemorySystem) -> dict[str, Any]:
        """Run the custom agent."""
        # Placeholder - implement based on skills defined
        return {
            "status": "success",
            "output": f"Agent {self.name} executed",
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize agent config."""
        return {
            "name": self.name,
            "md_path": str(self.md_path),
            "skill_path": str(self.skill_path) if self.skill_path else None,
            "system_prompt": self.system_prompt,
            "skills": self.skills,
        }
