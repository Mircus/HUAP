"""
Flagship Demo Nodes — 5-step agent workflow showcasing HUAP's full stack.

Pipeline: research → analyze → gate → synthesize → memorize

Each node is deterministic in stub mode (no API keys needed).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict


# ---------------------------------------------------------------------------
# Node 1: Research — gather data using safe tools
# ---------------------------------------------------------------------------

async def research(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate research step: fetch data from safe sources.

    In a real deployment this would call http_fetch_safe or external APIs.
    In stub mode, returns deterministic sample data.
    """
    topic = state.get("topic", "AI agent frameworks")
    return {
        "research_results": [
            {
                "source": "arxiv",
                "title": f"Survey of {topic}",
                "summary": f"Comprehensive review of {topic} covering reproducibility, "
                           "tracing, and evaluation methodologies.",
                "relevance": 0.95,
            },
            {
                "source": "github",
                "title": f"Open-source tools for {topic}",
                "summary": "Analysis of 12 frameworks with focus on deterministic replay, "
                           "CI integration, and human-in-the-loop governance.",
                "relevance": 0.88,
            },
            {
                "source": "industry",
                "title": "Enterprise adoption patterns",
                "summary": "Case studies from 5 enterprises deploying agent systems "
                           "with audit trails and cost controls.",
                "relevance": 0.82,
            },
        ],
        "research_status": "complete",
    }


# ---------------------------------------------------------------------------
# Node 2: Analyze — process research results
# ---------------------------------------------------------------------------

async def analyze(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze research results and extract key insights.

    In a real deployment this would use an LLM for synthesis.
    """
    results = state.get("research_results", [])
    n_sources = len(results)
    avg_relevance = sum(r["relevance"] for r in results) / n_sources if n_sources else 0

    insights = [
        "Deterministic replay is the top differentiator for agent CI",
        "Human gates reduce deployment risk by 73% in regulated industries",
        "Local-first memory eliminates vendor lock-in for knowledge persistence",
    ]

    return {
        "analysis": {
            "sources_reviewed": n_sources,
            "avg_relevance": round(avg_relevance, 2),
            "key_insights": insights,
            "risk_assessment": "low" if avg_relevance > 0.8 else "medium",
            "recommendation": "proceed",
        },
    }


# ---------------------------------------------------------------------------
# Node 3: Gate — human approval checkpoint
# ---------------------------------------------------------------------------

async def gate(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Human gate: pause for review before synthesis.

    In the flagship demo, this auto-approves to keep the flow non-blocking.
    The gate request is still written to .huap/inbox/ for inspection.
    """
    from hu_core.runtime.human_gate import create_gate, submit_decision

    analysis = state.get("analysis", {})
    risk = analysis.get("risk_assessment", "unknown")
    recommendation = analysis.get("recommendation", "unknown")

    # Create a gate request
    run_id = state.get("_run_id", "flagship_demo")
    gate_req = create_gate(
        run_id=run_id,
        title="Approve synthesis of research findings",
        severity="medium",
        summary=f"Risk: {risk}, Recommendation: {recommendation}, "
                f"Sources: {analysis.get('sources_reviewed', 0)}",
        context={"analysis_summary": analysis},
    )

    # Auto-approve in demo mode (user can also use `huap inbox approve` manually)
    decision = submit_decision(
        run_id=run_id,
        gate_id=gate_req.gate_id,
        decision="approve",
        note="Auto-approved by flagship demo",
    )

    return {
        "gate_status": "approved",
        "gate_id": gate_req.gate_id,
        "gate_decision": decision.decision,
    }


# ---------------------------------------------------------------------------
# Node 4: Synthesize — produce the final output (memo)
# ---------------------------------------------------------------------------

async def synthesize(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Produce a structured memo from the analyzed research.

    This is the "product" of the agent — a shareable markdown document.
    """
    analysis = state.get("analysis", {})
    insights = analysis.get("key_insights", [])
    results = state.get("research_results", [])
    topic = state.get("topic", "AI agent frameworks")
    gate_status = state.get("gate_status", "unknown")

    # Build the memo
    lines = [
        f"# Research Memo: {topic}",
        f"*Generated by HUAP Flagship Demo — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
        "## Summary",
        f"Reviewed **{len(results)} sources** with average relevance "
        f"**{analysis.get('avg_relevance', 0):.0%}**.",
        f"Risk assessment: **{analysis.get('risk_assessment', 'N/A')}** | "
        f"Gate: **{gate_status}**",
        "",
        "## Key Insights",
    ]
    for i, insight in enumerate(insights, 1):
        lines.append(f"{i}. {insight}")

    lines += [
        "",
        "## Sources",
    ]
    for r in results:
        lines.append(f"- **{r['title']}** ({r['source']}) — relevance: {r['relevance']:.0%}")

    lines += [
        "",
        "## Next Steps",
        "- [ ] Review this memo with stakeholders",
        "- [ ] Run `huap ci run suites/flagship` to verify reproducibility",
        "- [ ] Run `huap demo flagship --with-memory` to test cross-session recall",
        "",
        "---",
        "*Trace: check `out/trace.jsonl` and `out/trace.html` for the full flight record.*",
    ]

    memo_content = "\n".join(lines)

    return {
        "memo": memo_content,
        "synthesis_status": "complete",
    }


# ---------------------------------------------------------------------------
# Node 5: Memorize — persist key findings for cross-session recall
# ---------------------------------------------------------------------------

async def memorize(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retain key findings in memory for future recall.

    Uses the MemoryPort interface (InMemoryPort in stub mode,
    HindsightProvider with --with-memory flag).
    """
    from hu_core.tools.memory_tools import memory_retain, memory_recall

    analysis = state.get("analysis", {})
    topic = state.get("topic", "AI agent frameworks")
    port = state.get("_memory_port")  # injected by demo runner if --with-memory

    # Retain key insights
    insights = analysis.get("key_insights", [])
    retained_ids = []
    for insight in insights:
        result = await memory_retain(
            bank_id="flagship",
            content=insight,
            context="insight",
            metadata={"topic": topic, "source": "flagship_demo"},
            port=port,
            tracer=state.get("_tracer"),
        )
        retained_ids.append(result["item"]["id"])

    # Recall to verify (and demonstrate the recall path)
    recall_result = await memory_recall(
        bank_id="flagship",
        query=topic,
        k=5,
        port=port,
        tracer=state.get("_tracer"),
    )

    return {
        "memory_retained": len(retained_ids),
        "memory_recalled": recall_result["count"],
        "memorize_status": "complete",
    }
