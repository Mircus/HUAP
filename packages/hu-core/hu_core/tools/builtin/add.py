"""
Add Tool - Simple number addition for testing.

Pure Python, no external dependencies.
"""
from ..base import BaseTool, ExecutionContext, ToolCategory, ToolResult, ToolStatus


class AddTool(BaseTool):
    """Add two numbers together."""

    name = "add"
    description = "Add two numbers together"
    category = ToolCategory.UTILITY

    input_schema = {
        "type": "object",
        "properties": {
            "a": {
                "type": "number",
                "description": "First number",
            },
            "b": {
                "type": "number",
                "description": "Second number",
            },
        },
        "required": ["a", "b"],
    }

    async def execute(
        self,
        input_data: dict,
        context: ExecutionContext = None,
    ) -> ToolResult:
        """Execute the add tool."""
        a = input_data.get("a", 0)
        b = input_data.get("b", 0)
        result = a + b
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"result": result},
        )
