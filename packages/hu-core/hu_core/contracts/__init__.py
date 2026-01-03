"""
Pod Contract System.

This package provides:
- PodContract: Base class for pod implementations
- Contract validation utilities
- Type definitions for capabilities, tools, and trace requirements

Usage:
    from hu_core.contracts import PodContract, validate_pod

    class MySomaPod(PodContract):
        @property
        def name(self) -> str:
            return "soma"
        # ... implement other abstract methods

    # Validate pod implementation
    result = validate_pod(MySomaPod)
    if not result.valid:
        for issue in result.issues:
            print(f"{issue.severity}: {issue.message}")
"""

# Import from _base module (contracts base classes)
from ._base import (
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

# Export validation utilities
from .validation import (
    ContractValidator,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    validate_pod,
    validate_trace,
)

__all__ = [
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
    # Validation
    "ContractValidator",
    "ValidationResult",
    "ValidationIssue",
    "ValidationSeverity",
    "validate_pod",
    "validate_trace",
]
