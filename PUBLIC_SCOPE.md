# Public Scope

What is included (and not included) in HUAP Core Public Beta.

---

## What's Included

### Core Library (`hu-core`)

| Component | Description |
|-----------|-------------|
| Trace System | Event recording, replay, diff, evaluation |
| Tool System | Tool registry, base classes, built-in tools |
| LLM Client | OpenAI integration with stub mode |
| Policy Engine | Guard policies with allow/deny decisions |
| Graph Runner | Basic workflow execution |
| CLI | `huap` command with pod/trace/eval subcommands |

### Features

- Single-node execution
- Deterministic replay via stubs
- JSONL trace format
- Cost and quality grading
- Diff with severity levels
- CI-friendly stub mode

---

## What's NOT Included

HUAP Core Public Beta does **not** include:

| Feature | Reason | Available In |
|---------|--------|--------------|
| OAuth Integrations | Product-specific (Fitbit, Oura, Sahha) | HUAP Pro |
| Managed Hosting | Commercial infrastructure | HUAP Pro |
| Dashboard UI | Product surface | HUAP Pro |
| Vertical Pods | Domain-specific (health, finance, legal) | HUAP Pro |
| Multi-tenant | Enterprise feature | HUAP Pro |
| Policy Server | Centralized enforcement | HUAP Pro |
| Streaming LLM | Planned for future | Roadmap |
| Distributed Tracing | OpenTelemetry export | Roadmap |
| Other Providers | Anthropic, Azure, etc. | Roadmap |

---

## Execution Model

HUAP Core supports:

- **Single-process execution** - One agent, one machine
- **Async tools** - Non-blocking tool execution
- **Stub mode** - Deterministic testing without API calls

HUAP Core does **not** support:

- Distributed execution across machines
- Multi-agent orchestration
- Real-time streaming responses
- Database-backed trace storage

---

## LLM Support

Currently supported:
- OpenAI (gpt-4, gpt-4o, gpt-4o-mini, gpt-3.5-turbo)

Planned:
- Anthropic (Claude)
- Azure OpenAI
- Local models (Ollama, LM Studio)

---

## Environment Requirements

| Requirement | Version |
|-------------|---------|
| Python | 3.10+ |
| OpenAI API | v1.0+ |

Optional:
- PostgreSQL (for db extras)
- Cryptography (for encryption extras)

---

## License

HUAP Core is released under the **MIT License**.

You are free to:
- Use commercially
- Modify and distribute
- Include in proprietary projects

---

## Support

For HUAP Core (open source):
- GitHub Issues: [github.com/huap-ai/huap-core/issues](https://github.com/huap-ai/huap-core/issues)
- Documentation: This repo

For HUAP Pro (commercial):
- Contact: [huap.ai](https://huap.ai)

---

## Upgrade Path

When moving from Public Beta to Pro:

1. Install `huap-pro` package
2. Enable integrations (OAuth flows)
3. Configure multi-tenant settings
4. Deploy to managed hosting

Pro is a superset - all Public Beta code works unchanged.

---

**HUAP Core v0.1.0b1**
