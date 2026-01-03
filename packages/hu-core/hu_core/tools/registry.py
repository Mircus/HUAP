"""
Tool Registry for HUAP.

Provides centralized tool registration, discovery, and execution with
validation, timing, permission checking, and logging.
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from .base import (
    BaseTool,
    ExecutionContext,
    Tool,
    ToolCategory,
    ToolResult,
    ToolSpec,
    ToolStatus,
)

logger = logging.getLogger(__name__)


class ToolExecutionLog:
    """Record of a tool execution for auditing."""

    def __init__(
        self,
        tool_name: str,
        context: ExecutionContext,
        result: ToolResult,
        input_summary: Optional[str] = None,
    ):
        self.id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow()
        self.tool_name = tool_name
        self.user_id = context.user_id
        self.pod_name = context.pod_name
        self.session_id = context.session_id
        self.correlation_id = context.correlation_id
        self.status = result.status.value
        self.duration_ms = result.duration_ms
        self.error = result.error
        self.input_summary = input_summary

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "tool_name": self.tool_name,
            "user_id": self.user_id,
            "pod_name": self.pod_name,
            "session_id": self.session_id,
            "correlation_id": self.correlation_id,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "input_summary": self.input_summary,
        }


class ToolPermissionConfig:
    """Configuration for tool access permissions."""

    def __init__(self):
        # pod_name -> set of allowed tool names (* for all)
        self._pod_permissions: Dict[str, Set[str]] = {}
        # tool_name -> set of required capabilities
        self._tool_capabilities: Dict[str, Set[str]] = {}
        # Default: all pods can use all tools (can be restricted)
        self._allow_all_by_default = True

    def allow_pod(self, pod_name: str, tool_names: List[str]) -> None:
        """Allow a pod to use specific tools."""
        if pod_name not in self._pod_permissions:
            self._pod_permissions[pod_name] = set()
        self._pod_permissions[pod_name].update(tool_names)

    def allow_pod_all(self, pod_name: str) -> None:
        """Allow a pod to use all tools."""
        self._pod_permissions[pod_name] = {"*"}

    def deny_pod_all(self, pod_name: str) -> None:
        """Deny a pod access to all tools (must explicitly allow)."""
        self._pod_permissions[pod_name] = set()

    def set_tool_capabilities(self, tool_name: str, capabilities: List[str]) -> None:
        """Set required capabilities for a tool."""
        self._tool_capabilities[tool_name] = set(capabilities)

    def can_access(
        self,
        pod_name: Optional[str],
        tool_name: str,
        capabilities: List[str]
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a pod can access a tool.

        Returns (allowed, reason) tuple.
        """
        # Check pod-level permissions
        if pod_name and pod_name in self._pod_permissions:
            allowed_tools = self._pod_permissions[pod_name]
            if "*" not in allowed_tools and tool_name not in allowed_tools:
                return False, f"Pod '{pod_name}' not allowed to use tool '{tool_name}'"
        elif not self._allow_all_by_default and pod_name:
            return False, f"Pod '{pod_name}' has no tool permissions configured"

        # Check capability requirements
        if tool_name in self._tool_capabilities:
            required = self._tool_capabilities[tool_name]
            provided = set(capabilities)
            missing = required - provided
            if missing:
                return False, f"Missing capabilities: {', '.join(missing)}"

        return True, None


class ToolRegistry:
    """
    Central registry for tools in HUAP.

    Provides:
    - Tool registration with validation
    - Tool discovery by name, category, or capability
    - Execution with validation, timing, and logging
    - Permission checking
    - Tracing via TraceService integration
    """

    def __init__(self, tracer: Optional[Any] = None):
        self._tools: Dict[str, Tool] = {}
        self._execution_logs: List[ToolExecutionLog] = []
        self._permissions = ToolPermissionConfig()
        self._max_log_size = 10000  # Keep last N logs in memory
        self._on_execute_callbacks: List[Callable[[ToolExecutionLog], None]] = []
        self._tracer = tracer
        self._use_trace_service = hasattr(tracer, 'tool_call') if tracer else False

    def set_tracer(self, tracer: Any) -> None:
        """Set the tracer for this registry."""
        self._tracer = tracer
        self._use_trace_service = hasattr(tracer, 'tool_call') if tracer else False

    def get_tracer(self) -> Optional[Any]:
        """Get the current tracer for this registry."""
        return self._tracer

    # --- Registration ---

    def register(self, tool: Tool) -> None:
        """
        Register a tool with the registry.

        Args:
            tool: Tool instance implementing the Tool protocol

        Raises:
            ValueError: If tool with same name already exists
        """
        name = tool.spec.name
        if name in self._tools:
            raise ValueError(f"Tool '{name}' is already registered")

        self._tools[name] = tool
        logger.info(f"Registered tool: {name} v{tool.spec.version}")

    def unregister(self, name: str) -> bool:
        """
        Remove a tool from the registry.

        Returns True if tool was removed, False if not found.
        """
        if name in self._tools:
            del self._tools[name]
            logger.info(f"Unregistered tool: {name}")
            return True
        return False

    # --- Discovery ---

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[ToolSpec]:
        """List all registered tools."""
        return [tool.spec for tool in self._tools.values()]

    def discover(
        self,
        category: Optional[ToolCategory] = None,
        capability: Optional[str] = None,
        tag: Optional[str] = None,
        name_contains: Optional[str] = None,
    ) -> List[ToolSpec]:
        """
        Discover tools matching criteria.

        Args:
            category: Filter by tool category
            capability: Filter by required capability
            tag: Filter by tag
            name_contains: Filter by name substring

        Returns:
            List of matching tool specifications
        """
        results = []

        for tool in self._tools.values():
            spec = tool.spec

            # Apply filters
            if category and spec.category != category:
                continue
            if capability and capability not in spec.required_capabilities:
                continue
            if tag and tag not in spec.tags:
                continue
            if name_contains and name_contains.lower() not in spec.name.lower():
                continue

            results.append(spec)

        return results

    def get_by_category(self, category: ToolCategory) -> List[ToolSpec]:
        """Get all tools in a category."""
        return self.discover(category=category)

    # --- Execution ---

    async def execute(
        self,
        name: str,
        input: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
        validate: bool = True,
        check_permissions: bool = True,
    ) -> ToolResult:
        """
        Execute a tool with full validation, timing, logging, and tracing.

        Args:
            name: Tool name
            input: Input parameters
            context: Execution context (created if not provided)
            validate: Whether to validate input against schema
            check_permissions: Whether to check permissions

        Returns:
            ToolResult with status, data, and metadata
        """
        context = context or ExecutionContext()
        start_time = time.perf_counter()

        # Get tool
        tool = self._tools.get(name)
        if not tool:
            result = ToolResult(
                status=ToolStatus.ERROR,
                error=f"Tool '{name}' not found",
            )
            self._log_execution(name, context, result, input)
            self._trace_tool_result(name, result, context)
            return result

        # Check permissions
        permissions_dict = {}
        if check_permissions:
            allowed, reason = self._permissions.can_access(
                context.pod_name,
                name,
                context.capabilities
            )
            permissions_dict = {
                "allowed": allowed,
                "pod": context.pod_name,
                "capabilities": context.capabilities,
            }
            if not allowed:
                result = ToolResult(
                    status=ToolStatus.DENIED,
                    error=reason,
                )
                self._log_execution(name, context, result, input)
                self._trace_tool_result(name, result, context)
                return result

        # Validate input
        if validate and isinstance(tool, BaseTool):
            errors = tool.validate_input(input)
            if errors:
                result = ToolResult(
                    status=ToolStatus.VALIDATION_ERROR,
                    error="; ".join(errors),
                )
                self._log_execution(name, context, result, input)
                self._trace_tool_result(name, result, context)
                return result

        # Trace tool call (after validation passes)
        self._trace_tool_call(name, input, permissions_dict, context)

        # Execute tool
        try:
            data = await tool(input, context)
            duration_ms = (time.perf_counter() - start_time) * 1000

            result = ToolResult(
                status=ToolStatus.SUCCESS,
                data=data,
                duration_ms=duration_ms,
                metadata={
                    "tool_version": tool.spec.version,
                }
            )

        except TimeoutError as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            result = ToolResult(
                status=ToolStatus.TIMEOUT,
                error=str(e),
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(f"Tool '{name}' execution failed")
            result = ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
                duration_ms=duration_ms,
            )

        self._log_execution(name, context, result, input)
        self._trace_tool_result(name, result, context)
        return result

    # --- Permissions ---

    @property
    def permissions(self) -> ToolPermissionConfig:
        """Access permission configuration."""
        return self._permissions

    def validate_access(
        self,
        tool_name: str,
        pod_name: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if access to a tool is allowed.

        Returns (allowed, reason) tuple.
        """
        return self._permissions.can_access(
            pod_name,
            tool_name,
            capabilities or []
        )

    # --- Tracing ---

    def _trace_tool_call(
        self,
        tool_name: str,
        input: Dict[str, Any],
        permissions: Dict[str, Any],
        context: ExecutionContext,
    ) -> None:
        """Emit tool_call trace event."""
        if not self._tracer:
            return

        if self._use_trace_service:
            self._tracer.tool_call(
                tool=tool_name,
                input_data=input,
                permissions=permissions,
                pod=context.pod_name,
            )
        else:
            # Legacy callable tracer
            self._tracer({
                "event": "tool_call",
                "tool": tool_name,
                "input_keys": list(input.keys()) if input else [],
            })

    def _trace_tool_result(
        self,
        tool_name: str,
        result: ToolResult,
        context: ExecutionContext,
    ) -> None:
        """Emit tool_result trace event."""
        if not self._tracer:
            return

        if self._use_trace_service:
            result_data = result.data if result.data else {}
            self._tracer.tool_result(
                tool=tool_name,
                result=result_data if isinstance(result_data, dict) else {"value": result_data},
                duration_ms=result.duration_ms or 0,
                status=result.status.value,
                error=result.error,
                pod=context.pod_name,
            )
        else:
            # Legacy callable tracer
            self._tracer({
                "event": "tool_result",
                "tool": tool_name,
                "status": result.status.value,
                "duration_ms": result.duration_ms,
            })

    # --- Logging ---

    def _log_execution(
        self,
        tool_name: str,
        context: ExecutionContext,
        result: ToolResult,
        input: Dict[str, Any],
    ) -> None:
        """Log a tool execution."""
        # Create summary of input (avoid logging sensitive data)
        input_summary = ", ".join(input.keys()) if input else None

        log_entry = ToolExecutionLog(
            tool_name=tool_name,
            context=context,
            result=result,
            input_summary=input_summary,
        )

        # Store in memory (with limit)
        self._execution_logs.append(log_entry)
        if len(self._execution_logs) > self._max_log_size:
            self._execution_logs = self._execution_logs[-self._max_log_size:]

        # Log to standard logger
        log_level = logging.INFO if result.success else logging.WARNING
        logger.log(
            log_level,
            f"Tool execution: {tool_name} | "
            f"status={result.status.value} | "
            f"duration={result.duration_ms:.2f}ms | "
            f"pod={context.pod_name} | "
            f"user={context.user_id}"
        )

        # Notify callbacks
        for callback in self._on_execute_callbacks:
            try:
                callback(log_entry)
            except Exception:
                logger.exception("Error in tool execution callback")

    def get_execution_logs(
        self,
        tool_name: Optional[str] = None,
        pod_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get execution logs with optional filtering.

        Args:
            tool_name: Filter by tool name
            pod_name: Filter by pod name
            status: Filter by status
            limit: Maximum number of logs to return

        Returns:
            List of log entries as dictionaries
        """
        logs = self._execution_logs

        if tool_name:
            logs = [l for l in logs if l.tool_name == tool_name]
        if pod_name:
            logs = [l for l in logs if l.pod_name == pod_name]
        if status:
            logs = [l for l in logs if l.status == status]

        # Return most recent first
        return [l.to_dict() for l in reversed(logs[-limit:])]

    def on_execute(self, callback: Callable[[ToolExecutionLog], None]) -> None:
        """Register a callback to be called after each tool execution."""
        self._on_execute_callbacks.append(callback)

    # --- Stats ---

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_tools": len(self._tools),
            "total_executions": len(self._execution_logs),
            "tools_by_category": self._count_by_category(),
            "executions_by_status": self._count_by_status(),
        }

    def _count_by_category(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for tool in self._tools.values():
            cat = tool.spec.category.value
            counts[cat] = counts.get(cat, 0) + 1
        return counts

    def _count_by_status(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for log in self._execution_logs:
            counts[log.status] = counts.get(log.status, 0) + 1
        return counts


# =============================================================================
# CONTEXT-AWARE REGISTRY ACCESS
# =============================================================================

from contextvars import ContextVar

# Context-local registry (for concurrent run isolation)
_context_registry: ContextVar[Optional[ToolRegistry]] = ContextVar(
    "tool_registry", default=None
)

# Global registry instance (fallback when no context set)
_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """
    Get the tool registry for the current context.

    Resolution order:
    1. Context-local registry (if set via set_context_registry)
    2. Global singleton (fallback)

    This enables concurrent runs to use isolated registries without
    cross-contamination.
    """
    # Check context-local first
    ctx_registry = _context_registry.get()
    if ctx_registry is not None:
        return ctx_registry

    # Fall back to global singleton
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def set_context_registry(registry: Optional[ToolRegistry]) -> None:
    """
    Set the tool registry for the current async context.

    Use this to isolate concurrent runs:
        registry = ToolRegistry()
        set_context_registry(registry)
        try:
            await run_workflow(...)
        finally:
            set_context_registry(None)
    """
    _context_registry.set(registry)


def reset_tool_registry() -> None:
    """Reset the global tool registry (for testing)."""
    global _global_registry
    _global_registry = None
    _context_registry.set(None)


