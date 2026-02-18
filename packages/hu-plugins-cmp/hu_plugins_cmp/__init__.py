"""
hu-plugins-cmp — Commonplace (Polymath Protocol) toolpack for HUAP.

Tools:
    cmp.capture — append a markdown note with tags and links
    cmp.link    — add a bidirectional backlink between two notes
    cmp.search  — full-text search over the notes directory

Zero mandatory ML dependencies. Optional extras for embeddings later.
"""
from .toolpack import CommonplaceToolpack, cmp_capture, cmp_link, cmp_search

__all__ = ["CommonplaceToolpack", "cmp_capture", "cmp_link", "cmp_search"]
