"""User preferences of the interface (settings.json). No interface code."""

import json
import os
from dataclasses import asdict, dataclass, fields


@dataclass
class Settings:
    show_weight: bool = True
    animation: bool = True
    speed: int = 10  # 1 (slowest) .. 10 (no pauses)
    logs_symbols: str = ""
    execution_time_log: bool = False

    @classmethod
    def load(cls, path: str) -> "Settings":
        """Reads the file; missing file or keys fall back to the defaults."""
        settings = cls()
        if not os.path.exists(path):
            return settings
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return settings
        for field in fields(cls):
            if field.name in data:
                setattr(settings, field.name, data[field.name])
        return settings

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=4)
