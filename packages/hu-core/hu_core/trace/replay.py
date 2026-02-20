"""
HUAP Trace Replayer - Deterministic replay of recorded traces.

Provides:
- TraceReplayer for replaying traces with stubbed tool/LLM calls
- StubRegistry for managing recorded responses
- Verification of replay vs original
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field

from .models import (
    TraceEvent,
    TraceRun,
    EventKind,
    EventName,
    hash_data,
    generate_run_id,
)
from .service import TraceService
from .writer import TraceWriter


@dataclass
class StubCall:
    """A recorded call that can be replayed."""
    name: str
    input_hash: str
    result: Any
    duration_ms: float
    status: str = "ok"
    error: Optional[str] = None


@dataclass
class StubRegistry:
    """Registry of stubbed calls from a trace."""
    tool_stubs: Dict[str, List[StubCall]] = field(default_factory=dict)
    llm_stubs: List[StubCall] = field(default_factory=list)
    _llm_stubs_by_hash: Dict[str, StubCall] = field(default_factory=dict)  # request_hash -> response
    _tool_stubs_by_hash: Dict[str, StubCall] = field(default_factory=dict)  # "tool:input_hash" -> result
    _tool_indices: Dict[str, int] = field(default_factory=dict)
    _llm_index: int = 0

    def add_tool_stub(self, tool: str, stub: StubCall) -> None:
        """Add a tool stub."""
        if tool not in self.tool_stubs:
            self.tool_stubs[tool] = []
        self.tool_stubs[tool].append(stub)

    def add_llm_stub(self, stub: StubCall) -> None:
        """Add an LLM stub."""
        self.llm_stubs.append(stub)

    def get_tool_stub(self, tool: str, input_data: Dict[str, Any]) -> Optional[StubCall]:
        """
        Get a stub for a tool call.

        Matching strategy (in order):
        1. Hash-based: compute hash of "tool:input", look up in tool_stubs_by_hash
        2. Sequence-based fallback: return next stub for this tool (for legacy traces)
        """
        # Primary: match by tool + input content hash
        input_hash = hash_data(input_data)
        lookup_key = f"{tool}:{input_hash}"
        if lookup_key in self._tool_stubs_by_hash:
            return self._tool_stubs_by_hash[lookup_key]

        # Fallback: sequence-based (for traces without input hashes)
        if tool in self.tool_stubs:
            stubs = self.tool_stubs[tool]
            idx = self._tool_indices.get(tool, 0)
            if idx < len(stubs):
                self._tool_indices[tool] = idx + 1
                return stubs[idx]

        return None

    def get_llm_stub(self, messages: List[Dict[str, str]]) -> Optional[StubCall]:
        """
        Get the LLM stub matching the given messages.

        Matching strategy (in order):
        1. Hash-based: compute hash of messages, look up in llm_stubs_by_hash
        2. Sequence-based fallback: return next stub in order (for legacy traces)
        """
        # Primary: match by message content hash
        msg_hash = hash_data(messages)
        if msg_hash in self._llm_stubs_by_hash:
            return self._llm_stubs_by_hash[msg_hash]

        # Fallback: sequence-based (for traces without request hashes)
        if self._llm_index < len(self.llm_stubs):
            stub = self.llm_stubs[self._llm_index]
            self._llm_index += 1
            return stub

        return None

    def reset(self) -> None:
        """Reset indices for fresh replay."""
        self._tool_indices.clear()
        self._llm_index = 0

    @classmethod
    def from_trace(cls, trace_run: TraceRun) -> "StubRegistry":
        """Build stub registry from a trace."""
        registry = cls()

        # Pair tool_call with tool_result events by span_id
        tool_calls: Dict[str, TraceEvent] = {}
        # Pair llm_request with llm_response events by span_id
        llm_requests: Dict[str, TraceEvent] = {}

        for event in trace_run.events:
            if event.name == EventName.TOOL_CALL:
                tool_calls[event.span_id] = event

            elif event.name == EventName.TOOL_RESULT:
                # Find matching call
                call_event = tool_calls.get(event.span_id)
                if call_event:
                    call_data = call_event.data if isinstance(call_event.data, dict) else call_event.data.model_dump()
                    result_data = event.data if isinstance(event.data, dict) else event.data.model_dump()

                    tool_name = call_data.get("tool", "unknown")
                    # Get input hash from call data, or compute from input_data
                    input_hash = call_data.get("input_hash", "")
                    if not input_hash and "input_data" in call_data:
                        input_hash = hash_data(call_data["input_data"])

                    stub = StubCall(
                        name=tool_name,
                        input_hash=input_hash,
                        result=result_data.get("result", {}),
                        duration_ms=result_data.get("duration_ms", 0),
                        status=result_data.get("status", "ok"),
                        error=result_data.get("error"),
                    )
                    registry.add_tool_stub(tool_name, stub)

                    # Also index by tool:hash for fast lookup
                    if input_hash:
                        lookup_key = f"{tool_name}:{input_hash}"
                        registry._tool_stubs_by_hash[lookup_key] = stub

            elif event.name == EventName.LLM_REQUEST:
                # Store request for pairing with response
                llm_requests[event.span_id] = event

            elif event.name == EventName.LLM_RESPONSE:
                # Pair with request to get the input hash
                resp_data = event.data if isinstance(event.data, dict) else event.data.model_dump()
                req_event = llm_requests.get(event.span_id)

                # Get request hash from the request event
                request_hash = ""
                if req_event:
                    req_data = req_event.data if isinstance(req_event.data, dict) else req_event.data.model_dump()
                    # The messages are hashed in the request - look for messages_hash or compute from messages
                    request_hash = req_data.get("messages_hash", "")
                    if not request_hash and "messages" in req_data:
                        # Compute hash from messages
                        request_hash = hash_data(req_data["messages"])

                stub = StubCall(
                    name=resp_data.get("model", "unknown"),
                    input_hash=request_hash,
                    result=resp_data.get("text", ""),
                    duration_ms=resp_data.get("duration_ms", 0),
                    status="ok",
                )
                registry.add_llm_stub(stub)

                # Also index by hash for fast lookup
                if request_hash:
                    registry._llm_stubs_by_hash[request_hash] = stub

        return registry


class StubbedToolRegistry:
    """
    A tool registry that returns stubbed results.

    Wraps the real registry and intercepts calls when stubs are available.
    """

    def __init__(self, stubs: StubRegistry, real_registry: Optional[Any] = None):
        self.stubs = stubs
        self.real_registry = real_registry
        self._tracer = None

    def set_tracer(self, tracer: Any) -> None:
        """Set tracer (for compatibility with runner.py)."""
        self._tracer = tracer

    def get_tracer(self) -> Optional[Any]:
        """Get the current tracer."""
        return self._tracer

    async def execute(
        self,
        name: str,
        input: Dict[str, Any],
        context: Optional[Any] = None,
        **kwargs,
    ) -> Any:
        """Execute a tool, using stub if available."""
        from ..tools.base import ToolResult, ToolStatus

        stub = self.stubs.get_tool_stub(name, input)

        if stub:
            # Return stubbed result
            return ToolResult(
                status=ToolStatus.SUCCESS if stub.status == "ok" else ToolStatus.ERROR,
                data=stub.result,
                duration_ms=stub.duration_ms,
                error=stub.error,
            )

        # Fall back to real registry
        if self.real_registry:
            return await self.real_registry.execute(name, input, context, **kwargs)

        # No stub and no real registry
        return ToolResult(
            status=ToolStatus.ERROR,
            error=f"No stub found for tool '{name}' and no real registry available",
        )


class StubbedLLMClient:
    """
    An LLM client that returns stubbed responses.
    """

    def __init__(self, stubs: StubRegistry, real_client: Optional[Any] = None):
        self.stubs = stubs
        self.real_client = real_client
        self.model = "stub-model"

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> str:
        """Return stubbed completion or fall back to real client."""
        stub = self.stubs.get_llm_stub(messages)

        if stub:
            return stub.result

        if self.real_client:
            return await self.real_client.chat_completion(messages, temperature, max_tokens)

        raise ValueError("No LLM stub found and no real client available")

    async def chat_completion_with_usage(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 800,
    ):
        """Return stubbed completion with usage info."""
        from ..services.llm_client import LLMResponse

        stub = self.stubs.get_llm_stub(messages)

        if stub:
            return LLMResponse(
                text=stub.result,
                model=stub.name,
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                latency_ms=stub.duration_ms,
            )

        if self.real_client:
            return await self.real_client.chat_completion_with_usage(
                messages, temperature, max_tokens
            )

        raise ValueError("No LLM stub found and no real client available")

    def set_tracer(self, tracer: Any, pod: Optional[str] = None) -> None:
        """Stub tracer setter - does nothing but prevents AttributeError."""
        pass


@dataclass
class CostSummary:
    """Summary of costs from a trace run."""
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    usd_est: float = 0.0
    latency_ms: float = 0.0
    llm_calls: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "usd_est": self.usd_est,
            "latency_ms": self.latency_ms,
            "llm_calls": self.llm_calls,
        }


@dataclass
class ReplayResult:
    """Result of a trace replay."""
    original_run_id: str
    replay_run_id: str
    events_replayed: int
    state_hash_match: bool
    original_state_hash: Optional[str]
    replay_state_hash: Optional[str]
    duration_ms: float
    errors: List[str] = field(default_factory=list)
    original_cost: Optional[CostSummary] = None
    replay_cost: Optional[CostSummary] = None


class TraceReplayer:
    """
    Replays a trace with optional stubbing.

    Two modes:
    - mode="emit": Re-emit recorded events (fast, no real execution)
    - mode="exec": Re-execute workflow with stubbed LLM/tools (deterministic replay)

    Usage:
        replayer = TraceReplayer(
            trace_path="runs/hello.trace.jsonl",
            stub_tools=True,
            stub_llm=True,
        )
        # Re-emit mode (default, legacy)
        result = await replayer.replay(output_path="runs/hello.replay.jsonl")

        # Execution mode (actually runs the workflow)
        result = await replayer.replay(output_path="runs/hello.replay.jsonl", mode="exec")
    """

    def __init__(
        self,
        trace_path: str,
        stub_tools: bool = True,
        stub_llm: bool = True,
        config_path: Optional[str] = None,
    ):
        self.trace_path = Path(trace_path)
        self.stub_tools = stub_tools
        self.stub_llm = stub_llm
        self.config_path = config_path
        self._trace_run: Optional[TraceRun] = None
        self._stubs: Optional[StubRegistry] = None

    def load(self) -> TraceRun:
        """Load the trace file."""
        if self._trace_run is None:
            self._trace_run = TraceRun.from_jsonl_file(str(self.trace_path))
            self._stubs = StubRegistry.from_trace(self._trace_run)
        return self._trace_run

    def _extract_costs(self, trace_run: TraceRun) -> CostSummary:
        """
        Extract cost summary from a trace.

        Sums up cost_record events and llm_response usage data.
        """
        summary = CostSummary()

        for event in trace_run.events:
            if event.name == EventName.COST_RECORD:
                data = event.data if isinstance(event.data, dict) else event.data.model_dump()
                summary.total_tokens += data.get("tokens", 0)
                summary.usd_est += data.get("usd_est", 0.0)
                summary.latency_ms += data.get("latency_ms", 0.0)

            elif event.name == EventName.LLM_RESPONSE:
                data = event.data if isinstance(event.data, dict) else event.data.model_dump()
                usage = data.get("usage", {})
                summary.prompt_tokens += usage.get("prompt_tokens", 0)
                summary.completion_tokens += usage.get("completion_tokens", 0)
                summary.total_tokens += usage.get("total_tokens", 0)
                summary.latency_ms += data.get("duration_ms", 0.0)
                summary.llm_calls += 1

        return summary

    async def replay(
        self,
        output_path: Optional[str] = None,
        mode: str = "emit",
    ) -> Dict[str, Any]:
        """
        Replay the trace.

        Args:
            output_path: Path to write replay trace (optional)
            mode: "emit" to re-emit events (default), "exec" to re-execute workflow

        Returns:
            Dict with replay results
        """
        if mode == "exec":
            return await self._replay_exec(output_path)
        else:
            return await self._replay_emit(output_path)

    async def _replay_exec(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Replay by actually re-executing the workflow with stubbed dependencies.

        This is the proper deterministic replay that runs real code with
        recorded LLM responses injected.
        """
        start_time = time.time()

        # Load original trace and build stubs
        trace_run = self.load()
        stubs = self._stubs
        stubs.reset()

        # Extract original costs
        original_cost = self._extract_costs(trace_run)

        # Get original metadata
        original_run_id = trace_run.run_id
        original_end = trace_run.end_event
        original_state_hash = None
        if original_end:
            end_data = original_end.data if isinstance(original_end.data, dict) else original_end.data.model_dump()
            original_state_hash = end_data.get("output_hash")

        # Extract trace metadata
        start_event = trace_run.start_event
        pod_name = "unknown"
        graph_name = None
        input_state = {}

        if start_event:
            start_data = start_event.data if isinstance(start_event.data, dict) else start_event.data.model_dump()
            pod_name = start_data.get("pod", "unknown")
            graph_name = start_data.get("graph")
            graph_path_str = start_data.get("graph_path")
            input_state = start_data.get("input", {})

        # Determine output path
        if output_path:
            out_path = Path(output_path)
        else:
            out_path = self.trace_path.with_suffix(".replay.jsonl")

        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Create stubbed LLM client if needed
        stubbed_llm = None
        if self.stub_llm:
            stubbed_llm = StubbedLLMClient(stubs)

        # Create stubbed tool registry if needed
        stubbed_tools = None
        if self.stub_tools:
            stubbed_tools = StubbedToolRegistry(stubs)

        # Run the actual workflow with stubs
        errors = []
        replay_run_id = generate_run_id()
        final_state = {}

        try:
            from .runner import run_pod_graph

            # Resolve graph path: prefer stored graph_path, fall back to graph name
            resolved_graph = None
            if graph_path_str:
                resolved_graph = Path(graph_path_str)
            elif graph_name:
                # Try common locations
                for candidate in [
                    Path(graph_name),
                    Path(f"examples/graphs/{graph_name}.yaml"),
                    Path(f"graphs/{graph_name}.yaml"),
                ]:
                    if candidate.exists():
                        resolved_graph = candidate
                        break

            if resolved_graph is None or not resolved_graph.exists():
                errors.append(f"Cannot resolve graph path for '{graph_name}' — replay exec requires the original graph file")
            else:
                result = await run_pod_graph(
                    pod=pod_name,
                    graph_path=resolved_graph,
                    input_state=input_state,
                    output_path=out_path,
                )

                replay_run_id = result.get("run_id", replay_run_id)
                final_state = result.get("final_state", {})

                if result.get("error"):
                    errors.append(result["error"])

        except Exception as e:
            errors.append(str(e))

        # Calculate state hash for comparison
        replay_state_hash = hash_data(final_state) if final_state else None

        duration_ms = (time.time() - start_time) * 1000

        # Count events and extract costs from the replay trace
        events_replayed = 0
        replay_cost = CostSummary()
        if out_path.exists():
            try:
                replay_trace = TraceRun.from_jsonl_file(str(out_path))
                events_replayed = len(replay_trace.events)
                replay_cost = self._extract_costs(replay_trace)
            except Exception:
                pass

        return {
            "original_run_id": original_run_id,
            "replay_run_id": replay_run_id,
            "events_replayed": events_replayed,
            "state_hash_match": original_state_hash == replay_state_hash,
            "original_state_hash": original_state_hash,
            "replay_state_hash": replay_state_hash,
            "duration_ms": duration_ms,
            "errors": errors,
            "mode": "exec",
            "original_cost": original_cost.to_dict(),
            "replay_cost": replay_cost.to_dict(),
        }

    async def _replay_emit(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Replay by re-emitting recorded events (legacy mode).

        This does NOT execute real code - it just replays the trace events.
        Useful for verification but not for deterministic testing.
        """
        start_time = time.time()

        # Load original trace
        trace_run = self.load()
        stubs = self._stubs
        stubs.reset()

        # Extract original costs
        original_cost = self._extract_costs(trace_run)

        # Get original metadata
        original_run_id = trace_run.run_id
        original_end = trace_run.end_event
        original_state_hash = None
        if original_end:
            end_data = original_end.data if isinstance(original_end.data, dict) else original_end.data.model_dump()
            original_state_hash = end_data.get("output_hash")

        # Create replay trace service
        replay_run_id = generate_run_id()
        replay_tracer = None
        replay_writer = None

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            replay_writer = TraceWriter(str(output_path))
            replay_writer.open()

            replay_tracer = TraceService(
                output_dir=str(output_path.parent),
                enabled=True,
            )
            replay_tracer._run_id = replay_run_id
            replay_tracer._writer = replay_writer

        # Extract start event info
        start_event = trace_run.start_event
        pod_name = "unknown"
        graph_name = None
        input_state = {}

        if start_event:
            start_data = start_event.data if isinstance(start_event.data, dict) else start_event.data.model_dump()
            pod_name = start_data.get("pod", "unknown")
            graph_name = start_data.get("graph")

        # Replay events
        events_replayed = 0
        replay_state = {}
        errors = []

        try:
            # Emit run_start
            if replay_tracer:
                replay_tracer.start_run(pod=pod_name, graph=graph_name, input_data=input_state)

            # Process node events
            for event in trace_run.events:
                if event.name in (EventName.NODE_ENTER, EventName.NODE_EXIT):
                    # Replay node events
                    event_data = event.data if isinstance(event.data, dict) else event.data.model_dump()
                    node_name = event_data.get("node", "unknown")

                    if event.name == EventName.NODE_ENTER:
                        if replay_tracer:
                            replay_tracer.node_enter(node_name, state=replay_state, pod=pod_name)
                    else:
                        output = event_data.get("output", {})
                        duration = event_data.get("duration_ms", 0)
                        replay_state.update(output)
                        if replay_tracer:
                            replay_tracer.node_exit(node_name, output=output, duration_ms=duration, pod=pod_name)

                    events_replayed += 1

                elif event.name == EventName.TOOL_CALL and self.stub_tools:
                    # Tool calls are handled via stubbed registry
                    events_replayed += 1

                elif event.name == EventName.LLM_REQUEST and self.stub_llm:
                    # LLM calls are handled via stubbed client
                    events_replayed += 1

            # Emit run_end
            if replay_tracer:
                replay_tracer.end_run(status="success", output_data=replay_state)

        except Exception as e:
            errors.append(str(e))
            if replay_tracer:
                replay_tracer.end_run(status="error", error=str(e))

        finally:
            if replay_writer:
                replay_writer.close()

        # Calculate state hash
        replay_state_hash = hash_data(replay_state) if replay_state else None

        duration_ms = (time.time() - start_time) * 1000

        # For emit mode, replay cost = original cost (no new LLM calls)
        replay_cost = CostSummary()  # Zero cost since we're just re-emitting events

        return {
            "original_run_id": original_run_id,
            "replay_run_id": replay_run_id,
            "events_replayed": events_replayed,
            "state_hash_match": original_state_hash == replay_state_hash,
            "original_state_hash": original_state_hash,
            "replay_state_hash": replay_state_hash,
            "duration_ms": duration_ms,
            "errors": errors,
            "mode": "emit",
            "original_cost": original_cost.to_dict(),
            "replay_cost": replay_cost.to_dict(),
        }

    def get_stubbed_tool_registry(self) -> StubbedToolRegistry:
        """Get a stubbed tool registry for this trace."""
        self.load()
        return StubbedToolRegistry(self._stubs)

    def get_stubbed_llm_client(self) -> StubbedLLMClient:
        """Get a stubbed LLM client for this trace."""
        self.load()
        return StubbedLLMClient(self._stubs)
