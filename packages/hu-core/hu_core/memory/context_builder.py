"""
Context Builder

Event-sourced context builder that reconstructs context from trace events.
Produces deterministic output for replay and evaluation.

The ContextBuilder extracts:
- Facts: Observed data from trace events
- Decisions: Choices made during workflow
- Artifacts: Generated outputs (plans, analyses)
- Critiques: Issues identified during execution
- Closure status: Whether critiques were addressed
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .providers.base import MemoryProvider, MemoryEntry, MemoryType

logger = logging.getLogger("huap.memory.context_builder")


@dataclass
class ContextFact:
    """A fact extracted from trace events."""
    key: str
    value: Any
    source_event: str
    timestamp: str
    pod: Optional[str] = None


@dataclass
class ContextDecision:
    """A decision made during workflow execution."""
    key: str
    decision: Any
    rationale: Optional[str] = None
    source_event: str = ""
    timestamp: str = ""
    pod: Optional[str] = None


@dataclass
class ContextArtifact:
    """An artifact generated during workflow execution."""
    key: str
    artifact: Any
    artifact_type: str
    source_event: str
    timestamp: str
    pod: Optional[str] = None


@dataclass
class ContextCritique:
    """A critique or issue identified during execution."""
    key: str
    critique: str
    severity: str = "info"  # info, warning, error
    related_to: Optional[str] = None
    is_closed: bool = False
    source_event: str = ""
    timestamp: str = ""
    pod: Optional[str] = None


@dataclass
class ContextData:
    """
    Complete context data extracted from a trace.

    Provides a deterministic view of what happened during execution.
    """
    run_id: str
    pod: Optional[str] = None
    facts: List[ContextFact] = field(default_factory=list)
    decisions: List[ContextDecision] = field(default_factory=list)
    artifacts: List[ContextArtifact] = field(default_factory=list)
    critiques: List[ContextCritique] = field(default_factory=list)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def critique_closed_rate(self) -> float:
        """Calculate the critique closure rate (for quality evaluation)."""
        if not self.critiques:
            return 1.0  # No critiques = perfect
        closed = sum(1 for c in self.critiques if c.is_closed)
        return closed / len(self.critiques)

    @property
    def open_critiques(self) -> List[ContextCritique]:
        """Get all open (unaddressed) critiques."""
        return [c for c in self.critiques if not c.is_closed]

    @property
    def content_hash(self) -> str:
        """Generate deterministic hash of context content."""
        content = {
            "run_id": self.run_id,
            "facts": [{"key": f.key, "value": f.value} for f in self.facts],
            "decisions": [{"key": d.key, "decision": d.decision} for d in self.decisions],
            "artifacts": [{"key": a.key, "type": a.artifact_type} for a in self.artifacts],
            "critiques": [{"key": c.key, "closed": c.is_closed} for c in self.critiques],
        }
        serialized = json.dumps(content, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "run_id": self.run_id,
            "pod": self.pod,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "facts": [
                {"key": f.key, "value": f.value, "source": f.source_event, "ts": f.timestamp}
                for f in self.facts
            ],
            "decisions": [
                {"key": d.key, "decision": d.decision, "rationale": d.rationale}
                for d in self.decisions
            ],
            "artifacts": [
                {"key": a.key, "type": a.artifact_type, "artifact": a.artifact}
                for a in self.artifacts
            ],
            "critiques": [
                {"key": c.key, "critique": c.critique, "severity": c.severity, "closed": c.is_closed}
                for c in self.critiques
            ],
            "critique_closed_rate": self.critique_closed_rate,
            "content_hash": self.content_hash,
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class ContextBuilder:
    """
    Builds context from trace events.

    The ContextBuilder processes trace events and extracts:
    - Facts from node/tool/llm events
    - Decisions from explicit decision events or LLM choices
    - Artifacts from generation events
    - Critiques from error/policy events

    The output is deterministic - the same trace always produces
    the same context, enabling reproducible evaluation.
    """

    def __init__(
        self,
        provider: Optional[MemoryProvider] = None,
    ):
        """
        Initialize the context builder.

        Args:
            provider: Optional memory provider for persistence
        """
        self._provider = provider

    async def build_from_trace(
        self,
        trace_path: str,
        *,
        persist: bool = False,
    ) -> ContextData:
        """
        Build context from a trace file.

        Args:
            trace_path: Path to JSONL trace file
            persist: If True, persist extracted context to memory provider

        Returns:
            ContextData with extracted facts, decisions, artifacts, critiques
        """
        path = Path(trace_path)
        if not path.exists():
            raise FileNotFoundError(f"Trace file not found: {trace_path}")

        events = []
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))

        return await self.build_from_events(events, persist=persist)

    async def build_from_events(
        self,
        events: List[Dict[str, Any]],
        *,
        persist: bool = False,
    ) -> ContextData:
        """
        Build context from a list of trace events.

        Args:
            events: List of trace event dictionaries
            persist: If True, persist extracted context to memory provider

        Returns:
            ContextData with extracted facts, decisions, artifacts, critiques
        """
        if not events:
            return ContextData(run_id="empty")

        # Extract run metadata
        run_id = events[0].get("run_id", "unknown")
        pod = events[0].get("pod")

        context = ContextData(
            run_id=run_id,
            pod=pod,
        )

        # Process each event
        for event in events:
            self._process_event(event, context)

        # Calculate final status
        if context.end_time:
            run_end = next((e for e in events if e.get("name") == "run_end"), None)
            if run_end:
                context.status = run_end.get("data", {}).get("status", "unknown")

        # Persist if requested
        if persist and self._provider:
            await self._persist_context(context)

        logger.info(
            f"Built context from {len(events)} events: "
            f"{len(context.facts)} facts, "
            f"{len(context.decisions)} decisions, "
            f"{len(context.artifacts)} artifacts, "
            f"{len(context.critiques)} critiques"
        )

        return context

    def _process_event(self, event: Dict[str, Any], context: ContextData) -> None:
        """Process a single trace event and extract context."""
        name = event.get("name", "")
        event.get("kind", "")
        data = event.get("data", {})
        ts = event.get("ts", "")
        pod = event.get("pod")

        # Run lifecycle
        if name == "run_start":
            context.start_time = ts
            context.metadata["input_keys"] = data.get("input_keys", [])
            context.metadata["config"] = data.get("config", {})

        elif name == "run_end":
            context.end_time = ts
            context.metadata["output_keys"] = data.get("output_keys", [])
            context.metadata["duration_ms"] = data.get("duration_ms")

        # Node events -> Facts
        elif name == "node_enter":
            context.facts.append(ContextFact(
                key=f"node_state:{data.get('node', 'unknown')}",
                value={"state_keys": data.get("state_keys", [])},
                source_event=name,
                timestamp=ts,
                pod=pod,
            ))

        elif name == "node_exit":
            node_name = data.get("node", "unknown")
            output = data.get("output", {})
            if output:
                context.facts.append(ContextFact(
                    key=f"node_output:{node_name}",
                    value=output,
                    source_event=name,
                    timestamp=ts,
                    pod=pod,
                ))

        # Tool events -> Facts
        elif name == "tool_call":
            tool_name = data.get("tool", "unknown")
            context.facts.append(ContextFact(
                key=f"tool_input:{tool_name}:{ts}",
                value=data.get("input", {}),
                source_event=name,
                timestamp=ts,
                pod=pod,
            ))

        elif name == "tool_result":
            tool_name = data.get("tool", "unknown")
            status = data.get("status", "unknown")
            context.facts.append(ContextFact(
                key=f"tool_output:{tool_name}:{ts}",
                value=data.get("result", {}),
                source_event=name,
                timestamp=ts,
                pod=pod,
            ))

            # Tool errors become critiques
            if status == "error":
                context.critiques.append(ContextCritique(
                    key=f"tool_error:{tool_name}:{ts}",
                    critique=f"Tool '{tool_name}' failed: {data.get('error', 'unknown')}",
                    severity="error",
                    source_event=name,
                    timestamp=ts,
                    pod=pod,
                ))

        # LLM events -> Decisions/Artifacts
        elif name == "llm_request":
            # Extract decision context
            messages = data.get("messages", [])
            if messages:
                context.facts.append(ContextFact(
                    key=f"llm_prompt:{ts}",
                    value={"message_count": len(messages)},
                    source_event=name,
                    timestamp=ts,
                    pod=pod,
                ))

        elif name == "llm_response":
            # LLM responses are often artifacts or decisions
            text = data.get("text", "")
            if text:
                # Detect if it's a structured output (artifact)
                if "{" in text and "}" in text:
                    try:
                        parsed = json.loads(text)
                        context.artifacts.append(ContextArtifact(
                            key=f"llm_output:{ts}",
                            artifact=parsed,
                            artifact_type="llm_generation",
                            source_event=name,
                            timestamp=ts,
                            pod=pod,
                        ))
                    except json.JSONDecodeError:
                        # Not valid JSON, treat as decision
                        context.decisions.append(ContextDecision(
                            key=f"llm_decision:{ts}",
                            decision=text[:500],  # Truncate for storage
                            source_event=name,
                            timestamp=ts,
                            pod=pod,
                        ))
                else:
                    context.decisions.append(ContextDecision(
                        key=f"llm_decision:{ts}",
                        decision=text[:500],
                        source_event=name,
                        timestamp=ts,
                        pod=pod,
                    ))

        # Policy events -> Critiques
        elif name == "policy_check":
            if not data.get("passed", True):
                context.critiques.append(ContextCritique(
                    key=f"policy_violation:{ts}",
                    critique=data.get("message", "Policy check failed"),
                    severity="error",
                    source_event=name,
                    timestamp=ts,
                    pod=pod,
                ))

        # Error events -> Critiques
        elif name == "error":
            context.critiques.append(ContextCritique(
                key=f"error:{ts}",
                critique=data.get("message", "Unknown error"),
                severity="error",
                related_to=data.get("node"),
                source_event=name,
                timestamp=ts,
                pod=pod,
            ))

        # Quality events -> Facts
        elif name == "quality_record":
            context.facts.append(ContextFact(
                key=f"quality:{data.get('metric', 'unknown')}",
                value=data.get("value"),
                source_event=name,
                timestamp=ts,
                pod=pod,
            ))

        # Cost events -> Facts
        elif name == "cost_record":
            context.facts.append(ContextFact(
                key=f"cost:{ts}",
                value={
                    "tokens": data.get("tokens"),
                    "usd": data.get("usd"),
                },
                source_event=name,
                timestamp=ts,
                pod=pod,
            ))

    async def _persist_context(self, context: ContextData) -> None:
        """Persist context to memory provider."""
        if not self._provider:
            return

        # Store facts
        for fact in context.facts:
            await self._provider.store_fact(
                key=fact.key,
                value=fact.value,
                run_id=context.run_id,
                pod_name=context.pod,
            )

        # Store decisions
        for decision in context.decisions:
            await self._provider.store_decision(
                key=decision.key,
                decision=decision.decision,
                run_id=context.run_id,
                pod_name=context.pod,
                rationale=decision.rationale,
            )

        # Store artifacts
        for artifact in context.artifacts:
            await self._provider.store_artifact(
                key=artifact.key,
                artifact=artifact.artifact,
                run_id=context.run_id,
                pod_name=context.pod,
                artifact_type=artifact.artifact_type,
            )

        # Store critiques
        for critique in context.critiques:
            entry = MemoryEntry(
                key=critique.key,
                value=critique.critique,
                memory_type=MemoryType.CRITIQUE,
                namespace="critiques",
                run_id=context.run_id,
                pod_name=context.pod,
                is_closed=critique.is_closed,
                metadata={"severity": critique.severity},
            )
            await self._provider.set(entry)


def extract_critique_closed_metric(context: ContextData) -> Dict[str, Any]:
    """
    Extract critique_closed metric for quality evaluation.

    Returns:
        Dictionary with critique closure metrics
    """
    return {
        "metric": "critique_closed",
        "value": context.critique_closed_rate,
        "total_critiques": len(context.critiques),
        "closed_critiques": len([c for c in context.critiques if c.is_closed]),
        "open_critiques": len(context.open_critiques),
        "details": {
            "open": [
                {"key": c.key, "severity": c.severity, "critique": c.critique}
                for c in context.open_critiques
            ]
        },
    }
