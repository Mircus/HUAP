"""
Memory Tools — thin tool wrappers around the MemoryPort interface.

Exposed as standard HUAP tools so memory operations appear as
``tool_call`` / ``tool_result`` trace events.

Tools:
    memory.retain  — store a memory item
    memory.recall  — retrieve relevant memories
    memory.reflect — synthesise insights from memories
"""
from __future__ import annotations

import time
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
    tracer=None,
) -> Dict[str, Any]:
    """Tool: memory.retain — store a memory item."""
    if tracer:
        tracer.tool_call("memory.retain", {"bank_id": bank_id, "content": content[:200], "context": context})

    t0 = time.time()
    p = _get_port(port)
    item = await p.retain(bank_id, content, context=context, metadata=metadata)
    result = {"status": "retained", "item": item.to_dict()}

    if tracer:
        tracer.tool_result(
            "memory.retain",
            {"status": "retained", "item_id": item.id, "bank_id": bank_id},
            duration_ms=(time.time() - t0) * 1000,
        )

    return result


async def memory_recall(
    bank_id: str,
    query: str,
    k: int = 10,
    filters: Optional[Dict[str, Any]] = None,
    port: Optional[MemoryPort] = None,
    tracer=None,
) -> Dict[str, Any]:
    """Tool: memory.recall — retrieve relevant memories."""
    if tracer:
        tracer.tool_call("memory.recall", {"bank_id": bank_id, "query": query, "k": k})

    t0 = time.time()
    p = _get_port(port)
    items = await p.recall(bank_id, query, k=k, filters=filters)
    result = {
        "status": "recalled",
        "count": len(items),
        "items": [i.to_dict() for i in items],
    }

    if tracer:
        tracer.tool_result(
            "memory.recall",
            {"status": "recalled", "count": len(items), "query": query},
            duration_ms=(time.time() - t0) * 1000,
        )

    return result


async def memory_reflect(
    bank_id: str,
    query: str,
    k: int = 10,
    filters: Optional[Dict[str, Any]] = None,
    port: Optional[MemoryPort] = None,
    tracer=None,
) -> Dict[str, Any]:
    """Tool: memory.reflect — synthesise insights from memories."""
    if tracer:
        tracer.tool_call("memory.reflect", {"bank_id": bank_id, "query": query, "k": k})

    t0 = time.time()
    p = _get_port(port)
    items = await p.reflect(bank_id, query, k=k, filters=filters)
    result = {
        "status": "reflected",
        "count": len(items),
        "items": [i.to_dict() for i in items],
    }

    if tracer:
        tracer.tool_result(
            "memory.reflect",
            {"status": "reflected", "count": len(items)},
            duration_ms=(time.time() - t0) * 1000,
        )

    return result
