"""Tests for P6.5 — Human Gate runtime + inbox."""
import json
import pytest
from pathlib import Path

from hu_core.runtime.human_gate import (
    create_gate,
    submit_decision,
    get_decision,
    list_gates,
    gate_trace_event,
    GateRequest,
    GateDecision,
)


@pytest.fixture
def inbox_root(tmp_path):
    return str(tmp_path)


class TestCreateGate:
    def test_creates_request_file(self, inbox_root):
        req = create_gate("run_1", "Approve email", root=inbox_root)
        assert req.run_id == "run_1"
        assert req.title == "Approve email"
        assert req.status == "pending"
        path = Path(inbox_root) / "inbox" / "run_1" / f"{req.gate_id}.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["title"] == "Approve email"

    def test_default_severity(self, inbox_root):
        req = create_gate("run_1", "Test", root=inbox_root)
        assert req.severity == "medium"

    def test_custom_options(self, inbox_root):
        req = create_gate("run_1", "Test", suggested_options=["yes", "no", "maybe"],
                          root=inbox_root)
        assert req.suggested_options == ["yes", "no", "maybe"]


class TestSubmitDecision:
    def test_writes_decision_file(self, inbox_root):
        req = create_gate("run_1", "Test gate", root=inbox_root)
        dec = submit_decision("run_1", req.gate_id, "approve", note="LGTM",
                              root=inbox_root)
        assert dec.decision == "approve"
        assert dec.note == "LGTM"
        dec_path = Path(inbox_root) / "inbox" / "run_1" / f"{req.gate_id}.decision.json"
        assert dec_path.exists()

    def test_updates_request_status(self, inbox_root):
        req = create_gate("run_1", "Test", root=inbox_root)
        submit_decision("run_1", req.gate_id, "reject", root=inbox_root)
        req_path = Path(inbox_root) / "inbox" / "run_1" / f"{req.gate_id}.json"
        data = json.loads(req_path.read_text())
        assert data["status"] == "decided"


class TestGetDecision:
    def test_returns_none_when_pending(self, inbox_root):
        req = create_gate("run_1", "Test", root=inbox_root)
        assert get_decision("run_1", req.gate_id, root=inbox_root) is None

    def test_returns_decision_after_submit(self, inbox_root):
        req = create_gate("run_1", "Test", root=inbox_root)
        submit_decision("run_1", req.gate_id, "approve", note="ok", root=inbox_root)
        dec = get_decision("run_1", req.gate_id, root=inbox_root)
        assert dec is not None
        assert dec.decision == "approve"
        assert dec.note == "ok"


class TestListGates:
    def test_empty_inbox(self, inbox_root):
        assert list_gates(root=inbox_root) == []

    def test_lists_all_gates(self, inbox_root):
        create_gate("run_1", "Gate A", root=inbox_root)
        create_gate("run_1", "Gate B", root=inbox_root)
        create_gate("run_2", "Gate C", root=inbox_root)
        gates = list_gates(root=inbox_root)
        assert len(gates) == 3

    def test_filter_by_run(self, inbox_root):
        create_gate("run_1", "A", root=inbox_root)
        create_gate("run_2", "B", root=inbox_root)
        gates = list_gates(run_id="run_1", root=inbox_root)
        assert len(gates) == 1

    def test_filter_by_status(self, inbox_root):
        req = create_gate("run_1", "A", root=inbox_root)
        create_gate("run_1", "B", root=inbox_root)
        submit_decision("run_1", req.gate_id, "approve", root=inbox_root)
        pending = list_gates(status_filter="pending", root=inbox_root)
        decided = list_gates(status_filter="decided", root=inbox_root)
        assert len(pending) == 1
        assert len(decided) == 1

    def test_filter_by_severity(self, inbox_root):
        create_gate("run_1", "Low", severity="low", root=inbox_root)
        create_gate("run_1", "High", severity="high", root=inbox_root)
        high = list_gates(severity_filter="high", root=inbox_root)
        assert len(high) == 1
        assert high[0]["title"] == "High"


class TestGateTraceEvent:
    def test_produces_valid_event(self):
        evt = gate_trace_event("run_1", "gate_abc", "pending", reason="waiting")
        assert evt["kind"] == "policy"
        assert evt["name"] == "policy_check"
        assert evt["data"]["policy"] == "human_gate"
        assert evt["data"]["decision"] == "pending"
        assert evt["data"]["gate_id"] == "gate_abc"
        assert evt["run_id"] == "run_1"
