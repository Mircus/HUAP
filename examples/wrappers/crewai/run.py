"""
CrewAI + HUAP wrapper example.

Demonstrates huap_trace_crewai context manager in stub mode — no
API keys or CrewAI install required. Produces a HUAP trace file.

Usage:
    python examples/wrappers/crewai/run.py
    huap trace view traces/crewai_wrapper.jsonl
"""
from hu_core.adapters.crewai import huap_trace_crewai

# Open the tracer context — trace is written automatically on exit
with huap_trace_crewai(
    out="traces/crewai_wrapper.jsonl",
    run_name="crewai_wrapper_demo",
) as tracer:

    # --- Agent 1: researcher ---
    tracer.on_agent_step("researcher", "Find information about HUAP")
    tracer.on_tool_call("web_search", {"query": "HUAP agent framework"})
    tracer.on_tool_result(
        "web_search",
        {"results": ["HUAP: trace-first AI agent platform"]},
        duration_ms=95,
    )
    tracer.on_llm_request(
        "gpt-4o",
        [{"role": "user", "content": "Summarize what HUAP is"}],
    )
    tracer.on_llm_response(
        "gpt-4o",
        "HUAP is a deterministic, trace-first framework for building AI agents.",
        usage={"prompt_tokens": 18, "completion_tokens": 14, "total_tokens": 32},
        duration_ms=320,
    )

    # --- Agent 2: writer ---
    tracer.on_agent_step("writer", "Draft a one-paragraph summary")
    tracer.on_llm_request(
        "gpt-4o",
        [{"role": "user", "content": "Write a short summary of HUAP"}],
    )
    tracer.on_llm_response(
        "gpt-4o",
        "HUAP provides YAML-defined graphs, pluggable pods, and full trace replay.",
        usage={"prompt_tokens": 14, "completion_tokens": 12, "total_tokens": 26},
        duration_ms=280,
    )

print("Trace written to traces/crewai_wrapper.jsonl")
print("Inspect with:  huap trace view traces/crewai_wrapper.jsonl")
