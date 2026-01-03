# Trace Guide

Understanding HUAP trace format, replay semantics, and evaluation.

---

## Trace Format

Traces are JSONL files with one event per line:

```jsonl
{"kind":"run","name":"run_start","run_id":"run_abc123","span_id":"sp_001","ts":"2025-01-01T10:00:00Z","data":{"pod":"hello","graph":"default"}}
{"kind":"node","name":"node_enter","run_id":"run_abc123","span_id":"sp_002","ts":"2025-01-01T10:00:01Z","data":{"node":"start"}}
{"kind":"tool","name":"tool_call","run_id":"run_abc123","span_id":"sp_003","ts":"2025-01-01T10:00:02Z","data":{"tool":"echo","input":{"message":"hello"}}}
{"kind":"tool","name":"tool_result","run_id":"run_abc123","span_id":"sp_003","ts":"2025-01-01T10:00:03Z","data":{"tool":"echo","result":{"echoed":"hello"},"status":"ok"}}
{"kind":"run","name":"run_end","run_id":"run_abc123","span_id":"sp_001","ts":"2025-01-01T10:00:04Z","data":{"status":"success","duration_ms":4000}}
```

---

## Event Kinds

| Kind | Events | Description |
|------|--------|-------------|
| `run` | run_start, run_end, error | Run lifecycle |
| `node` | node_enter, node_exit | Graph node execution |
| `tool` | tool_call, tool_result | Tool invocations |
| `llm` | llm_request, llm_response | LLM API calls |
| `policy` | policy_check | Guard policy decisions |
| `memory` | memory_put, memory_get, memory_search | State persistence |
| `quality` | quality_record | Quality metrics |
| `cost` | cost_record | Cost tracking |

---

## Event Schema

Common fields:
```json
{
  "kind": "tool",
  "name": "tool_call",
  "run_id": "run_abc123",
  "span_id": "sp_003",
  "parent_span_id": "sp_002",
  "ts": "2025-01-01T10:00:02Z",
  "data": { ... }
}
```

---

## Replay Semantics

### What is Deterministic

- Tool results (stubbed from recorded data)
- LLM responses (stubbed from recorded data)
- Graph traversal (same nodes visited)
- Final state hash (if no external changes)

### What May Vary

- Timestamps
- Duration (ms)
- Span IDs (regenerated)
- Run IDs (regenerated)

---

## Replay Modes

### Emit Mode (Default)

Re-emits recorded events without execution:

```bash
huap trace replay trace.jsonl --mode emit
```

- Fast
- No real code execution
- Good for verification

### Exec Mode

Re-executes the workflow with stubbed dependencies:

```bash
huap trace replay trace.jsonl --mode exec
```

- Runs real code
- Injects recorded LLM/tool responses
- Verifies state hash matches

---

## Stub Matching

Stubs are matched by content hash:

1. **Tool stubs**: `hash(tool_name + input_data)`
2. **LLM stubs**: `hash(messages)`

If no exact match, falls back to sequence order.

---

## Redaction

Redact sensitive LLM content:

```bash
export HUAP_TRACE_REDACT_LLM=true
huap trace run hello default --out trace.jsonl
```

Redacted events:
```json
{
  "kind": "llm",
  "name": "llm_request",
  "data": {
    "model": "gpt-4o-mini",
    "messages": [
      {"role": "user", "content": "[REDACTED]", "_content_hash": "abc123"}
    ]
  }
}
```

---

## Diff Policy

Configure regression thresholds in YAML:

```yaml
# diff_policy.yaml
token_increase_warn_pct: 20.0
token_increase_fail_pct: 50.0
usd_increase_warn_pct: 20.0
usd_increase_fail_pct: 50.0
latency_increase_warn_pct: 50.0
latency_increase_fail_pct: 100.0

ignore_fields:
  - timestamp
  - run_id
  - span_id
  - duration_ms

allow_new_errors: false
```

Use with diff:

```python
from hu_core.trace import TraceDiffer, DiffPolicy

policy = DiffPolicy.from_yaml("diff_policy.yaml")
differ = TraceDiffer(policy=policy)
result = differ.diff("baseline.jsonl", "candidate.jsonl")

# result["overall_severity"]: "info" | "warn" | "fail"
```

---

## Hash Normalization

State hashes ignore ephemeral fields:

```python
from hu_core.trace import hash_state, EPHEMERAL_FIELDS

# These fields are excluded from hashes:
# timestamp, run_id, span_id, duration_ms, latency_ms, etc.

state1 = {"data": "hello", "timestamp": "2025-01-01"}
state2 = {"data": "hello", "timestamp": "2025-01-02"}

hash_state(state1) == hash_state(state2)  # True
```

---

## Cost Tracking

Cost events are emitted by LLM calls:

```json
{
  "kind": "cost",
  "name": "cost_record",
  "data": {
    "tokens": 150,
    "usd_est": 0.0003,
    "latency_ms": 450,
    "model": "gpt-4o-mini"
  }
}
```

Replay results include cost summary:

```python
result = await replayer.replay()
print(result["original_cost"])  # {"total_tokens": 150, ...}
print(result["replay_cost"])    # {"total_tokens": 0, ...} (stubbed)
```

---

## CLI Reference

```bash
# View trace
huap trace view trace.jsonl --kind llm --limit 10

# Replay
huap trace replay trace.jsonl --mode exec --verify

# Diff
huap trace diff baseline.jsonl candidate.jsonl --out diff.md

# Evaluate
huap eval trace trace.jsonl --scenario my_scenario
```

---

**HUAP Core v0.1.0b1**
