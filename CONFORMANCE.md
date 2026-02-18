# HUAP Conformance Specification

This document defines the contracts that any HUAP-compatible implementation must satisfy.

**Schema Versions:**
- Trace Schema: `1.0`
- Workflow Schema: `1.0`
- Interface Version: `1.0`

---

## 1. Storage Interfaces

Implementations must provide these abstract methods:

### TraceStore

```python
class TraceStore(ABC):
    @abstractmethod
    def save(self, run_id: str, events: List[Dict]) -> Path: ...

    @abstractmethod
    def load(self, run_id: str) -> List[Dict]: ...

    @abstractmethod
    def exists(self, run_id: str) -> bool: ...
```

### StateStore

```python
class StateStore(ABC):
    @abstractmethod
    def save(self, run_id: str, state: Dict) -> None: ...

    @abstractmethod
    def load(self, run_id: str) -> Optional[Dict]: ...
```

### KVStore

```python
class KVStore(ABC):
    @abstractmethod
    def get(self, namespace: str, key: str) -> Optional[Any]: ...

    @abstractmethod
    def set(self, namespace: str, key: str, value: Any) -> None: ...

    @abstractmethod
    def delete(self, namespace: str, key: str) -> bool: ...

    @abstractmethod
    def list_keys(self, namespace: str) -> List[str]: ...
```

---

## 2. Trace Schema (v0.1)

Every trace event must contain:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `v` | string | Yes | Schema version (e.g., "0.1") |
| `ts` | string | Yes | ISO 8601 timestamp |
| `name` | string | Yes | Event name |
| `kind` | string | Yes | Event kind |
| `run_id` | string | Yes | Unique run identifier |
| `span_id` | string | Yes | Span identifier |
| `pod` | string | Yes | Pod name |
| `data` | object | Yes | Event-specific payload |

### Event Kinds

| Kind | Events |
|------|--------|
| `lifecycle` | `run_start`, `run_end` |
| `node` | `node_enter`, `node_exit` |
| `tool` | `tool_call`, `tool_result` |
| `llm` | `llm_request`, `llm_response` |
| `cost` | `cost_record` |
| `policy` | `policy_check` |

### Invariants

1. Every `run_start` must have a matching `run_end`
2. Every `node_enter` must have a matching `node_exit`
3. Every `tool_call` must have a matching `tool_result`
4. Events must be ordered by timestamp
5. `run_id` must be consistent across all events in a trace

---

## 3. Workflow Schema (v1.0)

YAML workflow definitions must support:

```yaml
nodes:
  - name: string        # Required: unique node identifier
    run: string         # Optional: dotted path to function
    description: string # Optional: human-readable description

edges:
  - from: string        # Required: source node name
    to: string          # Required: target node name
    condition: string   # Optional: Python expression
```

### Invariants

1. All edge `from`/`to` references must exist in `nodes`
2. Graph must have at least one node
3. No duplicate node names

---

## 4. Tool Categories

Implementations must recognize these categories:

```python
class ToolCategory(str, Enum):
    AI = "ai"
    MEMORY = "memory"
    STORAGE = "storage"
    MESSAGING = "messaging"
    HTTP = "http"
    DATA = "data"
    UTILITY = "utility"
    EXTERNAL = "external"
```

---

## 5. CLI Commands

Conformant implementations must support:

| Command | Description | Exit Code |
|---------|-------------|-----------|
| `huap trace run <pod> <graph>` | Execute workflow, produce trace | 0 on success |
| `huap trace view <file>` | Display trace events | 0 on success |
| `huap trace replay <file>` | Replay with stubs | 0 on success |
| `huap trace diff <a> <b>` | Compare two traces | 0 if no regressions |
| `huap eval trace <file>` | Evaluate trace | 0 if passing |

### Required Options

- `huap trace run --out <path>` : Output trace file path
- `huap trace replay --verify` : Verify state hashes match
- `huap trace replay --mode <emit|exec>` : Replay mode

---

## 6. Conformance Tests

To verify conformance, run:

```bash
# 1. Execute golden workflow
HUAP_LLM_MODE=stub huap trace run hello examples/graphs/hello.yaml --out /tmp/test.jsonl

# 2. Verify trace schema
huap trace view /tmp/test.jsonl  # Must show valid events

# 3. Replay determinism
huap trace replay /tmp/test.jsonl --mode exec --verify  # Must pass

# 4. Diff stability
huap trace diff examples/traces/golden_hello.jsonl /tmp/test.jsonl  # No schema errors
```

### Golden Traces

Reference traces are provided in `examples/traces/`:

- `golden_hello.jsonl` - Minimal workflow baseline

These traces define expected event shapes and ordering.

---

## 7. Versioning Policy

| Change Type | Version Bump |
|-------------|--------------|
| New optional field | Patch (1.0.x) |
| New event kind | Minor (1.x.0) |
| Breaking schema change | Major (x.0.0) |
| Interface method change | Major (x.0.0) |

---

**HUAP Conformance Spec v1.0**
