"""
HUAP Pod Executor - Load and run pod workflows.

Pure Python, no external dependencies.
"""
from __future__ import annotations

import logging
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

from .graph import GraphRunner, load_graph_from_yaml

if TYPE_CHECKING:
    from ..trace import TraceService

logger = logging.getLogger(__name__)


class PodExecutor:
    """
    Execute pod workflows.

    Loads pod graph definitions and executes them with tracing.
    Pure Python implementation with no database dependencies.
    """

    def __init__(self, tracer: Optional[TraceService] = None):
        """
        Initialize executor.

        Args:
            tracer: Optional TraceService for event emission
        """
        self.tracer = tracer
        self._graph_cache: Dict[str, GraphRunner] = {}

    def set_tracer(self, tracer: TraceService) -> None:
        """Set the tracer for event emission."""
        self.tracer = tracer

    def load_graph(self, graph_path: Path) -> GraphRunner:
        """
        Load a graph from YAML file.

        Args:
            graph_path: Path to the YAML graph definition

        Returns:
            GraphRunner instance
        """
        cache_key = str(graph_path.resolve())
        if cache_key in self._graph_cache:
            runner = self._graph_cache[cache_key]
            runner.set_tracer(self.tracer)
            return runner

        if not graph_path.exists():
            raise FileNotFoundError(f"Graph file not found: {graph_path}")

        with open(graph_path, "r") as f:
            yaml_data = yaml.safe_load(f)

        runner = load_graph_from_yaml(yaml_data)
        runner.set_tracer(self.tracer)

        # Validate
        errors = runner.validate()
        if errors:
            raise ValueError(f"Graph validation failed: {errors}")

        self._graph_cache[cache_key] = runner
        return runner

    async def run(
        self,
        graph_path: Path,
        initial_state: Dict[str, Any],
        pod_name: str = "unknown",
        start_node: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a pod workflow.

        Args:
            graph_path: Path to the YAML graph definition
            initial_state: Initial state dictionary
            pod_name: Pod name for tracing
            start_node: Optional starting node (default: first node or {pod}_start)

        Returns:
            Final state after execution
        """
        runner = self.load_graph(graph_path)

        # Determine start node
        if start_node is None:
            # Try pod_start, then first node
            if f"{pod_name}_start" in runner.nodes:
                start_node = f"{pod_name}_start"
            elif "start" in runner.nodes:
                start_node = "start"
            elif runner.nodes:
                start_node = list(runner.nodes.keys())[0]
            else:
                raise ValueError("No nodes defined in graph")

        return await runner.run(
            start_node=start_node,
            initial_state=initial_state,
            pod_name=pod_name,
        )


async def run_pod_workflow(
    pod_name: str,
    graph_path: Path,
    initial_state: Dict[str, Any],
    tracer: Optional[TraceService] = None,
    start_node: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience function to run a pod workflow.

    Args:
        pod_name: Pod name for tracing
        graph_path: Path to the YAML graph definition
        initial_state: Initial state dictionary
        tracer: Optional TraceService for event emission
        start_node: Optional starting node

    Returns:
        Final state after execution
    """
    executor = PodExecutor(tracer=tracer)
    return await executor.run(
        graph_path=graph_path,
        initial_state=initial_state,
        pod_name=pod_name,
        start_node=start_node,
    )
