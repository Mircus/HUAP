"""
Human Gate — pause a workflow run until a human approves, rejects, or edits.

Artifacts:
    .huap/inbox/<run_id>/<gate_id>.json          — gate request
    .huap/inbox/<run_id>/<gate_id>.decision.json  — human decision

Trace events (reuses policy_check to avoid schema churn):
    policy_check(policy="human_gate", decision="pending", ...)
    policy_check(policy="human_gate", decision="approve|reject|edit", ...)
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class GateRequest:
    """A request for human review."""
    gate_id: str
    run_id: str
    title: str
    severity: str = "medium"  # low | medium | high | critical
    summary: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    suggested_options: List[str] = field(default_factory=lambda: ["approve", "reject"])
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "pending"  # pending | decided

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GateDecision:
    """A human's decision on a gate request."""
    gate_id: str
    run_id: str
    decision: str  # approve | reject | edit
    note: str = ""
    patch: Optional[Dict[str, Any]] = None
    decided_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    decided_by: str = "human"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Inbox paths
# ---------------------------------------------------------------------------

def _inbox_dir(run_id: str, root: Optional[str] = None) -> Path:
    base = Path(root) if root else Path(".huap")
    return base / "inbox" / run_id


def _request_path(run_id: str, gate_id: str, root: Optional[str] = None) -> Path:
    return _inbox_dir(run_id, root) / f"{gate_id}.json"


def _decision_path(run_id: str, gate_id: str, root: Optional[str] = None) -> Path:
    return _inbox_dir(run_id, root) / f"{gate_id}.decision.json"


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

def create_gate(
    run_id: str,
    title: str,
    severity: str = "medium",
    summary: str = "",
    context: Optional[Dict[str, Any]] = None,
    suggested_options: Optional[List[str]] = None,
    root: Optional[str] = None,
) -> GateRequest:
    """
    Create a gate request artifact and return the GateRequest.

    Writes ``<root>/inbox/<run_id>/<gate_id>.json``.
    """
    gate_id = f"gate_{uuid4().hex[:12]}"
    req = GateRequest(
        gate_id=gate_id,
        run_id=run_id,
        title=title,
        severity=severity,
        summary=summary,
        context=context or {},
        suggested_options=suggested_options or ["approve", "reject"],
    )
    path = _request_path(run_id, gate_id, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(req.to_dict(), indent=2, default=str), encoding="utf-8")
    return req


def submit_decision(
    run_id: str,
    gate_id: str,
    decision: str,
    note: str = "",
    patch: Optional[Dict[str, Any]] = None,
    decided_by: str = "human",
    root: Optional[str] = None,
) -> GateDecision:
    """
    Write a decision artifact for a gate.

    Writes ``<root>/inbox/<run_id>/<gate_id>.decision.json``.
    """
    dec = GateDecision(
        gate_id=gate_id,
        run_id=run_id,
        decision=decision,
        note=note,
        patch=patch,
        decided_by=decided_by,
    )
    path = _decision_path(run_id, gate_id, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dec.to_dict(), indent=2, default=str), encoding="utf-8")

    # Also update the request status
    req_path = _request_path(run_id, gate_id, root)
    if req_path.exists():
        req_data = json.loads(req_path.read_text(encoding="utf-8"))
        req_data["status"] = "decided"
        req_path.write_text(json.dumps(req_data, indent=2, default=str), encoding="utf-8")

    return dec


def get_decision(
    run_id: str,
    gate_id: str,
    root: Optional[str] = None,
) -> Optional[GateDecision]:
    """Return the decision for a gate, or None if still pending."""
    path = _decision_path(run_id, gate_id, root)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return GateDecision(**{k: v for k, v in data.items() if k in GateDecision.__dataclass_fields__})


def list_gates(
    run_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    severity_filter: Optional[str] = None,
    root: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    List gate requests, optionally filtered by run, status, or severity.

    Returns a list of dicts with gate request data plus ``has_decision``.
    """
    base = Path(root) if root else Path(".huap")
    inbox = base / "inbox"
    if not inbox.exists():
        return []

    results = []

    run_dirs = [inbox / run_id] if run_id else sorted(inbox.iterdir())
    for run_dir in run_dirs:
        if not run_dir.is_dir():
            continue
        for req_file in sorted(run_dir.glob("*.json")):
            if req_file.name.endswith(".decision.json"):
                continue
            try:
                data = json.loads(req_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            gate_id = data.get("gate_id", req_file.stem)
            has_decision = _decision_path(data.get("run_id", run_dir.name), gate_id, root).exists()
            effective_status = "decided" if has_decision else "pending"
            data["has_decision"] = has_decision
            data["effective_status"] = effective_status

            if status_filter and effective_status != status_filter:
                continue
            if severity_filter and data.get("severity") != severity_filter:
                continue

            results.append(data)

    return results


def wait_for_decision(
    run_id: str,
    gate_id: str,
    poll_interval: float = 1.0,
    timeout: Optional[float] = None,
    root: Optional[str] = None,
) -> Optional[GateDecision]:
    """
    Block until a decision file appears (or timeout).

    For use in synchronous workflow runners. Returns the decision or None
    on timeout.
    """
    start = time.time()
    while True:
        dec = get_decision(run_id, gate_id, root)
        if dec is not None:
            return dec
        if timeout and (time.time() - start) >= timeout:
            return None
        time.sleep(poll_interval)


# ---------------------------------------------------------------------------
# Trace helpers
# ---------------------------------------------------------------------------

def gate_trace_event(
    run_id: str,
    gate_id: str,
    decision: str,
    reason: str = "",
    inputs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a policy_check trace event for a human gate."""
    return {
        "v": "0.1",
        "ts": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "span_id": f"sp_{uuid4().hex[:12]}",
        "kind": "policy",
        "name": "policy_check",
        "pod": "runtime",
        "engine": "human_gate",
        "data": {
            "policy": "human_gate",
            "gate_id": gate_id,
            "decision": decision,
            "reason": reason,
            "inputs": inputs or {},
        },
    }
