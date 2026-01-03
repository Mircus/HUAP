"""
Memory Tools - File-based key-value storage.

Pure Python, no external dependencies.
Uses FileKVStore for persistence.
"""
from ..base import BaseTool, ExecutionContext, ToolCategory, ToolResult, ToolStatus


class MemoryReadTool(BaseTool):
    """Read a value from pod memory."""

    name = "memory_read"
    description = "Read a value from pod memory by key"
    category = ToolCategory.STORAGE

    input_schema = {
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": "Key to read",
            },
            "namespace": {
                "type": "string",
                "description": "Namespace (default: pod name)",
                "default": "default",
            },
        },
        "required": ["key"],
    }

    async def execute(
        self,
        input_data: dict,
        context: ExecutionContext = None,
    ) -> ToolResult:
        """Execute the memory read tool."""
        from ...persistence import FileKVStore

        key = input_data.get("key")
        namespace = input_data.get("namespace", "default")

        if context and context.pod_name:
            namespace = context.pod_name

        store = FileKVStore()
        value = store.get(namespace, key)

        if value is None:
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"key": key, "value": None, "found": False},
            )

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"key": key, "value": value, "found": True},
        )


class MemoryWriteTool(BaseTool):
    """Write a value to pod memory."""

    name = "memory_write"
    description = "Write a value to pod memory by key"
    category = ToolCategory.STORAGE

    input_schema = {
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": "Key to write",
            },
            "value": {
                "description": "Value to store (any JSON-serializable type)",
            },
            "namespace": {
                "type": "string",
                "description": "Namespace (default: pod name)",
                "default": "default",
            },
        },
        "required": ["key", "value"],
    }

    async def execute(
        self,
        input_data: dict,
        context: ExecutionContext = None,
    ) -> ToolResult:
        """Execute the memory write tool."""
        from ...persistence import FileKVStore

        key = input_data.get("key")
        value = input_data.get("value")
        namespace = input_data.get("namespace", "default")

        if context and context.pod_name:
            namespace = context.pod_name

        store = FileKVStore()
        store.set(namespace, key, value)

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"key": key, "written": True},
        )


class MemoryDeleteTool(BaseTool):
    """Delete a value from pod memory."""

    name = "memory_delete"
    description = "Delete a value from pod memory by key"
    category = ToolCategory.STORAGE

    input_schema = {
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": "Key to delete",
            },
            "namespace": {
                "type": "string",
                "description": "Namespace (default: pod name)",
                "default": "default",
            },
        },
        "required": ["key"],
    }

    async def execute(
        self,
        input_data: dict,
        context: ExecutionContext = None,
    ) -> ToolResult:
        """Execute the memory delete tool."""
        from ...persistence import FileKVStore

        key = input_data.get("key")
        namespace = input_data.get("namespace", "default")

        if context and context.pod_name:
            namespace = context.pod_name

        store = FileKVStore()
        deleted = store.delete(namespace, key)

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"key": key, "deleted": deleted},
        )


class MemoryListTool(BaseTool):
    """List all keys in pod memory."""

    name = "memory_list"
    description = "List all keys in pod memory"
    category = ToolCategory.STORAGE

    input_schema = {
        "type": "object",
        "properties": {
            "namespace": {
                "type": "string",
                "description": "Namespace (default: pod name)",
                "default": "default",
            },
        },
    }

    async def execute(
        self,
        input_data: dict,
        context: ExecutionContext = None,
    ) -> ToolResult:
        """Execute the memory list tool."""
        from ...persistence import FileKVStore

        namespace = input_data.get("namespace", "default")

        if context and context.pod_name:
            namespace = context.pod_name

        store = FileKVStore()
        keys = store.list_keys(namespace)

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"namespace": namespace, "keys": keys, "count": len(keys)},
        )
