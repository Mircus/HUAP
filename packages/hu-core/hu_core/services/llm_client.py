"""
LLM client (OpenAI) for HUAP.

Provides:
- chat_completion() for raw LLM calls
- chat_completion_with_usage() for calls that return token usage (for cost tracking)
- generate_workout_plan() for SOMA fitness plans
- analyze_health_data() for SOMA health analysis
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

        # Generate appropriate stub response based on context
        if "plan" in last_user or "workout" in last_user or "fitness" in last_user:
            return json.dumps({
                "weekly_overview": "Stub workout plan for testing",
                "days": [
                    {
                        "day": 1,
                        "focus": "Test workout",
                        "exercises": [
                            {"name": "Test exercise", "sets": 3, "reps": 10, "notes": "Stub"}
                        ],
                        "duration_min": 30,
                        "intensity": "moderate"
                    }
                ],
                "recovery": "Rest as needed",
                "progression": "Increase gradually"
            })
        elif "analyze" in last_user or "health" in last_user or "data" in last_user:
            return json.dumps({
                "observations": ["Stub observation 1", "Stub observation 2"],
                "patterns": ["Stub pattern"],
                "recommendations": ["Stub recommendation"],
                "concerns": [],
                "summary": "Stub analysis for testing"
            })
        else:
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

    async def generate_workout_plan(
        self,
        goal: str,
        current_fitness: Dict[str, Any],
        constraints: List[str],
        days_per_week: int = 4
    ) -> Dict[str, Any]:
        """
        Generate a personalized workout plan using LLM.

        Args:
            goal: User's fitness goal
            current_fitness: Current fitness state (posture, activity, etc.)
            constraints: List of constraints or focus areas
            days_per_week: Number of workout days per week

        Returns:
            Dict with 'plan', 'timestamp', and usage info
        """
        # Build prompt
        fitness_desc = json.dumps(current_fitness, indent=2)
        constraints_desc = "\n".join(f"- {c}" for c in constraints) if constraints else "None"

        prompt = f"""You are SOMA, an expert fitness coach. Create a personalized {days_per_week}-day/week workout plan.

Goal: {goal}

Current Fitness State:
{fitness_desc}

Constraints/Focus Areas:
{constraints_desc}

Generate a detailed workout plan with:
1. Weekly overview
2. Daily workouts with exercises, sets, reps, duration
3. Recovery recommendations
4. Progression notes

Return ONLY valid JSON in this format:
{{
    "weekly_overview": "Brief overview of the week's approach",
    "days": [
        {{
            "day": 1,
            "focus": "Upper body strength",
            "exercises": [
                {{"name": "Push-ups", "sets": 3, "reps": 12, "notes": "Focus on form"}}
            ],
            "duration_min": 45,
            "intensity": "moderate"
        }}
    ],
    "recovery": "Recovery recommendations",
    "progression": "How to progress over time"
}}"""

        messages = [
            {"role": "system", "content": "You are SOMA, an expert fitness coach. Respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ]

        response = await self.chat_completion_with_usage(
            messages=messages,
            temperature=0.7,
            max_tokens=1500
        )

        # Parse JSON from response
        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        try:
            plan_data = json.loads(text)
        except json.JSONDecodeError:
            plan_data = {"error": "Failed to parse plan", "raw": text}

        return {
            "plan": plan_data,
            "timestamp": datetime.utcnow().isoformat(),
            "usage": response.usage,
            "model": response.model,
            "latency_ms": response.latency_ms,
        }

    async def analyze_health_data(
        self,
        data: Dict[str, Any],
        context: str = "",
        goal: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze health data and provide insights using LLM.

        Args:
            data: Health data to analyze (metrics, etc.)
            context: Additional context
            goal: User's health goal

        Returns:
            Dict with 'analysis', 'data_analyzed', 'timestamp', and usage info
        """
        data_desc = json.dumps(data, indent=2)
        goal_text = f"\nUser's Goal: {goal}" if goal else ""
        context_text = f"\nContext: {context}" if context else ""

        prompt = f"""You are SOMA, an expert health analyst. Analyze the following health data and provide insights.

Health Data:
{data_desc}
{goal_text}
{context_text}

Provide:
1. Key observations from the data
2. Patterns or trends
3. Actionable recommendations
4. Areas of concern (if any)

Return ONLY valid JSON in this format:
{{
    "observations": ["observation 1", "observation 2"],
    "patterns": ["pattern 1", "pattern 2"],
    "recommendations": ["recommendation 1", "recommendation 2"],
    "concerns": ["concern 1"] or [],
    "summary": "Brief overall summary"
}}"""

        messages = [
            {"role": "system", "content": "You are SOMA, an expert health analyst. Respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ]

        response = await self.chat_completion_with_usage(
            messages=messages,
            temperature=0.5,
            max_tokens=1000
        )

        # Parse JSON from response
        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        try:
            analysis_data = json.loads(text)
        except json.JSONDecodeError:
            analysis_data = {"error": "Failed to parse analysis", "raw": text}

        return {
            "analysis": analysis_data.get("summary", str(analysis_data)),
            "data_analyzed": list(data.keys()),
            "full_analysis": analysis_data,
            "timestamp": datetime.utcnow().isoformat(),
            "usage": response.usage,
            "model": response.model,
            "latency_ms": response.latency_ms,
        }


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
