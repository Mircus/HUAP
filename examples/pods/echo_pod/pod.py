"""
Echo Pod Implementation - Minimal example for testing.
"""
from typing import Any, Dict, List

from hu_core.contracts import (
    PodContract,
    PodSchema,
    PodCapability,
    ToolDeclaration,
)


class EchoPod(PodContract):
    """
    Minimal pod that echoes input and greets user.

    Used for testing the trace/replay/eval pipeline.
    """

    @property
    def name(self) -> str:
        return "echo"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def description(self) -> str:
        return "Minimal echo pod for testing"

    def get_schema(self) -> PodSchema:
        return PodSchema(
            pod_name=self.name,
            fields=[
                {
                    "name": "message",
                    "type": "string",
                    "required": True,
                    "description": "Message to echo",
                },
            ],
        )

    async def extract_metrics(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "session_count": len(sessions),
            "total_messages": sum(
                1 for s in sessions if s.get("data_json", {}).get("message")
            ),
        }

    def get_system_prompt(self) -> str:
        return "You are a friendly echo assistant. Repeat what the user says with a greeting."

    def generate_analysis_prompt(self, metrics: Dict[str, Any]) -> str:
        return f"Echo pod processed {metrics.get('session_count', 0)} sessions."

    def generate_generic_prompt(self, metrics: Dict[str, Any]) -> str:
        return self.generate_analysis_prompt(metrics)

    def get_capabilities(self) -> List[PodCapability]:
        return [
            PodCapability.SESSION_TRACKING,
            PodCapability.TOOL_EXECUTION,
        ]

    def get_required_tools(self) -> List[ToolDeclaration]:
        return [
            ToolDeclaration(
                name="echo",
                required=True,
                description="Echo the input message",
                permissions=[],
            ),
        ]


# Singleton instance
_POD_INSTANCE = None


def get_pod() -> EchoPod:
    """Factory for pod registry."""
    global _POD_INSTANCE
    if _POD_INSTANCE is None:
        _POD_INSTANCE = EchoPod()
    return _POD_INSTANCE
