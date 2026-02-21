"""
HUAP Trace Differ - Compare two traces and identify differences.

Provides:
- TraceDiffer for semantic comparison of traces
- Detection of regressions (errors, missing events, cost/quality changes)
- Severity levels (INFO, WARN, FAIL) for CI integration
- Configurable diff policies via YAML
- Markdown and JSON output formats
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from .models import TraceEvent, TraceRun, EventKind, EventName


# =============================================================================
# SEVERITY LEVELS
# =============================================================================

class DiffSeverity(str, Enum):
    """Severity levels for diff findings."""
    INFO = "info"       # Informational, no action needed
    WARN = "warn"       # Warning, should be reviewed
    FAIL = "fail"       # Failure, CI should fail


@dataclass
class DiffPolicy:
    """
    Policy for evaluating trace diffs.

    Controls what counts as a regression and at what severity.
    Can be loaded from YAML configuration.
    """
    # Thresholds for cost increases (percentage)
    token_increase_warn_pct: float = 20.0    # >20% token increase = WARN
    token_increase_fail_pct: float = 50.0    # >50% token increase = FAIL
    usd_increase_warn_pct: float = 20.0
    usd_increase_fail_pct: float = 50.0
    latency_increase_warn_pct: float = 50.0
    latency_increase_fail_pct: float = 100.0

    # Fields to ignore in comparisons
    ignore_fields: List[str] = field(default_factory=lambda: [
        "timestamp", "run_id", "span_id", "parent_span_id",
        "duration_ms",  # Duration varies
    ])

    # Event types where removal is only INFO (not FAIL)
    removals_info_only: List[str] = field(default_factory=lambda: [
        "quality_record", "cost_record",  # Metadata events
    ])

    # Allow new errors without failing (for testing)
    allow_new_errors: bool = False

    @classmethod
    def from_yaml(cls, path: Path) -> "DiffPolicy":
        """Load policy from YAML file."""
        import yaml

        if not path.exists():
            return cls()

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        return cls(
            token_increase_warn_pct=data.get("token_increase_warn_pct", 20.0),
            token_increase_fail_pct=data.get("token_increase_fail_pct", 50.0),
            usd_increase_warn_pct=data.get("usd_increase_warn_pct", 20.0),
            usd_increase_fail_pct=data.get("usd_increase_fail_pct", 50.0),
            latency_increase_warn_pct=data.get("latency_increase_warn_pct", 50.0),
            latency_increase_fail_pct=data.get("latency_increase_fail_pct", 100.0),
            ignore_fields=data.get("ignore_fields", cls.ignore_fields),
            removals_info_only=data.get("removals_info_only", []),
            allow_new_errors=data.get("allow_new_errors", False),
        )

    @classmethod
    def default(cls) -> "DiffPolicy":
        """Return default policy."""
        return cls()


@dataclass
class EventDiff:
    """Difference between two events."""
    event_key: str  # Unique key for matching (kind/name/node/tool)
    baseline_event: Optional[TraceEvent]
    candidate_event: Optional[TraceEvent]
    diff_type: str  # "added" | "removed" | "changed"
    changes: Dict[str, Tuple[Any, Any]] = field(default_factory=dict)  # field -> (old, new)
    severity: DiffSeverity = DiffSeverity.INFO

    @property
    def is_regression(self) -> bool:
        """Check if this diff represents a regression (WARN or FAIL)."""
        return self.severity in (DiffSeverity.WARN, DiffSeverity.FAIL)

    def evaluate_severity(self, policy: Optional[DiffPolicy] = None) -> DiffSeverity:
        """
        Evaluate the severity of this diff based on policy.

        Returns severity and updates self.severity.
        """
        policy = policy or DiffPolicy.default()

        if self.diff_type == "removed":
            # Removing required events
            if self.baseline_event:
                event_name = self.baseline_event.name.value if hasattr(self.baseline_event.name, 'value') else str(self.baseline_event.name)
                if event_name in policy.removals_info_only:
                    self.severity = DiffSeverity.INFO
                elif self.baseline_event.name in (
                    EventName.RUN_START, EventName.RUN_END,
                    EventName.NODE_ENTER, EventName.NODE_EXIT,
                ):
                    self.severity = DiffSeverity.FAIL
                else:
                    self.severity = DiffSeverity.WARN

        elif self.diff_type == "changed":
            # Status changes
            if "status" in self.changes:
                old, new = self.changes["status"]
                if old == "ok" and new in ("error", "timeout"):
                    self.severity = DiffSeverity.FAIL
                elif old == "success" and new == "error":
                    self.severity = DiffSeverity.FAIL
                else:
                    self.severity = DiffSeverity.WARN

            # Policy violations
            elif "decision" in self.changes:
                old, new = self.changes["decision"]
                if old == "allow" and new == "deny":
                    self.severity = DiffSeverity.FAIL
                else:
                    self.severity = DiffSeverity.WARN
            else:
                # Other changes are INFO by default
                self.severity = DiffSeverity.INFO

        elif self.diff_type == "added":
            # Added events are usually INFO
            self.severity = DiffSeverity.INFO

        return self.severity


@dataclass
class CostDelta:
    """Difference in cost metrics between traces."""
    baseline_tokens: int = 0
    candidate_tokens: int = 0
    baseline_usd: float = 0.0
    candidate_usd: float = 0.0
    baseline_latency_ms: float = 0.0
    candidate_latency_ms: float = 0.0

    @property
    def tokens_delta(self) -> int:
        return self.candidate_tokens - self.baseline_tokens

    @property
    def usd_delta(self) -> float:
        return self.candidate_usd - self.baseline_usd

    @property
    def latency_delta_ms(self) -> float:
        return self.candidate_latency_ms - self.baseline_latency_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "baseline_tokens": self.baseline_tokens,
            "candidate_tokens": self.candidate_tokens,
            "tokens_delta": self.tokens_delta,
            "baseline_usd": self.baseline_usd,
            "candidate_usd": self.candidate_usd,
            "usd_delta": self.usd_delta,
            "baseline_latency_ms": self.baseline_latency_ms,
            "candidate_latency_ms": self.candidate_latency_ms,
            "latency_delta_ms": self.latency_delta_ms,
        }


@dataclass
class QualityDelta:
    """Difference in quality metrics between traces."""
    baseline_metrics: Dict[str, float] = field(default_factory=dict)
    candidate_metrics: Dict[str, float] = field(default_factory=dict)

    def get_delta(self, metric: str) -> float:
        baseline = self.baseline_metrics.get(metric, 0.0)
        candidate = self.candidate_metrics.get(metric, 0.0)
        return candidate - baseline

    def all_deltas(self) -> Dict[str, float]:
        all_metrics = set(self.baseline_metrics.keys()) | set(self.candidate_metrics.keys())
        return {metric: self.get_delta(metric) for metric in all_metrics}

    def to_dict(self) -> Dict[str, float]:
        return self.all_deltas()


class TraceDiffer:
    """
    Compare two traces and identify differences.

    Usage:
        differ = TraceDiffer()
        result = differ.diff("baseline.jsonl", "candidate.jsonl")
        markdown = differ.to_markdown(result)

        # With policy
        policy = DiffPolicy.from_yaml(Path("suites/smoke/diff_policy.yaml"))
        differ = TraceDiffer(policy=policy)
        result = differ.diff("baseline.jsonl", "candidate.jsonl")
        if result["overall_severity"] == "fail":
            sys.exit(1)  # CI fails
    """

    def __init__(
        self,
        ignore_timestamps: bool = True,
        ignore_span_ids: bool = True,
        ignore_run_ids: bool = True,
        policy: Optional[DiffPolicy] = None,
    ):
        self.ignore_timestamps = ignore_timestamps
        self.ignore_span_ids = ignore_span_ids
        self.ignore_run_ids = ignore_run_ids
        self.policy = policy or DiffPolicy.default()

    def diff(self, baseline_path: str, candidate_path: str) -> Dict[str, Any]:
        """
        Compare two trace files.

        Args:
            baseline_path: Path to baseline trace
            candidate_path: Path to candidate trace

        Returns:
            Dict with diff results
        """
        # Load traces
        baseline = TraceRun.from_jsonl_file(baseline_path)
        candidate = TraceRun.from_jsonl_file(candidate_path)

        # Build event sequences
        baseline_events = self._index_events(baseline.events)
        candidate_events = self._index_events(candidate.events)

        # Find differences
        added = []
        removed = []
        changed = []

        # Check for removed/changed events
        for key, b_event in baseline_events.items():
            if key not in candidate_events:
                diff = EventDiff(
                    event_key=key,
                    baseline_event=b_event,
                    candidate_event=None,
                    diff_type="removed",
                )
                diff.evaluate_severity(self.policy)
                removed.append(diff)
            else:
                c_event = candidate_events[key]
                changes = self._compare_events(b_event, c_event)
                if changes:
                    diff = EventDiff(
                        event_key=key,
                        baseline_event=b_event,
                        candidate_event=c_event,
                        diff_type="changed",
                        changes=changes,
                    )
                    diff.evaluate_severity(self.policy)
                    changed.append(diff)

        # Check for added events
        for key, c_event in candidate_events.items():
            if key not in baseline_events:
                diff = EventDiff(
                    event_key=key,
                    baseline_event=None,
                    candidate_event=c_event,
                    diff_type="added",
                )
                diff.evaluate_severity(self.policy)
                added.append(diff)

        # Calculate cost delta
        cost_delta = self._calculate_cost_delta(baseline, candidate)

        # Calculate quality delta
        quality_delta = self._calculate_quality_delta(baseline, candidate)

        # Identify regressions
        regressions = []
        for diff in removed + changed:
            if diff.is_regression:
                regressions.append(self._describe_regression(diff))

        # Check for new errors in candidate
        for event in candidate.events:
            if event.name == EventName.ERROR:
                event_data = event.data if isinstance(event.data, dict) else event.data.model_dump()
                regressions.append(f"New error: {event_data.get('error_type', 'unknown')}: {event_data.get('message', '')}")

        # Check for tool errors
        candidate_tool_errors = self._count_tool_errors(candidate)
        baseline_tool_errors = self._count_tool_errors(baseline)
        if candidate_tool_errors > baseline_tool_errors:
            regressions.append(f"Tool errors increased: {baseline_tool_errors} -> {candidate_tool_errors}")

        # Check for policy violations
        candidate_violations = self._count_policy_violations(candidate)
        baseline_violations = self._count_policy_violations(baseline)
        if candidate_violations > baseline_violations:
            regressions.append(f"Policy violations increased: {baseline_violations} -> {candidate_violations}")

        # Evaluate cost severity based on policy thresholds
        cost_severity = self._evaluate_cost_severity(cost_delta)

        # Calculate overall severity (highest of all findings)
        all_severities = [d.severity for d in added + removed + changed]
        all_severities.append(cost_severity)

        # New errors are FAIL severity (unless allowed by policy)
        has_new_errors = any(
            event.name == EventName.ERROR
            for event in candidate.events
        )
        if has_new_errors and not self.policy.allow_new_errors:
            all_severities.append(DiffSeverity.FAIL)

        # Determine overall severity
        if DiffSeverity.FAIL in all_severities:
            overall_severity = DiffSeverity.FAIL
        elif DiffSeverity.WARN in all_severities:
            overall_severity = DiffSeverity.WARN
        else:
            overall_severity = DiffSeverity.INFO

        return {
            "baseline_run_id": baseline.run_id,
            "candidate_run_id": candidate.run_id,
            "baseline_event_count": len(baseline.events),
            "candidate_event_count": len(candidate.events),
            "added": [self._event_diff_to_dict(d) for d in added],
            "removed": [self._event_diff_to_dict(d) for d in removed],
            "changed": [self._event_diff_to_dict(d) for d in changed],
            "cost_delta": cost_delta.to_dict(),
            "cost_severity": cost_severity.value,
            "quality_delta": quality_delta.to_dict(),
            "regressions": regressions,
            "overall_severity": overall_severity.value,
        }

    def _index_events(self, events: List[TraceEvent]) -> Dict[str, TraceEvent]:
        """
        Create index of events by semantic key.

        Key format: {sequence}_{kind}_{name}_{identifier}
        """
        indexed = {}
        counters: Dict[str, int] = {}

        for event in events:
            # Build semantic key
            event_data = event.data if isinstance(event.data, dict) else event.data.model_dump()

            identifier = ""
            if event.kind == EventKind.NODE:
                identifier = event_data.get("node", "")
            elif event.kind == EventKind.TOOL:
                identifier = event_data.get("tool", "")
            elif event.kind == EventKind.LLM:
                identifier = event_data.get("model", "")
            elif event.kind == EventKind.POLICY:
                identifier = event_data.get("policy", "")

            base_key = f"{event.kind}_{event.name}_{identifier}"

            # Add sequence number for duplicate keys
            count = counters.get(base_key, 0)
            counters[base_key] = count + 1

            key = f"{count}_{base_key}"
            indexed[key] = event

        return indexed

    def _compare_events(
        self,
        baseline: TraceEvent,
        candidate: TraceEvent,
    ) -> Dict[str, Tuple[Any, Any]]:
        """Compare two events and return differences."""
        changes = {}

        b_data = baseline.data if isinstance(baseline.data, dict) else baseline.data.model_dump()
        c_data = candidate.data if isinstance(candidate.data, dict) else candidate.data.model_dump()

        # Compare relevant fields based on event type
        compare_fields = self._get_compare_fields(baseline.name)

        for fld in compare_fields:
            b_val = b_data.get(fld)
            c_val = c_data.get(fld)

            if b_val != c_val:
                # Skip hash differences (these are expected for different inputs)
                if fld.endswith("_hash"):
                    continue
                # Skip duration differences within tolerance
                if fld == "duration_ms":
                    if b_val and c_val:
                        # Allow 50% variance in duration
                        if abs(b_val - c_val) / max(b_val, 1) < 0.5:
                            continue
                changes[fld] = (b_val, c_val)

        return changes

    def _get_compare_fields(self, event_name: EventName) -> List[str]:
        """Get fields to compare for an event type."""
        common = ["status", "error"]

        field_map = {
            EventName.NODE_ENTER: ["node"] + common,
            EventName.NODE_EXIT: ["node", "output", "duration_ms"] + common,
            EventName.TOOL_CALL: ["tool", "input"] + common,
            EventName.TOOL_RESULT: ["tool", "result", "duration_ms"] + common,
            EventName.LLM_REQUEST: ["model", "temperature", "max_tokens"] + common,
            EventName.LLM_RESPONSE: ["model", "text", "usage"] + common,
            EventName.POLICY_CHECK: ["policy", "decision", "reason"] + common,
            EventName.RUN_START: ["pod", "graph"] + common,
            EventName.RUN_END: ["status", "duration_ms", "error"] + common,
        }

        return field_map.get(event_name, common)

    def _calculate_cost_delta(self, baseline: TraceRun, candidate: TraceRun) -> CostDelta:
        """Calculate cost differences between traces."""
        delta = CostDelta()

        for event in baseline.events:
            if event.name == EventName.COST_RECORD:
                data = event.data if isinstance(event.data, dict) else event.data.model_dump()
                delta.baseline_tokens += data.get("tokens", 0)
                delta.baseline_usd += data.get("usd_est", 0)
                delta.baseline_latency_ms += data.get("latency_ms", 0)

        for event in candidate.events:
            if event.name == EventName.COST_RECORD:
                data = event.data if isinstance(event.data, dict) else event.data.model_dump()
                delta.candidate_tokens += data.get("tokens", 0)
                delta.candidate_usd += data.get("usd_est", 0)
                delta.candidate_latency_ms += data.get("latency_ms", 0)

        return delta

    def _calculate_quality_delta(self, baseline: TraceRun, candidate: TraceRun) -> QualityDelta:
        """Calculate quality metric differences between traces."""
        delta = QualityDelta()

        for event in baseline.events:
            if event.name == EventName.QUALITY_RECORD:
                data = event.data if isinstance(event.data, dict) else event.data.model_dump()
                metric = data.get("metric", "unknown")
                value = data.get("value", 0.0)
                delta.baseline_metrics[metric] = value

        for event in candidate.events:
            if event.name == EventName.QUALITY_RECORD:
                data = event.data if isinstance(event.data, dict) else event.data.model_dump()
                metric = data.get("metric", "unknown")
                value = data.get("value", 0.0)
                delta.candidate_metrics[metric] = value

        return delta

    def _count_tool_errors(self, trace: TraceRun) -> int:
        """Count tool execution errors in a trace."""
        count = 0
        for event in trace.events:
            if event.name == EventName.TOOL_RESULT:
                data = event.data if isinstance(event.data, dict) else event.data.model_dump()
                if data.get("status") == "error":
                    count += 1
        return count

    def _count_policy_violations(self, trace: TraceRun) -> int:
        """Count policy violations in a trace."""
        count = 0
        for event in trace.events:
            if event.name == EventName.POLICY_CHECK:
                data = event.data if isinstance(event.data, dict) else event.data.model_dump()
                if data.get("decision") == "deny":
                    count += 1
        return count

    def _evaluate_cost_severity(self, cost_delta: CostDelta) -> DiffSeverity:
        """
        Evaluate cost changes against policy thresholds.

        Returns the highest severity based on token, USD, and latency changes.
        """
        severity = DiffSeverity.INFO

        # Token increase check
        if cost_delta.baseline_tokens > 0:
            token_pct = (cost_delta.tokens_delta / cost_delta.baseline_tokens) * 100
            if token_pct >= self.policy.token_increase_fail_pct:
                severity = DiffSeverity.FAIL
            elif token_pct >= self.policy.token_increase_warn_pct:
                if severity != DiffSeverity.FAIL:
                    severity = DiffSeverity.WARN

        # USD increase check
        if cost_delta.baseline_usd > 0:
            usd_pct = (cost_delta.usd_delta / cost_delta.baseline_usd) * 100
            if usd_pct >= self.policy.usd_increase_fail_pct:
                severity = DiffSeverity.FAIL
            elif usd_pct >= self.policy.usd_increase_warn_pct:
                if severity != DiffSeverity.FAIL:
                    severity = DiffSeverity.WARN

        # Latency increase check
        if cost_delta.baseline_latency_ms > 0:
            latency_pct = (cost_delta.latency_delta_ms / cost_delta.baseline_latency_ms) * 100
            if latency_pct >= self.policy.latency_increase_fail_pct:
                severity = DiffSeverity.FAIL
            elif latency_pct >= self.policy.latency_increase_warn_pct:
                if severity != DiffSeverity.FAIL:
                    severity = DiffSeverity.WARN

        return severity

    def _describe_regression(self, diff: EventDiff) -> str:
        """Create human-readable description of a regression."""
        if diff.diff_type == "removed":
            return f"Missing event: {diff.event_key}"

        if diff.diff_type == "changed":
            changes_desc = ", ".join(
                f"{k}: {old} -> {new}"
                for k, (old, new) in diff.changes.items()
            )
            return f"Changed: {diff.event_key} ({changes_desc})"

        return f"Regression in {diff.event_key}"

    def _event_diff_to_dict(self, diff: EventDiff) -> Dict[str, Any]:
        """Convert EventDiff to dictionary."""
        return {
            "event_key": diff.event_key,
            "diff_type": diff.diff_type,
            "changes": {k: {"old": old, "new": new} for k, (old, new) in diff.changes.items()},
            "severity": diff.severity.value,
            "is_regression": diff.is_regression,
        }

    def to_markdown(self, diff_result: Dict[str, Any]) -> str:
        """Generate markdown report from diff result."""
        lines = []

        lines.append("# Trace Diff Report")
        lines.append("")
        lines.append(f"**Generated:** {datetime.utcnow().isoformat()}Z")
        lines.append("")

        # Overall severity badge
        overall = diff_result.get("overall_severity", "info")
        severity_emoji = {"info": "✅", "warn": "⚠️", "fail": "❌"}.get(overall, "❓")
        lines.append(f"**Overall Severity:** {severity_emoji} `{overall.upper()}`")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append("| Metric | Baseline | Candidate |")
        lines.append("|--------|----------|-----------|")
        lines.append(f"| Run ID | `{diff_result.get('baseline_run_id', 'N/A')[:12]}...` | `{diff_result.get('candidate_run_id', 'N/A')[:12]}...` |")
        lines.append(f"| Events | {diff_result.get('baseline_event_count', 0)} | {diff_result.get('candidate_event_count', 0)} |")
        lines.append("")

        # Regressions
        regressions = diff_result.get("regressions", [])
        if regressions:
            lines.append("## Regressions")
            lines.append("")
            for reg in regressions:
                lines.append(f"- {reg}")
            lines.append("")
        else:
            lines.append("## Regressions")
            lines.append("")
            lines.append("No regressions detected.")
            lines.append("")

        # Cost Delta
        cost = diff_result.get("cost_delta", {})
        cost_sev = diff_result.get("cost_severity", "info")
        cost_emoji = {"info": "✅", "warn": "⚠️", "fail": "❌"}.get(cost_sev, "❓")
        lines.append(f"## Cost Delta {cost_emoji}")
        lines.append("")
        lines.append(f"**Severity:** `{cost_sev.upper()}`")
        lines.append("")
        lines.append("| Metric | Baseline | Candidate | Delta |")
        lines.append("|--------|----------|-----------|-------|")
        lines.append(f"| Tokens | {cost.get('baseline_tokens', 0):,} | {cost.get('candidate_tokens', 0):,} | {cost.get('tokens_delta', 0):+,} |")
        lines.append(f"| USD | ${cost.get('baseline_usd', 0):.4f} | ${cost.get('candidate_usd', 0):.4f} | ${cost.get('usd_delta', 0):+.4f} |")
        lines.append(f"| Latency (ms) | {cost.get('baseline_latency_ms', 0):.1f} | {cost.get('candidate_latency_ms', 0):.1f} | {cost.get('latency_delta_ms', 0):+.1f} |")
        lines.append("")

        # Quality Delta
        quality = diff_result.get("quality_delta", {})
        if quality:
            lines.append("## Quality Delta")
            lines.append("")
            lines.append("| Metric | Delta |")
            lines.append("|--------|-------|")
            for metric, delta in quality.items():
                lines.append(f"| {metric} | {delta:+.2f} |")
            lines.append("")

        # Event Changes
        added = diff_result.get("added", [])
        removed = diff_result.get("removed", [])
        changed = diff_result.get("changed", [])

        if added or removed or changed:
            lines.append("## Event Changes")
            lines.append("")

            if added:
                lines.append("### Added Events")
                lines.append("")
                for evt in added[:20]:
                    lines.append(f"- `{evt.get('event_key', 'unknown')}`")
                if len(added) > 20:
                    lines.append(f"- ... and {len(added) - 20} more")
                lines.append("")

            if removed:
                lines.append("### Removed Events")
                lines.append("")
                for evt in removed[:20]:
                    sev = evt.get("severity", "info")
                    sev_badge = {"info": "ℹ️", "warn": "⚠️", "fail": "❌"}.get(sev, "")
                    lines.append(f"- {sev_badge} `{evt.get('event_key', 'unknown')}` [{sev.upper()}]")
                if len(removed) > 20:
                    lines.append(f"- ... and {len(removed) - 20} more")
                lines.append("")

            if changed:
                lines.append("### Changed Events")
                lines.append("")
                for evt in changed[:20]:
                    sev = evt.get("severity", "info")
                    sev_badge = {"info": "ℹ️", "warn": "⚠️", "fail": "❌"}.get(sev, "")
                    changes = evt.get("changes", {})
                    change_desc = ", ".join(f"{k}" for k in changes.keys())
                    lines.append(f"- {sev_badge} `{evt.get('event_key', 'unknown')}`: {change_desc} [{sev.upper()}]")
                if len(changed) > 20:
                    lines.append(f"- ... and {len(changed) - 20} more")
                lines.append("")

        lines.append("---")
        lines.append("*Generated by HUAP Trace Differ*")

        return "\n".join(lines)
