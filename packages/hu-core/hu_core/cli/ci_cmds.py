"""
HUAP CLI CI Commands

Provides CI/CD integration commands:
- huap ci check <suite> --budgets <file> - Run full CI check (replay + eval)
- huap ci status - Show CI status summary
"""
from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime

try:
    import click
    HAS_CLICK = True
except ImportError:
    HAS_CLICK = False


if HAS_CLICK:
    @click.group()
    def ci():
        """CI/CD integration commands."""
        pass

    @ci.command("check")
    @click.argument("suite", type=click.Path(exists=True))
    @click.option("--budgets", "-b", default=None, help="Budget config file (YAML/JSON)")
    @click.option("--out", "-o", default="ci_reports", help="Output directory for reports")
    @click.option("--replay/--no-replay", default=True, help="Run replay before eval")
    @click.option("--fail-fast", is_flag=True, help="Stop on first failure")
    @click.option("--verbose", "-v", is_flag=True, help="Verbose output")
    def ci_check(
        suite: str,
        budgets: Optional[str],
        out: str,
        replay: bool,
        fail_fast: bool,
        verbose: bool,
    ):
        """
        Run full CI check on a test suite.

        This command:
        1. Optionally replays traces to verify determinism
        2. Evaluates all traces against budget gates
        3. Generates reports (JSON + Markdown)
        4. Exits with non-zero code if any check fails

        SUITE: Path to directory containing trace files or test scenarios

        Example:
            huap ci check suites/smoke --budgets budgets/default.yaml
        """
        import asyncio
        from ..eval import BudgetConfig, SuiteRunner, get_default_budget_config
        from ..trace import TraceReplayer, TraceDiffer

        start_time = datetime.utcnow()
        suite_path = Path(suite)
        out_path = Path(out)
        out_path.mkdir(parents=True, exist_ok=True)

        click.echo("=" * 60)
        click.echo("HUAP CI Check")
        click.echo("=" * 60)
        click.echo(f"Suite: {suite}")
        click.echo(f"Timestamp: {start_time.isoformat()}Z")
        click.echo("")

        # Load budget config
        if budgets:
            try:
                budget = BudgetConfig.from_file(budgets)
                click.echo(f"Budget config: {budgets}")
            except Exception as e:
                click.echo(f"Error loading budget config: {e}", err=True)
                sys.exit(1)
        else:
            budget = get_default_budget_config()
            click.echo("Budget config: default")

        click.echo("")

        # Collect results
        ci_results = {
            "suite": str(suite_path),
            "timestamp": start_time.isoformat(),
            "budget_config": budgets or "default",
            "replay_enabled": replay,
            "traces": [],
            "replay_results": [],
            "eval_results": [],
            "passed": True,
            "failures": [],
        }

        # Find trace files
        trace_files = list(suite_path.glob("*.trace.jsonl"))
        trace_files.extend(suite_path.glob("*.jsonl"))
        trace_files = sorted(set(trace_files))

        if not trace_files:
            click.echo("No trace files found in suite directory.", err=True)
            sys.exit(1)

        click.echo(f"Found {len(trace_files)} trace file(s)")
        click.echo("")

        # Phase 1: Replay (if enabled)
        if replay:
            click.echo("-" * 40)
            click.echo("Phase 1: Replay Verification")
            click.echo("-" * 40)

            for trace_file in trace_files:
                if verbose:
                    click.echo(f"\nReplaying: {trace_file.name}")

                try:
                    replayer = TraceReplayer(
                        trace_path=str(trace_file),
                        stub_tools=True,
                        stub_llm=True,
                    )

                    replay_out = out_path / f"{trace_file.stem}.replay.jsonl"
                    result = asyncio.run(replayer.replay(output_path=str(replay_out)))

                    replay_result = {
                        "trace": str(trace_file),
                        "passed": result.get("state_hash_match", False),
                        "original_run_id": result.get("original_run_id"),
                        "replay_run_id": result.get("replay_run_id"),
                        "events_replayed": result.get("events_replayed", 0),
                    }
                    ci_results["replay_results"].append(replay_result)

                    if result.get("state_hash_match"):
                        if verbose:
                            click.echo(f"  PASS - State hash matches")
                    else:
                        click.echo(f"  FAIL - State hash mismatch: {trace_file.name}", err=True)
                        ci_results["passed"] = False
                        ci_results["failures"].append(f"Replay mismatch: {trace_file.name}")
                        if fail_fast:
                            break

                except Exception as e:
                    click.echo(f"  ERROR - {trace_file.name}: {e}", err=True)
                    ci_results["replay_results"].append({
                        "trace": str(trace_file),
                        "passed": False,
                        "error": str(e),
                    })
                    ci_results["passed"] = False
                    ci_results["failures"].append(f"Replay error: {trace_file.name}")
                    if fail_fast:
                        break

            replay_passed = sum(1 for r in ci_results["replay_results"] if r.get("passed", False))
            click.echo(f"\nReplay: {replay_passed}/{len(trace_files)} passed")

        # Phase 2: Evaluation
        click.echo("")
        click.echo("-" * 40)
        click.echo("Phase 2: Budget Evaluation")
        click.echo("-" * 40)

        runner = SuiteRunner(budget)
        eval_report = runner.run_suite(suite_path)

        ci_results["eval_results"] = eval_report.to_dict()

        for result in eval_report.results:
            if verbose:
                status = "PASS" if result.passed else "FAIL"
                click.echo(f"\n{Path(result.trace_path).name}: {status}")
                click.echo(f"  Cost: {result.cost_grade} | Quality: {result.quality_grade}")

            if not result.passed:
                ci_results["passed"] = False
                ci_results["failures"].append(f"Eval failed: {Path(result.trace_path).name}")
                for issue in result.issues:
                    ci_results["failures"].append(f"  - {issue}")
                if fail_fast:
                    break

        click.echo(f"\nEval: {eval_report.passed_traces}/{eval_report.total_traces} passed")
        click.echo(f"Pass rate: {eval_report.pass_rate:.1f}%")

        # Write reports
        click.echo("")
        click.echo("-" * 40)
        click.echo("Generating Reports")
        click.echo("-" * 40)

        # CI results JSON
        ci_json_path = out_path / "ci_results.json"
        ci_json_path.write_text(json.dumps(ci_results, indent=2, default=str))
        click.echo(f"CI Results: {ci_json_path}")

        # Eval report
        eval_json_path = out_path / "eval_report.json"
        eval_json_path.write_text(eval_report.to_json())
        click.echo(f"Eval Report (JSON): {eval_json_path}")

        eval_md_path = out_path / "eval_report.md"
        eval_md_path.write_text(eval_report.to_markdown())
        click.echo(f"Eval Report (MD): {eval_md_path}")

        # Summary
        click.echo("")
        click.echo("=" * 60)
        if ci_results["passed"]:
            click.echo("CI CHECK: PASSED")
        else:
            click.echo("CI CHECK: FAILED", err=True)
            click.echo("")
            click.echo("Failures:", err=True)
            for failure in ci_results["failures"][:10]:
                click.echo(f"  - {failure}", err=True)
            if len(ci_results["failures"]) > 10:
                click.echo(f"  ... and {len(ci_results['failures']) - 10} more", err=True)
        click.echo("=" * 60)

        # Exit with appropriate code
        if not ci_results["passed"]:
            sys.exit(1)

    @ci.command("status")
    @click.option("--reports", "-r", default="ci_reports", help="Reports directory")
    def ci_status(reports: str):
        """
        Show status from most recent CI run.

        Example:
            huap ci status --reports ci_reports/
        """
        reports_path = Path(reports)

        if not reports_path.exists():
            click.echo("No CI reports found.", err=True)
            click.echo(f"Run 'huap ci check' first to generate reports.")
            sys.exit(1)

        # Find most recent ci_results.json
        ci_results_path = reports_path / "ci_results.json"

        if not ci_results_path.exists():
            click.echo("No CI results found.", err=True)
            sys.exit(1)

        results = json.loads(ci_results_path.read_text())

        click.echo("")
        click.echo("Last CI Run")
        click.echo("-" * 40)
        click.echo(f"Suite: {results.get('suite', 'unknown')}")
        click.echo(f"Timestamp: {results.get('timestamp', 'unknown')}")
        click.echo(f"Budget Config: {results.get('budget_config', 'unknown')}")
        click.echo("")

        if results.get("passed"):
            click.echo("Status: PASSED")
        else:
            click.echo("Status: FAILED", err=True)
            click.echo("")
            click.echo("Failures:")
            for failure in results.get("failures", [])[:5]:
                click.echo(f"  - {failure}")
            if len(results.get("failures", [])) > 5:
                click.echo(f"  ... and {len(results['failures']) - 5} more")

        # Show eval summary
        eval_results = results.get("eval_results", {})
        if eval_results:
            click.echo("")
            click.echo("Eval Summary:")
            click.echo(f"  Total: {eval_results.get('total_traces', 0)}")
            click.echo(f"  Passed: {eval_results.get('passed_traces', 0)}")
            click.echo(f"  Failed: {eval_results.get('failed_traces', 0)}")

    @ci.command("init")
    @click.option("--out", "-o", default=".", help="Output directory")
    def ci_init(out: str):
        """
        Initialize CI configuration files.

        Creates:
        - .github/workflows/huap-ci.yml
        - budgets/default.yaml
        - suites/smoke/ directory

        Example:
            huap ci init --out .
        """
        from ..eval import get_default_budget_config

        out_path = Path(out)

        # Create directories
        (out_path / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
        (out_path / "budgets").mkdir(parents=True, exist_ok=True)
        (out_path / "suites" / "smoke").mkdir(parents=True, exist_ok=True)

        # Create GitHub workflow
        workflow_content = '''# HUAP CI Workflow
# Runs trace replay + evaluation on pull requests

name: HUAP CI

on:
  pull_request:
    branches: [ main, develop ]
  push:
    branches: [ main ]

jobs:
  ci-check:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e packages/hu-core
          pip install click pyyaml

      - name: Run HUAP CI Check
        run: |
          huap ci check suites/smoke --budgets budgets/default.yaml --out ci_reports/

      - name: Upload CI Reports
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: ci-reports
          path: ci_reports/

      - name: Comment on PR
        if: failure() && github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('ci_reports/eval_report.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '## HUAP CI Failed\\n\\n' + report.substring(0, 10000)
            });
'''
        workflow_path = out_path / ".github" / "workflows" / "huap-ci.yml"
        workflow_path.write_text(workflow_content)
        click.echo(f"Created: {workflow_path}")

        # Create default budget config
        budget = get_default_budget_config()
        budget_path = out_path / "budgets" / "default.yaml"
        try:
            budget_path.write_text(budget.to_yaml())
        except ImportError:
            budget_path = budget_path.with_suffix(".json")
            budget_path.write_text(budget.to_json())
        click.echo(f"Created: {budget_path}")

        # Create README for suites
        readme_content = '''# Test Suites

Place your trace files here for CI evaluation.

## Structure

```
suites/
├── smoke/           # Quick smoke tests
│   ├── soma_plan.trace.jsonl
│   └── basic_tool.trace.jsonl
├── integration/     # Full integration tests
└── regression/      # Regression test baselines
```

## Adding Tests

1. Run your pod with tracing: `huap trace run <pod> <graph> --out suites/smoke/<name>.trace.jsonl`
2. Verify the trace: `huap eval trace suites/smoke/<name>.trace.jsonl`
3. Commit the trace as a baseline

## Running CI Locally

```bash
huap ci check suites/smoke --budgets budgets/default.yaml
```
'''
        readme_path = out_path / "suites" / "README.md"
        readme_path.write_text(readme_content)
        click.echo(f"Created: {readme_path}")

        click.echo("")
        click.echo("CI configuration initialized!")
        click.echo("")
        click.echo("Next steps:")
        click.echo("  1. Add trace files to suites/smoke/")
        click.echo("  2. Run: huap ci check suites/smoke")
        click.echo("  3. Commit and push to trigger GitHub Actions")

else:
    def ci():
        print("CI commands require 'click' package. Install with: pip install click")


def register_ci_commands(cli_group):
    """Register CI commands with the main CLI group."""
    if HAS_CLICK:
        cli_group.add_command(ci)
