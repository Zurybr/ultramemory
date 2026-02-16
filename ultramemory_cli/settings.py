"""Settings management for Ultramemory CLI."""

import json
import os
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".ulmemory"
SETTINGS_FILE = CONFIG_DIR / "settings.json"


class Settings:
    """Manage CLI settings."""

    def __init__(self):
        self._settings: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load settings from file."""
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE) as f:
                self._settings = json.load(f)
        else:
            self._settings = self._default_settings()
            self.save()

    def _default_settings(self) -> dict[str, Any]:
        """Return default settings."""
        return {
            "mode": "local",
            "services": {
                "api": "http://localhost:8000",
                "graphiti": "http://localhost:8001",
                "qdrant": "http://localhost:6333",
                "redis": "localhost:6379",
                "falkordb": "localhost:6370",
                "postgres": "localhost:5432",
                "grafana": "http://localhost:3000",
                "prometheus": "http://localhost:9090",
                "pgadmin": "http://localhost:5050",
                "redisinsight": "http://localhost:5540",
            },
            "credentials": {
                "postgres": {"user": "postgres", "pass": "postgres"},
                "grafana": {"user": "admin", "pass": "admin"},
                "pgadmin": {"email": "admin@ultramemory.local", "pass": "admin"},
                "qdrant": {"api_key": ""},
                "redis": {"password": ""},
            },
            "llm_provider": "openai",
            "embedding_provider": "openai",
            "researcher_topics": [],
            "researcher_schedule": "daily",
            "researcher_output_dir": "./researches",
        }

    def save(self) -> None:
        """Save settings to file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self._settings, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """Get setting by key (supports dot notation)."""
        keys = key.split(".")
        value = self._settings
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def set(self, key: str, value: Any) -> None:
        """Set setting by key (supports dot notation)."""
        keys = key.split(".")
        target = self._settings
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value

    def get_all(self) -> dict[str, Any]:
        """Get all settings."""
        return self._settings.copy()

    @property
    def mode(self) -> str:
        return self._settings.get("mode", "local")

    @mode.setter
    def mode(self, value: str):
        self._settings["mode"] = value
        self.save()

    @property
    def services(self) -> dict[str, str]:
        return self._settings.get("services", {})

    @property
    def credentials(self) -> dict[str, Any]:
        return self._settings.get("credentials", {})


settings = Settings()
