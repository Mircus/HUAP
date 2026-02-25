# HUAP — Action List (Feb 2026)

Current state: **115 tests passing**, CI green (3.10-3.12), PyPI published (`pip install huap-core`), flagship demo, real SQLite memory, secret redaction, plugin boundary clean.

---

## COMPLETED SPRINTS

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

<details>
<summary>Final WOW Sprint ✅</summary>

- F1: Flagship demo (`huap flagship`) — 5-node pipeline with human gate + memory
- F2: Flagship suite + baseline — CI-gated regression detection
- F3: Memory CLI commands — `huap memory search/ingest/stats`
- F4: Memory events in trace + HTML report
- F5: Wrapper examples (LangChain + CrewAI)
- F6: Video script + assets
- F7: Adopter guide
- F8: README hero section with bold badges + PyPI link
- F9: PyPI publish + tag `v0.1.0b1`
</details>

<details>
<summary>Pre-PyPI Blockers ✅</summary>

- Blocker A: Moved HindsightProvider to `hu-plugins-hindsight` (plugin boundary)
- Blocker B: Wired `redact_secrets()` into persistence choke point
- CI: Removed `|| true` from flagship suite gate
- CI: Fixed cross-dependency install (core + plugin in single pip command)
- Fixed ruff lint error (undefined `repo_root` after refactor)
- Bundled flagship demo in wheel (`hu_core/examples/flagship/`)
- Switched badge to Shields.io (for-the-badge style)
</details>

---

## ✅ Public Beta — SHIPPED

- **PyPI**: `pip install huap-core` — [pypi.org/project/huap-core](https://pypi.org/project/huap-core/)
- **Git tag**: `v0.1.0b1`
- **GitHub Release**: Pre-release with release notes
- **CI**: Green on all Python versions (3.10, 3.11, 3.12)
- **115 tests passing**, ruff clean

---

## P2 — Post-launch (ecosystem & growth)

- `--pythonpath` flag on `trace run`
- Improve eval UX (`--fail-on` thresholds)
- More adapters (LlamaIndex, AutoGen, Semantic Kernel)
- Policy pipeline (`huap policy explain`)
- Web UI for inbox
- FTS5 / vector search for memory
- More memory backends (cloud-hosted)
- Agent message events (`message` trace kind) — see AFTERBETA.md
- Streaming token capture in LangChain adapter
- Parent span tracking for parallel execution branches
