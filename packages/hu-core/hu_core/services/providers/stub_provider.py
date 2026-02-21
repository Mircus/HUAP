"""
Stub provider — deterministic canned responses for testing / CI.
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional

from .base import BaseProvider, ProviderResponse


class StubProvider(BaseProvider):
    """Returns deterministic responses without any network calls."""

    provider_name = "stub"

    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 800,
        endpoint: Optional[str] = None,
    ) -> ProviderResponse:
        text = self._generate(messages)
        word_count = len(text.split())
        prompt_words = sum(len(m.get("content", "").split()) for m in messages)
        return ProviderResponse(
            text=text,
            model=f"{model}-stub",
            provider="stub",
            usage={
                "prompt_tokens": prompt_words * 2,
                "completion_tokens": word_count * 2,
                "total_tokens": (prompt_words + word_count) * 2,
            },
            latency_ms=5.0,
        )

    @staticmethod
    def _generate(messages: List[Dict[str, str]]) -> str:
        last_user = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user = msg.get("content", "").lower()
                break

        if "classify" in last_user:
            return json.dumps({"label": "general", "confidence": 0.95, "stub": True})
        if "extract" in last_user:
            return json.dumps({"entities": [], "stub": True})
        return json.dumps({"response": "Stub response for testing", "status": "ok", "stub": True})
