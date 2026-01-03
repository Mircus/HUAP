"""
HUAP Persistence Interfaces.

Abstract base classes for storage backends.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, List, Optional


class TraceStore(ABC):
    """Interface for trace storage."""

    @abstractmethod
    def append(self, run_id: str, event: Dict[str, Any]) -> None:
        """Append an event to a trace."""
        pass

    @abstractmethod
    def read(self, run_id: str) -> List[Dict[str, Any]]:
        """Read all events for a trace."""
        pass

    @abstractmethod
    def list_runs(self) -> List[str]:
        """List all run IDs."""
        pass

    @abstractmethod
    def exists(self, run_id: str) -> bool:
        """Check if a trace exists."""
        pass


class StateStore(ABC):
    """Interface for state snapshot storage."""

    @abstractmethod
    def save(self, state_ref: str, state: Dict[str, Any]) -> None:
        """Save a state snapshot."""
        pass

    @abstractmethod
    def load(self, state_ref: str) -> Optional[Dict[str, Any]]:
        """Load a state snapshot."""
        pass

    @abstractmethod
    def exists(self, state_ref: str) -> bool:
        """Check if a state snapshot exists."""
        pass

    @abstractmethod
    def delete(self, state_ref: str) -> bool:
        """Delete a state snapshot."""
        pass


class KVStore(ABC):
    """Interface for key-value storage."""

    @abstractmethod
    def get(self, namespace: str, key: str) -> Optional[Any]:
        """Get a value."""
        pass

    @abstractmethod
    def set(self, namespace: str, key: str, value: Any) -> None:
        """Set a value."""
        pass

    @abstractmethod
    def delete(self, namespace: str, key: str) -> bool:
        """Delete a value."""
        pass

    @abstractmethod
    def list_keys(self, namespace: str) -> List[str]:
        """List all keys in a namespace."""
        pass

    @abstractmethod
    def list_namespaces(self) -> List[str]:
        """List all namespaces."""
        pass
