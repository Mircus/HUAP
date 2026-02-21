# HUAP Core

**Trace-first primitives for deterministic, testable AI agents.**

HUAP Core provides the foundational toolkit for building AI agent systems that are traceable, deterministic, evaluatable, and CI-gated.

## Quick Start

```bash
pip install huap-core
huap demo
```

## Features

- **Traceable** — every action recorded as replayable JSONL events
- **Deterministic** — stub mode + replay verification for reproducible testing
- **Evaluatable** — cost/quality grading to gate regressions in CI
- **Squad-ready** — specialist model router picks the right model for each task
- **Framework-agnostic** — adapters for CrewAI, LangChain, or wrap any script
- **Human-gated** — pause, review, and approve agent actions via an inbox
- **Pluggable** — plugin SDK for memory backends, tool packs, and providers

## Documentation

Full docs: [github.com/Mircus/HUAP](https://github.com/Mircus/HUAP)
