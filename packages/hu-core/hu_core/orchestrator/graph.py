"""
HUAP Graph - DAG definition and execution.

Pure Python, no external dependencies.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..trace import TraceService

logger = logging.getLogger(__name__)


@dataclass
class Node:
    """A node in the workflow graph."""
    name: str
    func: Callable[[Dict[str, Any]], Dict[str, Any]]
    description: str = ""

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the node function with state."""
        import asyncio
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(state)
        else:
            return self.func(state)


@dataclass
class Edge:
    """An edge connecting two nodes."""
    source: str
    target: str
    condition: Optional[str] = None  # Python expression to evaluate

    def evaluate_condition(self, state: Dict[str, Any]) -> bool:
        """Evaluate the edge condition against state."""
        if self.condition is None:
            return True
        try:
            # Safe evaluation with limited context
            return bool(eval(self.condition, {"__builtins__": {}}, state))
        except Exception as e:
            logger.warning(f"Edge condition '{self.condition}' failed: {e}")
            return False


@dataclass
class GraphRunner:
    """
    Execute a workflow graph.

    Pure Python implementation with no database dependencies.
    """
    nodes: Dict[str, Node] = field(default_factory=dict)
    edges: Dict[str, List[Edge]] = field(default_factory=dict)
    tracer: Optional[TraceService] = None

    def add_node(self, node: Node) -> None:
        """Add a node to the graph."""
        self.nodes[node.name] = node

    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the graph."""
        if edge.source not in self.edges:
            self.edges[edge.source] = []
        self.edges[edge.source].append(edge)

    def set_tracer(self, tracer: TraceService) -> None:
        """Set the tracer for event emission."""
        self.tracer = tracer

    def get_next_nodes(self, current: str, state: Dict[str, Any]) -> List[str]:
        """Get the next nodes to execute based on edge conditions."""
        edges = self.edges.get(current, [])
        next_nodes = []
        for edge in edges:
            if edge.evaluate_condition(state):
                next_nodes.append(edge.target)
        return next_nodes

    async def run(
        self,
        start_node: str,
        initial_state: Dict[str, Any],
        pod_name: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Execute the graph starting from a node.

        Args:
            start_node: Name of the starting node
            initial_state: Initial state dictionary
            pod_name: Pod name for tracing

        Returns:
            Final state after execution
        """
        if start_node not in self.nodes:
            raise ValueError(f"Start node '{start_node}' not found in graph")

        state = initial_state.copy()
        current_nodes = [start_node]
        visited = set()

        while current_nodes:
            node_name = current_nodes.pop(0)

            # Prevent infinite loops
            if node_name in visited:
                logger.warning(f"Node '{node_name}' already visited, skipping")
                continue
            visited.add(node_name)

            node = self.nodes.get(node_name)
            if node is None:
                logger.warning(f"Node '{node_name}' not found, skipping")
                continue

            # Emit node enter event
            if self.tracer:
                self.tracer.node_enter(
                    node=node_name,
                    state=state,
                    pod=pod_name,
                )

            try:
                # Execute node
                result = await node.execute(state)
                if result:
                    state.update(result)

                # Emit node exit event
                if self.tracer:
                    self.tracer.node_exit(
                        node=node_name,
                        output=result,
                        pod=pod_name,
                    )

                # Get next nodes
                next_nodes = self.get_next_nodes(node_name, state)
                current_nodes.extend(next_nodes)

            except Exception as e:
                logger.error(f"Node '{node_name}' failed: {e}")
                if self.tracer:
                    self.tracer.error(
                        error_type=type(e).__name__,
                        message=str(e),
                        pod=pod_name,
                    )
                raise

        return state

    def validate(self) -> List[str]:
        """
        Validate the graph structure.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check all edge targets exist
        for source, edges in self.edges.items():
            if source not in self.nodes:
                errors.append(f"Edge source '{source}' not found in nodes")
            for edge in edges:
                if edge.target not in self.nodes:
                    errors.append(f"Edge target '{edge.target}' not found in nodes")

        return errors


def load_graph_from_yaml(yaml_data: Dict[str, Any]) -> GraphRunner:
    """
    Load a graph from YAML definition.

    Expected format:
    ```yaml
    nodes:
      - name: start
        run: my_pod.nodes.start_func
      - name: process
        run: my_pod.nodes.process_func
    edges:
      - from: start
        to: process
      - from: process
        to: end
        condition: "status == 'success'"
    ```
    """

    runner = GraphRunner()

    # Load nodes
    for node_def in yaml_data.get("nodes", []):
        name = node_def["name"]
        run_path = node_def.get("run", "")
        description = node_def.get("description", "")

        # Import the function
        func = _import_function(run_path) if run_path else _noop_func

        runner.add_node(Node(
            name=name,
            func=func,
            description=description,
        ))

    # Load edges
    for edge_def in yaml_data.get("edges", []):
        runner.add_edge(Edge(
            source=edge_def["from"],
            target=edge_def["to"],
            condition=edge_def.get("condition"),
        ))

    return runner


def _import_function(path: str) -> Callable:
    """Import a function from a dotted path."""
    from importlib import import_module

    if not path:
        return _noop_func

    parts = path.rsplit(".", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid function path: {path}")

    module_path, func_name = parts
    try:
        module = import_module(module_path)
        return getattr(module, func_name)
    except (ImportError, AttributeError) as e:
        raise ValueError(f"Could not import '{path}': {e}")


def _noop_func(state: Dict[str, Any]) -> Dict[str, Any]:
    """No-op function for nodes without implementation."""
    return state
