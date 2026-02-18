"""
HUAP LangChain / LangGraph Adapter — instrument LangChain runs as HUAP traces.

Usage:
    from hu_core.adapters.langchain import HuapCallbackHandler

    handler = HuapCallbackHandler(out="traces/langchain.jsonl", run_name="demo")
    chain.invoke({"input": "hello"}, config={"callbacks": [handler]})
    handler.flush()   # writes the trace

Requires: langchain-core (optional dependency)
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union
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
        "pod": "langchain_adapter",
        "engine": "langchain",
        "data": data,
    }


class HuapCallbackHandler:
    """
    LangChain-compatible callback handler that emits HUAP trace events.

    Implements the minimal callback interface so it works with both
    LangChain and LangGraph without requiring langchain-core at import time.
    """

    def __init__(
        self,
        out: str,
        run_name: str = "langchain_run",
    ):
        self.out = out
        self.run_name = run_name
        self.run_id = f"run_{uuid4().hex[:12]}"
        self._start = time.time()
        self.events: List[Dict[str, Any]] = [
            _evt(self.run_id, "lifecycle", "run_start", {
                "pod": "langchain_adapter",
                "graph": run_name,
                "input": {},
            })
        ]
        self._error: Optional[str] = None

    # ------------------------------------------------------------------
    # LLM callbacks
    # ------------------------------------------------------------------

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any,
    ) -> None:
        model = serialized.get("name", serialized.get("id", ["unknown"])[-1] if isinstance(serialized.get("id"), list) else "unknown")
        self.events.append(_evt(self.run_id, "llm", "llm_request", {
            "provider": "langchain",
            "model": str(model),
            "messages": [{"role": "user", "content": p[:2000]} for p in prompts],
        }))

    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[Any],
        **kwargs: Any,
    ) -> None:
        model = serialized.get("name", "unknown")
        flat: List[Dict[str, str]] = []
        for msg_batch in messages:
            if isinstance(msg_batch, list):
                for m in msg_batch:
                    if hasattr(m, "content"):
                        flat.append({"role": getattr(m, "type", "user"), "content": str(m.content)[:2000]})
            elif hasattr(msg_batch, "content"):
                flat.append({"role": getattr(msg_batch, "type", "user"), "content": str(msg_batch.content)[:2000]})
        self.events.append(_evt(self.run_id, "llm", "llm_request", {
            "provider": "langchain",
            "model": str(model),
            "messages": flat,
        }))

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        text = ""
        usage: Dict[str, int] = {}
        if hasattr(response, "generations") and response.generations:
            gen = response.generations[0]
            if isinstance(gen, list) and gen:
                text = gen[0].text if hasattr(gen[0], "text") else str(gen[0])
            elif hasattr(gen, "text"):
                text = gen.text
        if hasattr(response, "llm_output") and isinstance(response.llm_output, dict):
            usage = response.llm_output.get("token_usage", {})
        self.events.append(_evt(self.run_id, "llm", "llm_response", {
            "provider": "langchain",
            "model": "unknown",
            "text": str(text)[:5000],
            "usage": usage,
            "duration_ms": 0,
        }))

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        self._error = str(error)
        self.events.append(_evt(self.run_id, "system", "error", {
            "error_type": type(error).__name__,
            "message": str(error)[:2000],
        }))

    # ------------------------------------------------------------------
    # Tool callbacks
    # ------------------------------------------------------------------

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        tool_name = serialized.get("name", "unknown_tool")
        self.events.append(_evt(self.run_id, "tool", "tool_call", {
            "tool": tool_name,
            "input": {"raw": input_str[:2000]},
        }))

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        self.events.append(_evt(self.run_id, "tool", "tool_result", {
            "tool": "unknown",
            "result": {"raw": str(output)[:2000]},
            "duration_ms": 0,
            "status": "ok",
        }))

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        self.events.append(_evt(self.run_id, "tool", "tool_result", {
            "tool": "unknown",
            "result": {"error": str(error)[:2000]},
            "duration_ms": 0,
            "status": "error",
            "error": str(error)[:2000],
        }))

    # ------------------------------------------------------------------
    # Chain callbacks
    # ------------------------------------------------------------------

    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any) -> None:
        name = serialized.get("name", serialized.get("id", ["chain"])[-1] if isinstance(serialized.get("id"), list) else "chain")
        self.events.append(_evt(self.run_id, "node", "node_enter", {
            "node": str(name),
            "state_keys": list(inputs.keys()) if isinstance(inputs, dict) else [],
        }))

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        self.events.append(_evt(self.run_id, "node", "node_exit", {
            "node": "chain",
            "output": {},
            "duration_ms": 0,
        }))

    def on_chain_error(self, error: BaseException, **kwargs: Any) -> None:
        self._error = str(error)

    # ------------------------------------------------------------------
    # Flush
    # ------------------------------------------------------------------

    def flush(self) -> str:
        """Write all collected events to the output file and return the path."""
        duration_ms = (time.time() - self._start) * 1000
        self.events.append(_evt(self.run_id, "lifecycle", "run_end", {
            "status": "error" if self._error else "success",
            "duration_ms": round(duration_ms, 2),
            "error": self._error,
        }))

        out_path = Path(self.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            for e in self.events:
                f.write(json.dumps(e, default=str) + "\n")
        return str(out_path)
