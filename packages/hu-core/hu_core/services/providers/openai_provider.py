"""
OpenAI provider — requires the ``openai`` package (optional dep).
"""
from __future__ import annotations

import os
import time
from typing import Dict, List, Optional

from .base import BaseProvider, ProviderResponse


class OpenAIProvider(BaseProvider):
    """Calls the OpenAI chat completions API."""

    provider_name = "openai"

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")

    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 800,
        endpoint: Optional[str] = None,
    ) -> ProviderResponse:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ImportError(
                "openai package is required for OpenAI provider. "
                "Install with: pip install openai"
            ) from exc

        if not self._api_key:
            raise ValueError(
                "OPENAI_API_KEY not set. Provide it via env or constructor."
            )

        client = AsyncOpenAI(api_key=self._api_key)
        start = time.time()

        resp = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        latency_ms = (time.time() - start) * 1000
        text = resp.choices[0].message.content or ""
        usage = {
            "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
            "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
            "total_tokens": resp.usage.total_tokens if resp.usage else 0,
        }

        return ProviderResponse(
            text=text,
            model=resp.model,
            provider="openai",
            usage=usage,
            latency_ms=latency_ms,
        )
