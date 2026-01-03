"""
Memory Pod - Example demonstrating state management.

Demonstrates:
- In-memory key-value store
- State refs for persistence
- Memory tracing events
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from hu_core.tools import BaseTool, ToolResult, ToolStatus, ToolCategory


# =============================================================================
# SIMPLE MEMORY STORE
# =============================================================================

class MemoryStore:
    """Simple in-memory key-value store for demos."""

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._history: List[Dict[str, Any]] = []

    def put(self, key: str, value: Any) -> None:
        """Store a value."""
        self._data[key] = value
        self._history.append({"op": "put", "key": key, "value": value})

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value."""
        value = self._data.get(key, default)
        self._history.append({"op": "get", "key": key, "found": key in self._data})
        return value

    def delete(self, key: str) -> bool:
        """Delete a value."""
        existed = key in self._data
        if existed:
            del self._data[key]
        self._history.append({"op": "delete", "key": key, "existed": existed})
        return existed

    def list_keys(self) -> List[str]:
        """List all keys."""
        return list(self._data.keys())

    def clear(self) -> None:
        """Clear all data."""
        self._data.clear()
        self._history.append({"op": "clear"})

    def get_history(self) -> List[Dict[str, Any]]:
        """Get operation history."""
        return self._history.copy()


# Global memory store (for demo purposes)
_MEMORY_STORE: Optional[MemoryStore] = None


def get_memory_store() -> MemoryStore:
    """Get the global memory store."""
    global _MEMORY_STORE
    if _MEMORY_STORE is None:
        _MEMORY_STORE = MemoryStore()
    return _MEMORY_STORE


def reset_memory_store() -> None:
    """Reset the memory store (for testing)."""
    global _MEMORY_STORE
    _MEMORY_STORE = None


# =============================================================================
# TOOLS
# =============================================================================

class MemoryPutTool(BaseTool):
    """Store a value in memory."""

    name = "memory_put"
    description = "Store a key-value pair in memory"
    category = ToolCategory.STORAGE

    input_schema = {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Key to store under"},
            "value": {"description": "Value to store (any JSON-serializable type)"},
        },
        "required": ["key", "value"],
    }

    async def execute(self, input_data: Dict[str, Any], context: Any = None) -> ToolResult:
        key = input_data.get("key", "")
        value = input_data.get("value")

        if not key:
            return ToolResult(status=ToolStatus.ERROR, error="Key is required")

        store = get_memory_store()
        store.put(key, value)

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"key": key, "stored": True},
        )


class MemoryGetTool(BaseTool):
    """Retrieve a value from memory."""

    name = "memory_get"
    description = "Retrieve a value from memory by key"
    category = ToolCategory.STORAGE

    input_schema = {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Key to retrieve"},
            "default": {"description": "Default value if key not found"},
        },
        "required": ["key"],
    }

    async def execute(self, input_data: Dict[str, Any], context: Any = None) -> ToolResult:
        key = input_data.get("key", "")
        default = input_data.get("default")

        if not key:
            return ToolResult(status=ToolStatus.ERROR, error="Key is required")

        store = get_memory_store()
        value = store.get(key, default)

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"key": key, "value": value, "found": value is not default},
        )


class MemoryListTool(BaseTool):
    """List all keys in memory."""

    name = "memory_list"
    description = "List all keys currently stored in memory"
    category = ToolCategory.STORAGE

    input_schema = {
        "type": "object",
        "properties": {},
    }

    async def execute(self, input_data: Dict[str, Any], context: Any = None) -> ToolResult:
        store = get_memory_store()
        keys = store.list_keys()

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"keys": keys, "count": len(keys)},
        )


class MemoryDeleteTool(BaseTool):
    """Delete a value from memory."""

    name = "memory_delete"
    description = "Delete a key from memory"
    category = ToolCategory.STORAGE

    input_schema = {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Key to delete"},
        },
        "required": ["key"],
    }

    async def execute(self, input_data: Dict[str, Any], context: Any = None) -> ToolResult:
        key = input_data.get("key", "")

        if not key:
            return ToolResult(status=ToolStatus.ERROR, error="Key is required")

        store = get_memory_store()
        existed = store.delete(key)

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"key": key, "deleted": existed},
        )


# =============================================================================
# POD
# =============================================================================

class MemoryPod:
    """
    Memory Pod - Example for state management.

    Shows how to:
    - Store and retrieve data
    - Track memory operations in traces
    - Use StateRefs for persistence
    """

    name = "memory"
    version = "0.1.0"
    description = "Example pod demonstrating state management"

    def __init__(self):
        self.tools = [
            MemoryPutTool(),
            MemoryGetTool(),
            MemoryListTool(),
            MemoryDeleteTool(),
        ]

    def get_tools(self) -> List[BaseTool]:
        """Return the tools provided by this pod."""
        return self.tools

    async def run(self, input_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the memory workflow.

        Input:
            items: dict - Key-value pairs to store
            retrieve: list[str] - Keys to retrieve after storing

        Output:
            stored_count: int - Number of items stored
            retrieved: dict - Retrieved values
            all_keys: list[str] - All keys in memory
        """
        items = input_state.get("items", {})
        retrieve_keys = input_state.get("retrieve", [])

        # Reset store for clean run
        reset_memory_store()

        result = {}

        # Store items
        put_tool = MemoryPutTool()
        for key, value in items.items():
            await put_tool.execute({"key": key, "value": value})
        result["stored_count"] = len(items)

        # Retrieve requested keys
        get_tool = MemoryGetTool()
        retrieved = {}
        for key in retrieve_keys:
            get_result = await get_tool.execute({"key": key})
            if get_result.data.get("found"):
                retrieved[key] = get_result.data["value"]
        result["retrieved"] = retrieved

        # List all keys
        list_tool = MemoryListTool()
        list_result = await list_tool.execute({})
        result["all_keys"] = list_result.data["keys"]

        # Include operation history
        store = get_memory_store()
        result["operation_count"] = len(store.get_history())

        return result


# Singleton instance
_POD_INSTANCE: MemoryPod | None = None


def get_pod() -> MemoryPod:
    """Factory function for pod registry."""
    global _POD_INSTANCE
    if _POD_INSTANCE is None:
        _POD_INSTANCE = MemoryPod()
    return _POD_INSTANCE
