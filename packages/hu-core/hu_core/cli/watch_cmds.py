"""
HUAP Watch — tail a trace file and highlight issues, gates, and budget warnings.

Usage:
    huap watch traces/run.jsonl
    huap watch traces/run.jsonl --only issues,gates
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Optional, Set

import click


# ANSI colour helpers (degrade gracefully on Windows without colorama)
_RED = "\033[91m"
_YELLOW = "\033[93m"
_CYAN = "\033[96m"
_GREEN = "\033[92m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _colour(text: str, code: str) -> str:
    return f"{code}{text}{_RESET}"


# ── categories ────────────────────────────────────────────────────────────

_CATEGORIES: Set[str] = {"issues", "gates", "budget", "lifecycle", "all"}


def _categorise(event: dict) -> Optional[str]:
    """Map an event to a watch category (or None to skip)."""
    kind = event.get("kind", "")
    name = event.get("name", "")
    data = event.get("data", {})

    # Human gates
    policy = data.get("policy", "")
    if policy == "human_gate":
        return "gates"

    # Errors / violations
    if kind == "error" or data.get("status") == "error" or "error" in name:
        return "issues"
    if kind == "policy" and data.get("decision") in ("deny", "reject"):
        return "issues"

    # Budget warnings
    if kind == "eval" or name in ("cost_summary", "budget_check"):
        return "budget"

    # Lifecycle events
    if kind == "lifecycle":
        return "lifecycle"

    return None


def _format_event(event: dict, category: str) -> str:
    """Pretty-print a single event line."""
    ts = event.get("ts", "")[:19]
    kind = event.get("kind", "?")
    name = event.get("name", "?")
    data = event.get("data", {})

    prefix = ts

    if category == "issues":
        tag = _colour("[ISSUE]", _RED)
        detail = data.get("error") or data.get("reason") or data.get("message", "")
    elif category == "gates":
        decision = data.get("decision", "?")
        gate_id = data.get("gate_id", "?")
        if decision == "pending":
            tag = _colour("[GATE PENDING]", _YELLOW)
        elif decision == "approve":
            tag = _colour("[GATE APPROVED]", _GREEN)
        else:
            tag = _colour(f"[GATE {decision.upper()}]", _CYAN)
        detail = f"{gate_id}: {data.get('reason', '')}"
    elif category == "budget":
        tag = _colour("[BUDGET]", _YELLOW)
        detail = json.dumps(data, default=str)[:120]
    elif category == "lifecycle":
        tag = _colour(f"[{name.upper()}]", _CYAN)
        detail = data.get("status", "") or data.get("graph", "")
    else:
        tag = f"[{kind}]"
        detail = name

    return f"{prefix}  {tag}  {detail}"


# ── command ───────────────────────────────────────────────────────────────

@click.command("watch")
@click.argument("trace_file")
@click.option("--only", "only_str", default=None,
              help="Comma-separated categories: issues,gates,budget,lifecycle,all")
@click.option("--poll", "poll_interval", type=float, default=0.5,
              help="Poll interval in seconds (default 0.5)")
def watch(trace_file: str, only_str: Optional[str], poll_interval: float):
    """Live-tail a trace file and highlight issues, gates, and warnings."""
    path = Path(trace_file)

    show: Set[str] = set()
    if only_str:
        for tok in only_str.split(","):
            tok = tok.strip().lower()
            if tok in _CATEGORIES:
                show.add(tok)
            else:
                click.echo(f"Unknown category: '{tok}'. Valid: {', '.join(sorted(_CATEGORIES))}", err=True)
                sys.exit(1)
    if not show or "all" in show:
        show = {"issues", "gates", "budget", "lifecycle"}

    click.echo(_colour(f"Watching {trace_file}  (categories: {', '.join(sorted(show))})", _BOLD))
    click.echo("Press Ctrl+C to stop.\n")

    offset = 0

    try:
        while True:
            if not path.exists():
                time.sleep(poll_interval)
                continue

            with open(path, "r", encoding="utf-8") as f:
                f.seek(offset)
                new_lines = f.readlines()
                offset = f.tell()

            for line in new_lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                cat = _categorise(event)
                if cat and cat in show:
                    click.echo(_format_event(event, cat))

            time.sleep(poll_interval)
    except KeyboardInterrupt:
        click.echo("\nStopped.")
