


# HUAP Core 🧠⚙️

<p align="center">
  <img src="HUAP-logo.png" alt="HUAP-Logo" width="700"/>
  <br/>
  <strong>HUman Agentic Platform</strong>
  <br/>
  <em>Trace-first primitives for deterministic, testable agents</em>
</p>

**Build deterministic, traceable AI agents with replay, diff, and evaluation.**

HUAP Core provides the foundational toolkit for building AI agent systems that are:

- 🧾 **Traceable** — every action recorded as replayable events  
- 🔁 **Deterministic** — stub mode + replay verification for reproducible testing  
- 🧪 **Evaluatable** — cost/quality grading to gate regressions in CI  

---

## 🚀 Quick Start (PyPI)

```bash
pip install huap-core

# Create a pod (generates hu-<name>/hu_<name>/<name>.yaml)
huap pod create hello --description "My first agent"

# Run with tracing (stub mode - no API key needed)
export HUAP_LLM_MODE=stub
huap trace run hello hu-hello/hu_hello/hello.yaml --out traces/hello.jsonl

# Replay (deterministic verification)
huap trace replay traces/hello.jsonl --mode exec --verify

# Evaluate (budgets/grades)
huap eval trace traces/hello.jsonl
```

---

## 🧭 Golden Path (5 Minutes)

### 1) Create a pod
```bash
huap pod create hello --description "My first agent"
```

### 2) Run with tracing (stub mode)
```bash
export HUAP_LLM_MODE=stub
huap trace run hello hu-hello/hu_hello/hello.yaml --out traces/hello.jsonl
```

### 3) View the trace
```bash
huap trace view traces/hello.jsonl
```

### 4) Replay & verify (deterministic)
```bash
huap trace replay traces/hello.jsonl --mode exec --verify
```

### 5) Diff two runs (detect drift)
```bash
huap trace run hello hu-hello/hu_hello/hello.yaml --out traces/hello_v2.jsonl
huap trace diff traces/hello.jsonl traces/hello_v2.jsonl
```

---

## 🧩 Key Concepts

| Concept | Meaning |
|---|---|
| **Pod** | A self-contained agent: tools + workflows |
| **Trace** | JSONL event stream of the full run |
| **Replay** | Re-run deterministically using recorded events (or stubs) |
| **Diff** | Compare two traces for behavioral/cost regressions |
| **Eval** | Grade a trace against budgets/constraints |

---

## 🛠 CLI Reference

```bash
huap pod create <name>      # Create a new pod from template
huap pod validate <name>    # Validate pod contract
huap pod list               # List configured pods

huap trace run <pod> <graph>     # Run and record trace (graph is a YAML path)
huap trace view <file>           # View trace events
huap trace replay <file>         # Replay with stubs
huap trace diff <a> <b>          # Compare traces

huap eval trace <file>           # Evaluate single trace
huap eval run <suite>            # Evaluate suite of traces
huap eval init                   # Create budget config
```

---

## 🔐 Environment Variables

| Variable | Description | Default |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key | Required (live mode) |
| `HUAP_LLM_MODE` | Set to `stub` for testing | Live |
| `HUAP_TRACE_REDACT_LLM` | Redact LLM content | `false` |

---

## 🗂 Repository Layout

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

## 🧪 Example Pods

See `examples/pods/` for reference implementations:

- 👋 **hello-pod** — minimal deterministic tools (echo, add, normalize)  
- 🧠 **llm-pod** — LLM integration with stub mode (summarize, classify)  
- 🗃️ **memory-pod** — state management patterns (get, put, list)  

---

## 📚 Documentation

- [Getting Started](GETTING_STARTED.md) — full tutorial
- [Concepts](CONCEPTS.md) — core architecture
- [Pod Authoring](POD_AUTHORING.md) — building pods
- [Trace Guide](TRACE_GUIDE.md) — trace format & replay
- [Contributing](CONTRIBUTING.md) — how to contribute

---

## 🗺️ Next Steps



### 🔌 1) Adapter layer for popular agent frameworks
Goal: let people keep their existing framework but get HUAP’s trace/replay/diff/eval.

- **CrewAI adapter**: wrap CrewAI agent runs into HUAP traces  
- **LangChain adapter**: instrument chains/tools as HUAP events  
- **LlamaIndex adapter**: capture retrieval + synthesis steps as trace nodes  
- **AutoGen / Semantic Kernel adapters**: map multi-agent turns to trace spans  

Suggested shape:
- `packages/hu-adapters/huap_crewai/`
- `packages/hu-adapters/huap_langchain/`
- common interface: `Adapter.run(...) -> trace.jsonl`

### 🧾 2) Formalize the trace schema
- JSONSchema for events (versioned)
- canonical “event types” registry
- backwards compatibility rules (so old traces keep replaying)

### 🧪 3) More evaluation suites & golden traces
- curated “smoke” suite for CI
- example “budget packs” for common use cases (offline, cheap, fast, etc.)
- golden baselines in `examples/traces/` (small + deterministic)

### 🔭 4) Better trace UX (still open-source)
- richer `huap trace view` summaries
- optional HTML report output for `trace diff` / `eval`
- lightweight local UI to browse traces (even a static viewer)

### 🧰 5) More batteries-included tools (safe by default)
- HTTP tool with allowlist + rate limits
- filesystem tool with sandbox root
- structured redaction helpers

If you want to work on one of these, open an issue with the prefix **[RFC]**, **[Adapter]**, **[Trace]**, or **[Eval]**.

---

## 🤝 Contributing

We want contributors.

### Ways to contribute
- 🐛 bug fixes and test coverage
- 🔌 framework adapters (CrewAI / LangChain / etc.)
- 🧾 trace schema + compatibility tooling
- 🧪 evaluation suites + golden baselines
- 📝 docs and runnable examples

### Dev setup
```bash
# From repo root
pip install -e packages/hu-core[dev]

pytest -q
ruff check .
```

### PR hygiene (what makes reviews fast)
- keep changes small and well-scoped
- add/adjust a test or golden trace when behavior changes
- include a short note on replay/eval impact (tokens/tool calls)

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

**HUAP Core v0.1.0b1**
