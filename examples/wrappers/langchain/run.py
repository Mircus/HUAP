"""
LangChain + HUAP wrapper example.

Demonstrates HuapCallbackHandler in stub mode — no API keys or
LangChain install required. Produces a HUAP trace file.

Usage:
    python examples/wrappers/langchain/run.py
    huap trace view traces/langchain_wrapper.jsonl
"""
from hu_core.adapters.langchain import HuapCallbackHandler

# 1. Create the handler (trace sink)
handler = HuapCallbackHandler(
    out="traces/langchain_wrapper.jsonl",
    run_name="langchain_wrapper_demo",
)

# 2. Simulate a LangChain chain run (no real LangChain needed)
handler.on_chain_start(
    {"name": "SummarizeChain", "id": ["langchain", "chains", "SummarizeChain"]},
    {"input": "Explain HUAP in one sentence."},
)

handler.on_llm_start(
    {"name": "gpt-4o-mini", "id": ["langchain", "llms", "openai"]},
    ["Explain HUAP in one sentence."],
)


# Mock LangChain response objects (avoids importing langchain)
class _Gen:
    text = "HUAP is a deterministic, trace-first framework for AI agents."


class _Resp:
    generations = [[_Gen()]]
    llm_output = {
        "token_usage": {"prompt_tokens": 12, "completion_tokens": 14, "total_tokens": 26},
        "model_name": "gpt-4o-mini",
    }


handler.on_llm_end(_Resp())

handler.on_chain_end({"result": _Gen.text})

# 3. Flush events to disk
path = handler.flush()

print(f"Trace written to {path}")
print(f"Inspect with:  huap trace view {path}")
