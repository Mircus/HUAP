"""
hu-plugins-hindsight — Hindsight memory plugin for HUAP.

Provides:
- HindsightProvider: SQLite-backed MemoryProvider (get/set/delete/query)
- HindsightMemoryPort: REST API-backed MemoryPort (retain/recall/reflect)

Usage:
    # In plugins.yaml:
    plugins:
      - id: memory_hindsight
        type: memory
        impl: hu_plugins_hindsight:HindsightMemoryPort
        enabled: true
        settings:
          base_url: http://localhost:8888
"""
from .provider import HindsightProvider
from .port import HindsightMemoryPort

__all__ = ["HindsightProvider", "HindsightMemoryPort"]
