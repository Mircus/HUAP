"""
HUAP Trace Service - Main interface for emitting trace events.

Provides a high-level API for tracing agent runs with automatic
span management and event emission.
"""
from __future__ import annotations

import os
import time
import logging
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Generator

from .models import (
    TraceEvent,
    EventKind,
    EventName,
    RunStartData,
    RunEndData,
    ErrorData,
    NodeEnterData,
    NodeExitData,
    ToolCallData,
    ToolResultData,
    LLMRequestData,
    LLMResponseData,
    PolicyCheckData,
    CostRecordData,
    QualityRecordData,
    hash_data,
    generate_run_id,
    generate_span_id,
)
from .writer import TraceWriter

logger = logging.getLogger(__name__)

# Maximum size for trace input data (64KB)
MAX_TRACE_INPUT_SIZE = 64 * 1024

# Sensitive keys to redact (case-insensitive)
SENSITIVE_KEYS = frozenset([
    "api_key", "apikey", "api-key",
    "token", "access_token", "refresh_token", "bearer",
    "secret", "client_secret",
    "password", "passwd", "pwd",
    "authorization", "auth",
    "cookie", "set-cookie", "session",
    "private_key", "privatekey",
    "credential", "credentials",
])


def sanitize_trace_input(input_data: Any, max_size: int = MAX_TRACE_INPUT_SIZE) -> Any:
    """
    Sanitize input data for safe storage in traces.

    - Redacts sensitive keys (api_key, password, token, etc.)
    - Converts non-JSON-serializable types to strings
    - Truncates data if it exceeds max_size

    Args:
        input_data: The input data to sanitize
        max_size: Maximum size in bytes for the serialized output

    Returns:
        Sanitized data safe for trace storage
    """
    import json

    def _sanitize_value(value: Any, key: str = "") -> Any:
        """Recursively sanitize a value."""
        # Check if key is sensitive
        if key and key.lower() in SENSITIVE_KEYS:
            return "[REDACTED]"

        if value is None:
            return None
        elif isinstance(value, (bool, int, float, str)):
            return value
        elif isinstance(value, dict):
            return {k: _sanitize_value(v, k) for k, v in value.items()}
        elif isinstance(value, (list, tuple)):
            return [_sanitize_value(item) for item in value]
        else:
            # Convert non-JSON types to string representation
            try:
                return str(value)
            except Exception:
                return f"<{type(value).__name__}>"

    # Sanitize the data
    sanitized = _sanitize_value(input_data)

    # Check size
    try:
        serialized = json.dumps(sanitized, default=str)
        if len(serialized) > max_size:
            # Truncate and add metadata
            preview = serialized[:1000] + "..." if len(serialized) > 1000 else serialized
            return {
                "_truncated": True,
                "_original_size": len(serialized),
                "_hash": hash_data(input_data) if input_data else None,
                "_preview": preview,
                "_keys": list(input_data.keys()) if isinstance(input_data, dict) else None,
            }
    except (TypeError, ValueError):
        # If serialization fails, return a safe placeholder
        return {
            "_error": "serialization_failed",
            "_type": type(input_data).__name__,
        }

    return sanitized


class TraceService:
    """
    Main trace service for emitting events during agent runs.

    Features:
    - Automatic run_id and span_id management
    - Span nesting with parent tracking
    - High-level methods for common event types
    - Integration hooks for GraphRunner, ToolRegistry, LLMClient
    """

    def __init__(
        self,
        output_dir: str = "traces",
        enabled: bool = True,
        pod: str = "hu-core",
        engine: str = "native_graph",
        redact_llm: Optional[bool] = None,
    ):
        """
        Initialize trace service.

        Args:
            output_dir: Directory for trace files
            enabled: Whether tracing is enabled
            pod: Default pod name
            engine: Default engine name
            redact_llm: Whether to redact LLM messages/responses (default: from env)
        """
        self.output_dir = Path(output_dir)
        self.enabled = enabled
        self.default_pod = pod
        self.default_engine = engine

        # LLM redaction (default from env var HUAP_TRACE_REDACT_LLM)
        if redact_llm is None:
            redact_llm = os.getenv("HUAP_TRACE_REDACT_LLM", "false").lower() in ("true", "1", "yes")
        self.redact_llm = redact_llm

        # Current run state
        self._run_id: Optional[str] = None
        self._writer: Optional[TraceWriter] = None
        self._span_stack: List[str] = []
        self._run_start_time: Optional[float] = None
        self._trace_path: Optional[Path] = None

        # Context
        self._user_id: Optional[str] = None
        self._session_id: Optional[str] = None

        # Ensure output directory exists
        if enabled:
            self.output_dir.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # RUN LIFECYCLE
    # =========================================================================

    def start_run(
        self,
        pod: Optional[str] = None,
        graph: Optional[str] = None,
        graph_path: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        trace_path: Optional[Path] = None,
    ) -> str:
        """
        Start a new trace run.

        Args:
            pod: Pod name (uses default if not specified)
            graph: Graph/workflow name
            input_data: Input data for the run
            config: Run configuration
            user_id: Optional user ID
            session_id: Optional session ID
            trace_path: Optional explicit path for trace file. If provided,
                        the trace will be written to exactly this path.
                        If None, auto-generates filename in output_dir.

        Returns:
            The run_id
        """
        self._run_id = generate_run_id()
        self._run_start_time = time.time()
        self._span_stack = []
        self._user_id = user_id
        self._session_id = session_id

        if self.enabled:
            # Determine trace file path
            if trace_path is not None:
                # Use exact path provided
                actual_path = Path(trace_path)
                actual_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                # Auto-generate filename
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                filename = f"{self._run_id}_{timestamp}.trace.jsonl"
                actual_path = self.output_dir / filename

            self._trace_path = actual_path
            self._writer = TraceWriter(str(actual_path))
            self._writer.open()

            # Emit run_start event
            input_keys = list(input_data.keys()) if input_data else []
            self._emit(
                kind=EventKind.SYSTEM,
                name=EventName.RUN_START,
                pod=pod or self.default_pod,
                data=RunStartData(
                    pod=pod or self.default_pod,
                    graph=graph,
                    graph_path=graph_path,
                    input=sanitize_trace_input(input_data) if input_data else {},
                    input_keys=input_keys,
                    input_hash=hash_data(input_data) if input_data else None,
                    config=config or {},
                ),
            )

            logger.info(f"Started trace run: {self._run_id}")

        return self._run_id

    def end_run(
        self,
        status: str = "success",
        output_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        End the current trace run.

        Args:
            status: Run status ("success", "error", "timeout")
            output_data: Output data from the run
            error: Error message if status is "error"
        """
        if not self._run_id:
            return

        duration_ms = (time.time() - self._run_start_time) * 1000 if self._run_start_time else 0

        if self.enabled and self._writer:
            output_keys = list(output_data.keys()) if output_data else []
            self._emit(
                kind=EventKind.SYSTEM,
                name=EventName.RUN_END,
                data=RunEndData(
                    status=status,
                    output_keys=output_keys,
                    output_hash=hash_data(output_data) if output_data else None,
                    duration_ms=duration_ms,
                    error=error,
                ),
            )

            self._writer.close()
            logger.info(f"Ended trace run: {self._run_id} ({status}, {duration_ms:.1f}ms)")

        self._run_id = None
        self._writer = None
        self._span_stack = []
        self._run_start_time = None
        self._trace_path = None

    @property
    def run_id(self) -> Optional[str]:
        """Current run ID."""
        return self._run_id

    @property
    def is_active(self) -> bool:
        """Whether a run is currently active."""
        return self._run_id is not None

    @property
    def trace_path(self) -> Optional[Path]:
        """Path to the current trace file."""
        return self._trace_path

    # =========================================================================
    # SPAN MANAGEMENT
    # =========================================================================

    def push_span(self, span_id: Optional[str] = None) -> str:
        """Push a new span onto the stack."""
        span_id = span_id or generate_span_id()
        self._span_stack.append(span_id)
        return span_id

    def pop_span(self) -> Optional[str]:
        """Pop the current span from the stack."""
        if self._span_stack:
            return self._span_stack.pop()
        return None

    @property
    def current_span_id(self) -> Optional[str]:
        """Current span ID."""
        return self._span_stack[-1] if self._span_stack else None

    @property
    def parent_span_id(self) -> Optional[str]:
        """Parent span ID."""
        return self._span_stack[-2] if len(self._span_stack) > 1 else None

    # =========================================================================
    # NODE EVENTS
    # =========================================================================

    def node_enter(
        self,
        node: str,
        state: Optional[Dict[str, Any]] = None,
        pod: Optional[str] = None,
    ) -> str:
        """
        Record node entry.

        Returns the span_id for this node.
        """
        span_id = self.push_span()

        if self.enabled:
            state_keys = list(state.keys()) if state else []
            self._emit(
                kind=EventKind.NODE,
                name=EventName.NODE_ENTER,
                pod=pod,
                span_id=span_id,
                data=NodeEnterData(
                    node=node,
                    state_keys=state_keys,
                    state_hash=hash_data(state) if state else None,
                ),
            )

        return span_id

    def node_exit(
        self,
        node: str,
        output: Optional[Dict[str, Any]] = None,
        duration_ms: float = 0,
        pod: Optional[str] = None,
    ) -> None:
        """Record node exit."""
        span_id = self.pop_span()

        if self.enabled:
            self._emit(
                kind=EventKind.NODE,
                name=EventName.NODE_EXIT,
                pod=pod,
                span_id=span_id,
                data=NodeExitData(
                    node=node,
                    output=output or {},
                    output_hash=hash_data(output) if output else None,
                    duration_ms=duration_ms,
                ),
            )

    @contextmanager
    def trace_node(
        self,
        node: str,
        state: Optional[Dict[str, Any]] = None,
        pod: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """Context manager for tracing a node."""
        start = time.time()
        span_id = self.node_enter(node, state, pod)
        output = {}
        try:
            yield span_id
        finally:
            duration_ms = (time.time() - start) * 1000
            self.node_exit(node, output, duration_ms, pod)

    # =========================================================================
    # TOOL EVENTS
    # =========================================================================

    def tool_call(
        self,
        tool: str,
        input_data: Optional[Dict[str, Any]] = None,
        permissions: Optional[Dict[str, Any]] = None,
        pod: Optional[str] = None,
    ) -> str:
        """
        Record tool call.

        Returns the span_id for this tool call.
        """
        span_id = self.push_span()

        if self.enabled:
            self._emit(
                kind=EventKind.TOOL,
                name=EventName.TOOL_CALL,
                pod=pod,
                span_id=span_id,
                data=ToolCallData(
                    tool=tool,
                    input=input_data or {},
                    input_hash=hash_data(input_data) if input_data else None,
                    permissions=permissions or {},
                ),
            )

        return span_id

    def tool_result(
        self,
        tool: str,
        result: Optional[Dict[str, Any]] = None,
        duration_ms: float = 0,
        status: str = "ok",
        error: Optional[str] = None,
        pod: Optional[str] = None,
    ) -> None:
        """Record tool result."""
        span_id = self.pop_span()

        if self.enabled:
            self._emit(
                kind=EventKind.TOOL,
                name=EventName.TOOL_RESULT,
                pod=pod,
                span_id=span_id,
                data=ToolResultData(
                    tool=tool,
                    result=result or {},
                    result_hash=hash_data(result) if result else None,
                    duration_ms=duration_ms,
                    status=status,
                    error=error,
                ),
            )

    @contextmanager
    def trace_tool(
        self,
        tool: str,
        input_data: Optional[Dict[str, Any]] = None,
        pod: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """Context manager for tracing a tool call."""
        start = time.time()
        span_id = self.tool_call(tool, input_data, pod=pod)
        result = {"status": "ok"}
        try:
            yield span_id
            self.tool_result(tool, result, (time.time() - start) * 1000, "ok", pod=pod)
        except Exception as e:
            self.tool_result(tool, {}, (time.time() - start) * 1000, "error", str(e), pod=pod)
            raise

    # =========================================================================
    # LLM EVENTS
    # =========================================================================

    def _redact_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Redact message content, keeping structure and hashes."""
        redacted = []
        for msg in messages:
            redacted_msg = {"role": msg.get("role", "unknown")}
            content = msg.get("content", "")
            # Keep hash for matching, redact actual content
            redacted_msg["content"] = "[REDACTED]"
            redacted_msg["_content_hash"] = hash_data(content)
            redacted_msg["_content_len"] = len(content)
            redacted.append(redacted_msg)
        return redacted

    def _redact_text(self, text: str) -> Dict[str, Any]:
        """Redact response text, keeping hash and length."""
        return {
            "text": "[REDACTED]",
            "_text_hash": hash_data(text),
            "_text_len": len(text),
        }

    def llm_request(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 800,
        provider: str = "openai",
        pod: Optional[str] = None,
    ) -> str:
        """
        Record LLM request.

        Returns the span_id for this LLM call.
        """
        span_id = self.push_span()

        if self.enabled:
            # Redact messages if enabled
            stored_messages = self._redact_messages(messages) if self.redact_llm else messages

            self._emit(
                kind=EventKind.LLM,
                name=EventName.LLM_REQUEST,
                pod=pod,
                span_id=span_id,
                data=LLMRequestData(
                    provider=provider,
                    model=model,
                    messages=stored_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ),
            )

        return span_id

    def llm_response(
        self,
        model: str,
        text: str,
        usage: Dict[str, int],
        duration_ms: float,
        provider: str = "openai",
        pod: Optional[str] = None,
    ) -> None:
        """Record LLM response."""
        span_id = self.pop_span()

        if self.enabled:
            # Redact text if enabled
            if self.redact_llm:
                redacted = self._redact_text(text)
                stored_text = redacted["text"]
                # Store redaction metadata in a way that works with LLMResponseData
                # We'll include the hash in the response for verification
            else:
                stored_text = text

            self._emit(
                kind=EventKind.LLM,
                name=EventName.LLM_RESPONSE,
                pod=pod,
                span_id=span_id,
                data=LLMResponseData(
                    provider=provider,
                    model=model,
                    text=stored_text,
                    usage=usage,
                    duration_ms=duration_ms,
                ),
            )

            # Also emit cost record
            self._emit_cost_record(usage, duration_ms, model, pod)

    def _emit_cost_record(
        self,
        usage: Dict[str, int],
        latency_ms: float,
        model: Optional[str] = None,
        pod: Optional[str] = None,
    ) -> None:
        """Emit a cost record event."""
        # Estimate cost (simplified pricing)
        tokens = usage.get("total_tokens", 0)
        # Rough estimate: $0.002 per 1K tokens for gpt-4o-mini
        usd_est = tokens * 0.000002

        self._emit(
            kind=EventKind.COST,
            name=EventName.COST_RECORD,
            pod=pod,
            data=CostRecordData(
                tokens=tokens,
                usd_est=usd_est,
                latency_ms=latency_ms,
                model=model,
            ),
        )

    # =========================================================================
    # POLICY EVENTS
    # =========================================================================

    def policy_check(
        self,
        policy: str,
        decision: str,
        reason: Optional[str] = None,
        rule_id: Optional[str] = None,
        inputs: Optional[Dict[str, Any]] = None,
        pod: Optional[str] = None,
    ) -> None:
        """Record a policy check."""
        if self.enabled:
            self._emit(
                kind=EventKind.POLICY,
                name=EventName.POLICY_CHECK,
                pod=pod,
                data=PolicyCheckData(
                    policy=policy,
                    decision=decision,
                    reason=reason,
                    rule_id=rule_id,
                    inputs=inputs or {},
                ),
            )

    # =========================================================================
    # ERROR EVENTS
    # =========================================================================

    def error(
        self,
        error_type: str,
        message: str,
        traceback: Optional[str] = None,
        node: Optional[str] = None,
        tool: Optional[str] = None,
        pod: Optional[str] = None,
    ) -> None:
        """Record an error."""
        if self.enabled:
            self._emit(
                kind=EventKind.SYSTEM,
                name=EventName.ERROR,
                pod=pod,
                data=ErrorData(
                    error_type=error_type,
                    message=message,
                    traceback=traceback,
                    node=node,
                    tool=tool,
                ),
            )

    # =========================================================================
    # QUALITY EVENTS
    # =========================================================================

    def quality_record(
        self,
        metric: str,
        value: float,
        details: Optional[Dict[str, Any]] = None,
        pod: Optional[str] = None,
    ) -> None:
        """Record a quality metric."""
        if self.enabled:
            self._emit(
                kind=EventKind.QUALITY,
                name=EventName.QUALITY_RECORD,
                pod=pod,
                data=QualityRecordData(
                    metric=metric,
                    value=value,
                    details=details or {},
                ),
            )

    # =========================================================================
    # INTERNAL
    # =========================================================================

    def _emit(
        self,
        kind: EventKind,
        name: EventName,
        data: Any,
        pod: Optional[str] = None,
        span_id: Optional[str] = None,
    ) -> None:
        """Emit a trace event."""
        if not self.enabled or not self._writer or not self._run_id:
            return

        event = TraceEvent(
            run_id=self._run_id,
            span_id=span_id or self.current_span_id or generate_span_id(),
            parent_span_id=self.parent_span_id,
            kind=kind,
            name=name,
            pod=pod or self.default_pod,
            engine=self.default_engine,
            user_id=self._user_id,
            session_id=self._session_id,
            data=data,
        )

        self._writer.write(event)


# =============================================================================
# CONTEXT-AWARE SERVICE ACCESS
# =============================================================================

from contextvars import ContextVar  # noqa: E402

# Context-local tracer (for concurrent run isolation)
_context_tracer: ContextVar[Optional[TraceService]] = ContextVar(
    "trace_service", default=None
)

# Global tracer singleton (fallback when no context set)
_trace_service: Optional[TraceService] = None


def get_trace_service() -> TraceService:
    """
    Get the trace service for the current context.

    Resolution order:
    1. Context-local tracer (if set via set_context_tracer)
    2. Global singleton (fallback)

    This enables concurrent runs to use isolated tracers without
    cross-contamination.
    """
    # Check context-local first
    ctx_tracer = _context_tracer.get()
    if ctx_tracer is not None:
        return ctx_tracer

    # Fall back to global singleton
    global _trace_service
    if _trace_service is None:
        enabled = os.getenv("HUAP_TRACE_ENABLED", "true").lower() in ("true", "1", "yes")
        output_dir = os.getenv("HUAP_TRACE_DIR", "traces")
        _trace_service = TraceService(output_dir=output_dir, enabled=enabled)
    return _trace_service


def set_context_tracer(tracer: Optional[TraceService]) -> None:
    """
    Set the trace service for the current async context.

    Use this to isolate concurrent runs:
        tracer = TraceService(...)
        set_context_tracer(tracer)
        try:
            await run_workflow(...)
        finally:
            set_context_tracer(None)
    """
    _context_tracer.set(tracer)


def configure_trace_service(
    output_dir: str = "traces",
    enabled: bool = True,
    pod: str = "hu-core",
    engine: str = "native_graph",
) -> TraceService:
    """Configure and return the global trace service."""
    global _trace_service
    _trace_service = TraceService(
        output_dir=output_dir,
        enabled=enabled,
        pod=pod,
        engine=engine,
    )
    return _trace_service


def reset_trace_service() -> None:
    """Reset the trace service singleton (for testing)."""
    global _trace_service
    _trace_service = None
    _context_tracer.set(None)
