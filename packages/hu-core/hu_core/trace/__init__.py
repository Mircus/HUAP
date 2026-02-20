"""
HUAP Trace System v0.1

Provides replayable, eval-ready tracing for agent runs.

Usage:
    from hu_core.trace import get_trace_service, TraceEvent, EventKind, EventName

    # Get the global trace service
    tracer = get_trace_service()

    # Start a run
    tracer.start_run(pod="hello", graph="hello")

    # Emit events
    tracer.node_enter("start_node", state={"goal": "fitness"})
    tracer.node_exit("start_node", output={"ready": True}, duration_ms=10)

    # End the run
    tracer.end_run(status="success", duration_ms=1000)

Replay:
    from hu_core.trace import TraceReplayer

    replayer = TraceReplayer("trace.jsonl", stub_tools=True, stub_llm=True)
    result = await replayer.replay(output_path="replay.jsonl")

Diff:
    from hu_core.trace import TraceDiffer, DiffPolicy, DiffSeverity

    # Basic diff
    differ = TraceDiffer()
    diff = differ.diff("baseline.jsonl", "candidate.jsonl")
    markdown = differ.to_markdown(diff)

    # With policy (for CI)
    policy = DiffPolicy.from_yaml(Path("diff_policy.yaml"))
    differ = TraceDiffer(policy=policy)
    diff = differ.diff("baseline.jsonl", "candidate.jsonl")
    if diff["overall_severity"] == "fail":
        sys.exit(1)  # CI fails
"""
from .models import (
    # Enums
    EventKind,
    EventName,
    # Event data models
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
    MemoryPutData,
    MemoryGetData,
    MemorySearchData,
    MessageEventData,
    ArtifactCreatedData,
    CostRecordData,
    QualityRecordData,
    # Main classes
    TraceEvent,
    TraceRun,
    # Utilities
    hash_data,
    hash_state,
    normalize_for_hash,
    EPHEMERAL_FIELDS,
    generate_run_id,
    generate_span_id,
)
from .writer import TraceWriter, NullTraceWriter
from .service import (
    TraceService,
    get_trace_service,
    set_context_tracer,
    configure_trace_service,
    reset_trace_service,
)
from .replay import TraceReplayer, StubRegistry, StubbedToolRegistry, StubbedLLMClient, CostSummary
from .diff import TraceDiffer, EventDiff, CostDelta, QualityDelta, DiffSeverity, DiffPolicy
from .runner import run_pod_graph

__all__ = [
    # Enums
    "EventKind",
    "EventName",
    # Event data models
    "RunStartData",
    "RunEndData",
    "ErrorData",
    "NodeEnterData",
    "NodeExitData",
    "ToolCallData",
    "ToolResultData",
    "LLMRequestData",
    "LLMResponseData",
    "PolicyCheckData",
    "MemoryPutData",
    "MemoryGetData",
    "MemorySearchData",
    "MessageEventData",
    "ArtifactCreatedData",
    "CostRecordData",
    "QualityRecordData",
    # Main classes
    "TraceEvent",
    "TraceRun",
    "TraceWriter",
    "NullTraceWriter",
    "TraceService",
    # Replay
    "TraceReplayer",
    "StubRegistry",
    "StubbedToolRegistry",
    "StubbedLLMClient",
    "CostSummary",
    # Diff
    "TraceDiffer",
    "EventDiff",
    "CostDelta",
    "QualityDelta",
    "DiffSeverity",
    "DiffPolicy",
    # Runner
    "run_pod_graph",
    # Functions
    "hash_data",
    "hash_state",
    "normalize_for_hash",
    "EPHEMERAL_FIELDS",
    "generate_run_id",
    "generate_span_id",
    "get_trace_service",
    "set_context_tracer",
    "configure_trace_service",
    "reset_trace_service",
]
