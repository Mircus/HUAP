"""
HTTP Fetch Tool - Make HTTP requests.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..base import BaseTool, ExecutionContext, ToolCategory, ToolSpec


class HTTPFetchTool(BaseTool):
    """
    Tool for making HTTP requests.

    Input:
        - url: The URL to fetch
        - method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        - headers: Optional headers dict
        - body: Optional request body (for POST/PUT/PATCH)
        - timeout: Optional timeout in seconds (default 30)

    Output:
        - status_code: HTTP status code
        - headers: Response headers
        - body: Response body (text or JSON)
        - ok: Whether status code is 2xx
    """

    # URL allowlist patterns (can be configured)
    _allowed_domains: List[str] = []
    _blocked_domains: List[str] = []

    _spec = ToolSpec(
        name="http_fetch",
        description="Make HTTP requests to external APIs",
        version="1.0.0",
        category=ToolCategory.HTTP,
        input_schema={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to fetch",
                },
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                    "description": "HTTP method",
                    "default": "GET",
                },
                "headers": {
                    "type": "object",
                    "description": "Request headers",
                },
                "body": {
                    "description": "Request body (JSON-serializable)",
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds",
                    "default": 30,
                },
            },
            "required": ["url"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "status_code": {"type": "integer"},
                "headers": {"type": "object"},
                "body": {},
                "ok": {"type": "boolean"},
            },
        },
        required_capabilities=["http_access"],
        tags=["http", "api", "fetch", "request"],
    )

    @classmethod
    def set_allowed_domains(cls, domains: List[str]) -> None:
        """Set allowed domains for HTTP requests."""
        cls._allowed_domains = domains

    @classmethod
    def set_blocked_domains(cls, domains: List[str]) -> None:
        """Set blocked domains for HTTP requests."""
        cls._blocked_domains = domains

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    def _check_url_allowed(self, url: str) -> tuple[bool, Optional[str]]:
        """Check if URL is allowed based on domain rules."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Check blocked domains first
        for blocked in self._blocked_domains:
            if domain == blocked or domain.endswith(f".{blocked}"):
                return False, f"Domain '{domain}' is blocked"

        # If allowlist is set, check against it
        if self._allowed_domains:
            for allowed in self._allowed_domains:
                if domain == allowed or domain.endswith(f".{allowed}"):
                    return True, None
            return False, f"Domain '{domain}' is not in the allowlist"

        return True, None

    async def execute(
        self,
        input: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute HTTP request."""
        import aiohttp

        url = input["url"]
        method = input.get("method", "GET").upper()
        headers = input.get("headers", {})
        body = input.get("body")
        timeout_secs = input.get("timeout", 30)

        # Check URL is allowed
        allowed, reason = self._check_url_allowed(url)
        if not allowed:
            raise PermissionError(reason)

        # Prepare request kwargs
        kwargs: Dict[str, Any] = {
            "headers": headers,
            "timeout": aiohttp.ClientTimeout(total=timeout_secs),
        }

        if body is not None and method in ("POST", "PUT", "PATCH"):
            if isinstance(body, dict):
                kwargs["json"] = body
            else:
                kwargs["data"] = body

        # Make request
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, **kwargs) as response:
                # Get response body
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    try:
                        body_data = await response.json()
                    except Exception:
                        body_data = await response.text()
                else:
                    body_data = await response.text()

                return {
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "body": body_data,
                    "ok": 200 <= response.status < 300,
                }
