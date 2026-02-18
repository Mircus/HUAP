"""
Tool-Learning-with-Memory — nodes demonstrating memory-driven tool selection.

In stub mode: uses InMemoryPort (no persistence across runs).
With Hindsight plugin: memories persist and improve choices across runs.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict

from hu_core.ports.memory import InMemoryPort
from hu_core.tools.memory_tools import memory_recall, memory_retain
from hu_core.policies.memory_ingest import MemoryIngestPolicy

# Shared state for the demo
_port = InMemoryPort()
_policy = MemoryIngestPolicy()
_BANK = "tool_outcomes"


def _run_async(coro):
    """Run a coroutine from sync code, handling already-running loops."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


def recall_past_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Recall past tool outcomes to inform the current choice."""
    task = state.get("task", "summarize a document")
    result = _run_async(
        memory_recall(_BANK, f"tool for: {task}", k=3, port=_port)
    )
    state["recalled_memories"] = result.get("items", [])
    state["task"] = task
    return state


def choose_tool_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Pick a tool based on recalled memories (or default heuristic)."""
    memories = state.get("recalled_memories", [])

    # If we have a memory of a successful tool, reuse it
    for mem in memories:
        content = mem.get("content", "")
        if "success" in content.lower():
            # Extract tool name from memory
            if "summarize_v2" in content:
                state["chosen_tool"] = "summarize_v2"
                state["choice_reason"] = "recalled: summarize_v2 succeeded before"
                return state

    # Default: pick the basic tool
    state["chosen_tool"] = "summarize_v1"
    state["choice_reason"] = "no relevant memory; using default tool"
    return state


def execute_tool_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the chosen tool (stub: simulate success/failure)."""
    tool = state.get("chosen_tool", "summarize_v1")

    # Stub outcomes
    if tool == "summarize_v1":
        state["tool_result"] = "partial summary (v1 is slower, less accurate)"
        state["tool_status"] = "success"
    elif tool == "summarize_v2":
        state["tool_result"] = "full summary with key points (v2 is better)"
        state["tool_status"] = "success"
    else:
        state["tool_result"] = "unknown tool"
        state["tool_status"] = "error"

    return state


def retain_outcome_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Store the tool outcome in memory for future runs."""
    tool = state.get("chosen_tool", "?")
    status = state.get("tool_status", "?")
    result = state.get("tool_result", "")

    content = f"Tool '{tool}' for task '{state.get('task', '?')}': {status}. {result}"

    # Apply ingest policy
    decision = _policy.should_retain(content, context=f"tool_{status}")
    if decision.allowed:
        _run_async(
            memory_retain(
                _BANK, content,
                context=f"tool_{status}",
                metadata={"tool": tool, "status": status},
                port=_port,
            )
        )
        state["retained"] = True
    else:
        state["retained"] = False
        state["retain_reason"] = decision.reason

    return state
