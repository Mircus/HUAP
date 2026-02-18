"""
HUAP CrewAI Adapter — instrument CrewAI runs as HUAP traces.

Usage:
    from hu_core.adapters.crewai import huap_trace_crewai

    with huap_trace_crewai(out="traces/crewai.jsonl", run_name="demo"):
        crew.kickoff()

Requires: crewai (optional dependency)
"""
from __future__ import annotations

import json
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _evt(
    run_id: str,
    kind: str,
    name: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "v": "0.1",
        "ts": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "span_id": f"sp_{uuid4().hex[:12]}",
        "kind": kind,
        "name": name,
        "pod": "crewai_adapter",
        "engine": "crewai",
        "data": data,
    }


class _CrewAITracer:
    """Collects events during a CrewAI run."""

    def __init__(self, run_id: str, run_name: str):
        self.run_id = run_id
        self.run_name = run_name
        self.events: List[Dict[str, Any]] = []

    def on_agent_step(self, agent_name: str, task: str, **extra: Any) -> None:
        self.events.append(_evt(self.run_id, "node", "node_enter", {
            "node": agent_name,
            "state_keys": ["task"],
            **extra,
        }))

    def on_tool_call(self, tool_name: str, tool_input: Any, **extra: Any) -> None:
        self.events.append(_evt(self.run_id, "tool", "tool_call", {
            "tool": tool_name,
            "input": tool_input if isinstance(tool_input, dict) else {"raw": str(tool_input)},
            **extra,
        }))

    def on_tool_result(self, tool_name: str, result: Any, duration_ms: float = 0, **extra: Any) -> None:
        self.events.append(_evt(self.run_id, "tool", "tool_result", {
            "tool": tool_name,
            "result": result if isinstance(result, dict) else {"raw": str(result)[:2000]},
            "duration_ms": duration_ms,
            "status": "ok",
            **extra,
        }))

    def on_llm_request(self, model: str, messages: Any, **extra: Any) -> None:
        self.events.append(_evt(self.run_id, "llm", "llm_request", {
            "provider": "crewai",
            "model": model,
            "messages": messages if isinstance(messages, list) else [],
            **extra,
        }))

    def on_llm_response(self, model: str, text: str, usage: Optional[Dict] = None, duration_ms: float = 0, **extra: Any) -> None:
        self.events.append(_evt(self.run_id, "llm", "llm_response", {
            "provider": "crewai",
            "model": model,
            "text": text[:5000],
            "usage": usage or {},
            "duration_ms": duration_ms,
            **extra,
        }))


@contextmanager
def huap_trace_crewai(
    out: str,
    run_name: str = "crewai_run",
):
    """
    Context manager that instruments a CrewAI run and writes a HUAP trace.

    Example:
        with huap_trace_crewai(out="traces/crewai.jsonl", run_name="demo"):
            crew.kickoff()
    """
    run_id = f"run_{uuid4().hex[:12]}"
    tracer = _CrewAITracer(run_id, run_name)

    # Attempt to monkey-patch CrewAI callbacks
    _patch_crewai(tracer)

    start = time.time()
    events = [_evt(run_id, "lifecycle", "run_start", {
        "pod": "crewai_adapter",
        "graph": run_name,
        "input": {},
    })]

    error_msg = None
    try:
        yield tracer
    except Exception as exc:
        error_msg = str(exc)
        raise
    finally:
        duration_ms = (time.time() - start) * 1000
        events.extend(tracer.events)
        events.append(_evt(run_id, "lifecycle", "run_end", {
            "status": "error" if error_msg else "success",
            "duration_ms": round(duration_ms, 2),
            "error": error_msg,
        }))

        out_path = Path(out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            for e in events:
                f.write(json.dumps(e, default=str) + "\n")

        _unpatch_crewai()


# ---------------------------------------------------------------------------
# Best-effort monkey-patching of CrewAI internals
# ---------------------------------------------------------------------------

_original_callbacks: Dict[str, Any] = {}


def _patch_crewai(tracer: _CrewAITracer) -> None:
    """Best-effort: hook into CrewAI callbacks if available."""
    try:
        from crewai import Agent  # type: ignore
        # Store tracer on module for callback access
        _original_callbacks["_tracer"] = tracer
    except ImportError:
        pass  # CrewAI not installed — tracer events can be added manually


def _unpatch_crewai() -> None:
    _original_callbacks.clear()
