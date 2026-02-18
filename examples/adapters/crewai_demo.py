"""
CrewAI + HUAP adapter demo.

Runs in stub mode — no API keys or crewai install required.

Usage:
    python examples/adapters/crewai_demo.py
    huap trace view traces/crewai_demo.jsonl
"""
from hu_core.adapters.crewai import huap_trace_crewai

# Simulate a CrewAI-like run (stub, no crewai dependency needed)
with huap_trace_crewai(out="traces/crewai_demo.jsonl", run_name="crewai_stub_demo") as tracer:
    # Simulate agent steps manually (in real usage CrewAI patches would fire these)
    tracer.on_agent_step("researcher", "Find info about AI agents")
    tracer.on_tool_call("web_search", {"query": "AI agent frameworks 2025"})
    tracer.on_tool_result("web_search", {"results": ["HUAP", "CrewAI", "LangGraph"]}, duration_ms=120)
    tracer.on_llm_request("gpt-4o-mini", [{"role": "user", "content": "Summarize AI agent frameworks"}])
    tracer.on_llm_response("gpt-4o-mini", "AI agent frameworks include HUAP, CrewAI, and LangGraph.", usage={"prompt_tokens": 20, "completion_tokens": 15, "total_tokens": 35}, duration_ms=450)

    tracer.on_agent_step("writer", "Write a summary report")
    tracer.on_llm_request("gpt-4o-mini", [{"role": "user", "content": "Write a report on AI agents"}])
    tracer.on_llm_response("gpt-4o-mini", "# AI Agent Report\n\nAgents are cool.", usage={"prompt_tokens": 15, "completion_tokens": 10, "total_tokens": 25}, duration_ms=300)

print("CrewAI demo trace written to traces/crewai_demo.jsonl")
print("Run: huap trace view traces/crewai_demo.jsonl")
