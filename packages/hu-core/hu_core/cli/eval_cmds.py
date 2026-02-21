"""
HUAP CLI Eval Commands

Provides evaluation CLI commands:
- huap eval run <suite> --budgets <file> --out <dir>
- huap eval trace <trace.jsonl> --budgets <file>
- huap eval init --out budgets.yaml
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


if HAS_CLICK:
    @click.group()
    def eval():
        """Evaluation commands for scoring traces against budgets."""
        pass

    @eval.command("run")
    @click.argument("suite", type=click.Path(exists=True))
    @click.option("--budgets", "-b", default=None, help="Budget config file (YAML/JSON)")
    @click.option("--out", "-o", default="reports", help="Output directory for reports")
    @click.option("--format", "-f", "fmt", default="both", type=click.Choice(["json", "md", "both"]), help="Output format")
    @click.option("--scenario", "-s", default=None, help="Force scenario for all traces")
    def eval_run(suite: str, budgets: Optional[str], out: str, fmt: str, scenario: Optional[str]):
        """
        Run evaluation on a suite of traces.

        SUITE: Path to directory containing trace files

        Example:
            huap eval run suites/smoke --budgets budgets/default.yaml --out reports/
        """
        from ..eval import BudgetConfig, SuiteRunner, get_default_budget_config

        click.echo(f"Running evaluation on suite: {suite}")

        # Load budget config
        if budgets:
            try:
                budget = BudgetConfig.from_file(budgets)
                click.echo(f"Loaded budget config: {budget.name}")
            except Exception as e:
                click.echo(f"Error loading budget config: {e}", err=True)
                sys.exit(1)
        else:
            budget = get_default_budget_config()
            click.echo("Using default budget config")

        # Run evaluation
        runner = SuiteRunner(budget)

        scenario_map = {}
        if scenario:
            # Apply scenario to all traces
            suite_path = Path(suite)
            for trace_file in suite_path.glob("*.jsonl"):
                scenario_map[trace_file.name] = scenario

        report = runner.run_suite(suite, scenario_map=scenario_map if scenario else None)

        # Create output directory
        out_path = Path(out)
        out_path.mkdir(parents=True, exist_ok=True)

        # Write reports
        if fmt in ("json", "both"):
            json_path = out_path / "eval_report.json"
            json_path.write_text(report.to_json())
            click.echo(f"JSON report: {json_path}")

        if fmt in ("md", "both"):
            md_path = out_path / "eval_report.md"
            md_path.write_text(report.to_markdown())
            click.echo(f"Markdown report: {md_path}")

        # Print summary
        click.echo("")
        click.echo("=" * 50)
        click.echo(f"Suite: {report.suite_name}")
        click.echo(f"Status: {'PASSED' if report.passed else 'FAILED'}")
        click.echo(f"Pass Rate: {report.pass_rate:.1f}% ({report.passed_traces}/{report.total_traces})")
        click.echo("=" * 50)

        # Show grade distribution
        click.echo("\nCost Grades:")
        for grade in ["A", "B", "C", "D", "F"]:
            count = report.cost_grades.get(grade, 0)
            if count > 0:
                click.echo(f"  {grade}: {count}")

        click.echo("\nQuality Grades:")
        for grade in ["A", "B", "C", "D", "F"]:
            count = report.quality_grades.get(grade, 0)
            if count > 0:
                click.echo(f"  {grade}: {count}")

        # Show failures
        if report.failed_traces > 0:
            click.echo("\nFailed Traces:", err=True)
            for result in report.results:
                if not result.passed:
                    click.echo(f"  - {Path(result.trace_path).name}", err=True)
                    for issue in result.issues[:3]:
                        click.echo(f"    - {issue}", err=True)

        # Exit with error if any failures
        if not report.passed:
            sys.exit(1)

    @eval.command("trace")
    @click.argument("trace_file", type=click.Path(exists=True))
    @click.option("--budgets", "-b", default=None, help="Budget config file (YAML/JSON)")
    @click.option("--scenario", "-s", default=None, help="Scenario name for budget overrides")
    @click.option("--json", "output_json", is_flag=True, help="Output as JSON")
    def eval_trace(trace_file: str, budgets: Optional[str], scenario: Optional[str], output_json: bool):
        """
        Evaluate a single trace file.

        TRACE_FILE: Path to trace JSONL file

        Example:
            huap eval trace runs/hello.trace.jsonl --scenario hello
        """
        from ..eval import BudgetConfig, TraceEvaluator, get_default_budget_config
        import json

        # Load budget config
        if budgets:
            try:
                budget = BudgetConfig.from_file(budgets)
            except Exception as e:
                click.echo(f"Error loading budget config: {e}", err=True)
                sys.exit(1)
        else:
            budget = get_default_budget_config()

        # Evaluate
        evaluator = TraceEvaluator(budget)
        result = evaluator.evaluate(trace_file, scenario=scenario)

        if output_json:
            click.echo(json.dumps(result.to_dict(), indent=2))
        else:
            # Print results
            status = "PASSED" if result.passed else "FAILED"
            click.echo(f"\nEvaluation: {status}")
            click.echo(f"Run ID: {result.run_id[:16]}...")
            if scenario:
                click.echo(f"Scenario: {scenario}")
            click.echo("")

            # Grades
            click.echo(f"Cost Grade: {result.cost_grade}")
            click.echo(f"Quality Grade: {result.quality_grade}")
            click.echo(f"Overall Grade: {result.overall_grade}")
            click.echo("")

            # Cost metrics
            click.echo("Cost Metrics:")
            click.echo(f"  Tokens: {result.tokens_total:,}")
            click.echo(f"  USD: ${result.usd_total:.4f}")
            click.echo(f"  Latency: {result.latency_total_ms:.0f}ms")
            click.echo("")

            # Quality metrics
            click.echo("Quality Metrics:")
            click.echo(f"  Score: {result.quality_score:.2f}")
            click.echo(f"  Policy Violations: {result.policy_violations}")
            click.echo(f"  Tool Errors: {result.tool_errors}")
            for metric, value in result.quality_metrics.items():
                click.echo(f"  {metric}: {value:.2f}")
            click.echo("")

            # Issues
            if result.issues:
                click.echo("Issues:", err=True)
                for issue in result.issues:
                    click.echo(f"  - {issue}", err=True)

        if not result.passed:
            sys.exit(1)

    @eval.command("init")
    @click.option("--out", "-o", default="budgets.yaml", help="Output file path")
    @click.option("--format", "-f", "fmt", default="yaml", type=click.Choice(["yaml", "json"]), help="Output format")
    def eval_init(out: str, fmt: str):
        """
        Create a default budget configuration file.

        Example:
            huap eval init --out budgets/default.yaml
        """
        from ..eval import get_default_budget_config

        budget = get_default_budget_config()

        out_path = Path(out)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if fmt == "yaml":
            try:
                content = budget.to_yaml()
            except ImportError:
                click.echo("PyYAML not installed. Using JSON format instead.", err=True)
                content = budget.to_json()
                out_path = out_path.with_suffix(".json")
        else:
            content = budget.to_json()

        out_path.write_text(content)
        click.echo(f"Created budget config: {out_path}")
        click.echo("\nEdit this file to customize budget thresholds.")

    @eval.command("grades")
    def eval_grades():
        """
        Show grade thresholds and meanings.
        """
        click.echo("\nCost Grade Thresholds:")
        click.echo("  A: <= 50% of budget")
        click.echo("  B: <= 75% of budget")
        click.echo("  C: <= 90% of budget")
        click.echo("  D: <= 100% of budget")
        click.echo("  F: > 100% of budget (FAIL)")
        click.echo("")

        click.echo("Quality Grade Thresholds:")
        click.echo("  A: >= 95% quality score")
        click.echo("  B: >= 85% quality score")
        click.echo("  C: >= 75% quality score")
        click.echo("  D: >= 65% quality score")
        click.echo("  F: < 65% or hard fail (policy violation)")
        click.echo("")

        click.echo("Overall Grade:")
        click.echo("  Weighted average: 60% quality + 40% cost")
        click.echo("")

        click.echo("Hard Fail Conditions:")
        click.echo("  - Any policy violation (configurable)")
        click.echo("  - Cost exceeds budget")
        click.echo("  - Quality score below minimum threshold")

else:
    def eval():
        print("Eval commands require 'click' package. Install with: pip install click")


def register_eval_commands(cli_group):
    """Register eval commands with the main CLI group."""
    if HAS_CLICK:
        cli_group.add_command(eval)
