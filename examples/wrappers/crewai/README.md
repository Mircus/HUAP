# CrewAI + HUAP Tracing

Add HUAP tracing to CrewAI crews using manual instrumentation.
CrewAI does not expose a public callback API, so HUAP provides
explicit tracer methods you call around your CrewAI code.

## Prerequisites

```bash
# Install HUAP from source (not yet on PyPI)
pip install -e packages/hu-core

# CrewAI is NOT required — the demo runs in stub mode
```

## Run the demo

```bash
python examples/wrappers/crewai/run.py
```

This produces `traces/crewai_wrapper.jsonl`. Inspect it with:

```bash
huap trace view traces/crewai_wrapper.jsonl
```

## How it works

1. Open a `huap_trace_crewai` context manager with an output path.
2. Call tracer methods before/after each CrewAI operation.
3. The trace file is written automatically when the context exits.

Available tracer methods:
- `on_agent_step(agent_name, task)` -- agent begins a task
- `on_tool_call(tool_name, input)` -- tool invocation
- `on_tool_result(tool_name, result, duration_ms)` -- tool result
- `on_llm_request(model, messages)` -- LLM call
- `on_llm_response(model, text, usage, duration_ms)` -- LLM reply

## Real-world usage (with CrewAI installed)

```python
from crewai import Agent, Task, Crew
from hu_core.adapters.crewai import huap_trace_crewai

researcher = Agent(role="researcher", goal="Find info", llm="gpt-4o")
task = Task(description="Research AI agents", agent=researcher)
crew = Crew(agents=[researcher], tasks=[task])

with huap_trace_crewai(out="traces/my_crew.jsonl", run_name="research") as t:
    t.on_agent_step("researcher", "Research AI agents")
    result = crew.kickoff()
    t.on_llm_response("gpt-4o", str(result), usage={"total_tokens": 100})
```
