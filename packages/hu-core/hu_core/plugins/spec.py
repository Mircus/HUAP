"""
Plugin Spec — declarative plugin descriptors (YAML-driven).

A plugin YAML entry looks like:

    plugins:
      - id: memory_hindsight
        type: memory
        impl: hu_plugins_hindsight:HindsightMemoryPort
        enabled: true
        settings:
          base_url: http://localhost:8888
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


VALID_TYPES = {"memory", "toolpack", "provider", "other"}


@dataclass
class PluginSpec:
    """Metadata for one registered plugin."""
    id: str
    type: str  # memory | toolpack | provider | other
    impl: str  # import path, e.g. "hu_plugins_hindsight:HindsightMemoryPort"
    enabled: bool = True
    settings: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.type not in VALID_TYPES:
            raise ValueError(f"Unknown plugin type '{self.type}'. Valid: {VALID_TYPES}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "impl": self.impl,
            "enabled": self.enabled,
            "settings": self.settings,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PluginSpec":
        return cls(
            id=d["id"],
            type=d.get("type", "other"),
            impl=d.get("impl", ""),
            enabled=d.get("enabled", True),
            settings=d.get("settings", {}),
        )
