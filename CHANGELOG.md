# Changelog

All notable changes to HUAP Core are documented here.

## [0.1.0b1] — 2026-02-21

First public beta release.

### Core
- **Graph executor** — YAML-based `nodes[] + edges[]` workflow engine
- **Safe condition evaluator** — AST-based expression parser replaces `eval()` in edge conditions
- **Pod contract** — `PodContract` base class with schema, metrics, and capabilities
- **Pod scaffolder** — `huap pod create <name>` generates a runnable pod with tests

### Tracing
- **Trace service** — JSONL event recording with spans, hashing, and timestamps
- **Replay** — deterministic re-execution using recorded events or stubs
- **Diff** — compare two traces for behavioral and cost regressions
- **Wrap** — trace any external script via `huap trace wrap`
- **HTML reports** — standalone, self-contained trace reports

### Evaluation
- **Budget engine** — cost/quality grading (A-F) with configurable thresholds
- **Suite runner** — run scenarios, diff vs golden baselines, produce HTML reports
- **CI integration** — `huap ci run` with `--html` flag for artifact generation

### Model Router (Specialist Squad)
- **Model registry** — declare models with capabilities, privacy, cost
- **Rule-based router** — ordered policy rules, first match wins
- **Providers** — Stub (no deps), Ollama (stdlib), OpenAI (optional)
- **Explain** — full transparency on routing decisions

### Human Gates
- **Inbox system** — agents pause at gates, humans approve/reject/edit via CLI
- **Watch** — live-tail traces for gates, issues, and budget warnings

### Adapters
- **LangChain** — `HuapCallbackHandler` for automatic trace capture
- **CrewAI** — manual instrumentation context manager

### Plugins & Memory
- **Plugin SDK** — registry for memory backends, tool packs, providers
- **MemoryPort** — retain/recall/reflect interface for cross-run knowledge
- **Memory tools** — node-level access to memory operations
- **Ingest policy** — control what gets stored automatically

### CLI
- `huap demo` — one-liner: run graph, generate HTML report, open browser
- `huap init` — create a runnable workspace with hello workflow
- `huap pod create/validate/list` — pod lifecycle management
- `huap trace run/view/replay/diff/report/wrap/validate` — full trace toolkit
- `huap eval trace/run/init` — evaluation commands
- `huap ci run/check/status/init` — CI integration
- `huap models init/list/explain` — model router management
- `huap inbox list/show/approve/reject/edit` — human gate management
- `huap watch` — live trace tail
- `huap plugins init/list` — plugin management

### Developer Experience
- **96 tests** passing across Python 3.10, 3.11, 3.12
- **GitHub Actions CI** — lint (ruff), pytest, smoke test, golden path, artifact upload
- **Makefile** — `make install test lint smoke demo ci`
- **Smoke suite** — `suites/smoke/suite.yaml` with golden baseline
