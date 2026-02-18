"""
HUAP LangChain / LangGraph Adapter — instrument LangChain runs as HUAP traces.

Usage:
    from hu_core.adapters.langchain import HuapCallbackHandler

    handler = HuapCallbackHandler(out="traces/langchain.jsonl", run_name="demo")
    chain.invoke({"input": "hello"}, config={"callbacks": [handler]})
    handler.flush()   # writes the trace

Requires: langchain-core (optional dependency)

If langchain-core is installed, HuapCallbackHandler inherits from
BaseCallbackHandler for full type-safety. Otherwise it stands alone
using duck-typed methods (LangChain checks method names, not base class).
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

# ---------------------------------------------------------------------------
# Conditional base class — inherit if langchain-core is available
# ---------------------------------------------------------------------------
_LCBase: type = object
try:
    from langchain_core.callbacks import BaseCallbackHandler as _LCBase  # type: ignore
except ImportError:
    pass


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


class HuapCallbackHandler(_LCBase):  # type: ignore[misc]
    """
    LangChain-compatible callback handler that emits HUAP trace events.

    Implements the full BaseCallbackHandler interface. Works with LangChain
    chains, chat models, tools, retrievers, and LangGraph agents.

    If langchain-core is installed, this class inherits from
    BaseCallbackHandler. Otherwise it uses duck-typed methods.
    """

    def __init__(
        self,
        out: str,
        run_name: str = "langchain_run",
    ):
        # BaseCallbackHandler.__init__ is safe to call even when _LCBase is object
        if _LCBase is not object:
            super().__init__()
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
        # Track active tool names so on_tool_end can reference them
        self._active_tools: Dict[str, str] = {}  # lc_run_id -> tool_name

    # ------------------------------------------------------------------
    # LLM callbacks
    # ------------------------------------------------------------------

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        model = _extract_model_name(serialized)
        self.events.append(_evt(self.run_id, "llm", "llm_request", {
            "provider": "langchain",
            "model": model,
            "messages": [{"role": "user", "content": p[:2000]} for p in prompts],
            "lc_run_id": str(run_id) if run_id else None,
        }))

    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[Any],
        *,
        run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        model = _extract_model_name(serialized)
        flat: List[Dict[str, str]] = []
        for msg_batch in messages:
            if isinstance(msg_batch, list):
                for m in msg_batch:
                    flat.append(_message_to_dict(m))
            else:
                flat.append(_message_to_dict(msg_batch))
        self.events.append(_evt(self.run_id, "llm", "llm_request", {
            "provider": "langchain",
            "model": model,
            "messages": flat,
            "lc_run_id": str(run_id) if run_id else None,
        }))

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        text = ""
        usage: Dict[str, int] = {}
        model = "unknown"

        if hasattr(response, "generations") and response.generations:
            gen = response.generations[0]
            if isinstance(gen, list) and gen:
                text = getattr(gen[0], "text", str(gen[0]))
                # Extract model from generation_info if available
                info = getattr(gen[0], "generation_info", {}) or {}
                model = info.get("model_name", model)
            elif hasattr(gen, "text"):
                text = gen.text

        if hasattr(response, "llm_output") and isinstance(response.llm_output, dict):
            usage = response.llm_output.get("token_usage", {})
            model = response.llm_output.get("model_name", model)

        self.events.append(_evt(self.run_id, "llm", "llm_response", {
            "provider": "langchain",
            "model": model,
            "text": str(text)[:5000],
            "usage": usage,
            "lc_run_id": str(run_id) if run_id else None,
        }))

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._error = str(error)
        self.events.append(_evt(self.run_id, "system", "error", {
            "error_type": type(error).__name__,
            "message": str(error)[:2000],
            "source": "llm",
            "lc_run_id": str(run_id) if run_id else None,
        }))

    # ------------------------------------------------------------------
    # Tool callbacks
    # ------------------------------------------------------------------

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        tool_name = serialized.get("name", "unknown_tool")
        if run_id:
            self._active_tools[str(run_id)] = tool_name
        self.events.append(_evt(self.run_id, "tool", "tool_call", {
            "tool": tool_name,
            "input": {"raw": input_str[:2000]},
            "lc_run_id": str(run_id) if run_id else None,
        }))

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        tool_name = self._active_tools.pop(str(run_id), "unknown") if run_id else "unknown"
        self.events.append(_evt(self.run_id, "tool", "tool_result", {
            "tool": tool_name,
            "result": {"raw": str(output)[:2000]},
            "status": "ok",
            "lc_run_id": str(run_id) if run_id else None,
        }))

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        tool_name = self._active_tools.pop(str(run_id), "unknown") if run_id else "unknown"
        self.events.append(_evt(self.run_id, "tool", "tool_result", {
            "tool": tool_name,
            "result": {"error": str(error)[:2000]},
            "status": "error",
            "lc_run_id": str(run_id) if run_id else None,
        }))

    # ------------------------------------------------------------------
    # Chain callbacks
    # ------------------------------------------------------------------

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        name = _extract_model_name(serialized)
        self.events.append(_evt(self.run_id, "node", "node_enter", {
            "node": name,
            "state_keys": list(inputs.keys()) if isinstance(inputs, dict) else [],
            "lc_run_id": str(run_id) if run_id else None,
        }))

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        output_keys = list(outputs.keys()) if isinstance(outputs, dict) else []
        self.events.append(_evt(self.run_id, "node", "node_exit", {
            "node": "chain",
            "output_keys": output_keys,
            "lc_run_id": str(run_id) if run_id else None,
        }))

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._error = str(error)
        self.events.append(_evt(self.run_id, "system", "error", {
            "error_type": type(error).__name__,
            "message": str(error)[:2000],
            "source": "chain",
            "lc_run_id": str(run_id) if run_id else None,
        }))

    # ------------------------------------------------------------------
    # Retriever callbacks
    # ------------------------------------------------------------------

    def on_retriever_start(
        self,
        serialized: Dict[str, Any],
        query: str,
        *,
        run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        name = serialized.get("name", "retriever")
        self.events.append(_evt(self.run_id, "tool", "tool_call", {
            "tool": f"retriever:{name}",
            "input": {"query": query[:2000]},
            "lc_run_id": str(run_id) if run_id else None,
        }))

    def on_retriever_end(
        self,
        documents: Any,
        *,
        run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        doc_count = len(documents) if isinstance(documents, list) else 0
        summaries = []
        if isinstance(documents, list):
            for doc in documents[:5]:
                content = getattr(doc, "page_content", str(doc))[:200]
                metadata = getattr(doc, "metadata", {})
                summaries.append({"content_preview": content, "metadata": metadata})
        self.events.append(_evt(self.run_id, "tool", "tool_result", {
            "tool": "retriever",
            "result": {"document_count": doc_count, "documents": summaries},
            "status": "ok",
            "lc_run_id": str(run_id) if run_id else None,
        }))

    def on_retriever_error(
        self,
        error: BaseException,
        *,
        run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self.events.append(_evt(self.run_id, "tool", "tool_result", {
            "tool": "retriever",
            "result": {"error": str(error)[:2000]},
            "status": "error",
            "lc_run_id": str(run_id) if run_id else None,
        }))

    # ------------------------------------------------------------------
    # Text callback (used by some LLM wrappers)
    # ------------------------------------------------------------------

    def on_text(self, text: str, **kwargs: Any) -> None:
        pass  # Intentionally ignored — content captured via on_llm_end

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_model_name(serialized: Dict[str, Any]) -> str:
    """Extract a human-readable name from LangChain's serialized dict."""
    if "name" in serialized and serialized["name"]:
        return str(serialized["name"])
    ids = serialized.get("id", [])
    if isinstance(ids, list) and ids:
        return str(ids[-1])
    return "unknown"


def _message_to_dict(m: Any) -> Dict[str, str]:
    """Convert a LangChain message object to a simple dict."""
    if hasattr(m, "content"):
        role = getattr(m, "type", None) or getattr(m, "role", "unknown")
        return {"role": str(role), "content": str(m.content)[:2000]}
    if isinstance(m, dict):
        return {"role": m.get("role", "unknown"), "content": str(m.get("content", ""))[:2000]}
    return {"role": "unknown", "content": str(m)[:2000]}
