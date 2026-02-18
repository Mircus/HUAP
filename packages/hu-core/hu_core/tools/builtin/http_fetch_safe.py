"""
http_fetch_safe — Safe HTTP fetch tool with domain allowlist.

Enforces:
- Domain allowlist (required unless --unsafe)
- Timeout
- Max bytes
- Content-type allowlist (optional)
- Traces request metadata (no secrets)
"""
from __future__ import annotations

import urllib.request
import urllib.error
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from ..base import BaseTool, ToolResult, ToolStatus, ToolCategory


class HttpFetchSafe(BaseTool):
    """Safe HTTP GET with domain allowlist and size caps."""

    name = "http_fetch_safe"
    description = "Fetch a URL with safety guardrails (domain allowlist, timeout, size cap)"
    category = ToolCategory.HTTP

    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
            "allowed_domains": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Allowed domains (required unless unsafe=true)",
            },
            "timeout_s": {"type": "number", "default": 10, "description": "Timeout in seconds"},
            "max_bytes": {"type": "integer", "default": 1_048_576, "description": "Max response size in bytes (default 1 MB)"},
            "allowed_content_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Allowed content-type prefixes (e.g. ['text/', 'application/json'])",
            },
            "unsafe": {"type": "boolean", "default": False, "description": "Skip domain allowlist check"},
        },
        "required": ["url"],
    }

    async def execute(self, input_data: Dict[str, Any], context: Any = None) -> ToolResult:
        url: str = input_data["url"]
        allowed_domains: List[str] = input_data.get("allowed_domains", [])
        timeout_s: float = input_data.get("timeout_s", 10)
        max_bytes: int = input_data.get("max_bytes", 1_048_576)
        allowed_ct: List[str] = input_data.get("allowed_content_types", [])
        unsafe: bool = input_data.get("unsafe", False)

        parsed = urlparse(url)
        domain = parsed.hostname or ""

        # Domain check
        if not unsafe and not allowed_domains:
            return ToolResult(
                status=ToolStatus.ERROR,
                data={"error": "allowed_domains is required (or set unsafe=true)"},
            )
        if not unsafe and domain not in allowed_domains:
            return ToolResult(
                status=ToolStatus.ERROR,
                data={"error": f"Domain '{domain}' not in allowlist: {allowed_domains}"},
            )

        start = time.time()
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                ct = resp.headers.get("Content-Type", "")
                if allowed_ct and not any(ct.startswith(a) for a in allowed_ct):
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        data={"error": f"Content-Type '{ct}' not allowed. Allowed: {allowed_ct}"},
                    )
                body = resp.read(max_bytes)
                status_code = resp.status
        except urllib.error.URLError as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                data={"error": str(exc), "url": url},
            )
        except Exception as exc:
            return ToolResult(
                status=ToolStatus.ERROR,
                data={"error": str(exc), "url": url},
            )

        duration_ms = (time.time() - start) * 1000

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "url": url,
                "domain": domain,
                "status_code": status_code,
                "content_type": ct,
                "size_bytes": len(body),
                "body": body.decode("utf-8", errors="replace")[:50_000],
                "duration_ms": round(duration_ms, 2),
            },
        )
