"""
HUAP CI Runner — run suite scenarios, diff vs golden traces, evaluate budgets.

Used by ``huap ci run``.
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ScenarioResult:
    name: str
    passed: bool
    exit_code: int = 0
    trace_path: Optional[str] = None
    diff_issues: List[str] = field(default_factory=list)
    eval_issues: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class CIReport:
    suite: str
    timestamp: str
    scenarios: List[ScenarioResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(s.passed for s in self.scenarios)

    @property
    def pass_count(self) -> int:
        return sum(1 for s in self.scenarios if s.passed)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite": self.suite,
            "timestamp": self.timestamp,
            "passed": self.passed,
            "total": len(self.scenarios),
            "passed_count": self.pass_count,
            "scenarios": [
                {
                    "name": s.name,
                    "passed": s.passed,
                    "exit_code": s.exit_code,
                    "trace_path": s.trace_path,
                    "diff_issues": s.diff_issues,
                    "eval_issues": s.eval_issues,
                    "error": s.error,
                }
                for s in self.scenarios
            ],
        }


class CIRunner:
    """
    Run a YAML suite, diff against golden traces, evaluate budgets,
    and return a structured report.
    """

    def __init__(
        self,
        suite_path: str,
        budgets_path: Optional[str] = None,
        output_dir: str = "reports",
    ):
        self.suite_path = Path(suite_path)
        self.budgets_path = budgets_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> CIReport:
        """Execute the full CI pipeline and return a CIReport."""
        import yaml

        suite_data = yaml.safe_load(self.suite_path.read_text())
        suite_name = suite_data.get("name", self.suite_path.stem)

        report = CIReport(
            suite=suite_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        for scenario in suite_data.get("scenarios", []):
            result = self._run_scenario(scenario)
            report.scenarios.append(result)

        # Write report
        report_path = self.output_dir / "ci_report.json"
        report_path.write_text(json.dumps(report.to_dict(), indent=2, default=str))

        return report

    def _run_scenario(self, scenario: Dict[str, Any]) -> ScenarioResult:
        name = scenario.get("name", "unnamed")
        pod = scenario.get("pod", "")
        graph = scenario.get("graph", "")
        golden = scenario.get("golden")
        env_overrides = scenario.get("env", {})

        trace_out = self.output_dir / f"{name}.trace.jsonl"

        # 1. Run the workflow
        env = os.environ.copy()
        env.update({k: str(v) for k, v in env_overrides.items()})

        try:
            proc = subprocess.run(
                ["huap", "trace", "run", pod, graph, "--out", str(trace_out)],
                capture_output=True,
                text=True,
                env=env,
                timeout=120,
            )
            exit_code = proc.returncode
            if exit_code != 0:
                return ScenarioResult(
                    name=name,
                    passed=False,
                    exit_code=exit_code,
                    trace_path=str(trace_out),
                    error=proc.stderr[:2000] if proc.stderr else f"exit code {exit_code}",
                )
        except Exception as exc:
            return ScenarioResult(name=name, passed=False, error=str(exc))

        diff_issues: List[str] = []
        eval_issues: List[str] = []

        # 2. Diff against golden (if present)
        if golden and Path(golden).exists():
            try:
                from ..trace.diff import TraceDiffer
                differ = TraceDiffer(ignore_timestamps=True)
                diff_result = differ.diff(golden, str(trace_out))
                regressions = diff_result.get("regressions", [])
                if regressions:
                    diff_issues.extend(regressions[:10])
            except Exception as exc:
                diff_issues.append(f"Diff error: {exc}")

        # 3. Evaluate budgets (if provided)
        if self.budgets_path and Path(self.budgets_path).exists():
            try:
                from ..eval import BudgetConfig, TraceEvaluator
                budget = BudgetConfig.from_file(self.budgets_path)
                evaluator = TraceEvaluator(budget)
                eval_result = evaluator.evaluate(str(trace_out))
                if not eval_result.passed:
                    eval_issues.extend(eval_result.issues[:10])
            except Exception as exc:
                eval_issues.append(f"Eval error: {exc}")

        passed = exit_code == 0 and not diff_issues and not eval_issues

        return ScenarioResult(
            name=name,
            passed=passed,
            exit_code=exit_code,
            trace_path=str(trace_out),
            diff_issues=diff_issues,
            eval_issues=eval_issues,
        )
