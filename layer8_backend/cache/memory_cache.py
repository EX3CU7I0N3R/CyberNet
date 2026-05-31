from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class MemoryCache:
    values: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str):
        return self.values.get(key)

    def set(self, key: str, value):
        self.values[key] = value
        return value

    def clear(self) -> None:
        self.values.clear()
