"""
HUAP Core Library.

Provides core components for the HUAP multi-pod agent platform:
- Trace system for replayable, eval-ready agent runs
- Orchestrator for graph-based pod workflows
- Tools registry for tool registration and execution
- Services (LLM client, audit, etc.)
- Policy enforcement
- Pod contracts for standardized pod interfaces
"""

__version__ = "0.1.0"

# Expose trace module at package level for easy imports
from . import trace

# Expose contract types for pod implementations
from .contracts import (
    CONTRACT_VERSION,
    PodContract,
    Pod,
    PodSchema,
    PodCapability,
    ToolDeclaration,
    TraceRequirement,
    REQUIRED_TRACE_EVENTS,
    RECOMMENDED_TRACE_EVENTS,
)

__all__ = [
    "__version__",
    "trace",
    # Contract types
    "CONTRACT_VERSION",
    "PodContract",
    "Pod",
    "PodSchema",
    "PodCapability",
    "ToolDeclaration",
    "TraceRequirement",
    "REQUIRED_TRACE_EVENTS",
    "RECOMMENDED_TRACE_EVENTS",
]
