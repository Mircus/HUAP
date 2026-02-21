"""
Tool system base classes for HUAP.

Provides the foundation for a robust tool ecosystem where pods can
discover, validate, and execute tools with proper auditing.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


class ToolCategory(str, Enum):
    """
    Categories for organizing tools.

    - AI: LLM-powered tools (summarize, classify, generate)
    - MEMORY: In-memory state management (get, put, search)
    - STORAGE: Persistent file/KV storage (read, write, delete)
    - MESSAGING: Communication tools (email, sms, notifications)
    - HTTP: HTTP client tools (fetch, post)
    - DATA: Data transformation (parse, format, validate)
    - UTILITY: General purpose (echo, add, normalize)
    - EXTERNAL: Third-party API integrations (oauth services, webhooks)
    """
    AI = "ai"
    MEMORY = "memory"
    STORAGE = "storage"
    MESSAGING = "messaging"
    HTTP = "http"
    DATA = "data"
    UTILITY = "utility"
    EXTERNAL = "external"


@dataclass
class ToolSpec:
    """
    Specification for a tool including metadata and schemas.

    Attributes:
        name: Unique identifier for the tool
        description: Human-readable description
        version: Semantic version string
        category: Tool category for organization
        input_schema: JSON Schema for input validation
        output_schema: JSON Schema for output validation
        required_capabilities: Capabilities needed to use this tool
        tags: Additional tags for discovery
    """
    name: str
    description: str = ""
    version: str = "1.0.0"
    category: ToolCategory = ToolCategory.UTILITY
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    required_capabilities: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize spec to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "category": self.category.value,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "required_capabilities": self.required_capabilities,
            "tags": self.tags,
        }


@dataclass
class ExecutionContext:
    """
    Context passed to tool execution.

    Provides information about who is calling the tool and from where.
    """
    user_id: Optional[str] = None
    pod_name: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolStatus(str, Enum):
    """Status of tool execution."""
    SUCCESS = "success"
    ERROR = "error"
    DENIED = "denied"
    TIMEOUT = "timeout"
    VALIDATION_ERROR = "validation_error"


@dataclass
class ToolResult:
    """
    Standardized result from tool execution.

    Attributes:
        status: Execution status
        data: Result data on success
        error: Error message on failure
        duration_ms: Execution time in milliseconds
        metadata: Additional execution metadata
    """
    status: ToolStatus
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.status == ToolStatus.SUCCESS

    def to_dict(self) -> Dict[str, Any]:
        """Serialize result to dictionary."""
        return {
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


@runtime_checkable
class Tool(Protocol):
    """Protocol for tools that can be registered and executed."""
    spec: ToolSpec

    async def __call__(
        self,
        input: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute the tool with given input and context."""
        ...


class BaseTool(ABC):
    """
    Abstract base class for implementing tools.

    Provides common functionality and enforces the tool interface.
    Subclasses must implement the `execute` method.
    """

    @property
    @abstractmethod
    def spec(self) -> ToolSpec:
        """Return the tool specification."""
        ...

    @abstractmethod
    async def execute(
        self,
        input: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Execute the tool logic.

        Args:
            input: Validated input parameters
            context: Execution context with user/pod info

        Returns:
            Result data dictionary
        """
        ...

    async def __call__(
        self,
        input: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute the tool (delegates to execute method)."""
        return await self.execute(input, context)

    def validate_input(self, input: Dict[str, Any]) -> List[str]:
        """
        Validate input against the input schema.

        Returns list of validation errors (empty if valid).
        """
        errors = []
        schema = self.spec.input_schema

        if not schema:
            return errors

        # Check required fields
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        for field_name in required:
            if field_name not in input:
                errors.append(f"Missing required field: {field_name}")

        # Check field types
        for field_name, value in input.items():
            if field_name in properties:
                field_spec = properties[field_name]
                expected_type = field_spec.get("type")

                if expected_type and not self._check_type(value, expected_type):
                    errors.append(
                        f"Field '{field_name}' should be {expected_type}, "
                        f"got {type(value).__name__}"
                    )

        return errors

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected JSON schema type."""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None),
        }
        expected = type_map.get(expected_type)
        if expected is None:
            return True  # Unknown type, allow
        return isinstance(value, expected)
