---
title: "HUAP Public Beta Manual"
subtitle: "Ship agents like software: traceable, testable, governable"
version: "Public Beta (pre-1.0)"
date: "2026-02-25"
product: "huap-core"
---

# HUAP Public Beta Manual

**Ship agents like software: traceable, testable, governable**
<br/>
**Agent CI · Flight Recorder · Human Gates · Local Memory (Hindsight)**
<br/>
Version: Public Beta (pre-1.0) · Date: 2026-02-25

> ✅ **Start here (copy/paste):**
>
> ```bash
> pip install huap-core
> huap flagship
> ```

---

## Why this exists (a note from the builder)

Most "agent frameworks" **demo** well and **fail** badly once you try to operate them.

They look impressive on a laptop because nobody is asking the two questions that matter:

1. **Can you reproduce the run that failed?**
2. **Can you stop the agent before it does something dumb?**

HUAP exists because agentic systems are *software systems with uncertainty inside them* — models, tools, changing state, memory, actions. You don't manage uncertainty by ignoring it. You manage it by making runs **observable**, changes **reviewable**, and risky actions **controllable**.

If you build with HUAP, you're not buying "more agent magic."
You're buying **operational sanity**.

---

## Who this manual is for

### Primary readers

- **Tech Leads / Founders** — you want agents in production *and* you want to sleep at night.
- **Engineering Managers** — you need a workflow that doesn't depend on hero debugging.
- **AI Engineers** — you already use LangChain/CrewAI/etc. You want trace + CI + review on top.
- **R&D teams** — you want reproducible multi-step workflows with artifacts you can share.

### If this is you, HUAP is not necessary (yet)

- You only do one-shot prompts.
- You don't ship to users.
- You don't care if outputs drift over time.

---

# 0) The problem HUAP solves

Classic software is deterministic enough to test. Agents are workflows with uncertainty inside:

| Source of uncertainty | What happens |
|---|---|
| **Model calls** | Non-deterministic — same prompt, different output |
| **Tool calls** | External systems change state, fail, rate-limit |
| **Changing state** | The world evolves between runs |
| **Memory** | Context grows, drifts, accumulates noise |
| **Actions** | Real-world consequences — emails sent, files written, money spent |

So when something breaks, it sounds like this:

> *"It worked yesterday. Today it failed. Same prompt. Same code. Different outcome."*

That sentence is poison. It means you have no way to triage, no way to reproduce, and no way to prevent it next time.

### HUAP's answer

Treat agent runs like airplanes treat flights:

| Aviation | HUAP |
|---|---|
| Flight recorder | **Trace** (`trace.jsonl`) |
| Replay & investigate | **Replay** (`huap trace replay`) |
| Compare to known-good | **Baseline + Diff** (`huap trace diff`) |
| Crew approval for risky maneuvers | **Human Gates** (`huap inbox`) |
| Maintenance logs | **Memory** (Hindsight — auditable, searchable) |

No philosophy. Just engineering.

---

# 1) What HUAP is (and what it isn't)

### HUAP is

- A **runtime harness** for agent workflows (your code runs inside it).
- A **flight recorder** — every action becomes a `trace.jsonl` event + human-readable `trace.html`.
- A **CI runner** — compare current run against a known-good baseline, produce `diff.html`.
- A **governance layer** — human gates pause the agent and wait for approval.
- A **memory port** with a local SQLite backend (Hindsight) — searchable, auditable, redacted.

### HUAP is not

- A replacement for LangChain / CrewAI / LangGraph / AutoGen.
- A prompt playground.
- A full enterprise platform (that's the post-beta roadmap).

Think of HUAP as the layer that turns *"agent demos"* into *"agent systems."*

---

# 2) Pods — what they are

A **pod** is an agentic application built on top of HUAP. A pod can contain one agent, a squad of agents, or no agents at all — just orchestrated tool calls. HUAP provides the infrastructure (tracing, CI, gates, memory); the pod is your product logic.

```
┌─────────────────────────────────────────────────────┐
│              Your Pods (agentic apps)                │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Research  │  │ Customer │  │ Code Review      │  │
│  │ Assistant │  │ Support  │  │ Pipeline         │  │
│  │ (1 agent) │  │(3 agents)│  │ (tools only)     │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
├─────────────────────────────────────────────────────┤
│              HUAP Infrastructure                     │
│                                                     │
│  Trace    CI/Eval   Human Gates   Memory   Router   │
│  (JSONL)  (suites)  (inbox)       (SQLite) (squad)  │
└─────────────────────────────────────────────────────┘
```

Pods are **your code**. HUAP is **the platform underneath**. A pod can use any framework (CrewAI, LangChain, plain Python) — HUAP instruments it.

When you run `huap trace run <pod> <graph>`, the `<pod>` is just a label for your application. The `<graph>` defines the workflow (nodes + edges). One pod can have many graphs, and each graph can orchestrate any number of agents, tools, and LLM calls.

---

# 3) What you get (in plain words)

When you run a workflow under HUAP, you get **artifacts** you can review, share, and CI-gate:

| Artifact | What it is | Who reads it |
|---|---|---|
| `trace.jsonl` | Timeline of every event (machine-readable) | CI, replay engine, diff tool |
| `trace.html` | Standalone HTML report (human-readable) | Engineers, managers, auditors |
| `diff.html` | What changed vs baseline (visual diff) | PR reviewers, triage |
| `memo.md` | Agent-produced summary (flagship demo) | Anyone — shareable artifact |
| Suites + baselines | Regression tests for agents | CI pipeline |
| Gates | "Agents propose; humans dispose" | Gatekeepers, compliance |
| Memory DB | Local searchable store (`.huap/memory.db`) | Agents (cross-session recall) |

---

# 4) The 10-minute WOW path (do this first)

This proves the whole stack: multi-node workflow + trace + gates + memory + drift detection.

### 3.1 Install

```bash
pip install huap-core
```

### 3.2 Run the flagship demo

```bash
huap flagship
```

This runs a 5-node pipeline (research → analyze → human gate → synthesize → memorize) in stub mode — no API keys needed.

**Expected outputs** in `huap_flagship_demo/`:

| File | Contents |
|---|---|
| `trace.jsonl` | Full event timeline |
| `trace.html` | Standalone HTML report (opens in browser) |
| `memo.md` | Agent-produced research memo |

### 3.3 Prove Agent CI (baseline vs current)

```bash
huap ci run suites/flagship/suite.yaml --html reports/flagship.html
```

This replays the flagship workflow, diffs against a committed baseline, and produces an HTML report. If the run matches the baseline: **PASS**. If drift is detected: **FAIL** with a visual diff.

### 3.4 Prove drift detection

```bash
huap flagship --drift
huap ci run suites/flagship/suite.yaml --html reports/flagship_drift.html
```

The `--drift` flag injects a controlled change. The CI runner catches it and shows exactly what changed.

### 3.5 Prove memory persists across sessions

```bash
huap flagship --with-memory
huap flagship --with-memory
huap memory search "memo" --k 5
```

The first run stores findings in SQLite. The second run retrieves them. The search command queries the memory store directly.

> **What "DRIFT" means:** drift is any meaningful change between the current run and the baseline.
> Some drift is good (you improved behavior). Some drift is bad (you broke something).
> HUAP makes drift **visible** so you decide **intentionally**.

---

# 5) Mental model (two pictures)

### 4.1 Runtime loop

```
┌───────────────────┐
│   Your Agent       │   (LangChain / CrewAI / custom)
└─────────┬─────────┘
          │
          ▼
┌──────────────────────────────────────────────────────┐
│  HUAP Runtime                                        │
│                                                      │
│  · runs workflow graph (nodes + edges)               │
│  · calls tools via sandbox (safe batteries)          │
│  · records every event to trace.jsonl                │
│  · applies human gates (pause → inbox → decide)      │
│  · reads/writes memory via MemoryPort                │
│  · routes model calls via Specialist Squad           │
└─────────┬────────────────────────────────────────────┘
          │
          ▼
    Artifacts (reviewable)
    trace.jsonl · trace.html · memo.md · diff.html
```

### 4.2 CI loop

```
  Baseline (known good)          Current run (PR / main)
          │                              │
          └──────────┬───────────────────┘
                     ▼
              huap ci run
                     ▼
     PASS   or   DRIFT DETECTED (+ diff.html)
                     ▼
         fix  /  accept  /  refresh baseline (intentional)
```

**Remember:** Trace → Baseline → CI Diff. That's the whole loop.

---

# 6) Adoption paths (pick one)

### Path A — Wrap existing agents (fastest)

Keep LangChain/CrewAI/etc. HUAP adds trace + CI + gates on top.

```python
# LangChain — one callback handler
from hu_core.adapters.langchain import HuapCallbackHandler

handler = HuapCallbackHandler(out="traces/langchain.jsonl")
chain.invoke({"input": "hello"}, config={"callbacks": [handler]})
handler.flush()
```

```bash
# Or wrap any script
huap trace wrap --out traces/agent.jsonl -- python my_agent.py
```

See: `examples/wrappers/langchain/` and `examples/wrappers/crewai/`

#### Step-by-step: HUAPize a CrewAI app

CrewAI has no public callback API, so instrumentation is manual — but straightforward:

**1. Install** — `pip install huap-core` (your CrewAI code stays as-is)

**2. Wrap** — import the context manager and wrap your workflow:

```python
from hu_core.adapters.crewai import huap_trace_crewai

with huap_trace_crewai(out="traces/my_crew.jsonl", run_name="my_crew") as tracer:
    # your existing CrewAI code here
    ...
```

**3. Instrument** — call tracer methods at each step:

```python
    tracer.on_agent_step("researcher", "Search for AI frameworks")
    tracer.on_tool_call("web_search", {"query": "AI agent frameworks 2025"})
    result = do_search(...)
    tracer.on_tool_result("web_search", result, duration_ms=120)
    tracer.on_llm_request("gpt-4o", messages=[...])
    summary = call_llm(...)
    tracer.on_llm_response("gpt-4o", summary, usage={...}, duration_ms=800)
```

**4. View** — inspect the trace:

```bash
huap trace view traces/my_crew.jsonl
huap trace report traces/my_crew.jsonl --out reports/my_crew.html
```

**5. Baseline + CI** — commit the trace, gate regressions:

```bash
# Save as golden baseline
cp traces/my_crew.jsonl suites/my_crew/baseline.jsonl

# In CI: run again, diff against baseline
huap ci run suites/my_crew/suite.yaml --html reports/ci.html
```

> Try it live: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Mircus/HUAP/blob/main/notebooks/HUAPize_CrewAI.ipynb)

**Checklist:**
- [ ] Wrap your run entrypoint
- [ ] Route risky tools through safe wrappers or gates
- [ ] Baseline one "good" run
- [ ] Run a smoke suite in CI

### Path B — HUAP-native graphs (cleanest)

Define workflows as YAML graphs. Full tracing, replay, and CI built in.

```yaml
nodes:
  - name: research
    run: my_pod.nodes.research
  - name: analyze
    run: my_pod.nodes.analyze
edges:
  - from: research
    to: analyze
  - from: analyze
    to: null
```

**Checklist:**
- [ ] Define nodes / edges / conditions (safe condition evaluator)
- [ ] Baseline "good" behavior
- [ ] Gate risky nodes
- [ ] Add memory only for curated knowledge

### Path C — Mixed migration (realistic)

Wrap now; migrate critical workflows to native graphs later.

**Checklist:**
- [ ] Wrap existing agent for trace coverage today
- [ ] Migrate the critical workflow into a HUAP suite
- [ ] Gates early, memory last

---

# 7) Operating model (how teams avoid chaos)

### Roles

| Role | Responsibility |
|---|---|
| **Workflow owner** | Defines expected behavior + suite |
| **Baseline owner** | Approves baseline refreshes |
| **Gatekeeper** | Approves risky actions via inbox |
| **CI maintainer** | Keeps suites stable + fast |

### Baseline refresh policy

Refresh baselines only when:

1. The diff has been **reviewed**.
2. The change is **intentional**.
3. Someone **owns the outcome**.

> Never refresh baselines just to "make CI green."

### Drift triage workflow

1. Open `diff.html`.
2. Identify the source: prompt change? tool change? model update? memory drift? nondeterminism?
3. Decide: **fix** / **accept** / **refresh baseline intentionally**.

---

# 8) Local memory (Hindsight) — without shooting yourself

### What to store (good)

| Category | Example |
|---|---|
| Decisions + rationale | "Chose vendor X because of rate limits on Y" |
| Short stable summaries | "User prefers JSON output format" |
| Tool/API constraints | "API v2 has a 100 req/min limit" |
| Known failure modes | "Model hallucinates dates before 2020" |

### What NOT to store (bad)

| Category | Why |
|---|---|
| Raw secrets / tokens | Redacted automatically, but don't rely on it — don't store them |
| Full payload dumps | Bloats memory, adds noise |
| Unfiltered long transcripts | Low signal-to-noise ratio |

### Commands

```bash
# Check what's in memory
huap memory stats

# Ingest trace events into memory
huap memory ingest --from-trace traces/flagship.jsonl

# Search by keyword
huap memory search "rate limit" --k 5
```

### Reset memory (local store)

```bash
# Delete the local memory database
rm -rf .huap/
```

> **Secret redaction:** HUAP automatically strips API keys, tokens, and credentials before storing anything in memory. This happens at the persistence layer — you can't accidentally store `sk-abc123...` in the database.

---

# 9) CI cookbook (copy/paste mindset)

### Rollout cadence

| Week | Action |
|---|---|
| **Week 1** | Smoke suite in CI (proves the pipeline works) |
| **Week 2** | Baseline one critical workflow |
| **Week 3** | Gate the riskiest action |
| **Week 4** | Add memory (carefully, for curated knowledge only) |

### GitHub Actions example

```yaml
- name: Agent CI — smoke suite
  run: |
    export HUAP_LLM_MODE=stub
    huap ci run suites/smoke/suite.yaml --html reports/smoke.html

- name: Agent CI — flagship suite
  run: |
    export HUAP_LLM_MODE=stub
    huap ci run suites/flagship/suite.yaml --html reports/flagship.html

- name: Upload artifacts
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: huap-reports
    path: reports/*.html
    retention-days: 14
```

### Always upload artifacts

| Artifact | Purpose |
|---|---|
| `trace.html` | What happened |
| `diff.html` | What changed |
| `reports/*.html` | CI summary with pass/fail |

Artifacts turn *"CI failed"* into *"CI explained why."*

---

# 10) Security posture

### Tool risk tiers

| Tier | Examples | Default policy |
|---|---|---|
| **Low** | Read allowed local files | Allow |
| **Medium** | Safe HTTP GET to allowlisted domains | Allow + log |
| **High** | File writes, external API writes, publishing | Gate + log |
| **Critical** | Money transfers, irreversible actions | Gate + 2-person rule (roadmap) |

### Safe batteries included

HUAP ships two safe-by-default tools:

| Tool | What it does |
|---|---|
| `http_fetch_safe` | HTTP GET with domain allowlist, timeout, size cap, content-type filter |
| `fs_sandbox` | File I/O confined to a root directory — no path traversal |

### Memory safety

- Memory is sanitized on ingest via `redact_secrets()`.
- API keys, tokens, and credentials are automatically stripped.
- Allowlist what becomes memory — don't dump everything.

---

# 11) Rollout plan

### First 2 weeks

- [ ] Install HUAP (`pip install huap-core`)
- [ ] Wrap your agent (or run the flagship demo)
- [ ] Record traces — get comfortable reading `trace.html`
- [ ] Add 1 smoke suite to CI
- [ ] Add 1 gate for the riskiest action

### First 30 days

- [ ] Add a critical workflow suite with a committed baseline
- [ ] Establish baseline ownership (who reviews, who approves refresh)
- [ ] Upload `trace.html` and `diff.html` as CI artifacts
- [ ] Use memory only for curated summaries (not raw dumps)

### First 90 days

- [ ] Multiple suites (fast smoke vs slow integration)
- [ ] Structured policies for tool access tiers
- [ ] Optional: external memory backend
- [ ] Optional: team approval workflows

---

# 12) FAQ

**"Is this just logging?"**

No. Logging gives you text lines. HUAP gives you structured event timelines, baselines, visual diffs, CI gating, human approvals, and auditable memory — all in one pipeline.

**"What about nondeterminism?"**

Use stub mode in CI (`HUAP_LLM_MODE=stub`) for fully deterministic replay. For live runs: pin model providers, ignore noise fields in diffs, stabilize memory retrieval. HUAP's diff engine highlights *meaningful* changes, not random noise.

**"Do I have to rewrite my agents?"**

No. Start with wrappers (Path A). The LangChain adapter is one callback handler. The CrewAI adapter is manual but compatible with the full trace pipeline. Or wrap any script with `huap trace wrap`.

**"How big do traces get?"**

Traces record what you need to debug — node entries/exits, tool calls, LLM requests/responses, gate decisions, memory ops. Avoid dumping full web pages into state. Store large blobs separately and reference them by path.

**"Can I replace Hindsight?"**

Yes — that's the design. The `MemoryProvider` interface is a plugin boundary. Hindsight (SQLite) ships as the default. Future backends (vector stores, cloud-hosted) plug in without changing your workflow code.

**"What if I need real LLM calls in CI?"**

Set `HUAP_LLM_MODE=live` and provide `OPENAI_API_KEY`. But for regression testing, stub mode is recommended — it's free, fast, and fully deterministic.

**"Is HUAP production-ready?"**

This is a public beta. The core pipeline (trace → replay → diff → CI → gates → memory) is solid and tested (115 tests, CI on Python 3.10–3.12). The interfaces are stable. What's coming: more adapters, vector memory, web UI for gates.

---

# Appendix A — Command reference

### Core

```bash
huap --help                      # Show all commands
huap --version                   # Show version
huap init <name>                 # Create a runnable workspace
huap flagship                    # Full demo (opens browser)
huap flagship --no-open          # Full demo (no browser)
huap flagship --drift            # Demo with injected drift
huap flagship --with-memory      # Demo with persistent memory
huap demo                        # Simple hello graph demo
```

### Tracing

```bash
huap trace run <pod> <graph>     # Run and record trace
huap trace view <file>           # View trace events (terminal)
huap trace replay <file>         # Replay with stubs
huap trace diff <a> <b>          # Compare two traces
huap trace wrap -- <cmd>         # Wrap any command as a trace
huap trace report <file>         # Generate standalone HTML report
huap trace validate <file>       # Validate trace JSONL schema
```

### Evaluation

```bash
huap eval trace <file>           # Evaluate single trace
huap eval run <suite>            # Evaluate suite of traces
huap eval init                   # Create budget config
```

### Agent CI

```bash
huap ci init                     # Create CI config
huap ci run <suite>              # Run suite, diff vs golden
huap ci run <suite> --html <out> # Same, with HTML report
huap ci check <suite>            # Full CI check (replay + eval)
huap ci status                   # Show last CI run status
```

### Human Gates / Inbox

```bash
huap inbox list                  # List pending gate requests
huap inbox show <gate_id>        # Show gate details
huap inbox approve <gate_id>     # Approve a pending gate
huap inbox reject  <gate_id>     # Reject a pending gate
huap inbox edit    <gate_id>     # Edit params and approve
```

### Memory

```bash
huap memory stats                # Show database statistics
huap memory search <query>       # Keyword search
huap memory ingest --from-trace <file>  # Ingest trace into memory
```

### Model Router

```bash
huap models init                 # Create models.yaml + router.yaml
huap models list                 # List registered models
huap models explain              # Explain routing decision
```

### Plugins

```bash
huap plugins init                # Create plugins.yaml
huap plugins list                # List registered plugins
```

---

# Appendix B — Screenshots checklist

> **For PDF/web version:** add screenshots at the following locations.

| Section | Screenshot | Description |
|---|---|---|
| §3.2 | `trace_html_report.png` | Flagship trace.html open in browser |
| §3.3 | `ci_pass.png` | CI suite passing (terminal output) |
| §3.4 | `diff_html_report.png` | Drift diff.html showing changes |
| §3.5 | `memory_search.png` | `huap memory search` output |
| §4.1 | `flagship_terminal.png` | Full flagship run in terminal |
| §8 | `github_actions_artifacts.png` | CI artifacts in GitHub Actions |

---

<p align="center">
<strong>HUAP Core v0.1.0b1</strong> · <code>pip install huap-core</code>
<br/>
<a href="https://github.com/Mircus/HUAP">github.com/Mircus/HUAP</a> · <a href="https://pypi.org/project/huap-core/">pypi.org/project/huap-core</a>
</p>
