"""
HUAP Inbox CLI — manage human gate requests.

Commands:
    huap inbox list
    huap inbox show <gate_id>
    huap inbox approve <gate_id> --note "..."
    huap inbox reject  <gate_id> --note "..."
    huap inbox edit    <gate_id> --json patch.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click

from ..runtime.human_gate import (
    list_gates,
    submit_decision,
    _request_path,
    _decision_path,
)


@click.group("inbox")
def inbox():
    """Human gate inbox — review and decide on pending gates."""
    pass


# ── list ──────────────────────────────────────────────────────────────────

@inbox.command("list")
@click.option("--run", "run_id", default=None, help="Filter by run ID")
@click.option("--status", "status_filter", type=click.Choice(["pending", "decided"]),
              default=None, help="Filter by status")
@click.option("--severity", default=None, help="Filter by severity (low/medium/high/critical)")
@click.option("--root", default=None, help="Inbox root directory (default: .huap)")
def inbox_list(run_id: Optional[str], status_filter: Optional[str],
               severity: Optional[str], root: Optional[str]):
    """List gate requests in the inbox."""
    gates = list_gates(run_id=run_id, status_filter=status_filter,
                       severity_filter=severity, root=root)
    if not gates:
        click.echo("No gate requests found.")
        return

    click.echo(f"{'GATE ID':<22} {'STATUS':<10} {'SEVERITY':<10} {'TITLE'}")
    click.echo("-" * 72)
    for g in gates:
        status = g.get("effective_status", "pending")
        marker = "+" if status == "decided" else " "
        click.echo(
            f"{marker}{g.get('gate_id', '?'):<21} "
            f"{status:<10} "
            f"{g.get('severity', '?'):<10} "
            f"{g.get('title', '')}"
        )
    click.echo(f"\n{len(gates)} gate(s)")


# ── show ──────────────────────────────────────────────────────────────────

@inbox.command("show")
@click.argument("gate_id")
@click.option("--run", "run_id", default=None, help="Run ID (auto-detected if omitted)")
@click.option("--root", default=None, help="Inbox root directory")
def inbox_show(gate_id: str, run_id: Optional[str], root: Optional[str]):
    """Show details of a gate request."""
    # Find the gate
    gates = list_gates(run_id=run_id, root=root)
    match = [g for g in gates if g.get("gate_id") == gate_id]
    if not match:
        click.echo(f"Gate '{gate_id}' not found.", err=True)
        sys.exit(1)

    gate = match[0]
    click.echo(f"\n  Gate:     {gate.get('gate_id')}")
    click.echo(f"  Run:      {gate.get('run_id')}")
    click.echo(f"  Title:    {gate.get('title')}")
    click.echo(f"  Severity: {gate.get('severity')}")
    click.echo(f"  Status:   {gate.get('effective_status')}")
    click.echo(f"  Created:  {gate.get('created_at')}")
    click.echo(f"  Summary:  {gate.get('summary', '-')}")

    ctx = gate.get("context", {})
    if ctx:
        click.echo(f"  Context:  {json.dumps(ctx, indent=4, default=str)}")

    options = gate.get("suggested_options", [])
    if options:
        click.echo(f"  Options:  {', '.join(options)}")

    if gate.get("has_decision"):
        dec_path = _decision_path(gate["run_id"], gate_id, root)
        if dec_path.exists():
            dec = json.loads(dec_path.read_text(encoding="utf-8"))
            click.echo(f"\n  Decision:   {dec.get('decision')}")
            click.echo(f"  Note:       {dec.get('note', '-')}")
            click.echo(f"  Decided at: {dec.get('decided_at')}")
            click.echo(f"  Decided by: {dec.get('decided_by')}")
    click.echo()


# ── approve ───────────────────────────────────────────────────────────────

@inbox.command("approve")
@click.argument("gate_id")
@click.option("--run", "run_id", default=None, help="Run ID (auto-detected if omitted)")
@click.option("--note", default="", help="Human note")
@click.option("--root", default=None, help="Inbox root directory")
def inbox_approve(gate_id: str, run_id: Optional[str], note: str, root: Optional[str]):
    """Approve a pending gate."""
    rid = _resolve_run_id(gate_id, run_id, root)
    dec = submit_decision(rid, gate_id, "approve", note=note, root=root)
    click.echo(f"Approved gate '{gate_id}' (run {rid})")
    if note:
        click.echo(f"  Note: {note}")


# ── reject ────────────────────────────────────────────────────────────────

@inbox.command("reject")
@click.argument("gate_id")
@click.option("--run", "run_id", default=None, help="Run ID (auto-detected if omitted)")
@click.option("--note", default="", help="Human note")
@click.option("--root", default=None, help="Inbox root directory")
def inbox_reject(gate_id: str, run_id: Optional[str], note: str, root: Optional[str]):
    """Reject a pending gate."""
    rid = _resolve_run_id(gate_id, run_id, root)
    dec = submit_decision(rid, gate_id, "reject", note=note, root=root)
    click.echo(f"Rejected gate '{gate_id}' (run {rid})")
    if note:
        click.echo(f"  Note: {note}")


# ── edit ──────────────────────────────────────────────────────────────────

@inbox.command("edit")
@click.argument("gate_id")
@click.option("--run", "run_id", default=None, help="Run ID (auto-detected if omitted)")
@click.option("--json", "json_path", default=None, help="Path to JSON patch file")
@click.option("--note", default="", help="Human note")
@click.option("--root", default=None, help="Inbox root directory")
def inbox_edit(gate_id: str, run_id: Optional[str], json_path: Optional[str],
               note: str, root: Optional[str]):
    """Edit parameters via a JSON patch and approve."""
    rid = _resolve_run_id(gate_id, run_id, root)
    patch = None
    if json_path:
        p = Path(json_path)
        if not p.exists():
            click.echo(f"Patch file not found: {json_path}", err=True)
            sys.exit(1)
        patch = json.loads(p.read_text(encoding="utf-8"))

    dec = submit_decision(rid, gate_id, "edit", note=note, patch=patch, root=root)
    click.echo(f"Edited gate '{gate_id}' (run {rid})")


# ── helpers ───────────────────────────────────────────────────────────────

def _resolve_run_id(gate_id: str, run_id: Optional[str], root: Optional[str]) -> str:
    """Find the run_id for a gate, or die."""
    if run_id:
        return run_id
    gates = list_gates(root=root)
    for g in gates:
        if g.get("gate_id") == gate_id:
            return g["run_id"]
    click.echo(f"Gate '{gate_id}' not found. Specify --run.", err=True)
    sys.exit(1)
