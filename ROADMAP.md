# HUAP Roadmap

## Current: Public Beta (v0.1.x)

- [x] Core orchestrator (YAML graph, executor, safe-eval conditions)
- [x] Trace spec v0.1 (JSONL events, replay, diff, eval)
- [x] CI runner with golden baseline gating
- [x] Human gates (inbox pause/approve flow)
- [x] Plugin SDK (memory backends, tool packs, providers)
- [x] Model router (specialist squad, stub mode)
- [x] LangChain adapter (production)
- [x] CrewAI adapter (manual instrumentation)
- [x] CLI: `huap demo`, `huap flagship`, `huap init`, `huap trace *`, `huap ci *`, `huap eval *`
- [x] 96+ tests, CI green on Python 3.10/3.11/3.12

## Next: v0.2 — Storage & Adapters

- [ ] Persistent memory backends (Pinecone, Weaviate, Qdrant, ChromaDB) via `MemoryPort`
- [ ] Replace Hindsight stub with real SQLite/vector provider
- [ ] LlamaIndex adapter
- [ ] AutoGen adapter
- [ ] Semantic Kernel adapter
- [ ] Coding-agent integrations (Aider, OpenDevin, SWE-Agent)

## Later: v0.3+ — Platform

- [ ] Web UI for human gate inbox (browser-based review & approval)
- [ ] Trace schema formalization (JSONSchema, versioned backwards compatibility)
- [ ] Embedding-based semantic search in memory
- [ ] Remote trace storage and collaboration
- [ ] `CITATION.cff` and academic integration
- [ ] Make `openai` dependency optional in stub-only mode

## How to Influence the Roadmap

Open an issue with the `[RFC]` prefix to propose a feature or architectural change. We prioritize based on community demand and alignment with HUAP's core principle: **deterministic, traceable, framework-agnostic agent infrastructure**.
