# HUAP Adopter Guide

_For engineering leaders, platform teams, and compliance stakeholders._

---

## 1. What Is HUAP?

HUAP (HUman Agentic Platform) is an open-source Python framework for building AI agents that are **deterministic, traceable, and governable**. Every agent run produces a structured trace -- a complete record of every node execution, LLM call, tool invocation, and human decision. That trace becomes the foundation for automated replay, drift detection, CI gating, and audit compliance.

---

## 2. Three Problems HUAP Solves

| Problem | How It Manifests | HUAP Solution |
|---------|-----------------|---------------|
| **Reproducibility** | "The agent worked yesterday but gives different answers today." | **Trace replay.** Record a golden trace, replay it with stubbed LLM/tools, and verify the output hash matches. If it does not, you know exactly which node diverged. |
| **Drift detection** | "We updated the prompt and now costs doubled, but nobody noticed." | **Diff + CI.** HUAP diffs any two traces and surfaces changes in output, token usage, latency, and cost. CI blocks the merge if regressions exceed budget gates. |
| **Governance** | "The agent approved a $50k spend with no human review." | **Human gates.** Insert approval points into any graph. The agent pauses, a reviewer approves/rejects/edits via CLI or API, and the decision is recorded in the trace for audit. |

---

## 3. Adoption Paths

There is no need to rewrite existing agents. HUAP offers three on-ramps depending on where you are today.

### Path A: Wrap an Existing Framework

If you already use LangChain, CrewAI, or another orchestration framework, use `huap trace wrap` to capture a HUAP trace around your existing process.

```
huap trace wrap --out traces/run.jsonl -- python my_langchain_agent.py
```

You get tracing, diffing, and CI without changing a single line of agent code. A LangChain adapter is also available for deeper integration (automatic LLM/tool event capture).

### Path B: Build New Agents on HUAP

Define your agent as a YAML graph of nodes and edges. Each node points to a Python function. HUAP handles orchestration, tracing, human gates, and memory.

```
huap pod create research --description "Research agent"
```

This generates a full project scaffold: pod contract, workflow YAML, and tests.

### Path C: Mixed (Recommended for Large Orgs)

Wrap legacy agents with Path A for immediate traceability. Build new agents with Path B. Both produce the same trace format, so your CI pipeline and audit tooling work across both.

---

## 4. Operating Model

### Who Owns What

| Role | Responsibility |
|------|---------------|
| **Agent developer** | Writes pod code and graph YAML. Runs locally, commits golden traces as baselines. |
| **Platform / ML Ops** | Owns CI pipeline configuration, budget gates, and baseline refresh cadence. |
| **Reviewer / Approver** | Responds to human gate requests via `huap inbox`. Decisions are recorded in the trace. |
| **Compliance / Audit** | Reads HTML trace reports and CI diff outputs. No code access required. |

### Baseline Lifecycle

1. Developer runs agent, inspects trace, confirms correctness.
2. Developer commits trace as the golden baseline in `suites/<name>/baseline.jsonl`.
3. CI replays baseline on every PR. If output diverges, the PR is blocked.
4. When intentional changes are made (new model, updated prompt), developer refreshes the baseline and includes the diff in the PR description.

### Human Gate Flow

1. Agent graph hits a `human_gate` node and pauses.
2. Gate request is written to `.huap/inbox/` with severity, context, and suggested options.
3. Reviewer runs `huap inbox list`, inspects with `huap inbox show <id>`, and decides with `huap inbox approve <id>` or `huap inbox reject <id>`.
4. Decision (who, when, what, why) is recorded in the trace.
5. Agent resumes or halts based on the decision.

---

## 5. CI Cookbook

### When to Refresh Baselines

| Trigger | Action |
|---------|--------|
| Prompt wording change | Refresh baseline. Include before/after diff in PR. |
| Model upgrade (e.g., GPT-4 to GPT-4o) | Refresh baseline. Review cost and quality deltas. |
| New node added to graph | Refresh baseline. Old baseline will fail on event count mismatch. |
| Tool implementation change | Refresh baseline only if tool output format changed. |
| No code changes (flaky test) | Investigate non-determinism. Do NOT just refresh. |

### How to Triage Drift

1. **Read the CI output.** Look for `[FAIL]` lines. Each one names the scenario and the type of failure (diff, eval, or error).
2. **Open the diff report.** If CI produced an HTML report, open it in a browser. Look at the highlighted changes.
3. **Check cost delta.** Token or latency increases above 10% warrant investigation even if the output is correct.
4. **Check quality delta.** If evaluation scores dropped, compare the node outputs side by side.
5. **Decide: fix or refresh.** If the drift is unintentional, fix the code. If intentional, refresh the baseline and document why.

### What to Do When CI Fails

| Failure Type | Meaning | Resolution |
|-------------|---------|------------|
| **Replay mismatch** | Output hash differs from baseline | Check which node diverged. Fix non-determinism or refresh baseline. |
| **Budget violation** | Token count or cost exceeded threshold | Optimize prompts, reduce context, or raise the budget gate with justification. |
| **Eval regression** | Quality score dropped below threshold | Review prompt changes. Roll back or accept with documented rationale. |
| **Execution error** | Graph failed to run (import error, missing dep) | Fix the code. This is a standard bug. |

### Running CI Locally

```
huap ci run suites/flagship/suite.yaml
```

Add `--html reports/flagship.html` to generate a visual report for sharing.

---

## 6. Frequently Asked Questions

**Q: Do I need an OpenAI API key to try HUAP?**
No. HUAP ships with a stub mode (`HUAP_LLM_MODE=stub`) that returns deterministic responses with zero API calls. All demos and CI run in stub mode by default.

**Q: How is a HUAP trace different from normal logging?**
A HUAP trace is structured JSONL with a defined schema: every event has a run ID, span ID, kind, name, timestamp, and typed data payload. This structure enables automated replay, diffing, and evaluation -- none of which work with unstructured logs.

**Q: Can I use HUAP with my existing LangChain / CrewAI agents?**
Yes. Use `huap trace wrap` to capture a trace around any command. For LangChain specifically, a callback adapter is available that captures LLM and tool events automatically. CrewAI integration requires manual event emission (documented in the repo).

**Q: What happens if a human gate times out?**
The gate request stays in `pending` status in `.huap/inbox/`. The agent does not proceed until a decision is submitted. There is no automatic timeout -- this is by design for safety-critical workflows. If you need auto-approval, configure a policy in the gate node.

**Q: How much overhead does tracing add?**
Negligible for typical agent workloads. Trace events are appended to a JSONL file (one disk write per event). The bottleneck in any agent run is LLM latency, not trace I/O.

**Q: Can I run HUAP in production, or is it just for testing?**
HUAP is in public beta (v0.1.0b1). The trace format, CLI interface, and graph spec are stable. Memory and eval subsystems are maturing. Production deployments should pin the version and run CI baselines on every release.

**Q: Where are traces stored? Can I send them to a central system?**
Traces are local JSONL files by default. You can point `--out` to any path, including a shared filesystem or object store. A future release will add direct export to observability platforms.

**Q: How do I add HUAP CI to my GitHub Actions pipeline?**
Run `huap ci init` to generate a starter workflow file at `.github/workflows/huap-ci.yml`, a default budget config, and a suites directory. Commit and push -- CI will run on every PR.
