# LangChain + HUAP Tracing

Add deterministic HUAP tracing to any LangChain chain or agent
with a single callback handler.

## Prerequisites

```bash
# Install HUAP from source (not yet on PyPI)
pip install -e packages/hu-core

# LangChain is NOT required — the demo runs in stub mode
```

## Run the demo

```bash
python examples/wrappers/langchain/run.py
```

This produces `traces/langchain_wrapper.jsonl`. Inspect it with:

```bash
huap trace view traces/langchain_wrapper.jsonl
```

## How it works

1. Create a `HuapCallbackHandler` with an output path.
2. Pass it as a LangChain callback: `chain.invoke(input, config={"callbacks": [handler]})`.
3. Call `handler.flush()` to write the trace file.

The handler captures LLM calls, tool invocations, chain start/end,
and retriever events — all as standard HUAP trace events.

## Real-world usage (with LangChain installed)

```python
from langchain_openai import ChatOpenAI
from hu_core.adapters.langchain import HuapCallbackHandler

handler = HuapCallbackHandler(out="traces/my_run.jsonl", run_name="qa_chain")
llm = ChatOpenAI(model="gpt-4o", callbacks=[handler])
result = llm.invoke("What is HUAP?")
handler.flush()
```
