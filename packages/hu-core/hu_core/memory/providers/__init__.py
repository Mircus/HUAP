"""
Memory Providers Package

Provides different backends for the HUAP memory system:
- HindsightProvider: SQLite-backed persistent memory (via hu-plugins-hindsight)
- FileKVStore: File-based storage (from persistence module)

HindsightProvider is not eagerly imported to avoid circular dependencies
with the plugin package. Import it directly:
    from hu_core.memory.providers.hindsight import HindsightProvider
"""

from .base import MemoryProvider, MemoryEntry, MemoryQuery

__all__ = [
    "MemoryProvider",
    "MemoryEntry",
    "MemoryQuery",
]
