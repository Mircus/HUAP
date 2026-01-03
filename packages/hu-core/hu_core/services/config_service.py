"""Shared configuration service for pods and runtime services."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml

_CONFIG_CACHE: Dict[str, Dict[str, Any]] = {}


def _default_config_path() -> Path:
    """Resolve the default config path (supports HUAP_CONFIG_PATH override)."""
    env_path = os.getenv("HUAP_CONFIG_PATH")
    if env_path:
        return Path(env_path).expanduser()
    return Path(__file__).resolve().parents[4] / "config" / "config.yaml"


def clear_config_cache() -> None:
    """Clear cached config (primarily for tests)."""
    _CONFIG_CACHE.clear()


def load_config(path: str | Path | None = None) -> Dict[str, Any]:
    """
    Load YAML configuration with caching.

    Args:
        path: Optional custom path. Defaults to HUAP_CONFIG_PATH or repo config.
    """
    resolved = Path(path).expanduser() if path else _default_config_path()
    key = str(resolved.resolve())
    if key not in _CONFIG_CACHE:
        with open(resolved, "r", encoding="utf-8") as f:
            _CONFIG_CACHE[key] = yaml.safe_load(f) or {}
    return _CONFIG_CACHE[key]


def _get_section(section_path: str) -> Dict[str, Any]:
    """
    Return nested configuration section by dotted path (e.g. ``pods.soma``).
    """
    config = load_config()
    section: Any = config
    for key in section_path.split("."):
        if not isinstance(section, dict):
            return {}
        section = section.get(key)
        if section is None:
            return {}
    return section if isinstance(section, dict) else {}


def get_pod_settings(pod_name: str) -> Dict[str, Any]:
    """Return pod definition from config/pod registry."""
    return _get_section(f"pods.{pod_name}")


def get_integration_settings(name: str) -> Dict[str, Any]:
    """Return settings for a given integration (fitbit, oura, sahha...)."""
    return _get_section(f"integrations.{name}")


def get_platform_settings() -> Dict[str, Any]:
    """Return platform-level settings (UI redirects, feature flags, etc.)."""
    return _get_section("platform")


def get_scheduler_settings() -> Dict[str, Any]:
    """Return scheduler configuration."""
    return _get_section("scheduler")


def get_secret(name: str, default: str | None = None) -> str | None:
    """Fetch a secret from the process environment."""
    return os.getenv(name, default)
