# HUAP — After Beta Roadmap

## Message Tracking Gaps

### LangChain Adapter
- Inter-agent messages only captured as part of LLM request/response — no dedicated "agent-to-agent message" event type
- Streaming tokens (`on_llm_new_token`) not wired up — only final response captured
- LangChain internal memory (ConversationBufferMemory etc.) not extracted — only chain input/output visible
- Async parallel branches: events are flat, no parent_span_id linking parallel LangGraph nodes

### Native HUAP Graph
- Nodes communicate via shared state — every output is traced at `node_exit`
- No explicit "message" event type — agent-to-agent communication is implicit in state diffs
- Works well for pipeline patterns (A → B → C) but less visible for conversational agent patterns

## Proposed Action: Implement Agent Message Events

Add a `message` event kind to the trace schema so agents can explicitly log inter-agent communication:

```
kind: "message"
name: "agent_message"
data:
  from_agent: "researcher"
  to_agent: "analyst"
  content: "Found 3 relevant sources..."
  message_type: "handoff" | "request" | "response" | "broadcast"
```

This would:
- Give first-class visibility into multi-agent conversations
- Work for both native HUAP graphs and LangChain adapter
- Enable message-level diffing (did agents change what they say to each other?)
- Support conversational patterns (not just pipeline state passing)

Implementation: add `tracer.message()` helper, wire into LangChain adapter's chain callbacks, document for native graph node authors.

## Other Post-Beta Items
- Vector-based semantic search for memory (currently keyword/LIKE)
- LlamaIndex, AutoGen, Semantic Kernel adapters
- Web UI for inbox (browser-based gate review)
- Trace schema formalization (JSONSchema, versioned)
- Parent span tracking for parallel execution branches
