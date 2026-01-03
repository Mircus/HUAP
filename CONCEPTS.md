# HUAP Core Concepts

This document explains the core architecture and concepts behind HUAP.

---

## Core Philosophy

HUAP is built on three principles:

1. **Everything is traceable** - Every tool call, LLM request, and state change is recorded
2. **Replay is deterministic** - Given the same trace, replay produces the same output
3. **Quality is measurable** - Every run can be evaluated against cost and quality budgets

---

## Pods

A **pod** is a self-contained agent unit that:
- Defines a set of tools
- Implements a workflow graph
- Produces traceable output

```python
class MyPod:
    name = "my-pod"
    version = "0.1.0"

    def get_tools(self):
        return [MyTool()]

    async def run(self, input_state):
        # Execute workflow
        return output_state
```

---

## Tools

A **tool** is a discrete action an agent can take:

```python
class MyTool(BaseTool):
    name = "my_tool"
    category = ToolCategory.UTILITY

    async def execute(self, input_data, context=None):
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"result": "done"},
        )
```

Tool categories:
- `UTILITY` - General purpose (echo, add, normalize)
- `AI` - LLM-powered (summarize, classify, generate)
- `MEMORY` - In-memory state (get, put, search)
- `STORAGE` - Persistent file/KV storage (read, write, delete)
- `HTTP` - HTTP client (fetch, post)
- `DATA` - Data transformation (parse, format, validate)
- `MESSAGING` - Communication (email, sms, notifications)
- `EXTERNAL` - Third-party API integrations (oauth, webhooks)

---

## Traces

A **trace** is a JSONL file recording all events during a run:

```jsonl
{"kind":"run","name":"run_start","ts":"2025-01-01T10:00:00Z","data":{...}}
{"kind":"node","name":"node_enter","ts":"2025-01-01T10:00:01Z","data":{...}}
{"kind":"tool","name":"tool_call","ts":"2025-01-01T10:00:02Z","data":{...}}
{"kind":"tool","name":"tool_result","ts":"2025-01-01T10:00:03Z","data":{...}}
{"kind":"run","name":"run_end","ts":"2025-01-01T10:00:04Z","data":{...}}
```

Event kinds:
- `run` - Run lifecycle (start, end)
- `node` - Graph node execution
- `tool` - Tool calls and results
- `llm` - LLM requests and responses
- `policy` - Guard policy checks
- `memory` - State persistence
- `quality` - Quality metrics
- `cost` - Cost tracking

---

## Replay

**Replay** re-executes a trace with stubbed dependencies:

```python
replayer = TraceReplayer(
    "trace.jsonl",
    stub_tools=True,  # Return recorded tool results
    stub_llm=True,    # Return recorded LLM responses
)
result = await replayer.replay(mode="exec")
```

Two modes:
- `emit` - Re-emit recorded events (fast, no execution)
- `exec` - Re-execute workflow with stubs (deterministic)

---

## Diff

**Diff** compares two traces for regressions:

```python
differ = TraceDiffer(policy=DiffPolicy.from_yaml("policy.yaml"))
result = differ.diff("baseline.jsonl", "candidate.jsonl")

if result["overall_severity"] == "fail":
    sys.exit(1)
```

Severity levels:
- `info` - Informational changes
- `warn` - Should be reviewed
- `fail` - CI should fail

---

## Evaluation

**Eval** grades a trace against cost and quality budgets:

```python
evaluator = TraceEvaluator(budget)
result = evaluator.evaluate("trace.jsonl")

# Grades: A, B, C, D, F
print(result.cost_grade, result.quality_grade)
```

Cost metrics:
- Tokens consumed
- USD estimate
- Latency (ms)

Quality metrics:
- Policy violations
- Tool errors
- Custom scores

---

## StateRefs

**StateRef** is the pattern for passing state through a workflow:

```python
# State is a dict that flows through nodes
state = {"goal": "fitness", "user_id": "123"}

# Each node can read/write state
state["plan"] = generate_plan(state["goal"])

# State is hashed at run_end for verification
output_hash = hash_state(state)
```

---

## Graphs

A **graph** defines the workflow as YAML:

```yaml
name: my_workflow
entry: start

nodes:
  start:
    type: entry
    next: process

  process:
    type: action
    action: my_tool
    next: complete

  complete:
    type: exit
```

Node types:
- `entry` - Starting point
- `action` - Execute a tool
- `branch` - Conditional routing
- `wait` - Pause for input
- `exit` - End workflow

---

## Stub Mode

**Stub mode** enables testing without real API calls:

```bash
export HUAP_LLM_MODE=stub
```

In stub mode:
- LLM calls return deterministic responses
- No API key required
- Fast execution for CI

---

## Isolation

HUAP uses **contextvars** for concurrent run isolation:

```python
from hu_core.trace import set_context_tracer
from hu_core.tools import set_context_registry

# Each async task gets its own context
set_context_tracer(my_tracer)
set_context_registry(my_registry)
```

This prevents singleton poisoning in concurrent scenarios.

---

## Next Steps

- [Pod Authoring](POD_AUTHORING.md) - Building production pods
- [Trace Guide](TRACE_GUIDE.md) - Trace format details
- [Public Scope](PUBLIC_SCOPE.md) - What's included

---

**HUAP Core v0.1.0b1**
