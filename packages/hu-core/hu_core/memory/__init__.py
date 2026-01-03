"""
HUAP Memory System

This package provides a unified memory interface with multiple providers:
- HindsightProvider: Stub for Hindsight API integration
- FileKVStore: File-based key-value storage (from persistence module)

And a ContextBuilder that reconstructs context from trace events for
deterministic replay and evaluation.

Usage:
    from hu_core.memory import (
        MemoryProvider,
        ContextBuilder,
    )

    # Build context from trace
    builder = ContextBuilder(provider)
    context = await builder.build_from_trace("trace.jsonl")
"""

from .providers.base import MemoryProvider, MemoryEntry, MemoryQuery
from .providers.hindsight import HindsightProvider
from .context_builder import ContextBuilder, ContextData

__all__ = [
    # Providers
    "MemoryProvider",
    "MemoryEntry",
    "MemoryQuery",
    "HindsightProvider",
    # Context
    "ContextBuilder",
    "ContextData",
]
