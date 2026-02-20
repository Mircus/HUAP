# Getting Started with HUAP Core

This guide walks you through building and testing your first HUAP agent.

---

## Prerequisites

- Python 3.10+
- pip

---

## Installation

```bash
# Install from source (not yet on PyPI)
git clone https://github.com/Mircus/HUAP.git && cd HUAP
pip install -e packages/hu-core
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
  graph: hello

[00:00:00.010] node/node_enter
  span: sp-001
  node: start
...
```

---

## Step 4: Replay & Verify

Replay re-emits the same trace events:

```bash
huap trace replay examples/traces/golden_hello.jsonl --mode exec --verify
```

Output:
```
Replay saved to: examples/traces/golden_hello.replay.jsonl
Verification: PASSED (state hashes match)
```

---

## Step 5: Add a Node to Your Workflow

Add a node function to `hu_myagent/pod.py`:

```python
from typing import Any, Dict

def greet_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Greet a user by name."""
    name = state.get("name", "World")
    return {"greeting": f"Hello, {name}!"}
```

Then reference it in your workflow YAML:

```yaml
nodes:
  - name: greet
    run: hu_myagent.pod.greet_node
    description: "Greet the user"
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
  run: pip install -e packages/hu-core

- name: Run smoke tests
  run: |
    export HUAP_LLM_MODE=stub
    huap trace run hello examples/graphs/hello.yaml --out /tmp/smoke.jsonl
    huap trace replay /tmp/smoke.jsonl --mode exec --verify
    huap eval trace /tmp/smoke.jsonl
```

---

## Next Steps

- Read [Conformance](CONFORMANCE.md) for interface & schema contracts
- Explore examples in `examples/pods/`
- Try the model router: `huap models init && huap models list`
- Set up human gates: `huap inbox list`

---

**Happy building!**
