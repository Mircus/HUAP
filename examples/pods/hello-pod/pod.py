"""
Hello Pod - Minimal deterministic pod for HUAP demos.

Demonstrates:
- Tool registration and execution
- Trace recording
- State management
- Deterministic replay
"""
from __future__ import annotations

from typing import Any, Dict, List
from hu_core.tools import BaseTool, ToolResult, ToolStatus, ToolCategory


# =============================================================================
# TOOLS
# =============================================================================

class EchoTool(BaseTool):
    """Echo tool - returns the input message."""

    name = "echo"
    description = "Echo back the input message"
    category = ToolCategory.UTILITY

    input_schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Message to echo"},
        },
        "required": ["message"],
    }

    async def execute(self, input_data: Dict[str, Any], context: Any = None) -> ToolResult:
        message = input_data.get("message", "")
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"echoed": message, "length": len(message)},
        )


class AddTool(BaseTool):
    """Add tool - adds two numbers."""

    name = "add"
    description = "Add two numbers together"
    category = ToolCategory.UTILITY

    input_schema = {
        "type": "object",
        "properties": {
            "a": {"type": "number", "description": "First number"},
            "b": {"type": "number", "description": "Second number"},
        },
        "required": ["a", "b"],
    }

    async def execute(self, input_data: Dict[str, Any], context: Any = None) -> ToolResult:
        a = input_data.get("a", 0)
        b = input_data.get("b", 0)
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"result": a + b, "expression": f"{a} + {b}"},
        )


class NormalizeTextTool(BaseTool):
    """Normalize text - lowercase and strip whitespace."""

    name = "normalize_text"
    description = "Normalize text by lowercasing and stripping whitespace"
    category = ToolCategory.UTILITY

    input_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to normalize"},
        },
        "required": ["text"],
    }

    async def execute(self, input_data: Dict[str, Any], context: Any = None) -> ToolResult:
        text = input_data.get("text", "")
        normalized = text.lower().strip()
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "normalized": normalized,
                "original_length": len(text),
                "normalized_length": len(normalized),
            },
        )


# =============================================================================
# POD
# =============================================================================

class HelloPod:
    """
    Hello Pod - Minimal example for HUAP demos.

    This pod demonstrates:
    - Registering deterministic tools
    - Running a simple workflow
    - Recording traces
    - Verifying replay
    """

    name = "hello"
    version = "0.1.0"
    description = "Minimal example pod for HUAP demos"

    def __init__(self):
        self.tools = [EchoTool(), AddTool(), NormalizeTextTool()]

    def get_tools(self) -> List[BaseTool]:
        """Return the tools provided by this pod."""
        return self.tools

    async def run(self, input_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the hello workflow.

        Input:
            message: str - Message to process
            numbers: list[int] - Numbers to add (optional)

        Output:
            echoed: str - Echoed message
            normalized: str - Normalized message
            sum: int - Sum of numbers (if provided)
        """
        result = {}

        # Echo the message
        message = input_state.get("message", "Hello, HUAP!")
        echo_tool = EchoTool()
        echo_result = await echo_tool.execute({"message": message})
        result["echoed"] = echo_result.data["echoed"]

        # Normalize the message
        normalize_tool = NormalizeTextTool()
        norm_result = await normalize_tool.execute({"text": message})
        result["normalized"] = norm_result.data["normalized"]

        # Add numbers if provided
        numbers = input_state.get("numbers", [])
        if numbers:
            add_tool = AddTool()
            total = 0
            for num in numbers:
                add_result = await add_tool.execute({"a": total, "b": num})
                total = add_result.data["result"]
            result["sum"] = total

        return result


# Singleton instance
_POD_INSTANCE: HelloPod | None = None


def get_pod() -> HelloPod:
    """Factory function for pod registry."""
    global _POD_INSTANCE
    if _POD_INSTANCE is None:
        _POD_INSTANCE = HelloPod()
    return _POD_INSTANCE
