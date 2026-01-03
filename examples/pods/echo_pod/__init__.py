"""
Echo Pod - Minimal example pod for testing.

This pod has one tool (echo) and one LLM node for greeting.
Used for validating the trace/replay/eval pipeline.
"""
from .pod import EchoPod, get_pod

__all__ = ["EchoPod", "get_pod"]
