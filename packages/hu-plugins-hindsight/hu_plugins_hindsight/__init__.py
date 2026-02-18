"""
hu-plugins-hindsight — Hindsight-backed MemoryPort for HUAP.

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
from .port import HindsightMemoryPort

__all__ = ["HindsightMemoryPort"]
