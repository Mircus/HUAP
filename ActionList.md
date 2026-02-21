# HUAP — Action List (Feb 2026)

Current state: **96 tests passing**, CI green (3.10–3.12), safe condition evaluator, `huap demo`, suite runner with HTML reports, README wow path.

---

## P0 — Core hygiene ✅ COMPLETE

### 0.1 Remove SOMA contamination ✅
Removed all SOMA/workout/health_data references from 16 files.

### 0.2 GitHub Actions CI ✅
`.github/workflows/ci.yml` — Python 3.10/3.11/3.12 matrix, ruff, pytest, smoke, golden path, artifact upload.
All jobs green.

### 0.3 PyPI publish
**Status:** Not started — blocked on ship sprint (see below)

### 0.4 Tests ✅
96 tests total (was 76). Graph executor, YAML loading, PodExecutor, condition evaluator, hello e2e.

### 0.5 Merge duplicate hello graphs ✅

### 0.6 Smoke baseline ✅
`suites/smoke/hello_baseline.jsonl` + `suites/smoke/suite.yaml` committed.

### 0.7 Bug fixes ✅
- null edge targets, replay exec graph path, `graph_path` in trace events
- Windows encoding crash, eval stub scoring
- ruff lint errors (all 94 fixed, CI green)

---

## Adoption Sprint ✅ COMPLETE

### Safe condition evaluator ✅
Replaced `eval()` with AST-based `safe_eval_condition()` + `_SafeEvaluator` class.
8 new tests. Zero `eval(` calls in graph.py.

### Real CI workflow ✅
Golden path step (init → run → report → diff → eval) + artifact upload added.

### Suite runner with HTML ✅
- `suites/smoke/suite.yaml` created
- `CIReport.to_html()` method added
- `--html` flag on `huap ci run`

### `huap demo` command ✅
One-liner: runs hello graph in stub mode → generates HTML report → opens browser.

### README "3-Minute Wow Path" ✅
5 copy-paste commands, each with explanation of what it proves.

---

## Ship Sprint — Final Beta Push (in progress)

### S1. Fix pod template & verify end-to-end flow
**Status:** Not started
**Why:** `huap pod create hello && huap trace run ...` must work without manual fixup.
The POD_TEMPLATE has node functions defined at wrong indentation (inside class body string but outside class).

- [ ] Fix POD_TEMPLATE indentation — node functions should be module-level
- [ ] Verify full flow: `pod create → trace run → trace view → eval`

**Acceptance:** `huap pod create test && HUAP_LLM_MODE=stub huap trace run test hu-test/hu_test/test.yaml --out /tmp/test.jsonl` works.

### S2. Makefile
**Status:** Not started

- [ ] Create `Makefile` with: install, test, lint, smoke, demo, ci targets

### S3. PyPI publish
**Status:** Not started
**Why:** `pip install huap-core` is the bar for adoption.

- [ ] `python -m build && twine upload`
- [ ] Verify `pip install huap-core && huap demo` works from clean venv

### S4. CHANGELOG.md
**Status:** Not started

- [ ] Create CHANGELOG.md covering v0.1.0b1

### S5. GETTING_STARTED.md refresh
**Status:** Not started
**Why:** Currently references old patterns; should match the "3-min wow path".

- [ ] Rewrite to match current CLI and demo flow

---

## P2 — Post-launch (ecosystem & growth)

### 2.1 `--pythonpath` flag on `trace run`
### 2.2 Improve eval UX (`--fail-on` thresholds, better reports)
### 2.3 More framework adapters (LlamaIndex, AutoGen, Semantic Kernel)
### 2.4 Policy pipeline (deny tool calls, `huap policy explain`)
### 2.5 Web UI for inbox
### 2.6 More memory backends (SQLite, vector stores)

---

## Definition of Done — v0.1.0b1 (public beta)

- [x] Zero SOMA references in core library
- [x] CI green (GitHub Actions, 3 Python versions)
- [x] CI badge in README
- [x] Safe condition evaluator (no eval)
- [x] `huap demo` one-liner works
- [x] Suite runner with HTML reports
- [x] 96 tests passing
- [x] Smoke baseline committed
- [ ] `huap pod create → trace run` works end-to-end
- [ ] On PyPI (`pip install huap-core`)
- [ ] Makefile for contributors
- [ ] CHANGELOG.md
- [ ] GETTING_STARTED.md matches current CLI
