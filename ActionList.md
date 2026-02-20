# HUAP — Action List (post-audit, Feb 2026)

Current state: **88 tests passing**, all P0 items complete, SOMA-free core, CI added, smoke baseline committed.
This list covers everything remaining to make the repo **adoption-ready**.

---

## P0 — Core hygiene ✅ COMPLETE

### 0.1 Remove SOMA contamination from core library ✅
**Status:** Done
Removed all SOMA/workout/health_data references from 14 files across core library.
`grep -ri "soma\|workout\|health_data" packages/hu-core/hu_core/` returns 0 matches.

### 0.2 Add GitHub Actions CI ✅
**Status:** Done
Created `.github/workflows/ci.yml` — Python 3.10/3.11/3.12 matrix, ruff, pytest, stub smoke trace.

### 0.3 Publish to PyPI (or fix all "not yet on PyPI" claims)
**Status:** Not started
**Why:** README says "Install from source (not yet on PyPI)" — either publish or make the source install seamless.

- [ ] Option A: `python -m build && twine upload` to PyPI (preferred)
- [ ] Option B: If not ready, ensure `pip install -e packages/hu-core` is the only install instruction everywhere

**Acceptance:** `pip install huap-core` works OR all docs consistently say "install from source".

### 0.4 Add missing tests for core paths ✅
**Status:** Done (88 tests total, was 76)
Added `test_graph_executor.py` with 12 tests covering GraphRunner, YAML loading, PodExecutor, hello.yaml end-to-end.

### 0.5 Merge duplicate hello graphs ✅
**Status:** Done
Deleted `hello_workflow.yaml` (required pip install), kept `hello.yaml` (works from repo root). Updated all references.

### 0.6 Generate and commit smoke baseline trace ✅
**Status:** Done
`suites/smoke/hello_baseline.jsonl` committed. Replay exec + verify passes.

### Bug fixes (discovered during P0 work)
- **graph.py:** Skip edges with `null` targets (terminal nodes) instead of failing validation
- **replay.py:** Fixed exec mode — was passing `graph=` instead of `graph_path=`, added graph path resolution
- **trace schema:** Added `graph_path` field to `RunStartData` so replays can find the original graph file

---

## P1 — Adoption polish (makes first experience smooth)

### 1.1 Pod scaffolder should generate importable node functions
**Status:** Partially done — `start_node`, `process_node`, `end_node` added to POD_TEMPLATE
**Why:** The WORKFLOW_TEMPLATE references `hu_{name}.pod.start_node` etc, and those functions now exist in the template. But they're inside the `POD_TEMPLATE` string (the class file), not in a separate `nodes.py`. This works but is unusual.

- [ ] Consider generating a separate `nodes.py` with the node functions for cleaner separation
- [ ] Or verify the current approach (functions in `pod.py`) works end-to-end with `huap trace run`

**Acceptance:** `huap pod create hello && HUAP_LLM_MODE=stub huap trace run hello hu-hello/hu_hello/hello.yaml --out /tmp/test.jsonl` works.

---

### 1.2 Safe edge condition evaluator
**Status:** Not started
**Why:** `graph.py:47` uses `eval(condition, {"__builtins__": {}}, state)` — this is exploitable via `__import__` tricks.

- [ ] Replace with `ast.literal_eval` or a tiny safe expression parser (comparisons, `len`, `min`, `max`, `in`)
- [ ] Disallow attribute access, function calls (except whitelisted), `__dunder__` access

**Where:** `packages/hu-core/hu_core/orchestrator/graph.py`

---

### 1.3 Add `--pythonpath` to `huap trace run`
**Status:** Not started
**Why:** `_import_function` in `graph.py` already injects `cwd` into `sys.path`, but users creating pods outside cwd can't run them without manual `PYTHONPATH` hacks.

- [ ] Add `--pythonpath` / `-P` repeatable option to `trace run`
- [ ] Inject each path into `sys.path` before graph loading

**Where:** `cli/trace_cmds.py`

---

### 1.4 Improve eval UX
**Status:** Commands exist but experience is thin

- [ ] `huap eval run suites/smoke` — default convention for suite path
- [ ] `--fail-on` thresholds (max tokens, max USD, max tool errors)
- [ ] Better markdown report (summary table + per-trace details + issues list)

---

### 1.5 Add a Makefile / justfile for common workflows
**Status:** Not started
**Why:** Makes onboarding faster for contributors.

```makefile
install:    pip install -e packages/hu-core[dev]
test:       pytest packages/hu-core/tests/ -q
lint:       ruff check packages/hu-core/
smoke:      HUAP_LLM_MODE=stub huap trace run hello examples/graphs/hello.yaml --out /tmp/smoke.jsonl
```

---

## P2 — Ecosystem & growth

### 2.1 More framework adapters
- [ ] LlamaIndex adapter
- [ ] AutoGen adapter
- [ ] Semantic Kernel adapter

### 2.2 Policy pipeline
- [ ] Real `Policy` class that can deny tool calls (capabilities, domain allowlists, size/timeout limits)
- [ ] `huap policy explain` CLI command

### 2.3 Web UI for inbox
- [ ] Browser-based gate review and approval (replaces CLI-only workflow)

### 2.4 More memory backends
- [ ] SQLite backend for MemoryPort
- [ ] Vector store backend (FAISS / ChromaDB)

---

## Definition of Done — v0.1.x (adoption-ready)

- [x] Zero SOMA references in core library
- [x] CI workflow added (GitHub Actions)
- [ ] CI badge in README (needs first push to trigger)
- [ ] `huap init && huap pod create hello && HUAP_LLM_MODE=stub huap trace run ...` works end-to-end
- [x] One canonical hello example graph (no duplicates)
- [x] Smoke baseline trace committed and replayable
- [ ] On PyPI or docs consistently say "install from source"
- [x] Tests cover graph loading, executor, pod create, trace run/replay
