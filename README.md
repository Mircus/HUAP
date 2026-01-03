




# HUAP Core

<p align="center">
  <img src="HUAP-LOGO.png" alt="HUAP-Logo" width="500"/>
  <br/>
  <strong>HUman Agentic Platform</strong>
</p>

**Build deterministic, traceable AI agents with replay and evaluation.**

HUAP Core provides the foundational toolkit for building AI agent systems that are:
- **Traceable** - Every action recorded as replayable events
- **Deterministic** - Stub mode for reproducible testing
- **Evaluatable** - Built-in cost and quality grading

---

## Quick Start

```bash
# Install
pip install huap-core

# Create a pod
huap pod create myagent

# Run with tracing (stub mode - no API key needed)
export HUAP_LLM_MODE=stub
huap trace run myagent graphs/myagent.yaml --out traces/myagent.jsonl

# Replay (deterministic)
huap trace replay traces/myagent.jsonl --verify

# Evaluate
huap eval trace traces/myagent.jsonl
```

---

## Golden Path (5 Minutes)

### 1. Install

```bash
pip install huap-core
```

### 2. Create Your First Pod

```bash
huap pod create hello --description "My first agent"
```

### 3. Run with Tracing

```bash
# Use stub mode (no API key needed)
export HUAP_LLM_MODE=stub

huap trace run hello default --out traces/hello.jsonl
```

### 4. View the Trace

```bash
huap trace view traces/hello.jsonl
```

### 5. Replay & Verify

```bash
huap trace replay traces/hello.jsonl --verify
```

### 6. Diff Two Runs

```bash
# Run again
huap trace run hello default --out traces/hello_v2.jsonl

# Compare
huap trace diff traces/hello.jsonl traces/hello_v2.jsonl
```

---

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Pod** | A self-contained agent with tools and workflows |
| **Trace** | JSONL log of all events during a run |
| **Replay** | Re-execute a trace with stubbed dependencies |
| **Diff** | Compare two traces for regressions |
| **Eval** | Grade a trace on cost and quality |

---

## CLI Reference

```bash
huap pod create <name>      # Create a new pod from template
huap pod validate <name>    # Validate pod contract
huap pod list               # List configured pods

huap trace run <pod> <graph>   # Run and record trace
huap trace view <file>         # View trace events
huap trace replay <file>       # Replay with stubs
huap trace diff <a> <b>        # Compare traces

huap eval trace <file>      # Evaluate single trace
huap eval run <suite>       # Evaluate suite of traces
huap eval init              # Create budget config
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required (live mode) |
| `HUAP_LLM_MODE` | Set to `stub` for testing | Live |
| `HUAP_TRACE_REDACT_LLM` | Redact LLM content | `false` |

---

## Repository Layout

```
huap-core/
├── packages/
│   └── hu-core/          # Core library (pip installable)
├── examples/
│   ├── pods/             # Reference pod implementations
│   │   ├── hello-pod/    # Minimal deterministic example
│   │   ├── llm-pod/      # LLM integration example
│   │   └── memory-pod/   # State management example
│   └── graphs/           # Example workflow definitions
└── suites/
    └── smoke/            # CI baseline traces
```

---

## Example Pods

See `/examples/pods/` for reference implementations:

- **hello-pod** - Minimal deterministic tools (echo, add, normalize)
- **llm-pod** - LLM integration with stub mode (summarize, classify)
- **memory-pod** - State management patterns (get, put, list)

---

## Documentation

- [Getting Started](GETTING_STARTED.md) - Full tutorial
- [Concepts](CONCEPTS.md) - Core architecture
- [Pod Authoring](POD_AUTHORING.md) - Building pods
- [Trace Guide](TRACE_GUIDE.md) - Trace format & replay
- [Contributing](CONTRIBUTING.md) - How to contribute

---

## License

MIT License - See [LICENSE](LICENSE)

---

**HUAP Core v0.1.0b1**
