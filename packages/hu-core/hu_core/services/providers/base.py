"""
Base provider interface for HUAP model providers.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProviderResponse:
    """Unified response from any provider."""
    text: str
    model: str
    provider: str
    usage: Dict[str, int] = field(default_factory=lambda: {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    })
    latency_ms: float = 0.0


class BaseProvider(ABC):
    """Abstract base for model providers."""

    provider_name: str = "base"

    @abstractmethod
    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 800,
        endpoint: Optional[str] = None,
    ) -> ProviderResponse:
        """Send a chat completion request and return a unified response."""
        ...
