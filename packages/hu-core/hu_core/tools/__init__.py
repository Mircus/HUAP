"""
HUAP Tool System.

Provides a robust tool ecosystem for pods with:
- Tool registration and discovery
- Input/output validation
- Execution with timing and logging
- Permission checking
- Built-in tools for common operations

Usage:
    from hu_core.tools import get_tool_registry, register_builtin_tools

    # Get the global registry
    registry = get_tool_registry()

    # Register built-in tools
    register_builtin_tools(registry)

    # Discover tools
    ai_tools = registry.discover(category=ToolCategory.AI)

    # Execute a tool
    result = await registry.execute(
        "llm_call",
        {"user_prompt": "Hello!"},
        context=ExecutionContext(user_id="123", pod_name="soma")
    )
"""
from .base import (
    BaseTool,
    ExecutionContext,
    Tool,
    ToolCategory,
    ToolResult,
    ToolSpec,
    ToolStatus,
)
from .registry import (
    ToolExecutionLog,
    ToolPermissionConfig,
    ToolRegistry,
    get_tool_registry,
    set_context_registry,
    reset_tool_registry,
)
from .builtin import register_builtin_tools

__all__ = [
    # Base classes
    "BaseTool",
    "ExecutionContext",
    "Tool",
    "ToolCategory",
    "ToolResult",
    "ToolSpec",
    "ToolStatus",
    # Registry
    "ToolExecutionLog",
    "ToolPermissionConfig",
    "ToolRegistry",
    "get_tool_registry",
    "set_context_registry",
    "reset_tool_registry",
    # Built-in tools
    "register_builtin_tools",
]
