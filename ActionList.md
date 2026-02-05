# HUAP Public — Claude-Code Action List (Next Features, Still Public)

This action list focuses on **adoption** and making HUAP Public **actually runnable** with a clean **golden path**.  
It stays **100% Public** (no Pro-only features).

---

## P0 — Make HUAP Public runnable (golden path + repo consistency)

### 0.1 Fix the Pod scaffolder so generated pods run immediately
**Where:** `packages/hu-core/hu_core/cli/main.py`

- [ ] **Fix dependency name** in `PYPROJECT_TEMPLATE`  
  **Current:** `dependencies = ["hu-core"]`  
  **Correct:** `dependencies = ["huap-core"]`
- [ ] Replace the current `WORKFLOW_TEMPLATE` (the “type/action/next” format) with the **actual graph format** supported by `load_graph_from_yaml()`:
  - nodes as a **list** with `name` + `run`
  - edges as a **list** with `from` + `to` (+ optional `condition`)
- [ ] Generate a `nodes.py` in the new pod package with stub async funcs used by the YAML graph:
  - `start(state)`, `process(state)`, `analyze(state)`, `recommend(state)`
- [ ] Write the graph file in a predictable place and reference the node funcs correctly:
  - `hu-<name>/hu_<name>/<name>.yaml`
  - run paths like `hu_<name>.nodes.process`
- [ ] Update the generated tests to match the real tool interface (see 0.3).

**Acceptance:** after `huap pod create hello`, you can run:
- `HUAP_LLM_MODE=stub huap trace run hello hu-hello/hu_hello/hello.yaml --out traces/hello.jsonl`
…and it **imports nodes successfully** and writes a trace.

---

### 0.2 Make locally-created pods importable without forcing users to “pip install -e”
**Where:** `packages/hu-core/hu_core/trace/runner.py` (or `orchestrator/executor.py`)

- [ ] Before loading the YAML graph, **auto-inject an import root into `sys.path`** based on `graph_path`.
  - Heuristic that works for your scaffolded layout:
    - if `graph_path.parent` contains `__init__.py`, add `graph_path.parent.parent` to `sys.path`
- [ ] Add `--pythonpath` option to `huap trace run` (repeatable) to explicitly add extra import roots.

**Acceptance:** running a graph from a freshly created pod works from the directory where the pod folder exists.

---

### 0.3 Fix the tool interface mismatch in docs + examples
Right now: docs/examples often show tools returning `ToolResult`, but `BaseTool.execute()` returns `Dict` and the registry wraps it.

**Where:**
- Docs: `CONCEPTS.md`, `POD_AUTHORING.md`, `GETTING_STARTED.md`
- Examples: `examples/pods/*`

- [ ] Update docs to show the correct pattern:
  - `BaseTool.spec -> ToolSpec`
  - `BaseTool.execute(...) -> dict`
  - users get `ToolResult` from `ToolRegistry.execute(...)`
- [ ] Either:
  - (A) refactor `examples/pods/*` to the correct interface, **or**
  - (B) clearly label them as legacy and stop referencing them in the main README (recommended: A).

**Acceptance:** no “ToolResult return type” examples remain for `BaseTool.execute`.

---

### 0.4 Fix the “examples” so they actually run
Currently `examples/graphs/*.yaml` are not compatible with the graph loader and the dotted imports reference a non-package `examples`.

**Where:** `examples/`, `packages/hu-core/hu_core/examples/`

- [ ] Pick one of these approaches and make it consistent:
  1) **Make `examples/` importable** (add `examples/__init__.py`, `examples/pods/__init__.py`) and ensure graph format matches loader  
  **or**  
  2) Move runnable example node funcs under `hu_core.examples` and point YAML run paths to `hu_core.examples.nodes.*`
- [ ] Convert all `examples/graphs/*.yaml` to the supported schema:
  ```yaml
  nodes:
    - name: echo
      run: hu_core.examples.nodes.echo_node
  edges:
    - from: echo
      to: end
  ```
- [ ] Ensure at least one example graph is used as the canonical “Hello World”.

**Acceptance:** `HUAP_LLM_MODE=stub huap trace run echo examples/graphs/hello.yaml ...` works inside the repo.

---

### 0.5 Fix missing/phantom files referenced by docs (smoke suite + config)
**Where:** `suites/smoke/README.md`, `packages/hu-core/hu_core/services/config_service.py`, CLI pod commands

- [ ] Add the missing baseline trace file referenced in `suites/smoke/README.md` (e.g. `hello_baseline.jsonl`)  
  OR update the README so it doesn’t claim it exists.
- [ ] `config_service.py` currently defaults to `.../config/config.yaml` which does not exist.
  - Change default to `~/.huap/config.yaml` (or `.huap/config.yaml` in cwd), and **return `{}` if missing** instead of crashing.
- [ ] `huap pod list` should not hard-fail when no config exists:
  - if missing, print “no config found” + suggest `huap init` (see P1) and/or scan the local directory.

**Acceptance:** running core CLI commands doesn’t error due to absent config files.

---

### 0.6 Add a minimal CI so public users trust the repo
**Where:** add `.github/workflows/ci.yml`

- [ ] `pip install -e packages/hu-core[dev]`
- [ ] `ruff` (or at least `python -m compileall`)
- [ ] `pytest` (see P0 tests below)
- [ ] run a stub trace + replay verify:
  - `HUAP_LLM_MODE=stub huap trace run ...`
  - `huap trace replay ... --verify`

---

### 0.7 Add real tests for core invariants (small but high leverage)
**Where:** create `packages/hu-core/tests/`

- [ ] Test graph parsing for the supported YAML schema
- [ ] Test `huap pod create` output structure + that the generated YAML imports generated `nodes.py`
- [ ] Test `run_pod_graph(...HUAP_LLM_MODE=stub...)` creates a JSONL trace
- [ ] Test replay `--verify` on `examples/traces/golden_hello.jsonl`

---

## P1 — Adoption boosters (still public)

### 1.1 Add `huap init` to create a tiny “HUAP project workspace”
**Where:** `packages/hu-core/hu_core/cli/main.py`

Creates:
- `.huap/config.yaml` (local) or `~/.huap/config.yaml`
- `pods/`, `traces/`, `graphs/`, `suites/smoke/`
- `.env.example` with `HUAP_LLM_MODE=stub`, `OPENAI_MODEL=...`

**Acceptance:** a new user can do:
- `pip install huap-core`
- `huap init myproj && cd myproj`
- `huap pod create hello`
- `HUAP_LLM_MODE=stub huap trace run ...`

---

### 1.2 Improve trace UX: “stats”, “validate”, “report”
**Where:** `packages/hu-core/hu_core/cli/trace_cmds.py`, `hu_core/trace/*`

- [ ] `huap trace stats <trace.jsonl>`: totals (events, tokens, usd, tool errors, policy violations, runtime)
- [ ] `huap trace validate <trace.jsonl>`: schema + required event checks
- [ ] `huap trace report <trace.jsonl> --out report.html` (simple standalone HTML)

---

### 1.3 Publish a canonical “smoke suite” that actually runs
**Where:** `suites/smoke/`

- [ ] Include at least **one** baseline trace (`hello_baseline.jsonl`)
- [ ] Add a tiny `Makefile` or `justfile` with:
  - `make smoke-record`
  - `make smoke-replay`
  - `make smoke-eval`

---

### 1.4 Make evaluation feel “real” for users
**Where:** `hu_core/eval/*`, `cli/eval_cmds.py`

- [ ] Add a default suite runner path convention: `huap eval run suites/smoke`
- [ ] Improve markdown report formatting (top summary + per-trace table + issues list)
- [ ] Add `--fail-on` thresholds (policy violations, tool errors, max USD, max tokens)

---

### 1.5 Remove vertical contamination from core (keep public = generic)
**Where:** `packages/hu-core/hu_core/services/llm_client.py`

- [ ] Move SOMA-specific functions (`generate_workout_plan`, `analyze_health_data`) out of core:
  - either into `examples/` or into a separate public pod package later
- [ ] Keep `LLMClient` generic: chat completion, usage capture, stub mode, tracing hooks

---

## P2 — Ecosystem hooks that boost adoption (still public, optional deps)

### 2.1 Add a LangChain adapter (lowest-friction adoption hook)
**Where:** `packages/hu-core/hu_core/adapters/langchain.py` (or new `packages/huap-adapters/`)

- [ ] Provide a callback/handler that emits HUAP trace events:
  - `llm_request/llm_response`
  - `tool_call/tool_result`
- [ ] Minimal example script + doc page: “Instrument LangChain in 10 lines”

---

### 2.2 Add a CrewAI adapter (adoption magnet)
Same concept:
- capture agent step events, tool calls, model calls into HUAP trace

---

### 2.3 Harden policies (public-safe defaults)
**Where:** `hu_core/policy/*`, `tools/builtin/http_fetch.py`

- [ ] Implement a real `Policy` pipeline that can deny tool calls based on:
  - capabilities
  - domain allowlists
  - max response size / timeout
- [ ] Make `http_fetch` enforce:
  - max bytes
  - timeout
  - allowlist via config
- [ ] Add `huap policy explain` (prints active allow/deny reasons)

---

### 2.4 Improve edge condition evaluation safely
**Where:** `hu_core/orchestrator/graph.py`

- [ ] Replace raw `eval(..., {"__builtins__": {}}, state)` with a tiny safe expression evaluator:
  - allow `len`, `min`, `max`, basic ops, comparisons
  - disallow attribute access / calls except whitelisted
- [ ] Document it in `CONCEPTS.md`

---

## Definition of Done — HUAP Public v0.1.x (adoption-ready)

When P0 + parts of P1 are done, the repo should satisfy:

- [ ] `pip install huap-core` works
- [ ] `huap init && huap pod create && HUAP_LLM_MODE=stub huap trace run ...` works **without** extra sys.path hacks
- [ ] examples and docs match the actual runtime format
- [ ] smoke suite contains at least one real baseline trace
- [ ] CI runs stub trace + replay verify + pytest
