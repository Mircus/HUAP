
<p align="center">
  <img src="HUAP-logo.png" alt="HUAP-Logo" width="1000"/>
</p>

<div align="center">

<a href="https://github.com/Mircus/HUAP/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/Mircus/HUAP/ci.yml?branch=main&label=CI&style=for-the-badge" alt="CI"></a>
<a href="https://pypi.org/project/huap-core/"><img src="https://img.shields.io/pypi/v/huap-core?style=for-the-badge&label=PyPI&color=blue" alt="PyPI"></a>
<a href="https://pypi.org/project/huap-core/"><img src="https://img.shields.io/pypi/pyversions/huap-core?style=for-the-badge&label=Python" alt="Python"></a>
<a href="LICENSE"><img src="https://img.shields.io/github/license/Mircus/HUAP?style=for-the-badge&color=purple" alt="License"></a>
<a href="https://colab.research.google.com/github/Mircus/HUAP/blob/main/notebooks/Try_HUAP.ipynb"><img src="https://img.shields.io/badge/Try_it-Open_in_Colab-F9AB00?style=for-the-badge&logo=googlecolab" alt="Open In Colab"></a>

<br/>

**HUman Agentic Platform**
<br/>
*Trace-first primitives for deterministic, testable agents*

</div>

<br/>

<div align="center">
<table>
<tr>
<td align="center">

```
pip install huap-core
```

</td>
</tr>
</table>
</div>

---

### What HUAP is

HUAP is an **open-source Python framework** that adds tracing, replay, evaluation, and CI gating to AI agent systems. You define workflows as YAML graphs, and HUAP records every action as replayable JSONL events — so your agents become deterministic, testable, and diffable. It works with any LLM framework (LangChain, CrewAI, or plain scripts).

### What HUAP is *not*

HUAP is not another agent framework or LLM wrapper. It doesn't replace your stack — it **instruments** it. Think of it as "CI/CD for agents."

### 60-Second Quickstart

```bash
pip install huap-core
huap demo            # generates trace.jsonl + report.html (stub mode, no API keys needed)
huap flagship        # full 5-node pipeline: research → analyze → human gate → synthesize → memorize
```

---

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

## 🚀 3-Minute Wow Path

Six commands, copy-paste from repo root. No API keys needed.

```bash
# 1. Install
pip install huap-core

# 2. Flagship demo — research → analyze → human gate → synthesize → memorize
huap flagship --no-open
# outputs: huap_flagship_demo/trace.jsonl, trace.html, memo.md

# 3. One-liner demo — runs a graph, generates an HTML report, opens it in your browser
huap demo

# 4. Diff two stub runs — proves deterministic replay catches drift
HUAP_LLM_MODE=stub huap trace run hello examples/graphs/hello.yaml --out /tmp/a.jsonl
HUAP_LLM_MODE=stub huap trace run hello examples/graphs/hello.yaml --out /tmp/b.jsonl
huap trace diff /tmp/a.jsonl /tmp/b.jsonl

# 5. CI gate with baseline — runs suite, diffs vs golden, produces HTML report
huap ci run suites/smoke/suite.yaml --html reports/smoke.html

# 6. Shareable HTML artifact — standalone report you can send to anyone
huap trace report /tmp/a.jsonl --out reports/trace.html
```

| Command | What it proves |
|---|---|
| `huap flagship` | Full 5-node pipeline: research, analysis, human gate, synthesis, memory |
| `huap demo` | Full graph → trace → HTML report pipeline works out of the box |
| `huap trace diff` | Two identical stub runs produce zero drift |
| `huap ci run` | Suite runner diffs against golden baselines and gates CI |
| `huap trace report` | Any trace becomes a self-contained, shareable HTML artifact |

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

# Memory
huap memory search <query>       # Keyword search across stored memories
huap memory ingest --from-trace <file>  # Ingest trace events into memory
huap memory stats                # Show memory database statistics

# Flagship demo
huap flagship                    # Full pipeline: research → gate → memo (opens browser)
huap flagship --no-open          # Same, skip browser
huap flagship --with-memory      # Persist findings to SQLite memory
huap flagship --drift            # Inject drift to show diff detection

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

### HindsightProvider (SQLite memory backend)

The `HindsightProvider` gives agents persistent memory via SQLite — zero extra dependencies:

```bash
# Store findings during a flagship run
huap flagship --with-memory --no-open

# Search persisted memories
huap memory search "AI agent"

# View database statistics
huap memory stats

# Ingest any trace into memory
huap memory ingest --from-trace traces/hello.jsonl
```

Memory operations emit trace events, so they appear in HTML reports and can be diffed in CI.

### MemoryPort (retain / recall / reflect)

The `MemoryPort` interface lets agents persist and retrieve knowledge across runs:

| Method | Purpose |
|---|---|
| `retain(key, value)` | Store a finding for future sessions |
| `recall(query, k)` | Retrieve relevant memories by keyword |
| `reflect(user_id, pod)` | Summarize what the agent has learned |

### Memory Tools

Built-in `memory_tools` (`hu_core.tools.memory_tools`) give nodes access to `retain`, `recall`, and `reflect` operations. An **ingest policy** (`hu_core.policies`) controls what gets stored — with automatic **secret redaction** (API keys, tokens, credentials are stripped before storage).

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
HUAP/
├── packages/
│   ├── hu-core/              # Core library (pip install huap-core)
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
│   ├── flagship/              # Full-stack demo (research → gate → memo → memory)
│   ├── pods/                  # Reference pod implementations
│   │   ├── hello-pod/         # Minimal deterministic example
│   │   ├── llm-pod/           # LLM integration example
│   │   ├── memory-pod/        # State management example
│   │   ├── squad_ecom/        # Specialist squad demo (6 nodes)
│   │   ├── human_gate_demo/   # Human gate + inbox workflow
│   │   └── tool_learning/     # Tool learning with memory
│   ├── wrappers/              # Drop-in wrapper examples (LangChain, CrewAI)
│   ├── graphs/                # Runnable workflow definitions (nodes[] + edges[])
│   │   └── incubator/         # Experimental DSL (not executed)
│   ├── adapters/              # CrewAI + LangChain demo scripts
│   └── memory/                # Memory / Hindsight demo scripts
└── suites/
    ├── smoke/                 # Smoke test baseline traces
    └── flagship/              # Flagship demo baseline + suite
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
- **Vector memory backends** — embedding-based semantic search (current: keyword/SQLite)
- **Trace schema formalization** — JSONSchema for events, versioned backwards compatibility

If you want to work on one of these, open an issue with the prefix **[RFC]**, **[Adapter]**, **[Plugin]**, or **[Memory]**.

---

## 🤝 Contributing

We want contributors. See **[CONTRIBUTING.md](CONTRIBUTING.md)** for the full guide — dev setup, workflow, PR guidelines, and architecture reference.

Quick start:

```bash
pip install -e "packages/hu-core[dev]" -e packages/hu-plugins-hindsight
pytest -q && ruff check .
```

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

<p align="center">
  <strong>HUAP Core v0.1.0b1</strong> — <code>pip install huap-core</code>
</p>
