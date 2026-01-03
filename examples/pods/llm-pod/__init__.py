"""
LLM Pod - Example demonstrating LLM integration with stub mode.

This pod shows:
- LLM call with tracing
- Stub mode for deterministic testing
- Cost tracking
"""
from .pod import LLMPod, get_pod

__all__ = ["LLMPod", "get_pod"]
