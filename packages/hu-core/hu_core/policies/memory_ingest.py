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
import re
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

# Regex patterns for secrets that must be redacted before storage
_SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "[REDACTED_API_KEY]"),          # OpenAI keys
    (re.compile(r"sk-ant-[A-Za-z0-9\-]{20,}"), "[REDACTED_API_KEY]"),    # Anthropic keys
    (re.compile(r"ghp_[A-Za-z0-9]{36,}"), "[REDACTED_TOKEN]"),           # GitHub PAT
    (re.compile(r"gho_[A-Za-z0-9]{36,}"), "[REDACTED_TOKEN]"),           # GitHub OAuth
    (re.compile(r"glpat-[A-Za-z0-9\-]{20,}"), "[REDACTED_TOKEN]"),       # GitLab PAT
    (re.compile(r"Bearer\s+[A-Za-z0-9\._\-]{20,}"), "Bearer [REDACTED]"),  # Bearer tokens
    (re.compile(r"token[\"']?\s*[:=]\s*[\"'][A-Za-z0-9\._\-]{20,}[\"']"), "token: '[REDACTED]'"),
    (re.compile(r"password[\"']?\s*[:=]\s*[\"'][^\"']{8,}[\"']"), "password: '[REDACTED]'"),
    (re.compile(r"AKIA[A-Z0-9]{16}"), "[REDACTED_AWS_KEY]"),             # AWS access key
]


def redact_secrets(text: str) -> str:
    """Scrub obvious secrets/tokens/keys from text before memory storage."""
    for pattern, replacement in _SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


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

    def sanitize(self, content: str) -> str:
        """Redact secrets from content before storage. Always call before retain."""
        return redact_secrets(content)
