"""
HUAP Plugins CLI — list and scaffold plugin configurations.

Commands:
    huap plugins init    — write a starter plugins.yaml
    huap plugins list    — show registered plugins and status
"""
from __future__ import annotations

import sys
from pathlib import Path

import click

from ..plugins.registry import PluginRegistry


PLUGINS_YAML = """\
# HUAP Plugins Configuration
# Plugins are optional extras that extend HUAP without bloating core.
#
# Plugin types:
#   memory   — MemoryPort implementations (retain/recall/reflect)
#   toolpack — extra tool bundles (e.g. CMP capture/link/search)
#   provider — additional LLM/model providers
#   other    — custom extensions

plugins:
  - id: memory_hindsight
    type: memory
    impl: hu_plugins_hindsight:HindsightMemoryPort
    enabled: false
    settings:
      base_url: http://localhost:8888
      default_bank_id: demo

  - id: toolpack_cmp
    type: toolpack
    impl: hu_plugins_cmp:CommonplaceToolpack
    enabled: false
    settings:
      root: notes/
      index: .huap/cmp.index
"""


@click.group("plugins")
def plugins():
    """Plugin management commands."""
    pass


@plugins.command("init")
@click.option("--out", "-o", default="config/plugins.yaml", help="Output path")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing file")
def plugins_init(out: str, force: bool):
    """Create a starter plugins.yaml."""
    path = Path(out)
    if path.exists() and not force:
        click.echo(f"File already exists: {path}  (use --force to overwrite)")
        sys.exit(1)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PLUGINS_YAML, encoding="utf-8")
    click.echo(f"Created {path}")
    click.echo("Enable plugins by setting  enabled: true  and installing the plugin package.")


@plugins.command("list")
@click.option("--config", "-c", default=None, help="Path to plugins.yaml")
@click.option("--enabled-only", is_flag=True, help="Show only enabled plugins")
def plugins_list(config, enabled_only):
    """List registered plugins."""
    registry = PluginRegistry.load(config)
    specs = registry.list(only_enabled=enabled_only)

    if not specs:
        click.echo("No plugins configured." if not config else f"No plugins in {config}.")
        click.echo("Run  huap plugins init  to create a starter config.")
        return

    click.echo(f"{'ID':<24} {'TYPE':<12} {'ENABLED':<9} {'IMPL'}")
    click.echo("-" * 72)
    for s in specs:
        status = "yes" if s.enabled else "no"
        click.echo(f"{s.id:<24} {s.type:<12} {status:<9} {s.impl}")
    click.echo(f"\n{len(specs)} plugin(s)")
