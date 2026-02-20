"""
HUAP Graph - DAG definition and execution.

Pure Python, no external dependencies.
"""
from __future__ import annotations

import ast
import logging
import operator
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
            return bool(safe_eval_condition(self.condition, state))
        except Exception as e:
            logger.warning(f"Edge condition '{self.condition}' failed: {e}")
            return False


# ---------------------------------------------------------------------------
# Safe condition evaluator (replaces eval)
# ---------------------------------------------------------------------------

_SAFE_BUILTINS = {"len": len, "min": min, "max": max, "abs": abs,
                  "str": str, "int": int, "float": float, "bool": bool,
                  "True": True, "False": False, "None": None}

_CMP_OPS = {
    ast.Eq: operator.eq, ast.NotEq: operator.ne,
    ast.Lt: operator.lt, ast.LtE: operator.le,
    ast.Gt: operator.gt, ast.GtE: operator.ge,
    ast.Is: operator.is_, ast.IsNot: operator.is_not,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}

_BIN_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Mod: operator.mod,
}

_UNARY_OPS = {
    ast.Not: operator.not_,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


class _SafeEvaluator(ast.NodeVisitor):
    """Walk an AST and evaluate it against *state* with no dangerous ops."""

    def __init__(self, state: Dict[str, Any]):
        self.state = state

    # -- atoms --
    def visit_Constant(self, node: ast.Constant) -> Any:
        return node.value

    def visit_Name(self, node: ast.Name) -> Any:
        name = node.id
        if name in _SAFE_BUILTINS:
            return _SAFE_BUILTINS[name]
        if name in self.state:
            return self.state[name]
        raise ValueError(f"Unknown name: {name}")

    def visit_List(self, node: ast.List) -> Any:
        return [self.visit(e) for e in node.elts]

    def visit_Tuple(self, node: ast.Tuple) -> Any:
        return tuple(self.visit(e) for e in node.elts)

    # -- operators --
    def visit_Compare(self, node: ast.Compare) -> Any:
        left = self.visit(node.left)
        for op_node, comparator in zip(node.ops, node.comparators):
            right = self.visit(comparator)
            op_func = _CMP_OPS.get(type(op_node))
            if op_func is None:
                raise ValueError(f"Unsupported comparison: {type(op_node).__name__}")
            if not op_func(left, right):
                return False
            left = right
        return True

    def visit_BoolOp(self, node: ast.BoolOp) -> Any:
        if isinstance(node.op, ast.And):
            return all(self.visit(v) for v in node.values)
        if isinstance(node.op, ast.Or):
            return any(self.visit(v) for v in node.values)
        raise ValueError(f"Unsupported bool op: {type(node.op).__name__}")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        op_func = _UNARY_OPS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Unsupported unary op: {type(node.op).__name__}")
        return op_func(self.visit(node.operand))

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        op_func = _BIN_OPS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Unsupported binary op: {type(node.op).__name__}")
        return op_func(self.visit(node.left), self.visit(node.right))

    def visit_IfExp(self, node: ast.IfExp) -> Any:
        return self.visit(node.body) if self.visit(node.test) else self.visit(node.orelse)

    # -- subscript & attribute --
    def visit_Subscript(self, node: ast.Subscript) -> Any:
        value = self.visit(node.value)
        sl = self.visit(node.slice)
        return value[sl]

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        if node.attr.startswith("_"):
            raise ValueError(f"Access to private attribute '{node.attr}' is blocked")
        value = self.visit(node.value)
        return getattr(value, node.attr)

    # -- calls (allowlisted only) --
    def visit_Call(self, node: ast.Call) -> Any:
        func = self.visit(node.func)
        if func not in (len, min, max, abs, str, int, float, bool):
            raise ValueError(f"Function call not allowed: {func}")
        args = [self.visit(a) for a in node.args]
        return func(*args)

    # -- catch-all --
    def generic_visit(self, node: ast.AST) -> Any:
        raise ValueError(f"Unsupported expression: {type(node).__name__}")

    # Override visit to handle Expression wrapper
    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)


def safe_eval_condition(expr: str, state: Dict[str, Any]) -> bool:
    """
    Evaluate a condition expression safely using AST parsing.

    Only allows comparisons, boolean ops, arithmetic, subscripts,
    and a small set of allowlisted builtins (len, min, max, abs, str,
    int, float, bool).

    Raises ValueError on disallowed constructs (import, lambda, dunder access, etc.).
    """
    tree = ast.parse(expr, mode="eval")
    evaluator = _SafeEvaluator(state)
    return evaluator.visit(tree)


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

    # Load edges (skip terminal edges where target is null)
    for edge_def in yaml_data.get("edges", []):
        target = edge_def.get("to")
        if target is None:
            continue  # null target = terminal node, no edge needed
        runner.add_edge(Edge(
            source=edge_def["from"],
            target=target,
            condition=edge_def.get("condition"),
        ))

    return runner


def _import_function(path: str) -> Callable:
    """Import a function from a dotted path."""
    import sys
    from importlib import import_module

    if not path:
        return _noop_func

    parts = path.rsplit(".", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid function path: {path}")

    # Ensure workspace root (cwd) is importable so pods/ packages resolve
    import os
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    module_path, func_name = parts
    try:
        module = import_module(module_path)
        return getattr(module, func_name)
    except (ImportError, AttributeError) as e:
        raise ValueError(f"Could not import '{path}': {e}")


def _noop_func(state: Dict[str, Any]) -> Dict[str, Any]:
    """No-op function for nodes without implementation."""
    return state
