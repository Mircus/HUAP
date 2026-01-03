"""
Built-in tools for HUAP.

These tools provide core functionality that all pods can use:
- echo: Echo a message back
- add: Add two numbers
- llm_call: Call LLM with prompt
- http_fetch: Make HTTP requests
- memory_read/write/delete/list: File-based key-value storage
"""
from .echo import EchoTool
from .add import AddTool
from .llm_call import LLMCallTool
from .http_fetch import HTTPFetchTool
from .memory import MemoryReadTool, MemoryWriteTool, MemoryDeleteTool, MemoryListTool

__all__ = [
    "EchoTool",
    "AddTool",
    "LLMCallTool",
    "HTTPFetchTool",
    "MemoryReadTool",
    "MemoryWriteTool",
    "MemoryDeleteTool",
    "MemoryListTool",
]


def register_builtin_tools(registry) -> None:
    """Register all built-in tools with a registry."""
    tools = [
        EchoTool(),
        AddTool(),
        LLMCallTool(),
        HTTPFetchTool(),
        MemoryReadTool(),
        MemoryWriteTool(),
        MemoryDeleteTool(),
        MemoryListTool(),
    ]
    for tool in tools:
        try:
            registry.register(tool)
        except ValueError:
            # Already registered
            pass
