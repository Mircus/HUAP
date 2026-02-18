"""
CMP Toolpack — file-backed markdown notes with capture / link / search.

All tools are pure-Python, zero ML deps. Notes are plain ``.md`` files
stored under a configurable root directory.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _slugify(text: str) -> str:
    """Turn a string into a filesystem-safe slug."""
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return s[:80]


# ---------------------------------------------------------------------------
# cmp.capture
# ---------------------------------------------------------------------------

def cmp_capture(
    text: str,
    tags: Optional[List[str]] = None,
    links: Optional[List[str]] = None,
    title: Optional[str] = None,
    root: str = "notes",
) -> Dict[str, Any]:
    """
    Append (or create) a markdown note.

    Returns ``{"path": ..., "status": "captured"}``.
    """
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)

    slug = _slugify(title or text[:40])
    note_path = root_path / f"{slug}.md"

    now = datetime.now(timezone.utc).isoformat()

    # Build frontmatter block on first creation
    if not note_path.exists():
        fm_tags = ", ".join(tags or [])
        fm_links = ", ".join(links or [])
        header = (
            f"---\n"
            f"title: \"{title or slug}\"\n"
            f"tags: [{fm_tags}]\n"
            f"links: [{fm_links}]\n"
            f"created: {now}\n"
            f"---\n\n"
        )
        note_path.write_text(header + text + "\n", encoding="utf-8")
    else:
        # Append as a new section
        with open(note_path, "a", encoding="utf-8") as f:
            f.write(f"\n---\n_appended {now}_\n\n{text}\n")

    return {"path": str(note_path), "status": "captured", "slug": slug}


# ---------------------------------------------------------------------------
# cmp.link
# ---------------------------------------------------------------------------

def cmp_link(
    source: str,
    target: str,
    relation: str = "related",
    root: str = "notes",
) -> Dict[str, Any]:
    """
    Add a bidirectional backlink between two notes.

    Returns ``{"source": ..., "target": ..., "relation": ..., "status": "linked"}``.
    """
    root_path = Path(root)
    src_path = root_path / f"{_slugify(source)}.md"
    tgt_path = root_path / f"{_slugify(target)}.md"

    link_line_fwd = f"\n> [{relation}] → [[{_slugify(target)}]]\n"
    link_line_bwd = f"\n> [{relation}] ← [[{_slugify(source)}]]\n"

    for p, line in [(src_path, link_line_fwd), (tgt_path, link_line_bwd)]:
        if p.exists():
            existing = p.read_text(encoding="utf-8")
            if line.strip() not in existing:
                with open(p, "a", encoding="utf-8") as f:
                    f.write(line)

    return {
        "source": str(src_path),
        "target": str(tgt_path),
        "relation": relation,
        "status": "linked",
    }


# ---------------------------------------------------------------------------
# cmp.search
# ---------------------------------------------------------------------------

def cmp_search(
    query: str,
    k: int = 10,
    root: str = "notes",
) -> Dict[str, Any]:
    """
    Simple full-text search over markdown notes (case-insensitive substring).

    Returns ``{"results": [...], "count": N}``.
    """
    root_path = Path(root)
    if not root_path.exists():
        return {"results": [], "count": 0}

    ql = query.lower()
    hits: List[Dict[str, Any]] = []

    for md_file in sorted(root_path.glob("**/*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
        except OSError:
            continue
        tl = text.lower()
        if ql in tl:
            # Find matching line for snippet
            snippet = ""
            for line in text.splitlines():
                if ql in line.lower():
                    snippet = line.strip()[:200]
                    break
            hits.append({
                "path": str(md_file),
                "slug": md_file.stem,
                "snippet": snippet,
            })
        if len(hits) >= k:
            break

    return {"results": hits, "count": len(hits)}


# ---------------------------------------------------------------------------
# Toolpack class (for Plugin Registry integration)
# ---------------------------------------------------------------------------

class CommonplaceToolpack:
    """
    Registered as a HUAP toolpack plugin.

    Instantiated by the Plugin Registry with ``settings`` as kwargs.
    """

    def __init__(self, root: str = "notes", index: str = ".huap/cmp.index"):
        self.root = root
        self.index = index

    def get_tools(self) -> Dict[str, Any]:
        """Return a dict of tool functions keyed by tool name."""
        r = self.root
        return {
            "cmp.capture": lambda text, **kw: cmp_capture(text, root=r, **kw),
            "cmp.link": lambda source, target, **kw: cmp_link(source, target, root=r, **kw),
            "cmp.search": lambda query, **kw: cmp_search(query, root=r, **kw),
        }
