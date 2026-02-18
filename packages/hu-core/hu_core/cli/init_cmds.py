"""
HUAP CLI Init Command

Provides workspace initialization:
- huap init <name> - Create a runnable HUAP workspace in <60 seconds
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
# Templates
# ---------------------------------------------------------------------------

CONFIG_YAML = """\
# HUAP workspace configuration
workspace: {name}
version: "0.1.0"

pods:
  - name: hello
    path: pods/hello

graphs:
  - graphs/hello.yaml

traces_dir: traces
reports_dir: reports

defaults:
  llm_mode: stub
  router_enabled: false
"""

HELLO_GRAPH_YAML = """\
# Hello Workflow - Minimal runnable example
# Run with: HUAP_LLM_MODE=stub huap trace run hello graphs/hello.yaml --out traces/hello.jsonl
#
# HUAP executes the nodes[] + edges[] YAML spec.

name: hello
version: "0.1.0"
description: "A minimal hello-world workflow"

nodes:
  - name: start
    run: pods.hello.hello_nodes.start_node
    description: "Echo the input message"

  - name: greet
    run: pods.hello.hello_nodes.greet_node
    description: "Generate a greeting"

  - name: end
    run: pods.hello.hello_nodes.end_node
    description: "End the workflow"

edges:
  - from: start
    to: greet
  - from: greet
    to: end
"""

HELLO_NODES_PY = """\
\"\"\"
Hello pod node functions.

Each function takes a state dict and returns updates to merge into state.
\"\"\"
from typing import Any, Dict


def start_node(state: Dict[str, Any]) -> Dict[str, Any]:
    \"\"\"Echo the input message.\"\"\"
    message = state.get("message", "Hello, World!")
    return {"echoed": message}


def greet_node(state: Dict[str, Any]) -> Dict[str, Any]:
    \"\"\"Generate a greeting from the echoed message.\"\"\"
    echoed = state.get("echoed", "World")
    return {"greeting": f"Hello, {echoed}!"}


def end_node(state: Dict[str, Any]) -> Dict[str, Any]:
    \"\"\"Finalize the workflow.\"\"\"
    return {"status": "complete"}
"""

HELLO_INIT_PY = """\
\"\"\"Hello pod package.\"\"\"
"""

PODS_INIT_PY = """\
\"\"\"Pods package.\"\"\"
"""

SMOKE_SUITE_YAML = """\
# Smoke test suite
# Run with: huap ci check suites/smoke --budgets budgets/cheap.yaml

name: smoke
version: "0.1.0"
description: "Quick smoke tests for CI"

scenarios:
  - name: hello_stub
    pod: hello
    graph: graphs/hello.yaml
    golden: traces/golden/hello.jsonl
    env:
      HUAP_LLM_MODE: stub
"""

CHEAP_BUDGET_YAML = """\
# Budget: cheap  (stub / local models)
name: cheap
version: "0.1.0"

cost:
  max_usd: 0.01
  max_tokens: 1000
  max_latency_ms: 5000

quality:
  min_grade: C
  max_tool_errors: 0
  max_policy_violations: 0
"""

OFFLINE_LOCAL_BUDGET_YAML = """\
# Budget: offline_local  (no cloud calls allowed)
name: offline_local
version: "0.1.0"

cost:
  max_usd: 0.0
  max_tokens: 5000
  max_latency_ms: 10000

quality:
  min_grade: D
  max_tool_errors: 0
  max_policy_violations: 0
"""

ENV_EXAMPLE = """\
# HUAP environment variables
# Copy to .env and customize

# LLM mode: stub (no API key needed) | live (requires OPENAI_API_KEY)
HUAP_LLM_MODE=stub

# Model router (set to 1 to enable)
HUAP_ROUTER_ENABLED=0

# Optional: OpenAI API key (only needed in live mode)
# OPENAI_API_KEY=sk-...

# Optional: privacy mode (local | cloud_ok)
# HUAP_PRIVACY=local
"""


if HAS_CLICK:
    @click.command("init")
    @click.argument("name", default="huap-workspace")
    @click.option("--out", "-o", default=None, help="Parent directory (default: current dir)")
    @click.option("--force", "-f", is_flag=True, help="Overwrite existing directory")
    def init(name: str, out: Optional[str], force: bool):
        """
        Create a runnable HUAP workspace.

        NAME: Workspace directory name (default: huap-workspace)

        Creates a ready-to-run project with a hello workflow,
        smoke suite, budgets, and example .env.

        Example:
            huap init demo
            cd demo
            HUAP_LLM_MODE=stub huap trace run hello graphs/hello.yaml --out traces/hello.jsonl
        """
        parent = Path(out) if out else Path.cwd()
        workspace = parent / name

        if workspace.exists() and not force:
            click.echo(f"Error: {workspace} already exists. Use --force to overwrite.", err=True)
            sys.exit(1)

        click.echo(f"Creating HUAP workspace '{name}' ...")

        # Directories
        dirs = [
            "pods/hello",
            "graphs",
            "traces/golden",
            "suites/smoke",
            "budgets",
            "reports",
            ".huap",
        ]
        for d in dirs:
            (workspace / d).mkdir(parents=True, exist_ok=True)

        # Files
        files = {
            ".huap/config.yaml": CONFIG_YAML.format(name=name),
            "graphs/hello.yaml": HELLO_GRAPH_YAML,
            "pods/__init__.py": PODS_INIT_PY,
            "pods/hello/__init__.py": HELLO_INIT_PY,
            "pods/hello/hello_nodes.py": HELLO_NODES_PY,
            "suites/smoke/smoke.yaml": SMOKE_SUITE_YAML,
            "budgets/cheap.yaml": CHEAP_BUDGET_YAML,
            "budgets/offline_local.yaml": OFFLINE_LOCAL_BUDGET_YAML,
            ".env.example": ENV_EXAMPLE,
        }

        for rel_path, content in files.items():
            fp = workspace / rel_path
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(content)

        click.echo("")
        click.echo("Files created:")
        for rel_path in sorted(files):
            click.echo(f"  {name}/{rel_path}")
        click.echo("")
        click.echo(f"Workspace '{name}' created successfully!")
        click.echo("")
        click.echo("Next steps:")
        click.echo(f"  cd {name}")
        click.echo(f"  pip install -e ../packages/hu-core  # or: pip install huap-core")
        click.echo(f"  HUAP_LLM_MODE=stub huap trace run hello graphs/hello.yaml --out traces/hello.jsonl")
        click.echo(f"  huap trace view traces/hello.jsonl")

else:
    def init():
        print("Init command requires 'click' package. Install with: pip install click")


def register_init_commands(cli_group):
    """Register init command with the main CLI group."""
    if HAS_CLICK:
        cli_group.add_command(init)
