"""
Memory Providers Package

Provides different backends for the HUAP memory system:
- HindsightProvider: Hindsight API integration (stub)
- FileKVStore: File-based storage (from persistence module)
"""

from .base import MemoryProvider, MemoryEntry, MemoryQuery
from .hindsight import HindsightProvider

__all__ = [
    "MemoryProvider",
    "MemoryEntry",
    "MemoryQuery",
    "HindsightProvider",
]
