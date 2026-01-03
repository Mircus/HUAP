# Changelog

All notable changes to HUAP Core will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0b1] - 2025-12-30

### Added

- **Trace System**
  - JSONL event recording for all agent actions
  - `TraceService` with contextvars isolation for concurrent runs
  - `TraceReplayer` with emit and exec modes
  - `TraceDiffer` with severity levels (INFO, WARN, FAIL)
  - `DiffPolicy` for YAML-configurable regression thresholds
  - Cost tracking in replay results (`CostSummary`)
  - State hash normalization (`hash_state`, `normalize_for_hash`)
  - LLM content redaction via `HUAP_TRACE_REDACT_LLM`

- **Tool System**
  - `ToolRegistry` with contextvars isolation
  - `BaseTool` with input schema validation
  - Tool categories: UTILITY, AI, STORAGE, EXTERNAL
  - Execution timing and logging

- **LLM Integration**
  - OpenAI client with usage tracking
  - Stub mode (`HUAP_LLM_MODE=stub`) for CI testing
  - `chat_completion_with_usage()` for cost tracking

- **CLI**
  - `huap pod create` - Create pods from template
  - `huap pod validate` - Validate pod contracts
  - `huap trace run` - Run with tracing
  - `huap trace view` - View trace events
  - `huap trace replay` - Replay with stubs
  - `huap trace diff` - Compare traces
  - `huap eval trace` - Evaluate single trace
  - `huap eval run` - Evaluate suite

- **Examples**
  - `hello-pod` - Minimal deterministic tools
  - `llm-pod` - LLM integration with stub mode
  - `memory-pod` - State management patterns
  - `sequential.yaml` - Linear workflow graph
  - `branching_review_loop.yaml` - Conditional workflow

- **Documentation**
  - README with golden path
  - GETTING_STARTED tutorial
  - CONCEPTS architecture guide
  - POD_AUTHORING best practices
  - TRACE_GUIDE format details
  - PUBLIC_SCOPE boundaries

### Removed

- OAuth integrations (Fitbit, Oura, Sahha) - moved to HUAP Pro
- Product surfaces (apps/, .docs/) - moved to HUAP Pro
- Nested git repos (AegisStack-MVP)

### Schema Versions

- `trace.schema.version`: 1.0
- `pod.contract.version`: 1.0

---

## [Unreleased]

### Planned

- Streaming LLM support
- Anthropic/Azure providers
- OpenTelemetry trace export
- Per-model cost pricing tables

---

## Version Policy

- **Major (1.0.0)**: Breaking API changes
- **Minor (0.1.0)**: New features, backwards compatible
- **Patch (0.1.1)**: Bug fixes, backwards compatible
- **Beta (b1)**: Pre-release, API may change (PEP440 compliant)

---

**HUAP Core**
