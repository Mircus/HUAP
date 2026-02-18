# Getting Started with HUAP Core

This guide walks you through building and testing your first HUAP agent.

---

## Prerequisites

- Python 3.10+
- pip

---

## Installation

```bash
pip install huap-core
```

Verify installation:

```bash
huap version
```

---

## Step 1: Create a Pod

A pod is a self-contained agent with tools and workflows.

```bash
huap pod create myagent --description "My first HUAP agent"
```

This creates:
```
hu-myagent/
├── hu_myagent/
│   ├── __init__.py
│   ├── pod.py          # Your pod implementation
│   └── myagent.yaml    # Workflow definition (nodes[] + edges[] spec)
├── tests/
│   └── test_myagent_pod.py
└── pyproject.toml
```

The generated workflow YAML uses the **runnable `nodes[]` + `edges[]` spec**.
Each node's `run:` field points to an importable Python function.

---

## Step 2: Run a Workflow with Tracing

Run the example workflow to generate a trace:

```bash
# Run with stub mode (no API key needed)
export HUAP_LLM_MODE=stub

huap trace run hello examples/graphs/hello.yaml --out traces/hello.jsonl
```

Output:
```
Running pod 'hello' with graph 'examples/graphs/hello.yaml'...

Trace saved to: traces/hello.jsonl
Run ID: run_abc123
Status: success
Duration: 25.3ms
```

---

## Step 3: View a Trace

```bash
huap trace view traces/hello.jsonl
```

Output:
```
Run ID: run_abc123
Total events: 8

[00:00:00.000] system/run_start
  span: sp-000
  pod: hello
  graph: hello_workflow

[00:00:00.010] node/node_enter
  span: sp-001
  node: start
...
```

---

## Step 4: Replay & Verify

Replay re-emits the same trace events:

```bash
huap trace replay examples/traces/golden_hello.jsonl --verify
```

Output:
```
Replay saved to: examples/traces/golden_hello.replay.jsonl
Verification: PASSED (state hashes match)
```

---

## Step 5: Add a Tool to Your Pod

Edit `hu_myagent/pod.py`:

```python
from hu_core.tools import BaseTool, ToolResult, ToolStatus, ToolCategory

class GreetTool(BaseTool):
    name = "greet"
    description = "Greet a user by name"
    category = ToolCategory.UTILITY

    input_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
        },
        "required": ["name"],
    }

    async def execute(self, input_data, context=None):
        name = input_data.get("name", "World")
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"greeting": f"Hello, {name}!"},
        )
```

---

## Step 6: Diff Two Traces

Compare baseline and candidate traces:

```bash
huap trace diff baseline.jsonl candidate.jsonl
```

Output:
```
Summary:
  Events in baseline: 12
  Events in candidate: 14
  Added events: 2
  Changed events: 1

No regressions detected.
```

---

## Step 7: Evaluate a Trace

```bash
huap eval trace examples/traces/golden_hello.jsonl
```

Output:
```
Evaluation: PASSED
Cost Grade: A
Quality Grade: B
Overall Grade: B

Cost Metrics:
  Tokens: 43
  USD: $0.0001
  Latency: 440ms
```

---

## Step 8: CI Integration

Add to `.github/workflows/ci.yml`:

```yaml
- name: Install HUAP
  run: pip install huap-core

- name: Run smoke tests
  run: |
    export HUAP_LLM_MODE=stub
    huap trace replay suites/smoke/baseline.jsonl --verify
    huap eval trace suites/smoke/baseline.jsonl
```

---

## Next Steps

- Read [Concepts](CONCEPTS.md) for architecture details
- Read [Pod Authoring](POD_AUTHORING.md) for best practices
- Read [Trace Guide](TRACE_GUIDE.md) for trace format details
- Explore examples in `examples/pods/`

---

**Happy building!**
