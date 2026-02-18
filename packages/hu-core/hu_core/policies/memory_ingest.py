"""
Memory Ingest Policy — prevent "retain everything" anti-pattern.

Rules:
    - Retain only: stable preferences, outcomes, tool successes/failures, summaries
    - Skip: raw transcript dumps, very short content, duplicate content
    - Optional dedup guard by content hash

Usage:
    from hu_core.policies.memory_ingest import MemoryIngestPolicy

    policy = MemoryIngestPolicy()
    if policy.should_retain(content, context="tool_success"):
        await port.retain(bank_id, content)
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set


# Content that signals "retain"
_RETAIN_CONTEXTS = {
    "preference", "outcome", "tool_success", "tool_failure",
    "summary", "decision", "insight", "learning", "correction",
}

# Content patterns that signal "skip"
_SKIP_PATTERNS = [
    "raw transcript",
    "full conversation",
    "[system]",
]


@dataclass
class IngestDecision:
    """Result of an ingest policy check."""
    allowed: bool
    reason: str


@dataclass
class MemoryIngestPolicy:
    """
    Lightweight guard that decides whether a memory item should be retained.

    Parameters:
        min_content_length: skip items shorter than this (default 10)
        max_content_length: skip items longer than this (default 5000)
        dedup: enable content hash dedup (default True)
        allowed_contexts: retain only these context tags (None = allow all)
    """
    min_content_length: int = 10
    max_content_length: int = 5000
    dedup: bool = True
    allowed_contexts: Optional[Set[str]] = None

    _seen_hashes: Set[str] = field(default_factory=set, repr=False)

    def should_retain(
        self,
        content: str,
        context: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> IngestDecision:
        """Check whether *content* should be retained."""

        # Length checks
        if len(content) < self.min_content_length:
            return IngestDecision(False, f"Too short ({len(content)} < {self.min_content_length})")
        if len(content) > self.max_content_length:
            return IngestDecision(False, f"Too long ({len(content)} > {self.max_content_length})")

        # Skip patterns
        cl = content.lower()
        for pat in _SKIP_PATTERNS:
            if pat in cl:
                return IngestDecision(False, f"Matches skip pattern: '{pat}'")

        # Context filter
        if self.allowed_contexts is not None and context:
            if context not in self.allowed_contexts:
                return IngestDecision(False, f"Context '{context}' not in allowed set")

        # Default context heuristic (when no explicit allow set)
        if self.allowed_contexts is None and context:
            if context in _RETAIN_CONTEXTS:
                pass  # explicitly good
            # else: allow anyway — the caller opted in by calling retain

        # Dedup
        if self.dedup:
            h = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
            if h in self._seen_hashes:
                return IngestDecision(False, "Duplicate content (hash seen)")
            self._seen_hashes.add(h)

        return IngestDecision(True, "OK")
