"""
Memory Tools — thin tool wrappers around the MemoryPort interface.

Exposed as standard HUAP tools so memory operations appear as
``tool_call`` / ``tool_result`` trace events (no trace schema changes).

Tools:
    memory.retain  — store a memory item
    memory.recall  — retrieve relevant memories
    memory.reflect — synthesise insights from memories
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from ..ports.memory import MemoryPort, InMemoryPort


def _get_port(port: Optional[MemoryPort] = None) -> MemoryPort:
    """Return the supplied port or a default InMemoryPort."""
    return port or InMemoryPort()


async def memory_retain(
    bank_id: str,
    content: str,
    context: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    port: Optional[MemoryPort] = None,
) -> Dict[str, Any]:
    """Tool: memory.retain — store a memory item."""
    p = _get_port(port)
    item = await p.retain(bank_id, content, context=context, metadata=metadata)
    return {"status": "retained", "item": item.to_dict()}


async def memory_recall(
    bank_id: str,
    query: str,
    k: int = 10,
    filters: Optional[Dict[str, Any]] = None,
    port: Optional[MemoryPort] = None,
) -> Dict[str, Any]:
    """Tool: memory.recall — retrieve relevant memories."""
    p = _get_port(port)
    items = await p.recall(bank_id, query, k=k, filters=filters)
    return {
        "status": "recalled",
        "count": len(items),
        "items": [i.to_dict() for i in items],
    }


async def memory_reflect(
    bank_id: str,
    query: str,
    k: int = 10,
    filters: Optional[Dict[str, Any]] = None,
    port: Optional[MemoryPort] = None,
) -> Dict[str, Any]:
    """Tool: memory.reflect — synthesise insights from memories."""
    p = _get_port(port)
    items = await p.reflect(bank_id, query, k=k, filters=filters)
    return {
        "status": "reflected",
        "count": len(items),
        "items": [i.to_dict() for i in items],
    }
