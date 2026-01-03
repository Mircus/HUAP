"""
Echo Tool - Simple text echo for testing.

Pure Python, no external dependencies.
"""
from ..base import BaseTool, ExecutionContext, ToolCategory, ToolResult, ToolStatus


class EchoTool(BaseTool):
    """Echo a message back."""

    name = "echo"
    description = "Echo a message back unchanged"
    category = ToolCategory.UTILITY

    input_schema = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Message to echo",
            },
        },
        "required": ["message"],
    }

    async def execute(
        self,
        input_data: dict,
        context: ExecutionContext = None,
    ) -> ToolResult:
        """Execute the echo tool."""
        message = input_data.get("message", "")
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"echoed": message},
        )
