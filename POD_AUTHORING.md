# Pod Authoring Guide

Best practices for building HUAP pods.

---

## Pod Contract

Every pod must implement:

```python
class MyPod:
    name: str          # Unique identifier
    version: str       # Semantic version
    description: str   # Human-readable description

    def get_tools(self) -> List[BaseTool]:
        """Return tools this pod provides."""

    async def run(self, input_state: Dict) -> Dict:
        """Execute the main workflow."""
```

---

## Tool Schema

Tools define their inputs with JSON Schema:

```python
class MyTool(BaseTool):
    name = "my_tool"
    description = "What this tool does"
    category = ToolCategory.UTILITY

    input_schema = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Input message",
            },
            "count": {
                "type": "integer",
                "default": 1,
            },
        },
        "required": ["message"],
    }

    async def execute(self, input_data, context=None):
        # Validate: input_data matches input_schema
        message = input_data["message"]
        count = input_data.get("count", 1)

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"result": message * count},
        )
```

---

## Error Handling

Return errors via ToolResult, don't raise:

```python
async def execute(self, input_data, context=None):
    try:
        result = do_work(input_data)
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=result,
        )
    except ValidationError as e:
        return ToolResult(
            status=ToolStatus.ERROR,
            error=f"Validation failed: {e}",
        )
```

---

## LLM Integration

Use the LLM client with usage tracking:

```python
from hu_core.services.llm_client import get_llm_client

async def execute(self, input_data, context=None):
    client = get_llm_client()

    response = await client.chat_completion_with_usage(
        messages=[
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": input_data["prompt"]},
        ],
        temperature=0.3,
        max_tokens=200,
    )

    return ToolResult(
        status=ToolStatus.SUCCESS,
        data={
            "response": response.text,
            "tokens": response.usage["total_tokens"],
        },
    )
```

---

## Workflow Definition

Define workflows in YAML:

```yaml
name: my_workflow
entry: start

nodes:
  start:
    type: entry
    next: analyze

  analyze:
    type: action
    action: analyze_input
    input:
      text: "${input.text}"
    next: decide

  decide:
    type: branch
    condition: "${state.needs_review}"
    branches:
      true: review
      false: complete
    default: complete

  review:
    type: action
    action: human_review
    next: complete

  complete:
    type: exit
    output:
      result: "${state.result}"
```

---

## Testing

Write tests for your pod:

```python
import pytest
from my_pod import get_pod, MyTool

class TestMyPod:
    def test_pod_name(self):
        pod = get_pod()
        assert pod.name == "my-pod"

    @pytest.mark.asyncio
    async def test_tool_execution(self):
        tool = MyTool()
        result = await tool.execute({"message": "hello"})
        assert result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_workflow(self):
        pod = get_pod()
        result = await pod.run({"text": "test input"})
        assert "result" in result
```

Run with stub mode:

```bash
export HUAP_LLM_MODE=stub
pytest
```

---

## Best Practices

1. **Keep tools small** - One tool, one purpose
2. **Document inputs** - Use descriptions in schema
3. **Handle errors** - Return ToolResult.ERROR, don't raise
4. **Track costs** - Use chat_completion_with_usage
5. **Test with stubs** - CI should use HUAP_LLM_MODE=stub
6. **Record baselines** - Keep traces in suites/

---

## Validation

Validate your pod before deployment:

```bash
huap pod validate my-pod
```

Output:
```
Validating pod 'my-pod'...

INFO:
  Name: my-pod
  Version: 0.1.0
  Schema has 3 field(s)
  Capabilities: session_tracking, ai_coaching

Validation PASSED
```

---

**HUAP Core v0.1.0b1**
