"""
HUAP Filesystem Storage Implementations.

Pure Python, no external dependencies.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .interfaces import TraceStore, StateStore, KVStore


def get_huap_home() -> Path:
    """
    Get HUAP home directory.

    Uses HUAP_HOME env var or defaults to ~/.huap
    """
    home = os.environ.get("HUAP_HOME")
    if home:
        return Path(home)
    return Path.home() / ".huap"


class FileTraceStore(TraceStore):
    """
    Filesystem-based trace storage.

    Stores traces as JSONL files in {base_dir}/traces/{run_id}.jsonl
    """

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize the store.

        Args:
            base_dir: Base directory (default: HUAP_HOME/traces)
        """
        if base_dir is None:
            base_dir = get_huap_home() / "traces"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, run_id: str) -> Path:
        """Get the path for a trace file."""
        # Sanitize run_id to prevent path traversal
        safe_id = run_id.replace("/", "_").replace("\\", "_")
        return self.base_dir / f"{safe_id}.jsonl"

    def append(self, run_id: str, event: Dict[str, Any]) -> None:
        """Append an event to a trace."""
        path = self._get_path(run_id)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")

    def read(self, run_id: str) -> List[Dict[str, Any]]:
        """Read all events for a trace."""
        path = self._get_path(run_id)
        if not path.exists():
            return []

        events = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events

    def list_runs(self) -> List[str]:
        """List all run IDs."""
        runs = []
        for path in self.base_dir.glob("*.jsonl"):
            runs.append(path.stem)
        return sorted(runs)

    def exists(self, run_id: str) -> bool:
        """Check if a trace exists."""
        return self._get_path(run_id).exists()


class FileStateStore(StateStore):
    """
    Filesystem-based state storage.

    Stores state snapshots as JSON files in {base_dir}/state/{state_ref}.json
    """

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize the store.

        Args:
            base_dir: Base directory (default: HUAP_HOME/state)
        """
        if base_dir is None:
            base_dir = get_huap_home() / "state"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, state_ref: str) -> Path:
        """Get the path for a state file."""
        safe_ref = state_ref.replace("/", "_").replace("\\", "_")
        return self.base_dir / f"{safe_ref}.json"

    def save(self, state_ref: str, state: Dict[str, Any]) -> None:
        """Save a state snapshot."""
        path = self._get_path(state_ref)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, default=str, indent=2)

    def load(self, state_ref: str) -> Optional[Dict[str, Any]]:
        """Load a state snapshot."""
        path = self._get_path(state_ref)
        if not path.exists():
            return None

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def exists(self, state_ref: str) -> bool:
        """Check if a state snapshot exists."""
        return self._get_path(state_ref).exists()

    def delete(self, state_ref: str) -> bool:
        """Delete a state snapshot."""
        path = self._get_path(state_ref)
        if path.exists():
            path.unlink()
            return True
        return False


class FileKVStore(KVStore):
    """
    Filesystem-based key-value storage.

    Stores values as JSON files in {base_dir}/kv/{namespace}/{key}.json
    """

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize the store.

        Args:
            base_dir: Base directory (default: HUAP_HOME/kv)
        """
        if base_dir is None:
            base_dir = get_huap_home() / "kv"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_namespace_dir(self, namespace: str) -> Path:
        """Get the directory for a namespace."""
        safe_ns = namespace.replace("/", "_").replace("\\", "_")
        ns_dir = self.base_dir / safe_ns
        ns_dir.mkdir(parents=True, exist_ok=True)
        return ns_dir

    def _get_path(self, namespace: str, key: str) -> Path:
        """Get the path for a key."""
        safe_key = key.replace("/", "_").replace("\\", "_")
        return self._get_namespace_dir(namespace) / f"{safe_key}.json"

    def get(self, namespace: str, key: str) -> Optional[Any]:
        """Get a value."""
        path = self._get_path(namespace, key)
        if not path.exists():
            return None

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("value")

    def set(self, namespace: str, key: str, value: Any) -> None:
        """Set a value."""
        path = self._get_path(namespace, key)
        data = {
            "value": value,
            "updated_at": datetime.utcnow().isoformat(),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, default=str, indent=2)

    def delete(self, namespace: str, key: str) -> bool:
        """Delete a value."""
        path = self._get_path(namespace, key)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_keys(self, namespace: str) -> List[str]:
        """List all keys in a namespace."""
        ns_dir = self._get_namespace_dir(namespace)
        keys = []
        for path in ns_dir.glob("*.json"):
            keys.append(path.stem)
        return sorted(keys)

    def list_namespaces(self) -> List[str]:
        """List all namespaces."""
        namespaces = []
        for path in self.base_dir.iterdir():
            if path.is_dir():
                namespaces.append(path.name)
        return sorted(namespaces)
