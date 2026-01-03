"""
Hello Pod Node Functions.

Simple node functions for the hello workflow.
"""
from typing import Any, Dict


def echo_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Echo the message in state."""
    message = state.get("message", "Hello, World!")
    return {"echoed": message}


def add_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Add two numbers from state."""
    a = state.get("a", 0)
    b = state.get("b", 0)
    return {"sum": a + b}


def greet_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a greeting."""
    name = state.get("name", "World")
    return {"greeting": f"Hello, {name}!"}


def end_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """End node - just pass through."""
    return {"status": "complete"}
