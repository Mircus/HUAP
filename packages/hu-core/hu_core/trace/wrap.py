"""
HUAP Trace Wrap — capture any external command as a HUAP trace.

Usage (via CLI):
    huap trace wrap --out traces/wrapped.jsonl -- python my_agent.py ...

Captures:
- run_start / run_end events
- wall time, exit code
- stdout/stderr as trace events
- Optionally merges HUAP-emitted events from adapters
"""
from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _make_event(
    run_id: str,
    kind: str,
    name: str,
    data: Dict[str, Any],
    span_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a minimal HUAP trace event dict."""
    return {
        "v": "0.1",
        "ts": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "span_id": span_id or f"sp_{uuid4().hex[:12]}",
        "kind": kind,
        "name": name,
        "pod": "wrap",
        "engine": "trace_wrap",
        "data": data,
    }


def wrap_command(
    command: List[str],
    output_path: str,
    run_name: Optional[str] = None,
    merge_path: Optional[str] = None,
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Execute *command* in a subprocess and write a HUAP trace of the run.

    Returns a summary dict with run_id, exit_code, duration_ms, event_count.
    """
    run_id = f"run_{uuid4().hex[:12]}"
    events: List[Dict[str, Any]] = []

    cmd_str = " ".join(command)

    # run_start
    events.append(_make_event(run_id, "lifecycle", "run_start", {
        "pod": "wrap",
        "graph": run_name or cmd_str,
        "input": {"command": command},
        "config": {"timeout": timeout},
    }))

    start = time.time()

    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        exit_code = proc.returncode
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        error_msg = None
    except subprocess.TimeoutExpired:
        exit_code = -1
        stdout = ""
        stderr = ""
        error_msg = f"Command timed out after {timeout}s"
    except FileNotFoundError as exc:
        exit_code = -2
        stdout = ""
        stderr = str(exc)
        error_msg = str(exc)

    duration_ms = (time.time() - start) * 1000

    # stdout event
    if stdout:
        events.append(_make_event(run_id, "system", "stdout", {
            "stream": "stdout",
            "text": stdout[:50_000],  # cap at 50 KB
            "truncated": len(stdout) > 50_000,
        }))

    # stderr event
    if stderr:
        events.append(_make_event(run_id, "system", "stderr", {
            "stream": "stderr",
            "text": stderr[:50_000],
            "truncated": len(stderr) > 50_000,
        }))

    # Merge adapter-emitted events (if any)
    merged = 0
    if merge_path and Path(merge_path).exists():
        with open(merge_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                    evt["run_id"] = run_id  # re-parent under our run
                    events.append(evt)
                    merged += 1
                except json.JSONDecodeError:
                    pass

    # run_end
    status = "success" if exit_code == 0 else "error"
    events.append(_make_event(run_id, "lifecycle", "run_end", {
        "status": status,
        "exit_code": exit_code,
        "duration_ms": round(duration_ms, 2),
        "error": error_msg,
    }))

    # Write trace
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for evt in events:
            f.write(json.dumps(evt, default=str) + "\n")

    return {
        "run_id": run_id,
        "exit_code": exit_code,
        "duration_ms": round(duration_ms, 2),
        "event_count": len(events),
        "merged_events": merged,
        "trace_path": str(out),
    }
