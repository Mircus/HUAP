# Getting Started with HUAP Core

This guide walks you through HUAP in 5 minutes — from install to CI-gated traces.

---

## Prerequisites

- Python 3.10+
- pip

---

## Installation

```bash
pip install huap-core
```

Or install from source:

```bash
git clone https://github.com/Mircus/HUAP.git && cd HUAP
pip install -e packages/hu-core
```

Verify:

```bash
huap version
```

---

## Step 1: Run the Demo

The fastest way to see HUAP in action — one command, no API keys:

```bash
huap demo
```

This runs the built-in hello graph in stub mode, generates an HTML trace report, and opens it in your browser.

---

## Step 2: Create Your Own Pod

A pod is a self-contained agent with tools and workflows.

```bash
huap pod create myagent --description "My first HUAP agent"
```

This creates:
```
hu-myagent/
├── hu_myagent/
│   ├── __init__.py
│   ├── pod.py          # Pod class + node functions
│   └── myagent.yaml    # Workflow (nodes[] + edges[])
├── tests/
│   └── test_myagent_pod.py
└── pyproject.toml
```

Install and run it:

```bash
pip install -e hu-myagent
HUAP_LLM_MODE=stub huap trace run myagent hu-myagent/hu_myagent/myagent.yaml --out traces/myagent.jsonl
```

---

## Step 3: Explore the Trace

```bash
huap trace view traces/myagent.jsonl
```

Generate a shareable HTML report:

```bash
huap trace report traces/myagent.jsonl --out reports/myagent.html
```

Evaluate cost and quality:

```bash
huap eval trace traces/myagent.jsonl
```

---

## Step 4: Diff Two Runs

Run the same graph twice and compare:

```bash
HUAP_LLM_MODE=stub huap trace run myagent hu-myagent/hu_myagent/myagent.yaml --out traces/v2.jsonl
huap trace diff traces/myagent.jsonl traces/v2.jsonl
```

Identical stub runs produce zero drift — proving determinism.

---

## Step 5: Add a Custom Node

Add a function to `hu_myagent/pod.py`:

```python
def greet_node(state: Dict[str, Any]) -> Dict[str, Any]:
    name = state.get("name", "World")
    return {"greeting": f"Hello, {name}!"}
```

Reference it in your workflow YAML:

```yaml
nodes:
  - name: greet
    run: hu_myagent.pod.greet_node
    description: "Greet the user"
```

---

## Step 6: CI Integration

Run the built-in smoke suite with golden baseline diffing:

```bash
huap ci run suites/smoke/suite.yaml --html reports/smoke.html
```

Or add to your GitHub Actions workflow:

```yaml
- name: Install HUAP
  run: pip install -e packages/hu-core

- name: Run CI suite
  run: |
    export HUAP_LLM_MODE=stub
    huap ci run suites/smoke/suite.yaml --html reports/smoke.html
```

---

## Next Steps

- Explore example pods in `examples/pods/`
- Set up the model router: `huap models init && huap models list`
- Try human gates: `huap inbox list`
- Read [Conformance](CONFORMANCE.md) for interface & schema contracts
- See the full [CLI Reference](README.md#-cli-reference)

---

**Happy building!**
