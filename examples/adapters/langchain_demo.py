"""
LangChain + HUAP adapter demo.

Runs in stub mode — no API keys or langchain install required.

Usage:
    python examples/adapters/langchain_demo.py
    huap trace view traces/langchain_demo.jsonl
"""
from hu_core.adapters.langchain import HuapCallbackHandler

handler = HuapCallbackHandler(out="traces/langchain_demo.jsonl", run_name="langchain_stub_demo")

# Simulate LangChain callbacks manually (no langchain dependency needed)
handler.on_chain_start(
    {"name": "RetrievalQA", "id": ["langchain", "chains", "RetrievalQA"]},
    {"query": "What is HUAP?"},
)

handler.on_llm_start(
    {"name": "gpt-4o-mini", "id": ["langchain", "llms", "openai"]},
    ["What is HUAP?"],
)

# Simulate LLM response (mock object)
class MockGeneration:
    text = "HUAP is a trace-first agent framework."

class MockResponse:
    generations = [[MockGeneration()]]
    llm_output = {"token_usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18}}

handler.on_llm_end(MockResponse())

handler.on_tool_start(
    {"name": "web_search"},
    "HUAP framework",
)
handler.on_tool_end("HUAP: trace-first primitives for deterministic agents")

handler.on_chain_end({"result": "HUAP is a trace-first agent framework."})

path = handler.flush()
print(f"LangChain demo trace written to {path}")
print("Run: huap trace view traces/langchain_demo.jsonl")
