
<p align="center">
  <img src="HUAP-logo.png" alt="HUAP-Logo" width="700"/>
  <br/>
  <strong>HUman Agentic Platform</strong>
  <br/>
  <em>Trace-first primitives for deterministic, testable agents</em>
</p>

**Trace-first Agent CI + Specialist Squad Orchestrator.**

> "Keep your framework. HUAP makes it reproducible, diffable, and CI-gated."

HUAP Core provides the foundational toolkit for building AI agent systems that are:

- 🧾 **Traceable** — every action recorded as replayable JSONL events
- 🔁 **Deterministic** — stub mode + replay verification for reproducible testing
- 🧪 **Evaluatable** — cost/quality grading to gate regressions in CI
- 🤖 **Squad-ready** — specialist model router picks the right model for each task
- 🔌 **Framework-agnostic** — adapters for CrewAI, LangChain, or wrap any script
- 🚦 **Human-gated** — pause, review, and approve agent actions via an inbox
- 🧩 **Pluggable** — plugin SDK for memory backends, tool packs, and providers

---

## 🚀 Quick Start (60 seconds)

```bash
# Install from source (not yet on PyPI)
pip install -e packages/hu-core

# Option A: Create a full workspace (recommended)
huap init demo && cd demo
HUAP_LLM_MODE=stub huap trace run hello graphs/hello.yaml --out traces/hello.jsonl

# Option B: Create a single pod
huap pod create hello --description "My first agent"
HUAP_LLM_MODE=stub huap trace run hello hu-hello/hu_hello/hello.yaml --out traces/hello.jsonl

# View, replay, evaluate
huap trace view traces/hello.jsonl
huap trace replay traces/hello.jsonl --mode exec --verify
huap eval trace traces/hello.jsonl
```

---

## 🧭 Golden Path (5 Minutes)

### 1) Initialize a workspace
```bash
huap init myproject && cd myproject
```
Creates: `pods/`, `graphs/`, `traces/`, `suites/`, `budgets/`, `.env.example`, and a runnable hello workflow.

### 2) Run with tracing (stub mode)
```bash
export HUAP_LLM_MODE=stub
huap trace run hello graphs/hello.yaml --out traces/hello.jsonl
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
huap trace run hello graphs/hello.yaml --out traces/hello_v2.jsonl
huap trace diff traces/hello.jsonl traces/hello_v2.jsonl
```

### 6) Generate an HTML report
```bash
huap trace report traces/hello.jsonl --out reports/hello.html
```

### 7) Wrap any existing script
```bash
huap trace wrap --out traces/wrapped.jsonl -- python my_agent.py
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

### Workflow YAML Spec

HUAP currently executes the **`nodes[]` + `edges[]`** YAML spec.
Each node has a `run:` field pointing to an importable Python function:

```yaml
nodes:
  - name: start
    run: my_pod.nodes.start_node
  - name: greet
    run: my_pod.nodes.greet_node

edges:
  - from: start
    to: greet
  - from: greet
    to: null
```

> An experimental DSL (`type: entry/action/branch` with `${state...}`) lives in
> `examples/graphs/incubator/` — it is **not executed** by the current engine.

---

## 🛠 CLI Reference

```bash
# Workspace
huap init <name>                 # Create a runnable workspace with hello workflow

# Pod management
huap pod create <name>           # Create a new pod from template
huap pod validate <name>         # Validate pod contract
huap pod list                    # List configured pods

# Tracing
huap trace run <pod> <graph>     # Run and record trace
huap trace view <file>           # View trace events
huap trace replay <file>         # Replay with stubs
huap trace diff <a> <b>          # Compare traces
huap trace wrap -- <cmd>         # Wrap any command as a trace
huap trace report <file>         # Generate standalone HTML report
huap trace validate <file>       # Validate trace JSONL schema

# Evaluation
huap eval trace <file>           # Evaluate single trace
huap eval run <suite>            # Evaluate suite of traces
huap eval init                   # Create budget config

# Model Router (Specialist Squad)
huap models init                 # Create models.yaml + router.yaml
huap models list                 # List registered models
huap models explain              # Explain router decision

# Agent CI
huap ci init                     # Create CI config (GH Actions + budgets + suites)
huap ci run <suite>              # Run suite, diff vs golden, evaluate budgets
huap ci check <suite>            # Full CI check (replay + eval)
huap ci status                   # Show last CI run status

# Human Gates / Inbox
huap inbox list                  # List pending gate requests
huap inbox show <gate_id>        # Show gate details
huap inbox approve <gate_id>     # Approve a pending gate
huap inbox reject  <gate_id>     # Reject a pending gate
huap inbox edit    <gate_id>     # Edit params via JSON patch and approve

# Watch (live tail)
huap watch <trace>               # Live-tail a trace file (issues, gates, budget)

# Plugins
huap plugins init                # Create starter plugins.yaml
huap plugins list                # List registered plugins
```

---

## 🤖 Specialist Squad (Model Router)

HUAP's model router assigns the right model to each task — local-first, cost-aware, and fully deterministic.

```bash
huap models init
huap models list
huap models explain --capability chat --privacy local
```

| Feature | Description |
|---|---|
| **Model Registry** | Declare models with capabilities, privacy, and cost (`config/models.yaml`) |
| **Rule-based Router** | Ordered policy rules; first match wins (`config/router.yaml`) |
| **Providers** | Stub (no deps), Ollama (stdlib), OpenAI (optional) |
| **Explain** | Full transparency on every routing decision |
| **Trace Integration** | Router decisions emitted as `policy_check` trace events |

Enable with: `HUAP_ROUTER_ENABLED=1`

---

## 🔌 Framework Adapters

Keep your existing framework — HUAP makes it traceable.

**CrewAI (manual instrumentation):**
```python
from hu_core.adapters.crewai import huap_trace_crewai

with huap_trace_crewai(out="traces/crewai.jsonl", run_name="demo") as tracer:
    tracer.on_agent_step("researcher", "Find info about AI")
    tracer.on_llm_request("gpt-4o", [{"role": "user", "content": "..."}])
    tracer.on_llm_response("gpt-4o", "...", usage={"total_tokens": 50})
    crew.kickoff()
```
> CrewAI has no public callback API, so events must be added manually.
> The trace is still fully compatible with replay, diff, eval, and CI.

**LangChain / LangGraph:**
```python
from hu_core.adapters.langchain import HuapCallbackHandler

handler = HuapCallbackHandler(out="traces/langchain.jsonl")
chain.invoke({"input": "hello"}, config={"callbacks": [handler]})
handler.flush()
```

**Any script:**
```bash
huap trace wrap --out traces/agent.jsonl -- python my_agent.py
```

All adapters produce standard HUAP traces compatible with replay, diff, eval, and CI.

---

## 🧰 Safe Batteries

Two safe-by-default tools for agent workflows:

| Tool | Description |
|---|---|
| `http_fetch_safe` | HTTP GET with domain allowlist, timeout, size cap, content-type filter |
| `fs_sandbox` | File I/O confined to a root directory — no path traversal |

---

## 🚦 Human Gates & Inbox

Agents can pause at designated **human gates** — checkpoints that require human review before the workflow continues. Pending gates land in an inbox where a human can approve, reject, or edit parameters.

**Flow:** node raises gate → request written to `.huap/inbox/` → human decides via CLI → workflow resumes with the decision.

```bash
huap inbox list                             # See pending gates
huap inbox show <gate_id>                   # View gate details + context
huap inbox approve <gate_id> --note "LGTM"  # Approve and resume
huap inbox reject  <gate_id> --note "Too expensive"
huap inbox edit    <gate_id> --json patch.json  # Edit params and approve
```

Live-tail a trace to watch gates, issues, and budget warnings in real time:

```bash
huap watch traces/run.jsonl
huap watch traces/run.jsonl --only issues,gates
```

---

## 🧩 Plugins & Memory

HUAP's plugin SDK lets you extend the platform without bloating core.

```bash
huap plugins init           # Create config/plugins.yaml
huap plugins list           # Show registered plugins + status
```

### MemoryPort (retain / recall / reflect)

The `MemoryPort` interface lets agents persist and retrieve knowledge across runs. Implementations are loaded as plugins.

| Plugin | Package | Description |
|---|---|---|
| `memory_hindsight` | `hu-plugins-hindsight` | Hindsight memory backend (retain/recall/reflect) |
| `toolpack_cmp` | `hu-plugins-cmp` | Commonplace tool pack (capture/link/search notes) |

### Memory Tools

Built-in `memory_tools` (`hu_core.tools.memory_tools`) give nodes access to `retain`, `recall`, and `reflect` operations. An **ingest policy** (`hu_core.policies`) controls what gets stored automatically.

Install optional packages (from source):
```bash
pip install -e packages/hu-plugins-hindsight   # Memory backend
pip install -e packages/hu-plugins-cmp         # Commonplace tool pack
```

---

## 🔐 Environment Variables

| Variable | Description | Default |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key | Required (live mode) |
| `HUAP_LLM_MODE` | Set to `stub` for testing | `live` |
| `HUAP_ROUTER_ENABLED` | Enable model router | `0` |
| `HUAP_MODEL_REGISTRY_PATH` | Path to models.yaml | built-in defaults |
| `HUAP_ROUTER_POLICY_PATH` | Path to router.yaml | no rules |
| `HUAP_PRIVACY` | Privacy constraint (`local` \| `cloud_ok`) | `cloud_ok` |
| `HUAP_TRACE_REDACT_LLM` | Redact LLM content | `false` |
| `HUAP_PLUGINS_PATH` | Path to plugins.yaml | `config/plugins.yaml` |

---

## 🗂 Repository Layout

```
huap-core/
├── packages/
│   ├── hu-core/              # Core library (pip installable)
│   │   └── hu_core/
│   │       ├── cli/           # CLI commands (init, trace, eval, models, ci, inbox, watch, plugins)
│   │       ├── services/      # LLM client, model registry, router, providers
│   │       ├── trace/         # Trace recording, replay, diff, wrap, HTML report
│   │       ├── eval/          # Evaluation engine (budgets, grading)
│   │       ├── ci/            # CI runner (suite execution, diff + eval gating)
│   │       ├── adapters/      # CrewAI + LangChain adapters
│   │       ├── tools/         # Tool system + safe batteries + memory tools
│   │       ├── runtime/       # Human gates (gate → inbox → decide → resume)
│   │       ├── plugins/       # Plugin SDK + registry
│   │       ├── ports/         # MemoryPort interface
│   │       ├── policies/      # Ingest policy for memory
│   │       └── orchestrator/  # Workflow graph execution
│   ├── hu-plugins-hindsight/  # Hindsight memory backend (optional)
│   └── hu-plugins-cmp/        # Commonplace tool pack (optional)
├── examples/
│   ├── pods/                  # Reference pod implementations
│   │   ├── hello-pod/         # Minimal deterministic example
│   │   ├── llm-pod/           # LLM integration example
│   │   ├── memory-pod/        # State management example
│   │   ├── squad_ecom/        # Specialist squad demo (6 nodes)
│   │   ├── human_gate_demo/   # Human gate + inbox workflow
│   │   └── tool_learning/     # Tool learning with memory
│   ├── graphs/                # Runnable workflow definitions (nodes[] + edges[])
│   │   └── incubator/         # Experimental DSL (not executed)
│   ├── adapters/              # CrewAI + LangChain demo scripts
│   └── memory/                # Memory / Hindsight demo scripts
└── suites/
    └── smoke/                 # CI baseline traces
```

---

## 🧪 Example Pods

See `examples/pods/` for reference implementations:

- 👋 **hello-pod** — minimal deterministic tools (echo, add, normalize)
- 🧠 **llm-pod** — LLM integration with stub mode (summarize, classify)
- 🗃️ **memory-pod** — state management patterns (get, put, list)
- 🛒 **squad_ecom** — specialist squad demo with 6 nodes (SAM, VLM, MoE, LAM, SLM, LLM)
- 🚦 **human_gate_demo** — human gate + inbox approval workflow
- 🧠 **tool_learning** — tool learning with memory retain/recall

### Run the Squad Demo

```bash
HUAP_ROUTER_ENABLED=1 HUAP_LLM_MODE=stub \
  huap trace run squad_ecom examples/graphs/squad_ecom.yaml --out traces/squad_ecom.jsonl

huap trace report traces/squad_ecom.jsonl --out reports/squad_ecom.html
```

---

## 📚 Documentation

- [Getting Started](GETTING_STARTED.md) — full tutorial
- [Conformance](CONFORMANCE.md) — interface & schema contracts

> Previous guides (Concepts, Pod Authoring, Trace Guide, Contributing), the mini-book, and recipes
> have been archived locally and are no longer shipped with the repo.

---

## 🗺️ What's Next

Areas for future work:

- **More adapters** — LlamaIndex, AutoGen, Semantic Kernel
- **Plugin ecosystem** — community memory backends, tool packs, providers
- **Web UI for inbox** — browser-based gate review and approval
- **More memory backends** — vector stores, SQLite, cloud-hosted
- **Trace schema formalization** — JSONSchema for events, versioned backwards compatibility

If you want to work on one of these, open an issue with the prefix **[RFC]**, **[Adapter]**, **[Plugin]**, or **[Memory]**.

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

**HUAP Core v0.1.0b1 — Public Beta**
