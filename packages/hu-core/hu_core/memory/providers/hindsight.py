"""
Hindsight Provider — thin re-export from hu-plugins-hindsight.

The SQLite implementation lives in the hu-plugins-hindsight package
(plugin boundary). This module re-exports it so existing imports
like ``from hu_core.memory.providers.hindsight import HindsightProvider``
continue to work.

Install the plugin with:
    pip install hu-plugins-hindsight
    # or: pip install huap-core[default]
"""

try:
    from hu_plugins_hindsight.provider import HindsightProvider
except ImportError:
    raise ImportError(
        "HindsightProvider requires the hu-plugins-hindsight package.\n"
        "Install it with:  pip install hu-plugins-hindsight\n"
        "Or install huap-core with the default extra:  pip install huap-core[default]"
    ) from None

__all__ = ["HindsightProvider"]
