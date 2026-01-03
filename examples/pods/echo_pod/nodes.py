"""
Echo Pod Nodes - Minimal node implementations for testing.
"""
from typing import Any, Dict


async def echo_tool(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Echo tool node - echoes the input message.

    In a real pod, this would call a registered tool.
    For testing, we just echo the message directly.
    """
    message = state.get("message", "")
    return {"echoed": message}


async def echo_greet(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Echo greet node - generates a greeting.

    In a real pod, this would call an LLM.
    For testing, we generate a simple greeting.
    """
    echoed = state.get("echoed", "")
    greeting = f"Hello there! I heard you say '{echoed}' - what a classic greeting!"
    return {"greeting": greeting}
