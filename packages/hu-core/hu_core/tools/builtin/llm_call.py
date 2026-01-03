"""
LLM Call Tool - Call language models with prompts.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..base import BaseTool, ExecutionContext, ToolCategory, ToolSpec


class LLMCallTool(BaseTool):
    """
    Tool for calling LLM (OpenAI) with prompts.

    Input:
        - messages: List of message dicts with role and content
        - system_prompt: Optional system prompt (convenience)
        - user_prompt: Optional user prompt (convenience)
        - temperature: Optional temperature (default 0.2)
        - max_tokens: Optional max tokens (default 800)
        - model: Optional model override

    Output:
        - response: The LLM response text
        - model: Model used
        - usage: Token usage info (if available)
    """

    _spec = ToolSpec(
        name="llm_call",
        description="Call an LLM (OpenAI) with a prompt and get a response",
        version="1.0.0",
        category=ToolCategory.AI,
        input_schema={
            "type": "object",
            "properties": {
                "messages": {
                    "type": "array",
                    "description": "List of messages with role and content",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string", "enum": ["system", "user", "assistant"]},
                            "content": {"type": "string"},
                        },
                        "required": ["role", "content"],
                    },
                },
                "system_prompt": {
                    "type": "string",
                    "description": "System prompt (convenience, used if messages not provided)",
                },
                "user_prompt": {
                    "type": "string",
                    "description": "User prompt (convenience, used if messages not provided)",
                },
                "temperature": {
                    "type": "number",
                    "description": "Sampling temperature (0-2)",
                    "default": 0.2,
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Maximum tokens in response",
                    "default": 800,
                },
                "model": {
                    "type": "string",
                    "description": "Model to use (default: from config)",
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "response": {"type": "string"},
                "model": {"type": "string"},
                "usage": {"type": "object"},
            },
        },
        required_capabilities=["ai_access"],
        tags=["ai", "llm", "openai", "chat"],
    )

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    async def execute(
        self,
        input: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute LLM call."""
        from ...services.llm_client import get_llm_client

        client = get_llm_client()

        # Build messages
        messages = input.get("messages")
        if not messages:
            messages = []
            if input.get("system_prompt"):
                messages.append({
                    "role": "system",
                    "content": input["system_prompt"]
                })
            if input.get("user_prompt"):
                messages.append({
                    "role": "user",
                    "content": input["user_prompt"]
                })

        if not messages:
            raise ValueError("Either 'messages' or 'user_prompt' is required")

        # Get parameters
        temperature = input.get("temperature", 0.2)
        max_tokens = input.get("max_tokens", 800)

        # Call LLM
        response = await client.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return {
            "response": response,
            "model": client.model,
            "usage": {},  # Could be expanded with actual usage if needed
        }
