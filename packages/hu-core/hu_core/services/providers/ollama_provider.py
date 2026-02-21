"""
Ollama provider — uses stdlib urllib so no extra dependencies are required.
"""
from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from typing import Dict, List, Optional

from .base import BaseProvider, ProviderResponse

_DEFAULT_ENDPOINT = "http://localhost:11434"


class OllamaProvider(BaseProvider):
    """Calls a local Ollama server via its HTTP API."""

    provider_name = "ollama"

    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 800,
        endpoint: Optional[str] = None,
    ) -> ProviderResponse:
        base = (endpoint or _DEFAULT_ENDPOINT).rstrip("/")
        url = f"{base}/api/chat"

        payload = json.dumps({
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }).encode()

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        start = time.time()
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read())
        except (urllib.error.URLError, OSError) as exc:
            raise ConnectionError(
                f"Ollama not reachable at {base}. Is it running? ({exc})"
            ) from exc

        latency_ms = (time.time() - start) * 1000
        text = body.get("message", {}).get("content", "")

        prompt_tokens = body.get("prompt_eval_count", 0)
        completion_tokens = body.get("eval_count", 0)

        return ProviderResponse(
            text=text,
            model=model,
            provider="ollama",
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            latency_ms=latency_ms,
        )
