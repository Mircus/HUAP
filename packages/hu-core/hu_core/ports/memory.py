"""
MemoryPort — abstract interface for pluggable memory backends.

Follows the Hindsight abstraction: **retain / recall / reflect**.

- retain: store a memory item into a bank
- recall: retrieve relevant memories by query
- reflect: higher-level synthesis over memories (summaries, insights)

Implementations live in plugin packages (e.g. hu-plugins-hindsight).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class MemoryItem:
    """A single memory entry."""
    id: str
    content: str
    bank_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    context: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0  # relevance score (set by recall/reflect)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "bank_id": self.bank_id,
            "timestamp": self.timestamp,
            "context": self.context,
            "metadata": self.metadata,
            "score": self.score,
        }


class MemoryPort(ABC):
    """
    Abstract interface that all memory backends must implement.

    Plugins extend this (e.g. ``HindsightMemoryPort``) and are loaded
    via the Plugin Registry.
    """

    @abstractmethod
    async def retain(
        self,
        bank_id: str,
        content: str,
        context: Optional[str] = None,
        timestamp: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryItem:
        """Store a memory item. Returns the created MemoryItem."""
        ...

    @abstractmethod
    async def recall(
        self,
        bank_id: str,
        query: str,
        k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[MemoryItem]:
        """Retrieve the *k* most relevant memories for *query*."""
        ...

    @abstractmethod
    async def reflect(
        self,
        bank_id: str,
        query: str,
        k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[MemoryItem]:
        """
        Higher-level synthesis — returns insights or summaries derived from
        stored memories.  Implementations may simply alias ``recall``.
        """
        ...


# ---------------------------------------------------------------------------
# In-memory stub (useful for tests and stub mode)
# ---------------------------------------------------------------------------

class InMemoryPort(MemoryPort):
    """Trivial in-process memory backend (no persistence). Useful for tests."""

    def __init__(self):
        self._banks: Dict[str, List[MemoryItem]] = {}

    async def retain(self, bank_id, content, context=None, timestamp=None, metadata=None):
        from uuid import uuid4
        item = MemoryItem(
            id=f"mem_{uuid4().hex[:12]}",
            content=content,
            bank_id=bank_id,
            timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
            context=context,
            metadata=metadata or {},
        )
        self._banks.setdefault(bank_id, []).append(item)
        return item

    async def recall(self, bank_id, query, k=10, filters=None):
        items = self._banks.get(bank_id, [])
        # Simple substring match scoring
        scored = []
        ql = query.lower()
        for it in items:
            score = 1.0 if ql in it.content.lower() else 0.0
            scored.append((score, it))
        scored.sort(key=lambda x: -x[0])
        results = []
        for score, it in scored[:k]:
            it.score = score
            results.append(it)
        return results

    async def reflect(self, bank_id, query, k=10, filters=None):
        return await self.recall(bank_id, query, k, filters)
