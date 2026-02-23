# HUAP Demo Video Script

**Duration:** 3-5 minutes
**Format:** Screen recording with terminal + browser, narrator voiceover
**Prerequisites:** HUAP installed from source, `HUAP_LLM_MODE=stub` (no API keys needed)

---

## 0:00-0:20 -- Intro

**On-screen caption:** _"HUAP: Trace-First AI Agent Framework"_

**Narration:**
> HUAP is a framework for building deterministic, traceable AI agents. Every agent run produces a full trace -- a structured log of every node, LLM call, tool invocation, and human decision. That trace becomes the foundation for replay, drift detection, and CI. Let me show you the full stack in under five minutes.

**Terminal shows:**
```
huap version
```

**Expected output:**
```
huap CLI v0.1.0b1
HUAP CORE - Pod Development Tools
```

---

## 0:20-1:10 -- Flagship Demo

**On-screen caption:** _"Flagship Demo -- Full Stack in One Command"_

**Narration:**
> The flagship command runs a multi-node research agent with a human gate, stub LLM, trace recording, and an HTML report -- all in one command.

**Terminal shows:**
```
huap flagship --no-open
```

**Expected output (highlight these lines as they appear):**
```
============================================================
HUAP Flagship Demo
============================================================

Topic:   AI agent frameworks
Memory:  in-process (stub)
Drift:   no

Trace:   huap_flagship_demo/trace.jsonl
Memo:    huap_flagship_demo/memo.md
Report:  huap_flagship_demo/trace.html
```

**Narration (as output scrolls):**
> The graph executes node by node -- research, human gate for approval, synthesis, memo generation. Everything is captured in a JSONL trace file.

---

## 1:10-1:40 -- Opening the HTML Trace Report

**On-screen caption:** _"Shareable HTML Report -- No Server Required"_

**Narration:**
> Every run produces a standalone HTML report. Open it in any browser -- no backend needed. You can see the full timeline, every node's input and output, LLM token counts, and the human gate decision.

**Action:** Open `huap_flagship_demo/trace.html` in a browser.

**Must-show moments in the browser:**
- Timeline of nodes (start, research, human_gate, synthesize, memo, end)
- Expand one node to show input/output state
- The human gate row showing "approved" status with the reviewer note

---

## 1:40-2:10 -- CI Proof

**On-screen caption:** _"CI: Replay + Diff + Budget Gates"_

**Narration:**
> Traces are not just for debugging -- they are the backbone of CI. The `ci run` command replays golden baselines, diffs the output, and checks budget gates. If anything drifts, the pipeline fails.

**Terminal shows:**
```
huap ci run suites/flagship/suite.yaml
```

**Expected output (highlight PASS):**
```
============================================================
HUAP CI Run
============================================================
Suite: suites/flagship/suite.yaml
Output: reports

  [PASS] flagship

============================================================
CI RUN: PASSED (1/1)
============================================================
```

**Narration:**
> Green. The replay matched the golden baseline and all budget gates passed. This runs in GitHub Actions on every pull request.

---

## 2:10-2:50 -- Drift Detection

**On-screen caption:** _"Drift Detection -- Catch Regressions Before Production"_

**Narration:**
> What happens when an agent's behavior changes? The `--drift` flag injects a controlled change so we can see how HUAP catches it.

**Terminal shows:**
```
huap flagship --drift --no-open
```

**Expected output (highlight the diff line):**
```
============================================================
HUAP Flagship Demo
============================================================

Topic:   AI agent frameworks (with drift analysis)
Memory:  in-process (stub)
Drift:   yes (injected)

Trace:   huap_flagship_demo/trace.jsonl
Memo:    huap_flagship_demo/memo.md
Report:  huap_flagship_demo/trace.html
Diff:    huap_flagship_demo/diff.html
```

**Action:** Open `huap_flagship_demo/diff.html` in browser.

**Must-show moments in the browser:**
- Side-by-side diff showing changed events highlighted in red/green
- Cost delta section (tokens, latency)
- The "regressions detected" banner (if present)

**Narration:**
> The diff report highlights exactly what changed -- which nodes produced different output, how token usage shifted, and whether any regressions were introduced. In CI, this would block the merge.

---

## 2:50-3:30 -- Human Gate Approval

**On-screen caption:** _"Human Gates -- Governance Built Into the Graph"_

**Narration:**
> HUAP agents can pause at critical decision points and wait for human approval. The inbox CLI lets reviewers approve, reject, or edit parameters before the agent continues.

**Terminal shows:**
```
huap inbox list
```

**Expected output:**
```
GATE ID                STATUS     SEVERITY   TITLE
------------------------------------------------------------------------
 research_review       pending    medium     Review research findings

1 gate(s)
```

**Terminal shows (approve the gate):**
```
huap inbox approve research_review --note "Findings look good"
```

**Expected output:**
```
Approved gate 'research_review' (run ...)
  Note: Findings look good
```

**Narration:**
> Every gate decision is recorded in the trace. Auditors can see who approved what, when, and with what note -- full governance traceability.

---

## 3:30-4:10 -- Memory Persistence

**On-screen caption:** _"Memory -- Agents That Remember"_

**Narration:**
> The `--with-memory` flag enables persistent memory backed by SQLite. Facts, decisions, and artifacts from each run are stored and available to future runs.

**Terminal shows:**
```
huap flagship --with-memory --no-open
```

**Expected output (highlight the memory line):**
```
============================================================
HUAP Flagship Demo
============================================================

Topic:   AI agent frameworks
Memory:  persistent (SQLite)
Drift:   no

Trace:   huap_flagship_demo/trace.jsonl
Memo:    huap_flagship_demo/memo.md
Report:  huap_flagship_demo/trace.html
Memory:  .huap/memory.db (persisted)
```

**Narration:**
> The trace was recorded and the agent's knowledge was persisted to a local SQLite database. Now we can search it.

**Terminal shows:**
```
huap memory search "AI agent"
```

**Expected output:**
```
Found 3 result(s) for "AI agent":

  1. [fact] ai_agent_frameworks_overview
     AI agent frameworks provide orchestration for LLM-powered ...
     run: abc123  ns: flagship

  2. [decision] research_approach_selected
     Selected comparative analysis approach for AI agent framew...
     run: abc123  ns: flagship

  3. [artifact] research_memo
     # AI Agent Frameworks: Comparative Analysis ...
     run: abc123  ns: flagship
```

**Narration:**
> Three results -- a fact, a decision, and an artifact. Future runs can pull this context automatically. The agent gets smarter over time without re-doing work.

---

## 4:10-4:30 -- Memory Stats (optional, time permitting)

**Terminal shows:**
```
huap memory stats
```

**Expected output:**
```
Memory Database: .huap/memory.db
Size:            12.4 KB
Total entries:   8
Namespaces:      1
Runs:            1

By type:
  fact             4
  decision         2
  artifact         1
  critique         1
```

---

## 4:30-4:50 -- Closing

**On-screen caption:** _"HUAP: Deterministic. Traceable. Governable."_

**Narration:**
> That is the full HUAP stack: a traced agent run, a shareable HTML report, CI that catches drift, human gates for governance, and persistent memory. Every step is recorded, every decision is auditable, and every regression is caught before it reaches production.

**On-screen caption:** _"Get started: pip install -e packages/hu-core"_

**Final screen shows the three key commands:**
```
huap flagship --no-open          # run the full demo
huap ci run suites/flagship/suite.yaml  # prove it in CI
huap memory search "your topic"  # search agent memory
```

**On-screen caption:** _"github.com/Mircus/HUAP"_

---

## Production Notes

| Item | Detail |
|------|--------|
| Resolution | 1920x1080, 24fps minimum |
| Terminal font | Monospace, 16pt+, dark background |
| Browser | Chrome or Firefox, zoom to 125% for readability |
| Env vars | `export HUAP_LLM_MODE=stub` before recording |
| Audio | Record voiceover separately, mix at -6dB under terminal audio |
| Captions | Burn in on-screen captions; also provide SRT file |
| Cuts | Hard cut between sections; no transitions needed |
