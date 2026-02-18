"""
HUAP CLI Models Commands

Provides model registry and router commands:
- huap models init   - Create starter models.yaml + router.yaml
- huap models list   - List registered models
- huap models explain - Explain router decision for given constraints
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

try:
    import click
    HAS_CLICK = True
except ImportError:
    HAS_CLICK = False

# ---------------------------------------------------------------------------
# Starter config templates
# ---------------------------------------------------------------------------

MODELS_YAML = """\
models:
  - id: stub_chat
    provider: stub
    model: stub
    capabilities: [chat, classify, extract]
    privacy: local
    usd_per_1k_tokens_est: 0.0

  - id: ollama_phi3_chat
    provider: ollama
    model: phi3
    endpoint: http://localhost:11434
    capabilities: [chat, classify, extract]
    privacy: local
    usd_per_1k_tokens_est: 0.0

  - id: openai_gpt4omini_chat
    provider: openai
    model: gpt-4o-mini
    capabilities: [chat, classify, extract]
    privacy: cloud_ok
    usd_per_1k_tokens_est: 0.00015
"""

ROUTER_YAML = """\
rules:
  - name: local_first_chat
    when: { capability: chat, privacy: local }
    prefer: [ollama_phi3_chat, stub_chat]

  - name: default_chat
    when: { capability: chat }
    prefer: [openai_gpt4omini_chat, ollama_phi3_chat, stub_chat]

  - name: classify
    when: { capability: classify }
    prefer: [ollama_phi3_chat, openai_gpt4omini_chat, stub_chat]
"""


if HAS_CLICK:
    @click.group()
    def models():
        """Model registry and router commands."""
        pass

    @models.command("init")
    @click.option("--out", "-o", default="config", help="Output directory")
    @click.option("--force", "-f", is_flag=True, help="Overwrite existing files")
    def models_init(out: str, force: bool):
        """
        Create starter model registry and router config files.

        Example:
            huap models init
            huap models init --out .huap
        """
        out_path = Path(out)
        out_path.mkdir(parents=True, exist_ok=True)

        models_path = out_path / "models.yaml"
        router_path = out_path / "router.yaml"

        for fpath, content, label in [
            (models_path, MODELS_YAML, "Model registry"),
            (router_path, ROUTER_YAML, "Router policy"),
        ]:
            if fpath.exists() and not force:
                click.echo(f"Skipped (exists): {fpath}  — use --force to overwrite")
            else:
                fpath.write_text(content)
                click.echo(f"Created: {fpath}  ({label})")

        click.echo("")
        click.echo("Next steps:")
        click.echo(f"  export HUAP_MODEL_REGISTRY_PATH={models_path}")
        click.echo(f"  export HUAP_ROUTER_POLICY_PATH={router_path}")
        click.echo("  export HUAP_ROUTER_ENABLED=1")
        click.echo("  huap models list")

    @models.command("list")
    @click.option("--registry", "-r", default=None, help="Path to models.yaml")
    def models_list(registry: Optional[str]):
        """
        List all registered models.

        Example:
            huap models list
            huap models list --registry config/models.yaml
        """
        from ..services.model_registry import ModelRegistry

        reg = ModelRegistry.load(registry)
        specs = reg.list()

        if not specs:
            click.echo("No models registered.")
            return

        click.echo(f"{'ID':<30} {'Provider':<10} {'Model':<18} {'Privacy':<10} {'$/1k tok':<10} {'Capabilities'}")
        click.echo("-" * 100)
        for m in specs:
            caps = ", ".join(m.capabilities)
            click.echo(
                f"{m.id:<30} {m.provider:<10} {m.model:<18} {m.privacy:<10} "
                f"{m.usd_per_1k_tokens_est:<10.5f} {caps}"
            )

    @models.command("explain")
    @click.option("--capability", "-c", default="chat", help="Required capability")
    @click.option("--privacy", "-p", default=None, help="Privacy constraint (local | cloud_ok)")
    @click.option("--max-usd", default=None, type=float, help="Max USD per 1k tokens")
    @click.option("--registry", default=None, help="Path to models.yaml")
    @click.option("--policy", default=None, help="Path to router.yaml")
    def models_explain(
        capability: str,
        privacy: Optional[str],
        max_usd: Optional[float],
        registry: Optional[str],
        policy: Optional[str],
    ):
        """
        Explain which model the router would select and why.

        Example:
            huap models explain --capability chat --privacy local
        """
        from ..services.model_registry import ModelRegistry
        from ..services.model_router import ModelRouter

        reg = ModelRegistry.load(registry)
        router = ModelRouter.load(reg, policy)
        result = router.explain(capability=capability, privacy=privacy, max_usd_est=max_usd)

        if result.get("error"):
            click.echo(f"Error: {result['error']}", err=True)
            sys.exit(1)

        sel = result["selected"]
        click.echo("Router Decision")
        click.echo("-" * 40)
        click.echo(f"  Selected model : {sel['model_id']}")
        click.echo(f"  Provider       : {sel['provider']}")
        click.echo(f"  Rule matched   : {sel['rule_name']}")
        click.echo(f"  Reason         : {sel['reason']}")
        click.echo(f"  Candidates     : {sel['candidates_considered']}")
        click.echo(f"  Filters        : {', '.join(sel['filters_applied'])}")

else:
    def models():
        print("Models commands require 'click' package. Install with: pip install click")


def register_models_commands(cli_group):
    """Register models commands with the main CLI group."""
    if HAS_CLICK:
        cli_group.add_command(models)
