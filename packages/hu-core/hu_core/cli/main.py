"""
HUAP CLI Main Entry Point

Usage:
    huap pod create <name> [--description "..."]
    huap pod validate <name>
    huap pod list
    huap version
"""

import os
import sys
import importlib
import inspect
from pathlib import Path
from typing import Optional, List, Dict, Any

# Try to import click, fall back to argparse if not available
try:
    import click
    HAS_CLICK = True
except ImportError:
    HAS_CLICK = False
    import argparse

from ..contracts import PodContract, PodSchema
from ..contracts.validation import (
    ContractValidator,
    ValidationResult as ContractValidationResult,
    validate_pod as contract_validate_pod,
    validate_trace as contract_validate_trace,
)


# ============================================================================
# POD TEMPLATES
# ============================================================================

POD_TEMPLATE = '''"""
{name_title} Pod - {description}

This pod provides {description_lower}.
"""
from __future__ import annotations

from typing import Any, Dict, List

from hu_core.contracts import PodContract, PodSchema


class {class_name}Pod(PodContract):
    """
    {name_title} Pod Implementation.

    {description}
    """

    name = "{name}"
    version = "0.1.0"
    description = "{description}"

    def get_schema(self) -> PodSchema:
        """Return the fields required to start a session for this pod."""
        return PodSchema(
            pod_name=self.name,
            fields=[
                {{
                    "name": "session_type",
                    "type": "select",
                    "options": ["default", "quick", "detailed"],
                    "required": True,
                    "description": "Type of {name} session",
                }},
                {{
                    "name": "notes",
                    "type": "string",
                    "required": False,
                    "description": "Optional session notes",
                }},
            ],
        )

    async def extract_metrics(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate session data for dashboards/AI prompts."""
        if not sessions:
            return {{"session_count": 0}}

        return {{
            "session_count": len(sessions),
            "latest_session": sessions[-1].get("session_start") if sessions else None,
        }}


# ── Node functions referenced by WORKFLOW_TEMPLATE ──────────────────────

def start_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Initialize the workflow."""
    return {{"status": "started"}}


def process_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Process input data."""
    return {{"status": "processed"}}


def end_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Finalize the workflow."""
    return {{"status": "completed"}}

    def get_system_prompt(self) -> str:
        """Return the system prompt for single-pod AI analysis."""
        return (
            "You are an expert {name} coach. "
            "Provide personalized recommendations based on the user's {name} data."
        )

    def generate_analysis_prompt(self, metrics: Dict[str, Any]) -> str:
        """Return a pod-specific description for AI analysis."""
        session_count = metrics.get("session_count", 0)
        return (
            f"Analyze this user's {{self.name}} data from {{session_count}} sessions. "
            f"Provide 3 specific recommendations for improvement."
        )

    def generate_generic_prompt(self, metrics: Dict[str, Any]) -> str:
        """Return the prompt used when multiple pods are active."""
        return self.generate_analysis_prompt(metrics)

    def get_capabilities(self) -> List[str]:
        """Get list of pod capabilities."""
        return [
            "session_tracking",
            "ai_coaching",
        ]


# Singleton instance
_POD_INSTANCE: {class_name}Pod | None = None


def get_pod() -> {class_name}Pod:
    """Factory used by PodRegistry."""
    global _POD_INSTANCE
    if _POD_INSTANCE is None:
        _POD_INSTANCE = {class_name}Pod()
    return _POD_INSTANCE
'''

INIT_TEMPLATE = '''"""
{name_title} Pod Package

{description}
"""
from .pod import {class_name}Pod, get_pod

__all__ = ["{class_name}Pod", "get_pod"]
'''

PYPROJECT_TEMPLATE = '''[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"

[project]
name = "hu-{name}"
version = "0.1.0"
description = "{description}"
requires-python = ">=3.10"
dependencies = [
    "huap-core>=0.1.0b1",
]
'''

WORKFLOW_TEMPLATE = '''# {name_title} Pod Workflow
# Run with: huap trace run {name} hu-{name}/hu_{name}/{name}.yaml
#
# HUAP executes the nodes[] + edges[] YAML spec.
# Each node's "run:" points to an importable Python function.

name: {name}
version: "0.1.0"
description: "{description}"

nodes:
  - name: start
    run: hu_{name}.pod.start_node
    description: "Initialize the workflow"

  - name: process
    run: hu_{name}.pod.process_node
    description: "Process input data"

  - name: end
    run: hu_{name}.pod.end_node
    description: "Finalize the workflow"

edges:
  - from: start
    to: process
  - from: process
    to: end
'''

TEST_TEMPLATE = '''"""
Tests for {name_title} Pod
"""
import pytest
from hu_{name_underscore}.pod import {class_name}Pod, get_pod


class Test{class_name}Pod:
    def test_pod_name(self):
        pod = get_pod()
        assert pod.name == "{name}"

    def test_pod_version(self):
        pod = get_pod()
        assert pod.version == "0.1.0"

    def test_get_schema(self):
        pod = get_pod()
        schema = pod.get_schema()
        assert schema.pod_name == "{name}"
        assert len(schema.fields) > 0

    @pytest.mark.asyncio
    async def test_extract_metrics_empty(self):
        pod = get_pod()
        metrics = await pod.extract_metrics([])
        assert metrics["session_count"] == 0

    @pytest.mark.asyncio
    async def test_extract_metrics_with_data(self):
        pod = get_pod()
        sessions = [
            {{"session_start": "2025-01-01T10:00:00", "data_json": {{}}}},
            {{"session_start": "2025-01-02T10:00:00", "data_json": {{}}}},
        ]
        metrics = await pod.extract_metrics(sessions)
        assert metrics["session_count"] == 2

    def test_get_system_prompt(self):
        pod = get_pod()
        prompt = pod.get_system_prompt()
        assert len(prompt) > 0
        assert "{name}" in prompt

    def test_generate_analysis_prompt(self):
        pod = get_pod()
        prompt = pod.generate_analysis_prompt({{"session_count": 5}})
        assert len(prompt) > 0

    def test_capabilities(self):
        pod = get_pod()
        caps = pod.get_capabilities()
        assert "session_tracking" in caps
'''


# ============================================================================
# VALIDATION LOGIC
# ============================================================================

class ValidationResult:
    """Result of pod validation."""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, message: str):
        self.errors.append(message)

    def add_warning(self, message: str):
        self.warnings.append(message)

    def add_info(self, message: str):
        self.info.append(message)

    def __str__(self) -> str:
        lines = []
        if self.errors:
            lines.append("ERRORS:")
            for e in self.errors:
                lines.append(f"  - {e}")
        if self.warnings:
            lines.append("WARNINGS:")
            for w in self.warnings:
                lines.append(f"  - {w}")
        if self.info:
            lines.append("INFO:")
            for i in self.info:
                lines.append(f"  - {i}")
        if self.is_valid:
            lines.append("\nValidation PASSED")
        else:
            lines.append("\nValidation FAILED")
        return "\n".join(lines)


def validate_pod_implementation(pod_instance: PodContract) -> ValidationResult:
    """
    Validate a pod's implementation of PodContract.

    Checks:
    - All required properties are defined
    - All required methods are implemented
    - Schema is valid
    - Methods return correct types
    """
    result = ValidationResult()

    # Check required properties
    try:
        name = pod_instance.name
        if not name or not isinstance(name, str):
            result.add_error("Pod 'name' property must return a non-empty string")
        else:
            result.add_info(f"Name: {name}")
    except Exception as e:
        result.add_error(f"Pod 'name' property raised exception: {e}")

    try:
        version = pod_instance.version
        if not version or not isinstance(version, str):
            result.add_error("Pod 'version' property must return a non-empty string")
        else:
            result.add_info(f"Version: {version}")
    except Exception as e:
        result.add_error(f"Pod 'version' property raised exception: {e}")

    try:
        description = pod_instance.description
        if not description or not isinstance(description, str):
            result.add_error("Pod 'description' property must return a non-empty string")
        else:
            result.add_info(f"Description: {description}")
    except Exception as e:
        result.add_error(f"Pod 'description' property raised exception: {e}")

    # Check get_schema
    try:
        schema = pod_instance.get_schema()
        if not isinstance(schema, PodSchema):
            result.add_error("get_schema() must return a PodSchema instance")
        elif not schema.fields:
            result.add_warning("get_schema() returned empty fields list")
        else:
            result.add_info(f"Schema has {len(schema.fields)} field(s)")
    except Exception as e:
        result.add_error(f"get_schema() raised exception: {e}")

    # Check get_system_prompt
    try:
        prompt = pod_instance.get_system_prompt()
        if not prompt or not isinstance(prompt, str):
            result.add_error("get_system_prompt() must return a non-empty string")
        else:
            result.add_info(f"System prompt length: {len(prompt)} chars")
    except Exception as e:
        result.add_error(f"get_system_prompt() raised exception: {e}")

    # Check generate_analysis_prompt
    try:
        prompt = pod_instance.generate_analysis_prompt({"session_count": 0})
        if not prompt or not isinstance(prompt, str):
            result.add_error("generate_analysis_prompt() must return a non-empty string")
    except Exception as e:
        result.add_error(f"generate_analysis_prompt() raised exception: {e}")

    # Check generate_generic_prompt
    try:
        prompt = pod_instance.generate_generic_prompt({"session_count": 0})
        if not prompt or not isinstance(prompt, str):
            result.add_error("generate_generic_prompt() must return a non-empty string")
    except Exception as e:
        result.add_error(f"generate_generic_prompt() raised exception: {e}")

    # Check extract_metrics (sync test only - can't await in sync context)
    try:
        method = pod_instance.extract_metrics
        if not inspect.iscoroutinefunction(method):
            result.add_warning("extract_metrics should be an async method")
    except Exception as e:
        result.add_error(f"extract_metrics check raised exception: {e}")

    # Check optional methods
    try:
        caps = pod_instance.get_capabilities()
        if caps:
            result.add_info(f"Capabilities: {', '.join(caps)}")
    except Exception as e:
        result.add_warning(f"get_capabilities() raised exception: {e}")

    try:
        graph_path = pod_instance.get_graph_path()
        if graph_path:
            result.add_info(f"Graph path: {graph_path}")
    except Exception as e:
        result.add_warning(f"get_graph_path() raised exception: {e}")

    return result


def load_pod_module(pod_name: str, packages_dir: Optional[Path] = None) -> Optional[PodContract]:
    """
    Load a pod module by name.

    Tries to import hu_{pod_name}.pod and call get_pod().
    """
    if packages_dir:
        # Add packages dir to path
        sys.path.insert(0, str(packages_dir))

    module_name = f"hu_{pod_name}"

    try:
        # Try importing the module
        module = importlib.import_module(module_name)

        # Look for get_pod factory
        if hasattr(module, "get_pod"):
            return module.get_pod()

        # Fall back to looking in .pod submodule
        pod_module = importlib.import_module(f"{module_name}.pod")
        if hasattr(pod_module, "get_pod"):
            return pod_module.get_pod()

        return None
    except ImportError as e:
        print(f"Could not import {module_name}: {e}")
        return None
    finally:
        if packages_dir and str(packages_dir) in sys.path:
            sys.path.remove(str(packages_dir))


# ============================================================================
# CLI COMMANDS (CLICK VERSION)
# ============================================================================

if HAS_CLICK:
    @click.group()
    @click.version_option(version="0.1.0b1", prog_name="huap")
    def cli():
        """HUAP CLI - Pod development and trace tools."""
        pass

    @cli.group()
    def pod():
        """Pod management commands."""
        pass

    # Register trace commands
    from .trace_cmds import trace
    cli.add_command(trace)

    # Register eval commands
    from .eval_cmds import eval
    cli.add_command(eval)

    # Register CI commands
    from .ci_cmds import ci
    cli.add_command(ci)

    # Register init command
    from .init_cmds import init
    cli.add_command(init)

    # Register models commands
    from .models_cmds import models
    cli.add_command(models)

    # Register inbox commands (human gates)
    from .inbox_cmds import inbox
    cli.add_command(inbox)

    # Register watch command
    from .watch_cmds import watch
    cli.add_command(watch)

    # Register plugins commands
    from .plugins_cmds import plugins
    cli.add_command(plugins)

    @pod.command("create")
    @click.argument("name")
    @click.option("--description", "-d", default=None, help="Pod description")
    @click.option("--output", "-o", default=None, help="Output directory (default: packages/)")
    @click.option("--force", "-f", is_flag=True, help="Overwrite existing files")
    def pod_create(name: str, description: Optional[str], output: Optional[str], force: bool):
        """
        Create a new pod from template.

        NAME: Pod name (lowercase, no spaces)

        Example:
            huap pod create mind --description "Mental wellness tracking"
        """
        # Validate name
        name = name.lower().replace(" ", "_").replace("-", "_")
        if not name.isidentifier():
            click.echo(f"Error: '{name}' is not a valid Python identifier", err=True)
            sys.exit(1)

        # Set defaults
        if description is None:
            description = f"{name.title()} tracking and coaching"

        # Determine output directory
        if output:
            packages_dir = Path(output)
        else:
            # Try to find packages directory
            cwd = Path.cwd()
            if (cwd / "packages").exists():
                packages_dir = cwd / "packages"
            else:
                packages_dir = cwd

        pod_dir = packages_dir / f"hu-{name}"
        package_dir = pod_dir / f"hu_{name}"
        tests_dir = pod_dir / "tests"

        # Check if already exists
        if pod_dir.exists() and not force:
            click.echo(f"Error: Directory {pod_dir} already exists. Use --force to overwrite.", err=True)
            sys.exit(1)

        # Create directories
        click.echo(f"Creating pod '{name}' in {pod_dir}")

        package_dir.mkdir(parents=True, exist_ok=True)
        tests_dir.mkdir(parents=True, exist_ok=True)

        # Template variables
        class_name = "".join(word.title() for word in name.split("_"))
        name_title = name.replace("_", " ").title()
        name_underscore = name.replace("-", "_")
        description_lower = description.lower()

        # Create files
        files_created = []

        # pod.py
        pod_content = POD_TEMPLATE.format(
            name=name,
            name_title=name_title,
            class_name=class_name,
            description=description,
            description_lower=description_lower,
        )
        (package_dir / "pod.py").write_text(pod_content, encoding="utf-8")
        files_created.append(f"hu_{name}/pod.py")

        # __init__.py
        init_content = INIT_TEMPLATE.format(
            name_title=name_title,
            class_name=class_name,
            description=description,
        )
        (package_dir / "__init__.py").write_text(init_content, encoding="utf-8")
        files_created.append(f"hu_{name}/__init__.py")

        # pyproject.toml
        pyproject_content = PYPROJECT_TEMPLATE.format(
            name=name,
            description=description,
        )
        (pod_dir / "pyproject.toml").write_text(pyproject_content, encoding="utf-8")
        files_created.append("pyproject.toml")

        # workflow YAML
        workflow_content = WORKFLOW_TEMPLATE.format(
            name=name,
            name_title=name_title,
            description=description,
        )
        (package_dir / f"{name}.yaml").write_text(workflow_content, encoding="utf-8")
        files_created.append(f"hu_{name}/{name}.yaml")

        # tests/__init__.py
        (tests_dir / "__init__.py").write_text("", encoding="utf-8")
        files_created.append("tests/__init__.py")

        # tests/test_pod.py
        test_content = TEST_TEMPLATE.format(
            name=name,
            name_title=name_title,
            name_underscore=name_underscore,
            class_name=class_name,
        )
        (tests_dir / f"test_{name}_pod.py").write_text(test_content, encoding="utf-8")
        files_created.append(f"tests/test_{name}_pod.py")

        # Print summary
        click.echo("\nFiles created:")
        for f in files_created:
            click.echo(f"  {pod_dir / f}")

        click.echo(f"\nPod '{name}' created successfully!")
        click.echo("\nNext steps:")
        click.echo(f"  1. Edit {package_dir / 'pod.py'} to customize your pod")
        click.echo(f"  2. Edit {package_dir / f'{name}.yaml'} to define your workflow")
        click.echo(f"  3. Run: huap pod validate {name}")

    @pod.command("validate")
    @click.argument("name")
    @click.option("--packages", "-p", default=None, help="Packages directory")
    @click.option("--trace", "-t", default=None, help="Also validate a trace file")
    @click.option("--format", "-f", "output_format", type=click.Choice(["text", "json", "markdown"]), default="text", help="Output format")
    def pod_validate(name: str, packages: Optional[str], trace: Optional[str], output_format: str):
        """
        Validate a pod's contract implementation.

        NAME: Pod name to validate

        Examples:
            huap pod validate hello
            huap pod validate hello --trace traces/hello.jsonl
            huap pod validate hello --format markdown
        """
        name = name.lower().replace("-", "_")

        # Determine packages directory
        packages_dir = None
        if packages:
            packages_dir = Path(packages)
        else:
            cwd = Path.cwd()
            if (cwd / "packages").exists():
                packages_dir = cwd / "packages"

        click.echo(f"Validating pod '{name}'...")

        # Try to load the pod
        pod_instance = load_pod_module(name, packages_dir)

        if pod_instance is None:
            click.echo(f"Error: Could not load pod 'hu_{name}'", err=True)
            click.echo("\nMake sure:")
            click.echo(f"  - The package 'hu_{name}' is installed or in PYTHONPATH")
            click.echo(f"  - The package has a get_pod() function")
            sys.exit(1)

        # Validate pod implementation using new contract validator
        pod_result = contract_validate_pod(type(pod_instance))

        # Also run legacy validation for full coverage
        legacy_result = validate_pod_implementation(pod_instance)

        # Merge results (use contract result as primary)
        # Add legacy warnings/info if not already covered
        for warning in legacy_result.warnings:
            if not any(w.message == warning for w in pod_result.warnings):
                pod_result.add_warning("LEGACY_CHECK", warning)
        for info in legacy_result.info:
            if not any(i.message == info for i in [issue for issue in pod_result.issues if issue.severity.value == "info"]):
                pod_result.add_info("LEGACY_INFO", info)

        # Validate trace if provided
        trace_result = None
        if trace:
            click.echo(f"\nValidating trace file '{trace}'...")
            trace_result = contract_validate_trace(trace, pod_instance)

        # Output results
        if output_format == "json":
            import json
            output = {"pod_validation": pod_result.to_dict()}
            if trace_result:
                output["trace_validation"] = trace_result.to_dict()
            click.echo(json.dumps(output, indent=2))
        elif output_format == "markdown":
            click.echo(pod_result.to_markdown())
            if trace_result:
                click.echo("\n---\n")
                click.echo(trace_result.to_markdown())
        else:
            # Text format
            click.echo("\n" + str(legacy_result))
            if trace_result:
                click.echo("\n--- Trace Validation ---")
                click.echo(trace_result.to_markdown())

        # Exit with error if validation failed
        if not pod_result.valid:
            sys.exit(1)
        if trace_result and not trace_result.valid:
            sys.exit(1)

    @pod.command("list")
    @click.option("--config", "-c", default="config.yaml", help="Config file path")
    def pod_list(config: str):
        """
        List all registered pods.

        Example:
            huap pod list
        """
        config_path = Path(config)

        if not config_path.exists():
            # Try to find config.yaml
            cwd = Path.cwd()
            for candidate in [cwd / "config.yaml", cwd / ".." / "config.yaml"]:
                if candidate.exists():
                    config_path = candidate
                    break

        if not config_path.exists():
            # Try to discover pods by scanning for pod directories
            cwd = Path.cwd()
            packages_dir = cwd / "packages"
            pods_dir = cwd / "pods"

            discovered = []
            for scan_dir in [packages_dir, pods_dir]:
                if scan_dir.exists():
                    for child in sorted(scan_dir.iterdir()):
                        if child.is_dir() and child.name.startswith("hu-"):
                            pod_name = child.name[3:]  # strip "hu-"
                            discovered.append((pod_name, child))

            if discovered:
                click.echo(f"Discovered pods ({len(discovered)}):\n")
                for pod_name, pod_path in discovered:
                    click.echo(f"  {pod_name}")
                    click.echo(f"    Path: {pod_path}")
                    click.echo()
            else:
                click.echo("No pods found.")
                click.echo("Create one with: huap pod create <name>")
                click.echo("Or initialize a workspace: huap init <name>")
            return

        # Parse YAML
        try:
            import yaml
            with open(config_path) as f:
                cfg = yaml.safe_load(f)
        except ImportError:
            click.echo("Error: PyYAML not installed. Run: pip install pyyaml", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"Error reading config: {e}", err=True)
            sys.exit(1)

        pods = cfg.get("pods", {})

        if not pods:
            click.echo("No pods configured.")
            return

        click.echo(f"Configured pods ({len(pods)}):\n")

        for name, pod_cfg in pods.items():
            enabled = pod_cfg.get("enabled", True)
            version = pod_cfg.get("version", "unknown")
            desc = pod_cfg.get("description", "")
            status = "enabled" if enabled else "disabled"

            click.echo(f"  {name}")
            click.echo(f"    Version: {version}")
            click.echo(f"    Status: {status}")
            if desc:
                click.echo(f"    Description: {desc}")
            click.echo()

    @cli.group()
    def examples():
        """Example management commands."""
        pass

    @examples.command("copy")
    @click.option("--output", "-o", default=".", help="Output directory")
    @click.option("--force", "-f", is_flag=True, help="Overwrite existing files")
    def examples_copy(output: str, force: bool):
        """
        Copy HUAP examples to current directory.

        Downloads example pods, traces, and graphs to get started quickly.

        Example:
            huap examples copy
            huap examples copy --output ./my-project
        """
        import shutil
        from importlib.resources import files

        output_path = Path(output)

        # Try to find examples in package
        try:
            # Look for examples relative to package
            pkg_root = Path(__file__).resolve().parents[2]  # hu_core -> packages/hu-core
            repo_root = pkg_root.parent.parent  # packages -> repo

            examples_src = repo_root / "examples"
            if not examples_src.exists():
                examples_src = pkg_root.parent / "examples"

            if not examples_src.exists():
                click.echo("Error: Could not find examples directory.", err=True)
                click.echo("Examples are available at: https://github.com/Mircus/HUAP/tree/main/examples", err=True)
                sys.exit(1)

            examples_dest = output_path / "examples"

            if examples_dest.exists() and not force:
                click.echo(f"Error: {examples_dest} already exists. Use --force to overwrite.", err=True)
                sys.exit(1)

            if examples_dest.exists():
                shutil.rmtree(examples_dest)

            shutil.copytree(examples_src, examples_dest)

            click.echo(f"Examples copied to: {examples_dest}")
            click.echo()
            click.echo("Contents:")
            click.echo("  examples/pods/hello-pod/    - Minimal deterministic tools")
            click.echo("  examples/pods/llm-pod/      - LLM integration with stub mode")
            click.echo("  examples/pods/memory-pod/   - State management patterns")
            click.echo("  examples/graphs/            - Workflow graph examples")
            click.echo("  examples/traces/            - Golden trace files")
            click.echo()
            click.echo("Next steps:")
            click.echo("  cd examples/pods/hello-pod && python pod.py")

        except Exception as e:
            click.echo(f"Error copying examples: {e}", err=True)
            sys.exit(1)

    @cli.command()
    @click.option("--no-open", is_flag=True, help="Don't open report in browser")
    def demo(no_open):
        """Run a demo graph and produce a shareable HTML trace report."""
        import asyncio
        import webbrowser

        # Find the examples/graphs/hello.yaml relative to the repo
        pkg_root = Path(__file__).resolve().parents[2]  # hu_core -> packages/hu-core
        repo_root = pkg_root.parent.parent  # packages -> repo
        graph_path = repo_root / "examples" / "graphs" / "hello.yaml"

        if not graph_path.exists():
            click.echo(f"Error: Could not find {graph_path}", err=True)
            click.echo("Run this command from the HUAP repo root.", err=True)
            sys.exit(1)

        # Set stub mode
        os.environ["HUAP_LLM_MODE"] = "stub"

        # Create output dir
        demo_dir = Path("huap_demo")
        demo_dir.mkdir(exist_ok=True)
        trace_out = demo_dir / "hello.jsonl"
        report_out = demo_dir / "hello.html"

        click.echo("=" * 60)
        click.echo("HUAP Demo")
        click.echo("=" * 60)
        click.echo("")
        click.echo(f"Graph:  {graph_path}")
        click.echo(f"Mode:   stub (deterministic, no API keys needed)")
        click.echo("")

        # Run the graph
        orig_cwd = os.getcwd()
        try:
            os.chdir(str(repo_root))
            from ..trace.runner import run_pod_graph
            result = asyncio.run(run_pod_graph(
                pod="hello",
                graph_path=graph_path,
                input_state={"message": "Hello from HUAP demo!"},
                output_path=trace_out.resolve(),
            ))
        finally:
            os.chdir(orig_cwd)

        if result["status"] != "success":
            click.echo(f"Error: {result.get('error', 'unknown')}", err=True)
            sys.exit(1)

        click.echo(f"Trace:  {trace_out} ({result['status']})")

        # Generate HTML report
        from ..trace.report import generate_report
        generate_report(str(trace_out), str(report_out))
        click.echo(f"Report: {report_out}")
        click.echo("")

        # Open in browser
        if not no_open:
            webbrowser.open(str(report_out.resolve()))
            click.echo("Opened report in browser.")

        click.echo("")
        click.echo("Next steps:")
        click.echo(f"  huap trace view {trace_out}")
        click.echo(f"  huap eval trace {trace_out}")
        click.echo(f"  huap ci run suites/smoke/suite.yaml --html reports/smoke.html")
        click.echo("")

    @cli.command("version")
    def version():
        """Show HUAP CLI version."""
        click.echo("huap CLI v0.1.0b1")
        click.echo("HUAP CORE - Pod Development Tools")

else:
    # Fallback argparse implementation
    def cli():
        """HUAP CLI entry point (argparse fallback)."""
        parser = argparse.ArgumentParser(
            prog="huap",
            description="HUAP CLI - Pod development tools"
        )
        parser.add_argument("--version", action="version", version="huap 0.1.0b1")

        subparsers = parser.add_subparsers(dest="command")

        # pod subcommand
        pod_parser = subparsers.add_parser("pod", help="Pod management")
        pod_subparsers = pod_parser.add_subparsers(dest="pod_command")

        # pod create
        create_parser = pod_subparsers.add_parser("create", help="Create a new pod")
        create_parser.add_argument("name", help="Pod name")
        create_parser.add_argument("-d", "--description", help="Pod description")
        create_parser.add_argument("-o", "--output", help="Output directory")
        create_parser.add_argument("-f", "--force", action="store_true", help="Overwrite existing")

        # pod validate
        validate_parser = pod_subparsers.add_parser("validate", help="Validate a pod")
        validate_parser.add_argument("name", help="Pod name")
        validate_parser.add_argument("-p", "--packages", help="Packages directory")

        # pod list
        list_parser = pod_subparsers.add_parser("list", help="List pods")
        list_parser.add_argument("-c", "--config", default="config.yaml", help="Config file")

        args = parser.parse_args()

        if args.command == "pod":
            if args.pod_command == "create":
                print(f"Creating pod '{args.name}'...")
                print("Note: Install 'click' for full CLI support: pip install click")
            elif args.pod_command == "validate":
                print(f"Validating pod '{args.name}'...")
            elif args.pod_command == "list":
                print("Listing pods...")
            else:
                pod_parser.print_help()
        else:
            parser.print_help()


# Entry point
def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
