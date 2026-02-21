"""
HUAP Trace Report — generate a standalone HTML report from a trace file.

Usage (via CLI):
    huap trace report traces/run.jsonl --out reports/run.html
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _load_events(path: str) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return events


def _extract_summary(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract high-level summary from trace events."""
    summary: Dict[str, Any] = {
        "run_id": "",
        "pod": "",
        "status": "unknown",
        "duration_ms": 0,
        "total_events": len(events),
        "nodes": [],
        "tools": [],
        "llm_calls": [],
        "router_decisions": [],
        "errors": [],
        "cost": {"tokens": 0, "usd_est": 0.0, "latency_ms": 0.0},
    }

    for evt in events:
        name = evt.get("name", "")
        data = evt.get("data", {})
        evt.get("kind", "")

        if not summary["run_id"]:
            summary["run_id"] = evt.get("run_id", "")
        if not summary["pod"] and data.get("pod"):
            summary["pod"] = data["pod"]

        if name == "run_start":
            summary["pod"] = data.get("pod", summary["pod"])
        elif name == "run_end":
            summary["status"] = data.get("status", "unknown")
            summary["duration_ms"] = data.get("duration_ms", 0)
            if data.get("error"):
                summary["errors"].append(data["error"])
        elif name == "node_enter":
            summary["nodes"].append(data.get("node", "?"))
        elif name in ("tool_call", "tool_result"):
            summary["tools"].append({
                "tool": data.get("tool", "?"),
                "event": name,
                "status": data.get("status"),
                "duration_ms": data.get("duration_ms"),
            })
        elif name in ("llm_request", "llm_response"):
            summary["llm_calls"].append({
                "model": data.get("model", "?"),
                "event": name,
                "usage": data.get("usage"),
                "duration_ms": data.get("duration_ms"),
            })
        elif name == "policy_check" and data.get("policy") == "router":
            summary["router_decisions"].append({
                "decision": data.get("decision"),
                "reason": data.get("reason"),
            })
        elif name == "error":
            summary["errors"].append(data.get("message", str(data)))

        # Accumulate cost
        if data.get("usage"):
            usage = data["usage"]
            summary["cost"]["tokens"] += usage.get("total_tokens", 0)
        if data.get("duration_ms"):
            summary["cost"]["latency_ms"] += data["duration_ms"]

    return summary


def generate_report(
    trace_path: str,
    output_path: str,
    baseline_path: Optional[str] = None,
) -> str:
    """Generate a standalone HTML report and write it to *output_path*."""
    events = _load_events(trace_path)
    summary = _extract_summary(events)

    baseline_summary = None
    if baseline_path and Path(baseline_path).exists():
        baseline_events = _load_events(baseline_path)
        baseline_summary = _extract_summary(baseline_events)

    html = _render_html(summary, events, baseline_summary)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return str(out)


def _render_html(
    summary: Dict[str, Any],
    events: List[Dict[str, Any]],
    baseline: Optional[Dict[str, Any]] = None,
) -> str:
    """Render a self-contained HTML report (no external deps)."""

    status_color = "#27ae60" if summary["status"] == "success" else "#e74c3c"

    # Build timeline rows
    timeline_rows = ""
    for i, evt in enumerate(events):
        ts = evt.get("ts", "")
        if isinstance(ts, str) and "T" in ts:
            ts = ts.split("T")[1][:12]
        kind = evt.get("kind", "")
        name = evt.get("name", "")
        data = evt.get("data", {})
        detail = ""
        if name in ("node_enter", "node_exit"):
            detail = data.get("node", "")
        elif name in ("tool_call", "tool_result"):
            detail = data.get("tool", "")
        elif name in ("llm_request", "llm_response"):
            detail = data.get("model", "")
        elif name == "policy_check":
            detail = f'{data.get("policy", "")} -> {data.get("decision", "")}'
        timeline_rows += (
            f"<tr><td>{ts}</td><td><span class='badge {kind}'>{kind}</span></td>"
            f"<td>{name}</td><td>{detail}</td></tr>\n"
        )

    # Router decisions section
    router_html = ""
    if summary["router_decisions"]:
        router_html = "<h2>Router Decisions</h2><ul>"
        for rd in summary["router_decisions"]:
            router_html += f"<li><b>{rd['decision']}</b> &mdash; {rd['reason']}</li>"
        router_html += "</ul>"

    # Errors section
    errors_html = ""
    if summary["errors"]:
        errors_html = "<h2>Errors / Violations</h2><ul class='errors'>"
        for e in summary["errors"]:
            errors_html += f"<li>{e}</li>"
        errors_html += "</ul>"

    # Diff section
    diff_html = ""
    if baseline:
        token_delta = summary["cost"]["tokens"] - baseline["cost"]["tokens"]
        latency_delta = summary["cost"]["latency_ms"] - baseline["cost"]["latency_ms"]
        diff_html = f"""
        <h2>Diff vs Baseline</h2>
        <table><tr><th>Metric</th><th>Baseline</th><th>Current</th><th>Delta</th></tr>
        <tr><td>Events</td><td>{baseline['total_events']}</td><td>{summary['total_events']}</td>
            <td>{summary['total_events'] - baseline['total_events']:+d}</td></tr>
        <tr><td>Tokens</td><td>{baseline['cost']['tokens']}</td><td>{summary['cost']['tokens']}</td>
            <td>{token_delta:+d}</td></tr>
        <tr><td>Latency (ms)</td><td>{baseline['cost']['latency_ms']:.0f}</td>
            <td>{summary['cost']['latency_ms']:.0f}</td><td>{latency_delta:+.0f}</td></tr>
        </table>"""

    html = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>HUAP Trace Report &mdash; {summary['run_id']}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         margin: 2em auto; max-width: 960px; color: #222; background: #fafafa; }}
  h1 {{ border-bottom: 2px solid #333; padding-bottom: .3em; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
  th, td {{ border: 1px solid #ddd; padding: 6px 10px; text-align: left; }}
  th {{ background: #f5f5f5; }}
  .badge {{ padding: 2px 8px; border-radius: 4px; font-size: .85em; color: #fff; }}
  .lifecycle {{ background: #3498db; }}
  .node {{ background: #2ecc71; }}
  .tool {{ background: #e67e22; }}
  .llm {{ background: #9b59b6; }}
  .policy {{ background: #1abc9c; }}
  .system {{ background: #7f8c8d; }}
  .memory {{ background: #34495e; }}
  .cost {{ background: #f39c12; }}
  .quality {{ background: #2980b9; }}
  .summary-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1em; }}
  .card {{ background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 1em; }}
  .card h3 {{ margin-top: 0; }}
  .errors li {{ color: #c0392b; }}
  .status {{ font-size: 1.2em; font-weight: bold; color: {status_color}; }}
</style>
</head>
<body>
<h1>HUAP Trace Report</h1>

<div class="summary-grid">
  <div class="card">
    <h3>Run Info</h3>
    <p><b>Run ID:</b> {summary['run_id']}</p>
    <p><b>Pod:</b> {summary['pod']}</p>
    <p><b>Status:</b> <span class="status">{summary['status'].upper()}</span></p>
    <p><b>Duration:</b> {summary['duration_ms']:.0f} ms</p>
  </div>
  <div class="card">
    <h3>Cost / Usage</h3>
    <p><b>Total tokens:</b> {summary['cost']['tokens']}</p>
    <p><b>Est. USD:</b> ${summary['cost']['usd_est']:.4f}</p>
    <p><b>Total latency:</b> {summary['cost']['latency_ms']:.0f} ms</p>
    <p><b>Nodes:</b> {len(summary['nodes'])} | <b>Tool calls:</b> {len(summary['tools'])} | <b>LLM calls:</b> {len(summary['llm_calls'])}</p>
  </div>
</div>

{router_html}

<h2>Timeline ({summary['total_events']} events)</h2>
<table>
<tr><th>Time</th><th>Kind</th><th>Name</th><th>Detail</th></tr>
{timeline_rows}
</table>

{errors_html}
{diff_html}

<footer style="margin-top:2em;color:#999;font-size:.85em;">
  Generated by <b>huap trace report</b> &mdash; HUAP Core v0.1.0b1
</footer>
</body>
</html>"""
    return html
