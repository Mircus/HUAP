# Contributing to HUAP

Thanks for wanting to help build HUAP! Whether it's a bug fix, a new adapter, or a better doc page, every contribution matters. This guide will get you oriented fast.

---

## Quick Start (dev setup)

```bash
# Clone and install in editable mode with dev extras
git clone https://github.com/Mircus/HUAP.git
cd HUAP
pip install -e "packages/hu-core[dev]" -e packages/hu-plugins-hindsight

# Verify everything works
pytest -q                  # 96+ tests, all should pass
ruff check .               # zero lint errors expected
```

All LLM calls default to stub mode (`HUAP_LLM_MODE=stub`), so you don't need API keys to run the test suite.

---

## What to Contribute

Use the issue-prefix convention so maintainers can triage quickly:

| Prefix | Area | Examples |
|--------|------|----------|
| `[Bug]` | Bug fixes & test coverage | Fix null-edge crash, add missing assertion |
| `[Adapter]` | Framework adapters | LlamaIndex, AutoGen, Semantic Kernel |
| `[Plugin]` | Plugin ecosystem | New tool packs, community providers |
| `[Memory]` | Memory backends | Vector/embedding stores, persistent backends |
| `[Docs]` | Documentation & examples | Runnable tutorials, API docs, typo fixes |
| `[RFC]` | Design proposals | New trace schema, breaking API change |

Not sure where to start? Look for issues labelled **good first issue** or check the Roadmap section of the README.

---

## Development Workflow

### Branch naming

```
feat/short-description     # new feature
fix/issue-or-description   # bug fix
docs/what-changed          # documentation
test/what-covered          # test additions
```

### Running tests

```bash
# Full suite (stub mode — no API keys needed)
export HUAP_LLM_MODE=stub   # bash/zsh
pytest packages/hu-core/tests/ -q

# Single file
pytest packages/hu-core/tests/test_graph.py -q
```

### Linting

```bash
ruff check .          # lint
ruff format .         # auto-format
```

CI runs ruff + pytest across Python 3.10, 3.11, and 3.12 — make sure both pass locally before pushing.

### Smoke suite & demos

```bash
huap demo              # minimal hello-world pod
huap flagship          # full flagship demo with trace output
```

The smoke suite (`suites/smoke/suite.yaml`) runs automatically in CI and verifies golden baselines.

---

## PR Guidelines

- **Keep changes small and well-scoped.** One concern per PR.
- **Add or adjust a test** (or golden trace) when behavior changes.
- **Include a short note** on replay/eval impact (tokens, tool calls) if relevant.
- **Use conventional commits:**

```
feat: add LlamaIndex adapter
fix: handle null edge targets in executor
docs: update getting started guide
test: add replay verification tests
refactor: simplify condition evaluator
```

- CI must be green before merge (lint + pytest + smoke + golden path).

---

## Architecture Quick Reference

| Directory | What lives here |
|-----------|----------------|
| `hu_core/orchestrator/` | Graph loader, executor, safe-eval condition engine |
| `hu_core/trace/` | Trace service, replay, diff, report, models |
| `hu_core/ci/` | CI runner, HTML report generation |
| `hu_core/adapters/` | Framework adapters (LangChain, CrewAI) |
| `hu_core/plugins/` | Plugin loader and registry |
| `hu_core/memory/` | Memory providers (Hindsight stub) |
| `hu_core/ports/` | Abstract interfaces (MemoryPort, etc.) |
| `hu_core/cli/` | Click CLI commands (`main.py` + `*_cmds.py`) |
| `packages/hu-core/tests/` | pytest suite (96+ tests) |
| `suites/smoke/` | Smoke suite YAML + golden baselines |
| `examples/` | Runnable example pods |

---

## Where We Want to Grow

HUAP is in public beta — the highest-impact contributions right now expand what the platform can do:

- **Vector memory backends** — plug in Pinecone, Weaviate, Qdrant, ChromaDB, etc. via the `MemoryPort` interface.
- **Coding-agent integrations** — adapters for Aider, OpenDevin, SWE-Agent, or similar.
- **More framework adapters** — LlamaIndex, AutoGen, Semantic Kernel.
- **Evaluation & benchmarks** — new golden suites, scoring strategies, regression baselines.

## Out of Scope

- **Product verticals** — HUAP core stays domain-agnostic (no OAuth integrations, vertical-specific logic).
- **Breaking API changes** without an accepted `[RFC]` issue.
- **Large refactors** without prior discussion and maintainer buy-in.

---

## Questions?

Open an issue with the `[RFC]` prefix before starting large changes. For quick questions, a regular issue works fine.

**Thank you for contributing!**
