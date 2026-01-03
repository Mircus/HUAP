
from typing import Any, Dict

class Policy:
    """Very light policy placeholder. Extend for capabilities, auditing, etc."""
    def before_tool(self, tool_name: str, input: Dict[str, Any], ctx: Dict[str, Any] | None = None) -> None:
        # Insert capability checks and auditing here
        return

    def after_tool(self, tool_name: str, output: Dict[str, Any] | None, ctx: Dict[str, Any] | None = None) -> None:
        return
