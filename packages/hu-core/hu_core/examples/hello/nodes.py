"""
Hello Demo Nodes — minimal 2-node echo pipeline (bundled with package).
"""
from typing import Any, Dict


async def echo_tool(state: Dict[str, Any]) -> Dict[str, Any]:
    """Echo tool node - echoes the input message."""
    message = state.get("message", "")
    return {"echoed": message}


async def echo_greet(state: Dict[str, Any]) -> Dict[str, Any]:
    """Echo greet node - generates a greeting."""
    echoed = state.get("echoed", "")
    greeting = f"Hello there! I heard you say '{echoed}' - what a classic greeting!"
    return {"greeting": greeting}
