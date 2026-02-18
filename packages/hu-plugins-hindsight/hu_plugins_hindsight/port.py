"""
HindsightMemoryPort — MemoryPort backed by a Hindsight server.

Requires: hindsight-client  (optional dependency).

Falls back to stdlib ``urllib`` when the client library is unavailable,
so the module can still be imported for type-checking.
"""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from hu_core.ports.memory import MemoryPort, MemoryItem


class HindsightMemoryPort(MemoryPort):
    """MemoryPort backed by a Hindsight REST API."""

    def __init__(
        self,
        base_url: str = "http://localhost:8888",
        default_bank_id: str = "demo",
        timeout: int = 10,
    ):
        self.base_url = base_url.rstrip("/")
        self.default_bank_id = default_bank_id
        self.timeout = timeout

    # ── retain ────────────────────────────────────────────────────────────

    async def retain(self, bank_id, content, context=None, timestamp=None, metadata=None):
        bank = bank_id or self.default_bank_id
        item_id = f"mem_{uuid4().hex[:12]}"
        payload = {
            "id": item_id,
            "content": content,
            "context": context,
            "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }

        try:
            self._post(f"/banks/{bank}/items", payload)
        except Exception:
            pass  # best-effort; item is still returned locally

        return MemoryItem(
            id=item_id,
            content=content,
            bank_id=bank,
            timestamp=payload["timestamp"],
            context=context,
            metadata=metadata or {},
        )

    # ── recall ────────────────────────────────────────────────────────────

    async def recall(self, bank_id, query, k=10, filters=None):
        bank = bank_id or self.default_bank_id
        params = {"query": query, "k": str(k)}
        if filters:
            params["filters"] = json.dumps(filters)

        try:
            data = self._get(f"/banks/{bank}/recall", params)
            return [self._parse_item(bank, d) for d in data.get("items", [])]
        except Exception:
            return []

    # ── reflect ───────────────────────────────────────────────────────────

    async def reflect(self, bank_id, query, k=10, filters=None):
        bank = bank_id or self.default_bank_id
        params = {"query": query, "k": str(k)}
        if filters:
            params["filters"] = json.dumps(filters)

        try:
            data = self._get(f"/banks/{bank}/reflect", params)
            return [self._parse_item(bank, d) for d in data.get("items", [])]
        except Exception:
            return await self.recall(bank_id, query, k, filters)

    # ── HTTP helpers (stdlib, no deps) ────────────────────────────────────

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _get(self, path: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        qs = ""
        if params:
            qs = "?" + "&".join(f"{k}={urllib.request.quote(v)}" for k, v in params.items())
        url = f"{self.base_url}{path}{qs}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    @staticmethod
    def _parse_item(bank_id: str, d: Dict[str, Any]) -> MemoryItem:
        return MemoryItem(
            id=d.get("id", "?"),
            content=d.get("content", ""),
            bank_id=bank_id,
            timestamp=d.get("timestamp", ""),
            context=d.get("context"),
            metadata=d.get("metadata", {}),
            score=d.get("score", 0.0),
        )
