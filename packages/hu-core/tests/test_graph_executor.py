"""Tests for graph loading and pod executor."""
import pytest
import yaml
from pathlib import Path

from hu_core.orchestrator.graph import (
    GraphRunner,
    Node,
    Edge,
    load_graph_from_yaml,
    safe_eval_condition,
    _noop_func,
)
from hu_core.orchestrator.executor import PodExecutor


# ---------------------------------------------------------------------------
# Graph structure tests
# ---------------------------------------------------------------------------

class TestGraphRunner:
    def test_add_node(self):
        runner = GraphRunner()
        runner.add_node(Node(name="a", func=_noop_func))
        assert "a" in runner.nodes

    def test_add_edge(self):
        runner = GraphRunner()
        runner.add_edge(Edge(source="a", target="b"))
        assert "a" in runner.edges
        assert runner.edges["a"][0].target == "b"

    def test_validate_missing_target(self):
        runner = GraphRunner()
        runner.add_node(Node(name="a", func=_noop_func))
        runner.add_edge(Edge(source="a", target="b"))
        errors = runner.validate()
        assert any("b" in e for e in errors)

    def test_validate_ok(self):
        runner = GraphRunner()
        runner.add_node(Node(name="a", func=_noop_func))
        runner.add_node(Node(name="b", func=_noop_func))
        runner.add_edge(Edge(source="a", target="b"))
        errors = runner.validate()
        assert errors == []

    @pytest.mark.asyncio
    async def test_run_simple_graph(self):
        def inc(state):
            return {"x": state.get("x", 0) + 1}

        runner = GraphRunner()
        runner.add_node(Node(name="a", func=inc))
        runner.add_node(Node(name="b", func=inc))
        runner.add_edge(Edge(source="a", target="b"))

        result = await runner.run("a", {"x": 0})
        assert result["x"] == 2

    @pytest.mark.asyncio
    async def test_run_missing_start_raises(self):
        runner = GraphRunner()
        with pytest.raises(ValueError, match="not found"):
            await runner.run("missing", {})


# ---------------------------------------------------------------------------
# Safe condition evaluator tests
# ---------------------------------------------------------------------------

class TestSafeEvalCondition:
    def test_condition_simple_compare(self):
        assert safe_eval_condition("status == 'success'", {"status": "success"}) is True
        assert safe_eval_condition("status == 'success'", {"status": "fail"}) is False

    def test_condition_boolean_ops(self):
        assert safe_eval_condition("x > 0 and y < 10", {"x": 5, "y": 3}) is True
        assert safe_eval_condition("x > 0 and y < 10", {"x": -1, "y": 3}) is False

    def test_condition_no_condition(self):
        edge = Edge(source="a", target="b", condition=None)
        assert edge.evaluate_condition({}) is True

    def test_condition_len_call(self):
        assert safe_eval_condition("len(items) > 0", {"items": [1, 2, 3]}) is True
        assert safe_eval_condition("len(items) > 0", {"items": []}) is False

    def test_condition_in_operator(self):
        assert safe_eval_condition("'admin' in roles", {"roles": ["admin", "user"]}) is True
        assert safe_eval_condition("'admin' in roles", {"roles": ["user"]}) is False

    def test_condition_blocks_import(self):
        edge = Edge(source="a", target="b", condition="__import__('os')")
        assert edge.evaluate_condition({}) is False

    def test_condition_blocks_dunder(self):
        edge = Edge(source="a", target="b", condition="x.__class__.__bases__")
        assert edge.evaluate_condition({"x": 1}) is False

    def test_condition_invalid_syntax(self):
        edge = Edge(source="a", target="b", condition="!!!")
        assert edge.evaluate_condition({}) is False


# ---------------------------------------------------------------------------
# YAML loading tests
# ---------------------------------------------------------------------------

class TestLoadGraphFromYaml:
    def test_load_hello_yaml(self):
        """Load the real hello.yaml and check structure."""
        repo = Path(__file__).resolve().parents[3]
        hello = repo / "examples" / "graphs" / "hello.yaml"
        if not hello.exists():
            pytest.skip("hello.yaml not found")

        with open(hello) as f:
            data = yaml.safe_load(f)

        runner = load_graph_from_yaml(data)
        assert "echo_tool" in runner.nodes
        assert "echo_greet" in runner.nodes
        errors = runner.validate()
        assert errors == []

    def test_load_minimal(self):
        data = {
            "nodes": [
                {"name": "a", "run": ""},
                {"name": "b", "run": ""},
            ],
            "edges": [
                {"from": "a", "to": "b"},
            ],
        }
        runner = load_graph_from_yaml(data)
        assert len(runner.nodes) == 2
        assert runner.validate() == []

    def test_load_with_condition(self):
        data = {
            "nodes": [
                {"name": "a", "run": ""},
                {"name": "b", "run": ""},
            ],
            "edges": [
                {"from": "a", "to": "b", "condition": "x > 0"},
            ],
        }
        runner = load_graph_from_yaml(data)
        assert runner.edges["a"][0].condition == "x > 0"

    def test_empty_graph(self):
        runner = load_graph_from_yaml({"nodes": [], "edges": []})
        assert len(runner.nodes) == 0


# ---------------------------------------------------------------------------
# PodExecutor tests
# ---------------------------------------------------------------------------

class TestPodExecutor:
    @pytest.mark.asyncio
    async def test_run_hello_graph(self):
        """Run the real hello.yaml graph end-to-end."""
        repo = Path(__file__).resolve().parents[3]
        hello = repo / "examples" / "graphs" / "hello.yaml"
        if not hello.exists():
            pytest.skip("hello.yaml not found")

        import os
        orig_cwd = os.getcwd()
        try:
            os.chdir(str(repo))
            executor = PodExecutor()
            result = await executor.run(
                graph_path=hello,
                initial_state={"message": "hi"},
                pod_name="hello",
            )
            # echo_tool echoes message, echo_greet creates greeting
            assert "echoed" in result
            assert "greeting" in result
        finally:
            os.chdir(orig_cwd)

    @pytest.mark.asyncio
    async def test_missing_graph_raises(self, tmp_path):
        executor = PodExecutor()
        with pytest.raises(FileNotFoundError):
            await executor.run(
                graph_path=tmp_path / "nonexistent.yaml",
                initial_state={},
                pod_name="test",
            )
