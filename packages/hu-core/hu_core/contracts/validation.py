"""
Contract Validation - Verify pod contract compliance.

This module provides validation for:
1. Pod implementation compliance (all abstract methods implemented)
2. Trace event compliance (required events emitted)
3. Tool declaration compliance (required tools available)

See docs/POD_CONTRACT_v0.1.md for full specification.
"""

from typing import Dict, Any, List, Optional, Set, Type
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

from ._base import (
    PodContract,
    REQUIRED_TRACE_EVENTS,
    RECOMMENDED_TRACE_EVENTS,
    ToolDeclaration,
)


class ValidationSeverity(str, Enum):
    """Severity level for validation issues."""
    ERROR = "error"      # Fails validation
    WARNING = "warning"  # Non-blocking issue
    INFO = "info"        # Informational note


@dataclass
class ValidationIssue:
    """Single validation issue found."""
    severity: ValidationSeverity
    code: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of contract validation."""
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    pod_name: Optional[str] = None
    contract_version: Optional[str] = None

    def add_error(self, code: str, message: str, **context) -> None:
        """Add an error issue."""
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            code=code,
            message=message,
            context=context
        ))
        self.valid = False

    def add_warning(self, code: str, message: str, **context) -> None:
        """Add a warning issue."""
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.WARNING,
            code=code,
            message=message,
            context=context
        ))

    def add_info(self, code: str, message: str, **context) -> None:
        """Add an informational note."""
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.INFO,
            code=code,
            message=message,
            context=context
        ))

    @property
    def errors(self) -> List[ValidationIssue]:
        """Get only error issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        """Get only warning issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "pod_name": self.pod_name,
            "contract_version": self.contract_version,
            "issue_count": len(self.issues),
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "issues": [
                {
                    "severity": i.severity.value,
                    "code": i.code,
                    "message": i.message,
                    "context": i.context
                }
                for i in self.issues
            ]
        }

    def to_markdown(self) -> str:
        """Generate markdown report."""
        lines = []
        status = "✅ PASS" if self.valid else "❌ FAIL"
        lines.append(f"# Contract Validation: {status}")
        lines.append("")

        if self.pod_name:
            lines.append(f"**Pod:** {self.pod_name}")
        if self.contract_version:
            lines.append(f"**Contract Version:** {self.contract_version}")
        lines.append("")

        if not self.issues:
            lines.append("No issues found.")
        else:
            lines.append(f"## Issues ({len(self.issues)})")
            lines.append("")

            for issue in self.issues:
                icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(issue.severity.value, "•")
                lines.append(f"- {icon} **{issue.code}**: {issue.message}")
                if issue.context:
                    for k, v in issue.context.items():
                        lines.append(f"  - {k}: {v}")

        return "\n".join(lines)


class ContractValidator:
    """
    Validates pod contract compliance.

    Usage:
        validator = ContractValidator()

        # Validate pod implementation
        result = validator.validate_pod(MyPod)

        # Validate trace file
        result = validator.validate_trace("trace.jsonl", MyPod)
    """

    def validate_pod(self, pod_class: Type[PodContract]) -> ValidationResult:
        """
        Validate a pod class implements the contract correctly.

        Args:
            pod_class: Pod class to validate

        Returns:
            ValidationResult with any issues found
        """
        result = ValidationResult(valid=True)

        # Check it's a subclass of PodContract
        if not issubclass(pod_class, PodContract):
            result.add_error(
                "NOT_POD_CONTRACT",
                f"{pod_class.__name__} is not a subclass of PodContract"
            )
            return result

        # Try to instantiate
        try:
            pod = pod_class()
        except Exception as e:
            result.add_error(
                "INSTANTIATION_FAILED",
                f"Failed to instantiate {pod_class.__name__}: {e}"
            )
            return result

        result.pod_name = pod.name
        result.contract_version = pod.get_contract_version()

        # Validate required properties
        self._validate_properties(pod, result)

        # Validate schema
        self._validate_schema(pod, result)

        # Validate capabilities
        self._validate_capabilities(pod, result)

        # Validate tool declarations
        self._validate_tools(pod, result)

        return result

    def _validate_properties(self, pod: PodContract, result: ValidationResult) -> None:
        """Validate required pod properties."""
        # Name
        if not pod.name:
            result.add_error("MISSING_NAME", "Pod name is empty")
        elif not pod.name.islower() or not pod.name.replace("_", "").isalnum():
            result.add_warning(
                "INVALID_NAME_FORMAT",
                f"Pod name '{pod.name}' should be lowercase alphanumeric with underscores"
            )

        # Version
        if not pod.version:
            result.add_error("MISSING_VERSION", "Pod version is empty")
        else:
            parts = pod.version.split(".")
            if len(parts) != 3 or not all(p.isdigit() for p in parts):
                result.add_warning(
                    "INVALID_VERSION_FORMAT",
                    f"Version '{pod.version}' should be semantic (x.y.z)"
                )

        # Description
        if not pod.description:
            result.add_warning("MISSING_DESCRIPTION", "Pod description is empty")

    def _validate_schema(self, pod: PodContract, result: ValidationResult) -> None:
        """Validate pod schema."""
        try:
            schema = pod.get_schema()
        except Exception as e:
            result.add_error("SCHEMA_ERROR", f"Failed to get schema: {e}")
            return

        if schema.pod_name != pod.name:
            result.add_warning(
                "SCHEMA_NAME_MISMATCH",
                f"Schema pod_name '{schema.pod_name}' doesn't match pod name '{pod.name}'"
            )

        if not schema.fields:
            result.add_info("EMPTY_SCHEMA", "Pod schema has no fields defined")

        # Validate each field
        for i, fld in enumerate(schema.fields):
            if not isinstance(fld, dict):
                result.add_error(
                    "INVALID_FIELD",
                    f"Field {i} is not a dictionary"
                )
                continue

            if "name" not in fld:
                result.add_error("FIELD_MISSING_NAME", f"Field {i} has no 'name'")

            if "type" not in fld:
                result.add_error(
                    "FIELD_MISSING_TYPE",
                    f"Field {i} ({fld.get('name', '?')}) has no 'type'"
                )

    def _validate_capabilities(self, pod: PodContract, result: ValidationResult) -> None:
        """Validate pod capabilities."""
        try:
            capabilities = pod.get_capabilities()
        except Exception as e:
            result.add_error("CAPABILITIES_ERROR", f"Failed to get capabilities: {e}")
            return

        if not capabilities:
            result.add_info("NO_CAPABILITIES", "Pod declares no capabilities")

    def _validate_tools(self, pod: PodContract, result: ValidationResult) -> None:
        """Validate tool declarations."""
        try:
            tools = pod.get_required_tools()
        except Exception as e:
            result.add_error("TOOLS_ERROR", f"Failed to get required tools: {e}")
            return

        for tool in tools:
            if not isinstance(tool, ToolDeclaration):
                result.add_error(
                    "INVALID_TOOL_DECLARATION",
                    f"Tool declaration is not a ToolDeclaration: {tool}"
                )
                continue

            if not tool.name:
                result.add_error("TOOL_MISSING_NAME", "Tool declaration has empty name")

    def validate_trace(
        self,
        trace_path: str,
        pod: Optional[PodContract] = None
    ) -> ValidationResult:
        """
        Validate a trace file for contract compliance.

        Args:
            trace_path: Path to JSONL trace file
            pod: Optional pod instance for additional validation

        Returns:
            ValidationResult with any issues found
        """
        result = ValidationResult(valid=True)
        path = Path(trace_path)

        if not path.exists():
            result.add_error("TRACE_NOT_FOUND", f"Trace file not found: {trace_path}")
            return result

        # Parse trace events
        events = []
        try:
            with open(path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        events.append(event)
                    except json.JSONDecodeError as e:
                        result.add_error(
                            "INVALID_JSON",
                            f"Invalid JSON on line {line_num}: {e}"
                        )
        except Exception as e:
            result.add_error("TRACE_READ_ERROR", f"Failed to read trace: {e}")
            return result

        if not events:
            result.add_error("EMPTY_TRACE", "Trace file contains no events")
            return result

        # Extract pod name from first event
        first_event = events[0]
        result.pod_name = first_event.get("pod")

        # Check for required events
        event_names = {e.get("name") for e in events}
        self._validate_required_events(event_names, result, pod)

        # Check for recommended events
        self._validate_recommended_events(event_names, result)

        # Validate event structure
        self._validate_event_structure(events, result)

        # Check run lifecycle
        self._validate_run_lifecycle(events, result)

        return result

    def _validate_required_events(
        self,
        event_names: Set[str],
        result: ValidationResult,
        pod: Optional[PodContract] = None
    ) -> None:
        """Check that required trace events are present."""
        required = REQUIRED_TRACE_EVENTS
        if pod:
            required = pod.get_trace_requirements()

        missing = required - event_names
        if missing:
            result.add_error(
                "MISSING_REQUIRED_EVENTS",
                f"Missing required trace events: {', '.join(sorted(missing))}",
                missing_events=list(missing)
            )

    def _validate_recommended_events(
        self,
        event_names: Set[str],
        result: ValidationResult
    ) -> None:
        """Check for recommended trace events."""
        missing = RECOMMENDED_TRACE_EVENTS - event_names
        if missing:
            result.add_info(
                "MISSING_RECOMMENDED_EVENTS",
                f"Missing recommended trace events: {', '.join(sorted(missing))}",
                missing_events=list(missing)
            )

    def _validate_event_structure(
        self,
        events: List[Dict[str, Any]],
        result: ValidationResult
    ) -> None:
        """Validate event structure matches spec."""
        required_fields = {"v", "ts", "run_id", "span_id", "kind", "name", "data"}

        for i, event in enumerate(events):
            missing = required_fields - set(event.keys())
            if missing:
                result.add_warning(
                    "EVENT_MISSING_FIELDS",
                    f"Event {i} missing fields: {', '.join(missing)}",
                    event_index=i,
                    event_name=event.get("name", "?")
                )

            # Check version
            if event.get("v") != "0.1":
                result.add_warning(
                    "VERSION_MISMATCH",
                    f"Event {i} has version '{event.get('v')}', expected '0.1'",
                    event_index=i
                )

    def _validate_run_lifecycle(
        self,
        events: List[Dict[str, Any]],
        result: ValidationResult
    ) -> None:
        """Validate run start/end lifecycle."""
        run_starts = [e for e in events if e.get("name") == "run_start"]
        run_ends = [e for e in events if e.get("name") == "run_end"]

        if len(run_starts) == 0:
            result.add_error("NO_RUN_START", "Trace has no run_start event")
        elif len(run_starts) > 1:
            result.add_warning(
                "MULTIPLE_RUN_STARTS",
                f"Trace has {len(run_starts)} run_start events"
            )

        if len(run_ends) == 0:
            result.add_error("NO_RUN_END", "Trace has no run_end event")
        elif len(run_ends) > 1:
            result.add_warning(
                "MULTIPLE_RUN_ENDS",
                f"Trace has {len(run_ends)} run_end events"
            )

        # Check run_start is first, run_end is last
        if events and events[0].get("name") != "run_start":
            result.add_warning(
                "RUN_START_NOT_FIRST",
                f"First event is '{events[0].get('name')}', expected 'run_start'"
            )

        if events and events[-1].get("name") != "run_end":
            result.add_warning(
                "RUN_END_NOT_LAST",
                f"Last event is '{events[-1].get('name')}', expected 'run_end'"
            )

    def validate_tool_availability(
        self,
        pod: PodContract,
        available_tools: Set[str]
    ) -> ValidationResult:
        """
        Validate that all required tools are available.

        Args:
            pod: Pod to validate
            available_tools: Set of available tool names

        Returns:
            ValidationResult with any issues found
        """
        result = ValidationResult(valid=True)
        result.pod_name = pod.name

        for tool in pod.get_required_tools():
            if tool.required and tool.name not in available_tools:
                result.add_error(
                    "MISSING_REQUIRED_TOOL",
                    f"Required tool '{tool.name}' is not available",
                    tool=tool.name,
                    description=tool.description
                )
            elif not tool.required and tool.name not in available_tools:
                result.add_info(
                    "MISSING_OPTIONAL_TOOL",
                    f"Optional tool '{tool.name}' is not available",
                    tool=tool.name
                )

        return result


def validate_pod(pod_class: Type[PodContract]) -> ValidationResult:
    """Convenience function to validate a pod class."""
    return ContractValidator().validate_pod(pod_class)


def validate_trace(trace_path: str, pod: Optional[PodContract] = None) -> ValidationResult:
    """Convenience function to validate a trace file."""
    return ContractValidator().validate_trace(trace_path, pod)
