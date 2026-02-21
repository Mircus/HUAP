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

## Ship Sprint ✅ COMPLETE

### S1. Fix pod template & verify end-to-end flow ✅
Fixed POD_TEMPLATE indentation — node functions at module level, class methods inside class.
Verified: `pod create → install → trace run → success (Grade A)`.

### S2. Makefile ✅
`Makefile` with install, test, lint, smoke, demo, ci, clean targets.

### S3. PyPI publish — ⏳ BLOCKED on credentials
Build artifacts ready (`sdist + wheel`). `pyproject.toml` fixed (SPDX license, README).
**Next:** Mirco gets PyPI credentials → `twine upload dist/*` → verify clean install.

### S4. CHANGELOG.md ✅
Created for v0.1.0b1.

### S5. GETTING_STARTED.md refresh ✅
Rewritten to match current CLI and demo flow.

---

## P1 — Next up (Monday)

### 1.1 PyPI publish
**Status:** Blocked — waiting for Mirco's PyPI credentials/token.
- [ ] `twine upload dist/*`
- [ ] Verify `pip install huap-core && huap demo` from clean venv

### 1.2 Real Hindsight memory backend
**Status:** Not started
**Why:** Current `HindsightProvider` is a stub (in-memory only, `connect()` returns False).
`MemoryPort` interface is solid; needs a real persistent implementation.
- [ ] Decide backend: SQLite? vector store? filesystem?
- [ ] Implement real `retain/recall/reflect` with persistence
- [ ] Tests for persistence across sessions

---

## P2 — Post-launch (ecosystem & growth)

### 2.1 `--pythonpath` flag on `trace run`
### 2.2 Improve eval UX (`--fail-on` thresholds, better reports)
### 2.3 More framework adapters (LlamaIndex, AutoGen, Semantic Kernel)
### 2.4 Policy pipeline (deny tool calls, `huap policy explain`)
### 2.5 Web UI for inbox
### 2.6 More memory backends (vector stores, cloud-hosted)

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
- [x] `huap pod create → trace run` works end-to-end
- [x] Makefile for contributors
- [x] CHANGELOG.md
- [x] GETTING_STARTED.md matches current CLI
- [ ] On PyPI (`pip install huap-core`) — blocked on credentials
