# HUAP — Action List (Feb 2026)

Current state: **110 tests passing**, CI green (3.10-3.12), safe condition evaluator, `huap demo`, suite runner with HTML reports, README wow path, real SQLite memory backend.

---

## COMPLETED SPRINTS (collapsed)

<details>
<summary>P0 — Core hygiene ✅</summary>

- SOMA decontamination (16 files)
- GitHub Actions CI (3 Python versions, ruff, pytest, smoke, golden path, artifacts)
- 110 tests, ruff clean
- Smoke baseline + suite
- Bug fixes (null edges, replay, Windows encoding, eval scoring)
- Merged duplicate hello graphs
</details>

<details>
<summary>Adoption Sprint ✅</summary>

- Safe condition evaluator (AST-based, 8 tests)
- Real CI workflow (golden path + artifact upload)
- Suite runner with HTML (`CIReport.to_html()`, `--html` flag)
- `huap demo` one-liner
- README "3-Minute Wow Path"
</details>

<details>
<summary>Ship Sprint ✅</summary>

- POD_TEMPLATE fix + end-to-end verified
- Makefile (install, test, lint, smoke, demo, ci, clean)
- PyPI build ready (sdist + wheel)
- CHANGELOG.md
- GETTING_STARTED.md refresh
</details>

<details>
<summary>Hindsight Sprint ✅</summary>

- Real SQLite-backed `HindsightProvider` (was stub)
- Full CRUD, keyword search, episode retrieval, reflect, summarize
- 14 new tests (persistence across sessions verified)
</details>

---

## FINAL WOW SPRINT — Public Beta Release

### Goal
Ship HUAP Public Beta that showcases:
**Agent CI + Flight Recorder + Human Gates + Real Local Memory**

### F1. Flagship demo (`huap demo flagship`)
**Why:** The existing `huap demo` runs hello (trivial). A flagship demo shows the FULL stack: multi-node graph, human gate, memory, drift detection.

- [ ] Create `examples/flagship/` with:
  - Multi-node graph (research → analyze → gate → synthesize → memorize)
  - Node functions using safe tools, human gate, memory retain/recall
- [ ] Add `huap demo flagship` CLI command with flags:
  - `--drift` — inject controlled drift to showcase diff
  - `--with-memory` — use HindsightProvider for persist/retrieve
  - Default: stub mode, no keys needed
- [ ] Artifacts written to `huap_flagship_demo/` in cwd:
  - `trace.jsonl`, `trace.html`
- [ ] `examples/flagship/README.md` with 3 commands + expected output

### F2. Flagship suite + baseline
**Why:** Proves CI catches regressions on a real workflow.

- [ ] Create `suites/flagship/suite.yaml` pointing to flagship graph
- [ ] Generate + commit `suites/flagship/baseline.jsonl` in stub mode
- [ ] Verify `huap ci run suites/flagship --html reports/flagship.html` passes

### F3. Memory CLI commands
**Why:** Makes memory discoverable without writing code.

- [ ] `huap memory search <query>` — keyword search across stored memories
- [ ] `huap memory ingest --from-trace <file>` — ingest trace into memory via ContextBuilder
- [ ] `huap memory stats` — show db path, entry count, types breakdown
- [ ] Wire into main CLI group

### F4. Memory events in trace + HTML report
**Why:** Memory operations must be visible in the flight recorder.

- [ ] Emit `memory_retain` and `memory_recall` trace events from memory_tools
- [ ] Add "Memory" section to HTML report (`trace/report.py`):
  - List of retained items
  - List of recalled items with scores
- [ ] Works in both stub and real mode

### F5. Wrapper examples (adoption paths)
**Why:** "Keep your framework, HUAP makes it traceable" needs proof.

- [ ] `examples/wrappers/langchain/` — before/after showing HuapCallbackHandler
  - `run.py` that runs in stub mode, produces trace + report
  - `README.md` with commands
- [ ] `examples/wrappers/crewai/` — before/after showing manual instrumentation
  - `run.py` stub mode, produces trace + report
  - `README.md` with commands

### F6. Video script + assets
**Why:** Mirco needs to record the demo video.

- [ ] `docs/media/video_script.md` with:
  - Timestamps, exact terminal commands, on-screen captions
  - Must-show: flagship demo, HTML report, CI pass, drift detection, human gate, memory
- [ ] Clean screenshot of HTML report for thumbnail

### F7. Adopter guide (markdown)
**Why:** Non-technical stakeholders need to understand value without reading code.

- [ ] `docs/HUAP_Adopter_Guide.md` covering:
  - What HUAP is (1 page)
  - 3 problems it solves (reproducibility, drift detection, governance)
  - Adoption paths (wrap existing / build new / mixed)
  - Operating model (who owns baselines, who approves gates)
  - CI cookbook (when to refresh baselines, drift triage)
  - FAQ

### F8. README hero section update
**Why:** First impression for GitHub visitors.

- [ ] Top of README: video placeholder + flagship command + value bullets
- [ ] Add Memory section with 2 commands
- [ ] Links to: adopter guide, wrapper examples, suites
- [ ] Keep existing sections intact

### F9. PyPI publish + tag
**Why:** `pip install huap-core` is the adoption bar.

- [ ] Mirco provides PyPI credentials
- [ ] `twine upload dist/*`
- [ ] Verify `pip install huap-core && huap demo` from clean venv
- [ ] Git tag `v0.1.0b1`
- [ ] GitHub Release with release notes

---

## Final QA checklist (run before tagging)

- [ ] `pytest` all green (target: 120+ tests)
- [ ] `huap demo` works
- [ ] `huap demo flagship` works (stub mode, no keys)
- [ ] `huap demo flagship --with-memory` persists + retrieves on 2nd run
- [ ] `huap ci run suites/smoke` PASS
- [ ] `huap ci run suites/flagship` PASS
- [ ] `huap memory search` returns results
- [ ] GH Actions workflow green on main
- [ ] README links all valid
- [ ] No `eval()` in core
- [ ] No secrets in repo
- [ ] ruff clean

---

## Execution order

**Phase A — Memory integration + flagship** (Claude)
1. F3: Memory CLI commands
2. F4: Memory in trace + report
3. F1: Flagship demo
4. F2: Flagship suite + baseline

**Phase B — Distribution + adoption** (Claude)
5. F5: Wrapper examples
6. F8: README hero update
7. F6: Video script
8. F7: Adopter guide

**Phase C — Release** (Mirco + Claude)
9. F9: PyPI publish + tag
10. Mirco: record + upload video, add YouTube link

---

## P2 — Post-launch (ecosystem & growth)

- `--pythonpath` flag on `trace run`
- Improve eval UX (`--fail-on` thresholds)
- More adapters (LlamaIndex, AutoGen, Semantic Kernel)
- Policy pipeline (`huap policy explain`)
- Web UI for inbox
- FTS5 / vector search for memory
- More memory backends (cloud-hosted)
