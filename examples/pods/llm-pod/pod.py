"""
LLM Pod - Example demonstrating LLM integration with HUAP.

Demonstrates:
- LLM calls with usage tracking
- Stub mode (HUAP_LLM_MODE=stub) for CI
- Cost tracking in traces
- Tool + LLM workflow
"""
from __future__ import annotations

import os
from typing import Any, Dict, List
from hu_core.tools import BaseTool, ToolResult, ToolStatus, ToolCategory
from hu_core.services.llm_client import get_llm_client, LLMResponse


# =============================================================================
# TOOLS
# =============================================================================

class SummarizeTool(BaseTool):
    """Summarize text using LLM."""

    name = "summarize"
    description = "Summarize text using an LLM"
    category = ToolCategory.AI

    input_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to summarize"},
            "max_words": {"type": "integer", "description": "Maximum words in summary", "default": 50},
        },
        "required": ["text"],
    }

    async def execute(self, input_data: Dict[str, Any], context: Any = None) -> ToolResult:
        text = input_data.get("text", "")
        max_words = input_data.get("max_words", 50)

        client = get_llm_client()

        messages = [
            {"role": "system", "content": "You are a helpful assistant that summarizes text concisely."},
            {"role": "user", "content": f"Summarize this text in {max_words} words or less:\n\n{text}"},
        ]

        try:
            response = await client.chat_completion_with_usage(
                messages=messages,
                temperature=0.3,
                max_tokens=200,
            )

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "summary": response.text,
                    "model": response.model,
                    "tokens": response.usage.get("total_tokens", 0),
                },
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
            )


class ClassifyTool(BaseTool):
    """Classify text into categories using LLM."""

    name = "classify"
    description = "Classify text into one of the provided categories"
    category = ToolCategory.AI

    input_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to classify"},
            "categories": {"type": "array", "items": {"type": "string"}, "description": "Possible categories"},
        },
        "required": ["text", "categories"],
    }

    async def execute(self, input_data: Dict[str, Any], context: Any = None) -> ToolResult:
        text = input_data.get("text", "")
        categories = input_data.get("categories", [])

        if not categories:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="No categories provided",
            )

        client = get_llm_client()

        categories_str = ", ".join(categories)
        messages = [
            {"role": "system", "content": "You are a classifier. Respond with only the category name, nothing else."},
            {"role": "user", "content": f"Classify this text into one of these categories: {categories_str}\n\nText: {text}"},
        ]

        try:
            response = await client.chat_completion_with_usage(
                messages=messages,
                temperature=0.1,
                max_tokens=50,
            )

            category = response.text.strip()
            # Validate it's one of the provided categories
            if category not in categories:
                # Try to find a close match
                for cat in categories:
                    if cat.lower() in category.lower():
                        category = cat
                        break

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "category": category,
                    "model": response.model,
                    "tokens": response.usage.get("total_tokens", 0),
                },
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
            )


# =============================================================================
# POD
# =============================================================================

class LLMPod:
    """
    LLM Pod - Example for LLM integration with HUAP.

    Shows how to:
    - Make LLM calls with tracing
    - Use stub mode for testing
    - Track costs
    """

    name = "llm"
    version = "0.1.0"
    description = "Example pod demonstrating LLM integration"

    def __init__(self):
        self.tools = [SummarizeTool(), ClassifyTool()]

    def get_tools(self) -> List[BaseTool]:
        """Return the tools provided by this pod."""
        return self.tools

    async def run(self, input_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the LLM workflow.

        Input:
            text: str - Text to process
            task: str - "summarize" or "classify"
            categories: list[str] - Categories for classification (if task=classify)

        Output:
            result: str - Summary or category
            tokens_used: int - Total tokens consumed
        """
        text = input_state.get("text", "Hello, world!")
        task = input_state.get("task", "summarize")

        result = {}
        total_tokens = 0

        if task == "summarize":
            tool = SummarizeTool()
            tool_result = await tool.execute({"text": text, "max_words": 30})
            if tool_result.status == ToolStatus.SUCCESS:
                result["summary"] = tool_result.data["summary"]
                total_tokens = tool_result.data.get("tokens", 0)
            else:
                result["error"] = tool_result.error

        elif task == "classify":
            categories = input_state.get("categories", ["positive", "negative", "neutral"])
            tool = ClassifyTool()
            tool_result = await tool.execute({"text": text, "categories": categories})
            if tool_result.status == ToolStatus.SUCCESS:
                result["category"] = tool_result.data["category"]
                total_tokens = tool_result.data.get("tokens", 0)
            else:
                result["error"] = tool_result.error

        result["tokens_used"] = total_tokens
        result["stub_mode"] = os.getenv("HUAP_LLM_MODE", "").lower() == "stub"

        return result


# Singleton instance
_POD_INSTANCE: LLMPod | None = None


def get_pod() -> LLMPod:
    """Factory function for pod registry."""
    global _POD_INSTANCE
    if _POD_INSTANCE is None:
        _POD_INSTANCE = LLMPod()
    return _POD_INSTANCE
