"""
HUAP Trace Spec v0.1 - Pydantic Models

Defines the canonical trace format for replayable, eval-ready agent runs.
Each trace is a JSONL file where each line is a TraceEvent.

Spec: See docs/manual/HUAP_Public_Beta_Manual.md (Trace Spec section).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# ENUMS
# =============================================================================

class EventKind(str, Enum):
    """Kind of trace event."""
    LIFECYCLE = "lifecycle"  # run_start, run_end
    NODE = "node"
    TOOL = "tool"
    LLM = "llm"
    POLICY = "policy"
    MEMORY = "memory"
    MESSAGE = "message"
    ARTIFACT = "artifact"
    SYSTEM = "system"
    COST = "cost"
    QUALITY = "quality"


class EventName(str, Enum):
    """Specific event names within each kind."""
    # System events
    RUN_START = "run_start"
    RUN_END = "run_end"
    ERROR = "error"

    # Node events
    NODE_ENTER = "node_enter"
    NODE_EXIT = "node_exit"

    # Tool events
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"

    # LLM events
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"

    # Policy events
    POLICY_CHECK = "policy_check"

    # Memory events
    MEMORY_PUT = "memory_put"
    MEMORY_GET = "memory_get"
    MEMORY_SEARCH = "memory_search"

    # Message events
    MESSAGE_SENT = "message_sent"
    MESSAGE_DELIVERED = "message_delivered"
    MESSAGE_ACK = "message_ack"
    MESSAGE_RETRY = "message_retry"

    # Artifact events
    ARTIFACT_CREATED = "artifact_created"

    # Cost/Quality events
    COST_RECORD = "cost_record"
    QUALITY_RECORD = "quality_record"


# =============================================================================
# EVENT DATA MODELS (payload for each event type)
# =============================================================================

class RunStartData(BaseModel):
    """Data for run_start event."""
    pod: str
    graph: Optional[str] = None
    graph_path: Optional[str] = None  # Full path for replay exec resolution
    input: Dict[str, Any] = Field(default_factory=dict)  # Full input for replay exec
    input_keys: List[str] = Field(default_factory=list)  # Kept for backward compat
    input_hash: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)


class RunEndData(BaseModel):
    """Data for run_end event."""
    status: str  # "success" | "error" | "timeout"
    output_keys: List[str] = Field(default_factory=list)
    output_hash: Optional[str] = None
    duration_ms: float
    error: Optional[str] = None


class ErrorData(BaseModel):
    """Data for error event."""
    error_type: str
    message: str
    traceback: Optional[str] = None
    node: Optional[str] = None
    tool: Optional[str] = None


class NodeEnterData(BaseModel):
    """Data for node_enter event."""
    node: str
    state_keys: List[str] = Field(default_factory=list)
    state_hash: Optional[str] = None


class NodeExitData(BaseModel):
    """Data for node_exit event."""
    node: str
    output: Dict[str, Any] = Field(default_factory=dict)
    output_hash: Optional[str] = None
    duration_ms: float


class ToolCallData(BaseModel):
    """Data for tool_call event."""
    tool: str
    input: Dict[str, Any] = Field(default_factory=dict)
    input_hash: Optional[str] = None
    permissions: Dict[str, Any] = Field(default_factory=dict)


class ToolResultData(BaseModel):
    """Data for tool_result event."""
    tool: str
    result: Dict[str, Any] = Field(default_factory=dict)
    result_hash: Optional[str] = None
    duration_ms: float
    status: str  # "ok" | "error"
    error: Optional[str] = None


class LLMRequestData(BaseModel):
    """Data for llm_request event."""
    provider: str = "openai"
    model: str
    messages: List[Dict[str, str]]
    temperature: float = 0.2
    max_tokens: int = 800


class LLMResponseData(BaseModel):
    """Data for llm_response event."""
    provider: str = "openai"
    model: str
    text: str
    usage: Dict[str, int]  # prompt_tokens, completion_tokens, total_tokens
    duration_ms: float


class PolicyCheckData(BaseModel):
    """Data for policy_check event."""
    policy: str
    decision: str  # "allow" | "deny"
    reason: Optional[str] = None
    rule_id: Optional[str] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)


class MemoryPutData(BaseModel):
    """Data for memory_put event."""
    key: str
    namespace: Optional[str] = None
    value_hash: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class MemoryGetData(BaseModel):
    """Data for memory_get event."""
    key: str
    namespace: Optional[str] = None
    found: bool
    value_hash: Optional[str] = None


class MemorySearchData(BaseModel):
    """Data for memory_search event."""
    query: str
    k: int = 20
    results_count: int = 0


class MessageEventData(BaseModel):
    """Data for message events."""
    message_id: str
    channel: Optional[str] = None
    sender_pod: str
    target_pod: Optional[str] = None
    correlation_id: Optional[str] = None


class ArtifactCreatedData(BaseModel):
    """Data for artifact_created event."""
    artifact_type: str  # "markdown" | "json" | "pdf" | "zip"
    path: str
    sha256: Optional[str] = None
    size_bytes: Optional[int] = None


class CostRecordData(BaseModel):
    """Data for cost_record event."""
    tokens: int
    usd_est: float
    latency_ms: float
    model: Optional[str] = None


class QualityRecordData(BaseModel):
    """Data for quality_record event."""
    metric: str  # "json_valid" | "critique_closed" | "policy_violations" | etc.
    value: float  # 0.0 - 1.0 typically
    details: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# TRACE EVENT (Envelope)
# =============================================================================

# Union of all possible event data types
EventData = Union[
    RunStartData, RunEndData, ErrorData,
    NodeEnterData, NodeExitData,
    ToolCallData, ToolResultData,
    LLMRequestData, LLMResponseData,
    PolicyCheckData,
    MemoryPutData, MemoryGetData, MemorySearchData,
    MessageEventData,
    ArtifactCreatedData,
    CostRecordData, QualityRecordData,
    Dict[str, Any],  # Fallback for custom events
]


class TraceEvent(BaseModel):
    """
    Canonical trace event envelope.

    Every event in a trace file follows this structure.
    """
    v: str = "0.1"  # Trace spec version
    ts: datetime = Field(default_factory=datetime.utcnow)
    run_id: str
    span_id: str = Field(default_factory=lambda: f"sp_{uuid4().hex[:12]}")
    parent_span_id: Optional[str] = None
    kind: EventKind
    name: EventName
    pod: str = "hu-core"
    engine: str = "native_graph"
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    data: EventData = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=True)

    def to_jsonl(self) -> str:
        """Serialize to JSONL-compatible string."""
        return self.model_dump_json()

    @classmethod
    def from_jsonl(cls, line: str) -> "TraceEvent":
        """Deserialize from JSONL line."""
        return cls.model_validate_json(line)


# =============================================================================
# TRACE RUN (Collection of events)
# =============================================================================

class TraceRun(BaseModel):
    """
    A complete trace run (collection of events).

    Used for loading/analyzing entire trace files.
    """
    run_id: str
    events: List[TraceEvent] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def start_event(self) -> Optional[TraceEvent]:
        """Get the run_start event."""
        for e in self.events:
            if e.name == EventName.RUN_START:
                return e
        return None

    @property
    def end_event(self) -> Optional[TraceEvent]:
        """Get the run_end event."""
        for e in self.events:
            if e.name == EventName.RUN_END:
                return e
        return None

    @property
    def duration_ms(self) -> Optional[float]:
        """Total run duration in milliseconds."""
        end = self.end_event
        if end and isinstance(end.data, dict):
            return end.data.get("duration_ms")
        return None

    def filter_by_kind(self, kind: EventKind) -> List[TraceEvent]:
        """Filter events by kind."""
        return [e for e in self.events if e.kind == kind]

    def filter_by_name(self, name: EventName) -> List[TraceEvent]:
        """Filter events by name."""
        return [e for e in self.events if e.name == name]

    @classmethod
    def from_jsonl_file(cls, path: str) -> "TraceRun":
        """Load trace from JSONL file."""
        events = []
        run_id = None

        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                event = TraceEvent.from_jsonl(line)
                events.append(event)
                if run_id is None:
                    run_id = event.run_id

        return cls(run_id=run_id or f"run_{uuid4().hex[:8]}", events=events)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

# Fields to exclude from hash normalization (ephemeral data)
EPHEMERAL_FIELDS = frozenset({
    "timestamp", "run_id", "span_id", "parent_span_id",
    "duration_ms", "latency_ms", "start_time", "end_time",
    "_id", "id", "created_at", "updated_at",
})


def normalize_for_hash(
    data: Any,
    exclude_fields: Optional[set] = None,
    float_precision: int = 4,
) -> Any:
    """
    Normalize data for consistent hashing.

    - Removes ephemeral fields (timestamps, IDs)
    - Rounds floats to avoid precision issues
    - Recursively sorts dicts and lists

    Args:
        data: Data to normalize
        exclude_fields: Additional fields to exclude (merged with EPHEMERAL_FIELDS)
        float_precision: Decimal places to round floats to

    Returns:
        Normalized data structure suitable for hashing
    """
    excluded = EPHEMERAL_FIELDS | (exclude_fields or set())

    def _normalize(obj: Any) -> Any:
        if obj is None:
            return None
        elif isinstance(obj, dict):
            # Sort keys and recurse, excluding ephemeral fields
            normalized = {}
            for k in sorted(obj.keys()):
                if k not in excluded:
                    normalized[k] = _normalize(obj[k])
            return normalized
        elif isinstance(obj, (list, tuple)):
            # Normalize each element
            return [_normalize(item) for item in obj]
        elif isinstance(obj, float):
            # Round floats to avoid precision issues
            return round(obj, float_precision)
        elif hasattr(obj, 'model_dump'):
            # Pydantic model
            return _normalize(obj.model_dump())
        elif hasattr(obj, '__dict__'):
            # Generic object with __dict__ - convert to dict
            return _normalize(vars(obj))
        else:
            return obj

    return _normalize(data)


def hash_data(data: Any, normalize: bool = False) -> str:
    """
    Create a stable hash of data for comparison.

    Args:
        data: Data to hash
        normalize: If True, normalize data before hashing (removes ephemeral fields)

    Returns:
        16-character hex hash string
    """
    if data is None:
        return ""

    if normalize:
        data = normalize_for_hash(data)

    if isinstance(data, (dict, list)):
        serialized = json.dumps(data, sort_keys=True, default=str)
    else:
        serialized = str(data)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]


def hash_state(state: Dict[str, Any]) -> str:
    """
    Hash a state dict with normalization.

    Convenience function for hashing state objects in traces.
    """
    return hash_data(state, normalize=True)


def generate_run_id() -> str:
    """Generate a unique run ID."""
    return f"run_{uuid4().hex[:12]}"


def generate_span_id() -> str:
    """Generate a unique span ID."""
    return f"sp_{uuid4().hex[:12]}"
