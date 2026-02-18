"""
Hindsight Memory Demo — retain, recall, reflect with HUAP memory tools.

Usage (with InMemoryPort, no server needed):
    python examples/memory/hindsight_demo.py

Usage (with Hindsight plugin):
    1. Enable memory_hindsight in config/plugins.yaml
    2. Start a Hindsight server
    3. python examples/memory/hindsight_demo.py --hindsight
"""
from __future__ import annotations

import asyncio
import json
import sys

from hu_core.ports.memory import InMemoryPort
from hu_core.tools.memory_tools import memory_retain, memory_recall, memory_reflect


async def main(use_hindsight: bool = False):
    # Choose port
    if use_hindsight:
        try:
            from hu_plugins_hindsight import HindsightMemoryPort
            port = HindsightMemoryPort(base_url="http://localhost:8888")
            print("Using HindsightMemoryPort")
        except ImportError:
            print("hu-plugins-hindsight not installed. Falling back to InMemoryPort.")
            port = InMemoryPort()
    else:
        port = InMemoryPort()
        print("Using InMemoryPort (in-process, no persistence)")

    bank = "demo_bank"

    # 1. Retain some facts
    print("\n--- Retaining memories ---")
    facts = [
        ("User prefers dark mode", "preference"),
        ("Summarize_v2 succeeded on document task", "tool_success"),
        ("API call to /orders returned 500 at 14:32", "tool_failure"),
        ("User timezone is UTC+1", "preference"),
    ]
    for content, ctx in facts:
        result = await memory_retain(bank, content, context=ctx, port=port)
        print(f"  Retained: {content[:50]}  (id={result['item']['id']})")

    # 2. Recall
    print("\n--- Recalling: 'tool success' ---")
    result = await memory_recall(bank, "tool success", k=3, port=port)
    for item in result["items"]:
        print(f"  [{item['score']:.1f}] {item['content'][:80]}")

    # 3. Reflect
    print("\n--- Reflecting: 'user preferences' ---")
    result = await memory_reflect(bank, "user preferences", k=3, port=port)
    for item in result["items"]:
        print(f"  [{item['score']:.1f}] {item['content'][:80]}")

    print("\nDone.")


if __name__ == "__main__":
    use_hs = "--hindsight" in sys.argv
    asyncio.run(main(use_hindsight=use_hs))
