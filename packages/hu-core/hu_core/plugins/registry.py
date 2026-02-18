"""
Plugin Registry — discover, load, and resolve plugins from config.

Config search order:
    1. ``HUAP_PLUGINS_PATH`` env var
    2. ``.huap/plugins.yaml`` (project workspace)
    3. ``config/plugins.yaml`` (repo root)

The registry is intentionally lazy: it parses specs from YAML but only
imports the ``impl`` when ``resolve(plugin_id)`` is called. This keeps
core dependency-light.
"""
from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .spec import PluginSpec

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# ---------------------------------------------------------------------------
# Default config paths
# ---------------------------------------------------------------------------

_SEARCH_PATHS = [
    ".huap/plugins.yaml",
    "config/plugins.yaml",
]


def _find_config() -> Optional[Path]:
    env = os.environ.get("HUAP_PLUGINS_PATH")
    if env:
        p = Path(env)
        if p.exists():
            return p
    for rel in _SEARCH_PATHS:
        p = Path(rel)
        if p.exists():
            return p
    return None


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class PluginRegistry:
    """Manages plugin specs and lazy-loads implementations on demand."""

    def __init__(self, specs: Optional[List[PluginSpec]] = None):
        self._specs: Dict[str, PluginSpec] = {}
        if specs:
            for s in specs:
                self._specs[s.id] = s

    # ── load from YAML ────────────────────────────────────────────────────

    @classmethod
    def load(cls, path: Optional[str] = None) -> "PluginRegistry":
        """Load registry from a YAML file (or auto-detected config)."""
        if not HAS_YAML:
            return cls()

        config_path = Path(path) if path else _find_config()
        if config_path is None or not config_path.exists():
            return cls()

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        raw_plugins = data.get("plugins", [])
        specs = []
        for entry in raw_plugins:
            try:
                specs.append(PluginSpec.from_dict(entry))
            except (ValueError, KeyError):
                pass  # skip malformed entries silently

        return cls(specs)

    # ── queries ───────────────────────────────────────────────────────────

    def list(self, only_enabled: bool = False) -> List[PluginSpec]:
        """Return all specs (optionally filtered to enabled only)."""
        out = list(self._specs.values())
        if only_enabled:
            out = [s for s in out if s.enabled]
        return out

    def get(self, plugin_id: str) -> Optional[PluginSpec]:
        return self._specs.get(plugin_id)

    def by_type(self, plugin_type: str) -> List[PluginSpec]:
        return [s for s in self._specs.values() if s.type == plugin_type]

    # ── resolve (lazy import) ─────────────────────────────────────────────

    def resolve(self, plugin_id: str) -> Any:
        """
        Import and return the class/object referenced by ``spec.impl``.

        The ``impl`` field uses ``module.path:ClassName`` notation.
        Raises ImportError or AttributeError on failure.
        """
        spec = self._specs.get(plugin_id)
        if spec is None:
            raise KeyError(f"Plugin '{plugin_id}' not registered")

        module_path, _, attr = spec.impl.partition(":")
        if not attr:
            raise ValueError(f"Plugin impl '{spec.impl}' must use 'module:Class' format")

        mod = importlib.import_module(module_path)
        return getattr(mod, attr)

    def resolve_instance(self, plugin_id: str) -> Any:
        """Resolve and instantiate with settings as kwargs."""
        cls_or_fn = self.resolve(plugin_id)
        spec = self._specs[plugin_id]
        return cls_or_fn(**spec.settings) if spec.settings else cls_or_fn()
