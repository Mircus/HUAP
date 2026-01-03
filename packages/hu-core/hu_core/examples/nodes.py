"""
Example Node Functions for HUAP workflows.

These are simple, pure-Python node functions for testing.
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


def normalize_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize text to lowercase."""
    text = state.get("text", state.get("message", ""))
    return {"normalized": text.lower().strip()}


def end_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """End node - marks workflow complete."""
    return {"status": "complete"}
