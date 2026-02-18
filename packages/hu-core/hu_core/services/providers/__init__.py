"""
HUAP Provider Abstraction Layer.

Each provider implements the same async interface so the router
can dispatch to any backend transparently.
"""
from .base import BaseProvider, ProviderResponse
from .stub_provider import StubProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider

__all__ = [
    "BaseProvider",
    "ProviderResponse",
    "StubProvider",
    "OllamaProvider",
    "OpenAIProvider",
]
