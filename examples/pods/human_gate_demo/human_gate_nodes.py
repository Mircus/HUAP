"""
Human Gate Demo — nodes that exercise approve/reject/resume flow.

Scenario: an agent proposes sending an email, which requires human approval.

All nodes are stub-safe (no external dependencies).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from hu_core.runtime.human_gate import (
    create_gate,
    get_decision,
    submit_decision,
    gate_trace_event,
)


def prepare_email_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare a draft email for human review."""
    draft = {
        "to": "customer@example.com",
        "subject": "Your order #ORD-42 has shipped",
        "body": "Dear customer, your order has been dispatched and will arrive in 2-3 days.",
    }
    state["draft_email"] = draft
    state["status"] = "email_drafted"
    return state


def request_approval_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Hit a human gate — the run pauses until a human approves or rejects.

    In stub mode we auto-approve immediately so the demo is runnable end-to-end.
    """
    import os

    run_id = state.get("run_id", "run_demo")
    draft = state.get("draft_email", {})

    gate = create_gate(
        run_id=run_id,
        title="Approve outbound email",
        severity="high",
        summary=f"Send email to {draft.get('to', '?')}: {draft.get('subject', '?')}",
        context={"draft": draft},
        suggested_options=["approve", "reject", "edit"],
    )

    state["gate_id"] = gate.gate_id
    state["gate_status"] = "pending"

    # Emit trace event
    state.setdefault("_trace_events", []).append(
        gate_trace_event(run_id, gate.gate_id, "pending",
                         reason="Waiting for human to approve outbound email",
                         inputs={"draft": draft})
    )

    # In stub mode, auto-approve so the demo completes
    stub_mode = os.environ.get("HUAP_LLM_MODE", "live") == "stub"
    if stub_mode:
        submit_decision(run_id, gate.gate_id, "approve",
                        note="Auto-approved (stub mode)", decided_by="stub")

    # Check for decision
    dec = get_decision(run_id, gate.gate_id)
    if dec:
        state["gate_status"] = dec.decision
        state["gate_note"] = dec.note
        state.setdefault("_trace_events", []).append(
            gate_trace_event(run_id, gate.gate_id, dec.decision,
                             reason=dec.note)
        )
    else:
        state["gate_status"] = "waiting"

    return state


def send_email_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Send the email if approved, skip if rejected."""
    decision = state.get("gate_status", "waiting")

    if decision == "approve":
        state["email_sent"] = True
        state["status"] = "email_sent"
    elif decision == "reject":
        state["email_sent"] = False
        state["status"] = "email_rejected"
    elif decision == "edit":
        # Apply any edits from the human, then send
        state["email_sent"] = True
        state["status"] = "email_sent_with_edits"
    else:
        state["email_sent"] = False
        state["status"] = "waiting_for_human"

    return state


def finalize_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Log outcome."""
    state["completed"] = True
    return state
