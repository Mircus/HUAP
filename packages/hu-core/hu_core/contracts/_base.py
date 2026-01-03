"""
Pod Contract v0.1: Interface that every pod must implement.

This module defines the contract (interface) that every pod must follow.
It ensures all pods provide consistent methods for:
- Schema definition
- Metric extraction
- AI analysis prompts
- Tool/capability declarations
- Trace event emission requirements
- Policy hook integration

See docs/POD_CONTRACT_v0.1.md for full specification.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Set, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

if TYPE_CHECKING:
    from ..trace import TraceService


# =============================================================================
# CONTRACT VERSION
# =============================================================================

CONTRACT_VERSION = "0.1"


# =============================================================================
# TRACE REQUIREMENTS
# =============================================================================

class TraceRequirement(str, Enum):
    """Required trace events that pods must emit."""
    RUN_START = "run_start"
    RUN_END = "run_end"
    NODE_ENTER = "node_enter"
    NODE_EXIT = "node_exit"
    ERROR = "error"


# Minimum required events for contract compliance
REQUIRED_TRACE_EVENTS: Set[str] = {
    TraceRequirement.RUN_START.value,
    TraceRequirement.RUN_END.value,
}

# Recommended events for full observability
RECOMMENDED_TRACE_EVENTS: Set[str] = {
    TraceRequirement.NODE_ENTER.value,
    TraceRequirement.NODE_EXIT.value,
    TraceRequirement.ERROR.value,
}


# =============================================================================
# CAPABILITY DECLARATIONS
# =============================================================================

class PodCapability(str, Enum):
    """Standard pod capabilities."""
    SESSION_TRACKING = "session_tracking"
    AI_COACHING = "ai_coaching"
    WORKFLOW_EXECUTION = "workflow_execution"
    TOOL_EXECUTION = "tool_execution"
    LLM_CALLS = "llm_calls"
    MEMORY_ACCESS = "memory_access"
    MESSAGING = "messaging"
    POLICY_ENFORCEMENT = "policy_enforcement"


@dataclass
class ToolDeclaration:
    """Declaration of a tool used by a pod."""
    name: str
    required: bool = True
    description: str = ""
    permissions: List[str] = field(default_factory=list)


@dataclass
class PodSchema:
    """Schema for pod's session data form generation"""
    pod_name: str
    fields: List[Dict[str, Any]]


class PodContract(ABC):
    """
    Contract (interface) that every pod must implement.

    A pod is a self-contained domain-specific module that:
    - Defines a workflow for users to interact with it
    - Provides a schema for collecting user data
    - Extracts metrics from user data
    - Generates AI analysis prompts for recommendations

    All pods must inherit from this class and implement all abstract methods.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Pod name (lowercase, identifier)."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Pod version (semantic versioning)."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Pod description (human-readable)."""
        pass

    @abstractmethod
    def get_schema(self) -> PodSchema:
        """Return pod's data schema for form generation."""
        pass

    @abstractmethod
    async def extract_metrics(
        self,
        sessions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract metrics from raw session data."""
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get system prompt for specialized AI analysis."""
        pass

    @abstractmethod
    def generate_analysis_prompt(
        self,
        metrics: Dict[str, Any]
    ) -> str:
        """Generate analysis prompt for specialized analysis."""
        pass

    async def hydrate_memory(
        self,
        memory: Dict[str, Any],
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Optional hook for pods to expand session data using persisted memory."""
        return payload

    async def persist_memory(
        self,
        memory: Dict[str, Any],
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Optional hook to update shared memory after a workflow run."""
        return memory

    @abstractmethod
    def generate_generic_prompt(
        self,
        metrics: Dict[str, Any]
    ) -> str:
        """Generate analysis prompt for generic mode (multiple pods)."""
        pass

    def get_capabilities(self) -> List[PodCapability]:
        """Get list of pod capabilities."""
        return [
            PodCapability.SESSION_TRACKING,
            PodCapability.AI_COACHING
        ]

    def get_required_tools(self) -> List[ToolDeclaration]:
        """Declare tools required by this pod."""
        return []

    def get_trace_requirements(self) -> Set[str]:
        """Get trace events this pod must emit."""
        return REQUIRED_TRACE_EVENTS.copy()

    def get_recommended_trace_events(self) -> Set[str]:
        """Get recommended trace events for full observability."""
        return RECOMMENDED_TRACE_EVENTS.copy()

    def get_contract_version(self) -> str:
        """Get the contract version this pod implements."""
        return CONTRACT_VERSION

    # =========================================================================
    # POLICY HOOKS
    # =========================================================================

    async def pre_run_hook(
        self,
        state: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Hook called before workflow run starts."""
        return state

    async def post_run_hook(
        self,
        state: Dict[str, Any],
        result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Hook called after workflow run completes."""
        return result

    async def on_error_hook(
        self,
        error: Exception,
        state: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Hook called when an error occurs during workflow."""
        return None

    def get_graph_path(self) -> str:
        """Get path to workflow YAML file."""
        return f"{self.name}.yaml"

    # =========================================================================
    # AGENT DECLARATIONS
    # =========================================================================

    def get_agents(self) -> List[Dict[str, Any]]:
        """
        Declare agent programs owned by this pod.

        Returns list of AgentSpec-compatible dicts or AgentSpec instances.
        Each agent spec includes:
        - name: Agent identifier
        - goal_template: Task template with {task} placeholder
        - system_prompt: Agent's system prompt
        - allowed_tools: List of tool names agent can use
        - max_steps: Maximum ReAct loop iterations
        - model: LLM model to use
        - temperature: LLM temperature

        Example:
            return [
                {
                    "name": "planner",
                    "goal_template": "Create a fitness plan for: {task}",
                    "system_prompt": "You are SOMA fitness coach.",
                    "allowed_tools": ["memory_read", "memory_write"],
                    "max_steps": 5,
                }
            ]
        """
        return []

    def get_agent_factory(self) -> Dict[str, Any]:
        """
        Return factory callables for creating agent instances.

        Returns dict mapping agent name to factory function.
        Override in subclass to provide agent creation logic.
        """
        return {}

    def validate_session_data(
        self,
        data: Dict[str, Any]
    ) -> bool:
        """Validate session data against pod's requirements."""
        return True

    def get_metric_fields(self) -> List[str]:
        """Get list of metric field names for JSONB queries."""
        return []

    def __repr__(self) -> str:
        """String representation"""
        return f"{self.__class__.__name__}({self.name} v{self.version})"


# Type alias for pod implementations
Pod = PodContract
