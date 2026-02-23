# HUAP Flagship Demo

Full-stack showcase: multi-node graph, human gate, memory, trace, HTML report, and shareable memo.

## Quick Start

```bash
# 1. Basic run (stub mode, no API keys needed)
huap flagship --no-open

# 2. With persistent memory (SQLite)
huap flagship --with-memory --no-open

# 3. With drift injection (shows diff detection)
huap flagship --drift --no-open
```

## Output Artifacts

| File | Description |
|---|---|
| `huap_flagship_demo/trace.jsonl` | Full trace (flight recorder) |
| `huap_flagship_demo/trace.html` | Standalone HTML report |
| `huap_flagship_demo/memo.md` | Shareable research memo |
| `huap_flagship_demo/diff.html` | Drift report (only with `--drift`) |

## Pipeline

```
research → analyze → gate → synthesize → memorize
```

1. **research** — Gather data from safe sources (stubbed)
2. **analyze** — Extract insights and assess risk
3. **gate** — Human approval checkpoint (auto-approved in demo)
4. **synthesize** — Produce a structured markdown memo
5. **memorize** — Persist key findings for cross-session recall

## Memory Demo

Run twice with `--with-memory` to see cross-session recall:

```bash
rm -rf .huap huap_flagship_demo
huap flagship --with-memory --no-open
huap flagship --with-memory --no-open   # second run retrieves memories
huap memory search "AI agent"           # search persisted memories
huap memory stats                       # see database statistics
```

## CI Integration

```bash
huap ci run suites/flagship/suite.yaml --html reports/flagship.html
```
