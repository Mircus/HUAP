"""
HUAP CLI Trace Commands

Provides trace-related CLI commands:
- huap trace run <pod> <graph> --out trace.jsonl
- huap trace view trace.jsonl
- huap trace replay trace.jsonl --stubs tools|llm|all
- huap trace diff baseline.jsonl candidate.jsonl --out diff.md
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, List

try:
    import click
    HAS_CLICK = True
except ImportError:
    HAS_CLICK = False


if HAS_CLICK:
    @click.group()
    def trace():
        """Trace commands for recording, replaying, and diffing agent runs."""
        pass

    @trace.command("run")
    @click.argument("pod")
    @click.argument("graph", type=click.Path(exists=True))
    @click.option("--out", "-o", default=None, help="Output trace file path")
    @click.option("--input", "-i", "input_file", default=None, help="JSON file with input state")
    @click.option("--start-node", "-s", default=None, help="Starting node (default: {pod}_start)")
    def trace_run(pod: str, graph: str, out: Optional[str], input_file: Optional[str], start_node: Optional[str]):
        """
        Run a pod workflow and record trace.

        POD: Pod name (e.g., hello, myagent)
        GRAPH: Path to YAML graph definition

        Examples:
            huap trace run hello examples/graphs/hello.yaml --out traces/hello.jsonl
            huap trace run myagent graphs/myagent.yaml --input input.json
        """
        import asyncio
        import json
        from datetime import datetime

        click.echo(f"Running pod '{pod}' with graph '{graph}'...")

        # Parse input state
        input_state = {}
        if input_file:
            try:
                input_path = Path(input_file)
                if input_path.exists():
                    input_state = json.loads(input_path.read_text())
                    click.echo(f"Loaded input from {input_file}")
            except Exception as e:
                click.echo(f"Warning: Could not load input file: {e}", err=True)

        # Determine output path
        if out:
            output_path = Path(out)
        else:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            pod_name = pod.replace("hu-", "").replace("hu_", "")
            output_path = Path("traces") / f"{pod_name}_{timestamp}.trace.jsonl"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Import and run
        try:
            from ..trace.runner import run_pod_graph

            result = asyncio.run(run_pod_graph(
                pod=pod,
                graph_path=Path(graph),
                input_state=input_state,
                output_path=output_path,
                start_node=start_node,
            ))

            actual_path = result.get('trace_path') or str(output_path)
            click.echo(f"\nTrace saved to: {actual_path}")
            click.echo(f"Run ID: {result.get('run_id', 'unknown')}")
            click.echo(f"Status: {result.get('status', 'unknown')}")
            if result.get('duration_ms'):
                click.echo(f"Duration: {result['duration_ms']:.1f}ms")

            if result.get('error'):
                click.echo(f"Error: {result['error']}", err=True)
                sys.exit(1)

        except ImportError as e:
            click.echo(f"Error: Missing dependency: {e}", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"Error running workflow: {e}", err=True)
            import traceback
            traceback.print_exc()
            sys.exit(1)

    @trace.command("replay")
    @click.argument("trace_file", type=click.Path(exists=True))
    @click.option("--stubs", "-s", default="all", help="What to stub: tools|llm|all|none")
    @click.option("--out", "-o", default=None, help="Output replay trace file")
    @click.option("--verify", "-v", is_flag=True, help="Verify replay matches original")
    @click.option("--mode", "-m", default="emit", type=click.Choice(["emit", "exec"]), help="Replay mode: emit (re-emit events) or exec (re-execute workflow)")
    @click.option("--config", "-c", "config_file", default=None, help="Path to config.yaml (for exec mode)")
    def trace_replay(trace_file: str, stubs: str, out: Optional[str], verify: bool, mode: str, config_file: Optional[str]):
        """
        Replay a trace with optional stubs.

        TRACE_FILE: Path to the trace JSONL file

        Modes:
        - emit: Re-emit recorded events (fast, no execution) [default]
        - exec: Re-execute workflow with stubbed LLM/tools (deterministic)

        Stub options:
        - tools: Stub tool calls with recorded results
        - llm: Stub LLM calls with recorded responses
        - all: Stub both tools and LLM (default)
        - none: No stubs (live execution)

        Examples:
            huap trace replay runs/hello.trace.jsonl --stubs llm --out runs/hello.replay.jsonl
            huap trace replay runs/hello.trace.jsonl --mode exec --verify
        """
        import asyncio

        click.echo(f"Replaying trace: {trace_file}")
        click.echo(f"Mode: {mode}")
        click.echo(f"Stubs: {stubs}")

        # Parse stub options
        stub_tools = stubs in ("tools", "all")
        stub_llm = stubs in ("llm", "all")

        # Determine output path
        if out:
            output_path = Path(out)
        else:
            trace_path = Path(trace_file)
            output_path = trace_path.with_suffix(".replay.jsonl")

        try:
            from ..trace.replay import TraceReplayer

            replayer = TraceReplayer(
                trace_path=trace_file,
                stub_tools=stub_tools,
                stub_llm=stub_llm,
                config_path=config_file,
            )

            result = asyncio.run(replayer.replay(output_path=str(output_path), mode=mode))

            click.echo(f"\nReplay saved to: {output_path}")
            click.echo(f"Replay mode: {result.get('mode', mode)}")
            click.echo(f"Original run_id: {result.get('original_run_id', 'unknown')}")
            click.echo(f"Replay run_id: {result.get('replay_run_id', 'unknown')}")
            click.echo(f"Events replayed: {result.get('events_replayed', 0)}")

            # Show any errors
            errors = result.get('errors', [])
            if errors:
                click.echo(f"\nErrors ({len(errors)}):", err=True)
                for err in errors[:5]:
                    click.echo(f"  - {err}", err=True)

            if verify:
                if result.get('state_hash_match'):
                    click.echo("\nVerification: PASSED (state hashes match)")
                else:
                    click.echo("\nVerification: FAILED (state hashes differ)", err=True)
                    click.echo(f"  Original: {result.get('original_state_hash', 'N/A')}")
                    click.echo(f"  Replay:   {result.get('replay_state_hash', 'N/A')}")
                    sys.exit(1)

        except Exception as e:
            click.echo(f"Error replaying trace: {e}", err=True)
            sys.exit(1)

    @trace.command("diff")
    @click.argument("baseline", type=click.Path(exists=True))
    @click.argument("candidate", type=click.Path(exists=True))
    @click.option("--out", "-o", default=None, help="Output diff file (markdown)")
    @click.option("--format", "-f", "fmt", default="md", type=click.Choice(["md", "json"]), help="Output format")
    @click.option("--ignore-timestamps", is_flag=True, help="Ignore timestamp differences")
    def trace_diff(baseline: str, candidate: str, out: Optional[str], fmt: str, ignore_timestamps: bool):
        """
        Compare two traces and show differences.

        BASELINE: Path to the baseline trace JSONL
        CANDIDATE: Path to the candidate trace JSONL

        Example:
            huap trace diff baseline.jsonl candidate.jsonl --out diff.md
        """
        click.echo(f"Comparing traces:")
        click.echo(f"  Baseline:  {baseline}")
        click.echo(f"  Candidate: {candidate}")

        # Determine output path
        if out:
            output_path = Path(out)
        else:
            output_path = Path(f"trace_diff.{fmt}")

        try:
            from ..trace.diff import TraceDiffer

            differ = TraceDiffer(
                ignore_timestamps=ignore_timestamps,
            )

            diff_result = differ.diff(baseline, candidate)

            # Generate output
            if fmt == "md":
                output = differ.to_markdown(diff_result)
            else:
                import json
                output = json.dumps(diff_result, indent=2, default=str)

            output_path.write_text(output, encoding="utf-8")

            click.echo(f"\nDiff saved to: {output_path}")
            click.echo(f"\nSummary:")
            click.echo(f"  Events in baseline: {diff_result.get('baseline_event_count', 0)}")
            click.echo(f"  Events in candidate: {diff_result.get('candidate_event_count', 0)}")
            click.echo(f"  Added events: {len(diff_result.get('added', []))}")
            click.echo(f"  Removed events: {len(diff_result.get('removed', []))}")
            click.echo(f"  Changed events: {len(diff_result.get('changed', []))}")

            # Cost delta
            cost_delta = diff_result.get('cost_delta', {})
            if cost_delta:
                click.echo(f"\nCost Delta:")
                click.echo(f"  Tokens: {cost_delta.get('tokens_delta', 0):+d}")
                click.echo(f"  USD: ${cost_delta.get('usd_delta', 0):+.4f}")
                click.echo(f"  Latency: {cost_delta.get('latency_delta_ms', 0):+.1f}ms")

            # Quality delta
            quality_delta = diff_result.get('quality_delta', {})
            if quality_delta:
                click.echo(f"\nQuality Delta:")
                for metric, delta in quality_delta.items():
                    click.echo(f"  {metric}: {delta:+.2f}")

            # Regressions
            regressions = diff_result.get('regressions', [])
            if regressions:
                click.echo(f"\nRegressions ({len(regressions)}):", err=True)
                for reg in regressions[:5]:  # Show first 5
                    click.echo(f"  - {reg}", err=True)
                if len(regressions) > 5:
                    click.echo(f"  ... and {len(regressions) - 5} more", err=True)
                sys.exit(1)
            else:
                click.echo("\nNo regressions detected.")

        except Exception as e:
            click.echo(f"Error diffing traces: {e}", err=True)
            sys.exit(1)

    @trace.command("view")
    @click.argument("trace_file", type=click.Path(exists=True))
    @click.option("--kind", "-k", default=None, help="Filter by event kind")
    @click.option("--name", "-n", default=None, help="Filter by event name")
    @click.option("--limit", "-l", default=50, help="Max events to show")
    def trace_view(trace_file: str, kind: Optional[str], name: Optional[str], limit: int):
        """
        View events in a trace file.

        TRACE_FILE: Path to the trace JSONL file

        Example:
            huap trace view runs/hello.trace.jsonl --kind llm --limit 10
        """
        from ..trace.models import TraceRun

        click.echo(f"Loading trace: {trace_file}\n")

        try:
            trace_run = TraceRun.from_jsonl_file(trace_file)

            events = trace_run.events

            # Apply filters
            if kind:
                events = [e for e in events if e.kind == kind]
            if name:
                events = [e for e in events if e.name == name]

            click.echo(f"Run ID: {trace_run.run_id}")
            click.echo(f"Total events: {len(trace_run.events)}")
            if kind or name:
                click.echo(f"Filtered events: {len(events)}")
            click.echo()

            # Show events
            for i, event in enumerate(events[:limit]):
                ts = event.ts.strftime("%H:%M:%S.%f")[:-3] if event.ts else "N/A"
                click.echo(f"[{ts}] {event.kind}/{event.name}")
                click.echo(f"  span: {event.span_id}")
                if event.parent_span_id:
                    click.echo(f"  parent: {event.parent_span_id}")

                # Show key data fields
                if hasattr(event.data, 'model_dump'):
                    data = event.data.model_dump()
                elif isinstance(event.data, dict):
                    data = event.data
                else:
                    data = {}

                for key, value in list(data.items())[:5]:
                    if key not in ('input', 'output', 'messages', 'text', 'result'):
                        click.echo(f"  {key}: {value}")

                click.echo()

            if len(events) > limit:
                click.echo(f"... and {len(events) - limit} more events (use --limit to show more)")

        except Exception as e:
            click.echo(f"Error viewing trace: {e}", err=True)
            sys.exit(1)

    @trace.command("wrap", context_settings=dict(
        ignore_unknown_options=True,
    ))
    @click.option("--out", "-o", required=True, help="Output trace file path")
    @click.option("--name", "-n", default=None, help="Run name (default: command string)")
    @click.option("--merge", default=None, help="Merge adapter-emitted events from this file")
    @click.option("--timeout", "-t", default=None, type=int, help="Timeout in seconds")
    @click.argument("command", nargs=-1, type=click.UNPROCESSED, required=True)
    def trace_wrap(out: str, name: Optional[str], merge: Optional[str], timeout: Optional[int], command):
        """
        Wrap any command and produce a HUAP trace.

        Captures run_start/run_end, wall time, exit code, and stdout/stderr
        as trace events.

        COMMAND: The command to run (use -- to separate from huap flags)

        Examples:
            huap trace wrap --out traces/x.jsonl -- python -c "print('hi')"
            huap trace wrap --out traces/agent.jsonl -- python my_agent.py --mode fast
        """
        if not command:
            click.echo("Error: No command specified.", err=True)
            sys.exit(1)

        from ..trace.wrap import wrap_command

        cmd_list = list(command)
        click.echo(f"Wrapping command: {' '.join(cmd_list)}")

        result = wrap_command(
            command=cmd_list,
            output_path=out,
            run_name=name,
            merge_path=merge,
            timeout=timeout,
        )

        click.echo(f"\nTrace saved to: {result['trace_path']}")
        click.echo(f"Run ID: {result['run_id']}")
        click.echo(f"Exit code: {result['exit_code']}")
        click.echo(f"Duration: {result['duration_ms']:.1f}ms")
        click.echo(f"Events: {result['event_count']}")
        if result.get('merged_events'):
            click.echo(f"Merged adapter events: {result['merged_events']}")

        if result['exit_code'] != 0:
            sys.exit(result['exit_code'])

    @trace.command("report")
    @click.argument("trace_file", type=click.Path(exists=True))
    @click.option("--out", "-o", default=None, help="Output HTML file path")
    @click.option("--baseline", "-b", default=None, type=click.Path(exists=True), help="Baseline trace for diff summary")
    def trace_report(trace_file: str, out: Optional[str], baseline: Optional[str]):
        """
        Generate a standalone HTML report from a trace file.

        TRACE_FILE: Path to the trace JSONL file

        Examples:
            huap trace report traces/run.jsonl --out reports/run.html
            huap trace report traces/run.jsonl --baseline traces/golden/run.jsonl
        """
        if out is None:
            out = Path(trace_file).with_suffix(".html")

        from ..trace.report import generate_report

        click.echo(f"Generating report from: {trace_file}")
        report_path = generate_report(
            trace_path=trace_file,
            output_path=str(out),
            baseline_path=baseline,
        )
        click.echo(f"Report saved to: {report_path}")
        click.echo("Open in a browser to view.")

    @trace.command("validate")
    @click.argument("trace_file", type=click.Path(exists=True))
    def trace_validate(trace_file: str):
        """
        Validate a trace file's JSONL schema.

        TRACE_FILE: Path to the trace JSONL file

        Example:
            huap trace validate traces/x.jsonl
        """
        import json as _json

        click.echo(f"Validating: {trace_file}")
        errors = []
        event_count = 0

        with open(trace_file, "r") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = _json.loads(line)
                    event_count += 1
                    if "run_id" not in evt:
                        errors.append(f"Line {i}: missing 'run_id'")
                    if "kind" not in evt and "name" not in evt:
                        errors.append(f"Line {i}: missing 'kind' or 'name'")
                except _json.JSONDecodeError as e:
                    errors.append(f"Line {i}: invalid JSON — {e}")

        if errors:
            click.echo(f"\nValidation FAILED ({len(errors)} error(s)):", err=True)
            for err in errors[:10]:
                click.echo(f"  - {err}", err=True)
            sys.exit(1)
        else:
            click.echo(f"Valid HUAP trace: {event_count} event(s)")

else:
    # Fallback for when click is not available
    def trace():
        print("Trace commands require 'click' package. Install with: pip install click")


def register_trace_commands(cli_group):
    """Register trace commands with the main CLI group."""
    if HAS_CLICK:
        cli_group.add_command(trace)
