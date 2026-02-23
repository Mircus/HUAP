"""
HUAP Memory System

This package provides a unified memory interface with multiple providers:
- HindsightProvider: SQLite-backed persistent memory (via hu-plugins-hindsight)
- FileKVStore: File-based key-value storage (from persistence module)

And a ContextBuilder that reconstructs context from trace events for
deterministic replay and evaluation.

Usage:
    from hu_core.memory import MemoryProvider, ContextBuilder

    # For the SQLite provider (requires hu-plugins-hindsight):
    from hu_core.memory.providers.hindsight import HindsightProvider

    # Build context from trace
    builder = ContextBuilder(provider)
    context = await builder.build_from_trace("trace.jsonl")
"""

from .providers.base import MemoryProvider, MemoryEntry, MemoryQuery
from .context_builder import ContextBuilder, ContextData

__all__ = [
    # Providers
    "MemoryProvider",
    "MemoryEntry",
    "MemoryQuery",
    # Context
    "ContextBuilder",
    "ContextData",
]
