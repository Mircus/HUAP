"""
HUAP Trace Runner - Execute pod graphs with tracing.

Pure Python, no external dependencies.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Optional

from .service import TraceService, configure_trace_service


async def run_pod_graph(
    pod: str,
    graph_path: Path,
    input_state: Dict[str, Any],
    tracer: Optional[TraceService] = None,
    output_path: Optional[Path] = None,
    start_node: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run a pod graph with tracing.

    Args:
        pod: Pod name (for tracing metadata)
        graph_path: Path to the YAML graph definition
        input_state: Initial state for the graph
        tracer: Optional TraceService (created if not provided)
        output_path: Optional exact path to write trace file
        start_node: Optional starting node (default: {pod}_start or first node)

    Returns:
        Dict with run_id, status, duration_ms, final_state, and trace_path
    """
    from ..orchestrator import PodExecutor

    start_time = time.time()

    # Normalize pod name
    pod_key = _normalize_pod_name(pod)

    # Create tracer if not provided
    if tracer is None:
        output_dir = str(output_path.parent) if output_path else "traces"
        tracer = configure_trace_service(
            output_dir=output_dir,
            enabled=True,
            pod=pod_key,
        )

    # Start the run
    run_id = tracer.start_run(
        pod=pod_key,
        graph=graph_path.stem if graph_path else "default",
        input_data=input_state,
        trace_path=output_path,
    )

    final_state = input_state.copy()
    status = "success"
    error_msg = None

    try:
        # Create executor and run
        executor = PodExecutor(tracer=tracer)
        final_state = await executor.run(
            graph_path=graph_path,
            initial_state=input_state,
            pod_name=pod_key,
            start_node=start_node,
        )

    except FileNotFoundError as e:
        status = "error"
        error_msg = f"Graph file not found: {e}"
        tracer.error(
            error_type="FileNotFoundError",
            message=str(e),
            pod=pod_key,
        )

    except ValueError as e:
        status = "error"
        error_msg = f"Configuration error: {e}"
        tracer.error(
            error_type="ValueError",
            message=str(e),
            pod=pod_key,
        )

    except Exception as e:
        status = "error"
        error_msg = str(e)
        tracer.error(
            error_type=type(e).__name__,
            message=str(e),
            pod=pod_key,
        )

    # End the run
    duration_ms = (time.time() - start_time) * 1000
    tracer.end_run(status=status, output_data=final_state, error=error_msg)

    return {
        "run_id": run_id,
        "status": status,
        "duration_ms": duration_ms,
        "final_state": final_state,
        "error": error_msg,
        "trace_path": str(tracer.trace_path) if tracer.trace_path else None,
    }


def _normalize_pod_name(pod: str) -> str:
    """
    Normalize pod name.

    Examples:
        hu-myagent -> myagent
        hu_myagent -> myagent
        myagent -> myagent
    """
    if pod.startswith("hu-"):
        return pod[3:]
    elif pod.startswith("hu_"):
        return pod[3:]
    return pod
