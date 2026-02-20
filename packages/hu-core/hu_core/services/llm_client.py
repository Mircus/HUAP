"""
LLM client (OpenAI) for HUAP.

Provides:
- chat_completion() for raw LLM calls
- chat_completion_with_usage() for calls that return token usage (for cost tracking)
"""
from __future__ import annotations
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    pass  # For future type hints if needed
from dataclasses import dataclass
from openai import AsyncOpenAI


@dataclass
class LLMResponse:
    """Response from LLM with usage info for cost tracking."""
    text: str
    model: str
    usage: Dict[str, int]  # prompt_tokens, completion_tokens, total_tokens
    latency_ms: Optional[float] = None


class LLMClient:
    """OpenAI LLM client with usage tracking and tracing.

    Supports stub mode for CI/testing via HUAP_LLM_MODE=stub environment variable.
    In stub mode, returns deterministic canned responses without calling OpenAI.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        tracer: Optional[Any] = None,
        stub_mode: Optional[bool] = None,
    ):
        # Check if stub mode is enabled via env or parameter
        if stub_mode is None:
            stub_mode = os.getenv("HUAP_LLM_MODE", "").lower() == "stub"

        self._stub_mode = stub_mode
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self._tracer = tracer
        self._use_trace_service = hasattr(tracer, 'llm_request') if tracer else False
        self._pod: Optional[str] = None

        if self._stub_mode:
            # Stub mode - no API key needed
            self.api_key = None
            self._client = None
        else:
            # Live mode - require API key
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError(
                    "OpenAI API key not configured. Set OPENAI_API_KEY or use HUAP_LLM_MODE=stub for testing."
                )
            self._client = AsyncOpenAI(api_key=self.api_key)

    def set_tracer(self, tracer: Any, pod: Optional[str] = None) -> None:
        """Set the tracer for this client."""
        self._tracer = tracer
        self._use_trace_service = hasattr(tracer, 'llm_request') if tracer else False
        self._pod = pod

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 800
    ) -> str:
        """
        Simple chat completion that returns just the text.

        For cost tracking, use chat_completion_with_usage() instead.
        In stub mode, returns a deterministic response.
        """
        if self._stub_mode:
            return self._generate_stub_response(messages)

        resp = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""

    async def chat_completion_with_usage(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 800
    ) -> LLMResponse:
        """
        Chat completion that returns text + usage info for cost tracking.

        Returns:
            LLMResponse with text, model, and token usage.
            In stub mode, returns deterministic response with fake usage.
        """
        import time
        start = time.time()

        # Trace LLM request
        self._trace_llm_request(messages, temperature, max_tokens)

        if self._stub_mode:
            # Stub mode - return canned response
            text = self._generate_stub_response(messages)
            latency_ms = 50.0  # Fake latency
            usage = {
                "prompt_tokens": sum(len(m.get("content", "").split()) for m in messages) * 2,
                "completion_tokens": len(text.split()) * 2,
                "total_tokens": 0,
            }
            usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
            model = f"{self.model}-stub"
        else:
            resp = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            latency_ms = (time.time() - start) * 1000

            usage = {
                "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
                "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
                "total_tokens": resp.usage.total_tokens if resp.usage else 0,
            }

            text = resp.choices[0].message.content or ""
            model = resp.model

        # Trace LLM response
        self._trace_llm_response(text, usage, latency_ms, model)

        return LLMResponse(
            text=text,
            model=model,
            usage=usage,
            latency_ms=latency_ms,
        )

    def _generate_stub_response(self, messages: List[Dict[str, str]]) -> str:
        """Generate a deterministic stub response for testing."""
        # Look at the last user message to determine response type
        last_user = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user = msg.get("content", "").lower()
                break

        # Generic stub response
        return json.dumps({
            "response": "Stub response for testing",
            "status": "ok",
            "stub_mode": True
        })

    def _trace_llm_request(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> None:
        """Emit llm_request trace event."""
        if not self._tracer:
            return

        if self._use_trace_service:
            self._tracer.llm_request(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                provider="openai",
                pod=self._pod,
            )
        else:
            # Legacy callable tracer
            self._tracer({
                "event": "llm_request",
                "model": self.model,
                "message_count": len(messages),
            })

    def _trace_llm_response(
        self,
        text: str,
        usage: Dict[str, int],
        latency_ms: float,
        model: str,
    ) -> None:
        """Emit llm_response trace event."""
        if not self._tracer:
            return

        if self._use_trace_service:
            self._tracer.llm_response(
                model=model,
                text=text,
                usage=usage,
                duration_ms=latency_ms,
                provider="openai",
                pod=self._pod,
            )
        else:
            # Legacy callable tracer
            self._tracer({
                "event": "llm_response",
                "model": model,
                "tokens": usage.get("total_tokens", 0),
                "latency_ms": latency_ms,
            })


# =============================================================================
# ROUTED LLM CLIENT (Specialist Squad integration)
# =============================================================================


class RoutedLLMClient:
    """
    LLM client that delegates model selection to the ModelRouter.

    Enable with ``HUAP_ROUTER_ENABLED=1``.  Falls back to stub when
    ``HUAP_LLM_MODE=stub`` regardless of router config.

    Back-compatible: callers can keep using ``chat_completion_with_usage``
    exactly as before, but optionally pass ``capability`` to let the router
    choose the model.
    """

    def __init__(
        self,
        tracer: Optional[Any] = None,
        registry_path: Optional[str] = None,
        policy_path: Optional[str] = None,
    ):
        from .model_registry import ModelRegistry
        from .model_router import ModelRouter
        from .providers import StubProvider, OllamaProvider, OpenAIProvider

        self._tracer = tracer
        self._pod: Optional[str] = None
        self._registry = ModelRegistry.load(registry_path)
        self._router = ModelRouter.load(self._registry, policy_path)

        self._providers = {
            "stub": StubProvider(),
            "ollama": OllamaProvider(),
            "openai": OpenAIProvider(),
        }

        self._stub_mode = os.getenv("HUAP_LLM_MODE", "").lower() == "stub"

    def set_tracer(self, tracer: Any, pod: Optional[str] = None) -> None:
        self._tracer = tracer
        self._pod = pod

    async def chat_completion_with_usage(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 800,
        capability: str = "chat",
    ) -> LLMResponse:
        """Route to the best model, call the provider, and trace the decision."""
        import time

        # Force stub when HUAP_LLM_MODE=stub
        if self._stub_mode:
            from .providers import StubProvider
            provider = StubProvider()
            resp = await provider.chat_completion("stub", messages, temperature, max_tokens)
            self._trace_router_decision("stub_chat", "stub", "__forced_stub", "HUAP_LLM_MODE=stub")
            return LLMResponse(
                text=resp.text,
                model=resp.model,
                usage=resp.usage,
                latency_ms=resp.latency_ms,
            )

        decision = self._router.select(capability=capability)
        spec = decision.model

        self._trace_router_decision(spec.id, spec.provider, decision.rule_name, decision.reason)

        provider = self._providers.get(spec.provider)
        if provider is None:
            raise ValueError(f"Unknown provider '{spec.provider}' for model '{spec.id}'")

        resp = await provider.chat_completion(
            model=spec.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            endpoint=spec.endpoint,
        )

        return LLMResponse(
            text=resp.text,
            model=resp.model,
            usage=resp.usage,
            latency_ms=resp.latency_ms,
        )

    def _trace_router_decision(
        self,
        model_id: str,
        provider: str,
        rule_name: str,
        reason: str,
    ) -> None:
        """Emit a policy_check trace event for the routing decision."""
        if not self._tracer:
            return
        if hasattr(self._tracer, "policy_check"):
            self._tracer.policy_check(
                policy="router",
                decision=model_id,
                reason=reason,
                inputs={"provider": provider, "rule": rule_name},
                pod=self._pod,
            )


# =============================================================================
# CONTEXT-AWARE CLIENT ACCESS
# =============================================================================

from contextvars import ContextVar

# Context-local client (for concurrent run isolation)
_context_client: ContextVar[Optional[LLMClient]] = ContextVar(
    "llm_client", default=None
)

# Global client singleton (fallback when no context set)
_client_singleton: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """
    Get the LLM client for the current context.

    Resolution order:
    1. Context-local client (if set via set_context_client)
    2. Global singleton (fallback)

    This enables concurrent runs to use isolated clients without
    cross-contamination.
    """
    # Check context-local first
    ctx_client = _context_client.get()
    if ctx_client is not None:
        return ctx_client

    # Fall back to global singleton
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = LLMClient()
    return _client_singleton


def set_context_client(client: Optional[LLMClient]) -> None:
    """
    Set the LLM client for the current async context.

    Use this to isolate concurrent runs:
        client = LLMClient()
        set_context_client(client)
        try:
            await run_workflow(...)
        finally:
            set_context_client(None)
    """
    _context_client.set(client)


def reset_llm_client() -> None:
    """Reset the LLM client singleton (for testing)."""
    global _client_singleton
    _client_singleton = None
    _context_client.set(None)
