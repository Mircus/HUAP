"""
HUAP Eval Scoring - Evaluate traces against budgets.

Provides:
- TraceEvaluator for scoring traces
- EvalReport for structured evaluation results
- Suite runner for batch evaluation
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..trace.models import TraceRun, EventName
from .budgets import BudgetConfig, get_default_budget_config


@dataclass
class EvalResult:
    """Result of evaluating a single trace."""
    trace_path: str
    run_id: str
    scenario: Optional[str]

    # Overall status
    passed: bool
    cost_passed: bool
    quality_passed: bool

    # Grades
    cost_grade: str
    quality_grade: str
    overall_grade: str

    # Cost metrics
    tokens_total: int = 0
    usd_total: float = 0.0
    latency_total_ms: float = 0.0

    # Quality metrics
    policy_violations: int = 0
    tool_errors: int = 0
    quality_score: float = 1.0
    quality_metrics: Dict[str, float] = field(default_factory=dict)

    # Issues
    issues: List[str] = field(default_factory=list)

    # Timing
    eval_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_path": self.trace_path,
            "run_id": self.run_id,
            "scenario": self.scenario,
            "passed": self.passed,
            "cost_passed": self.cost_passed,
            "quality_passed": self.quality_passed,
            "cost_grade": self.cost_grade,
            "quality_grade": self.quality_grade,
            "overall_grade": self.overall_grade,
            "tokens_total": self.tokens_total,
            "usd_total": self.usd_total,
            "latency_total_ms": self.latency_total_ms,
            "policy_violations": self.policy_violations,
            "tool_errors": self.tool_errors,
            "quality_score": self.quality_score,
            "quality_metrics": self.quality_metrics,
            "issues": self.issues,
            "eval_timestamp": self.eval_timestamp,
        }


@dataclass
class EvalReport:
    """Report for a suite of trace evaluations."""
    suite_name: str
    budget_name: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Results
    results: List[EvalResult] = field(default_factory=list)

    # Summary
    total_traces: int = 0
    passed_traces: int = 0
    failed_traces: int = 0

    # Aggregate grades
    cost_grades: Dict[str, int] = field(default_factory=dict)
    quality_grades: Dict[str, int] = field(default_factory=dict)

    def add_result(self, result: EvalResult) -> None:
        """Add an evaluation result."""
        self.results.append(result)
        self.total_traces += 1

        if result.passed:
            self.passed_traces += 1
        else:
            self.failed_traces += 1

        # Track grades
        self.cost_grades[result.cost_grade] = self.cost_grades.get(result.cost_grade, 0) + 1
        self.quality_grades[result.quality_grade] = self.quality_grades.get(result.quality_grade, 0) + 1

    @property
    def passed(self) -> bool:
        """Whether all traces passed."""
        return self.failed_traces == 0

    @property
    def pass_rate(self) -> float:
        """Pass rate as percentage."""
        if self.total_traces == 0:
            return 0.0
        return (self.passed_traces / self.total_traces) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "suite_name": self.suite_name,
            "budget_name": self.budget_name,
            "timestamp": self.timestamp,
            "passed": self.passed,
            "total_traces": self.total_traces,
            "passed_traces": self.passed_traces,
            "failed_traces": self.failed_traces,
            "pass_rate": self.pass_rate,
            "cost_grades": self.cost_grades,
            "quality_grades": self.quality_grades,
            "results": [r.to_dict() for r in self.results],
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def to_markdown(self) -> str:
        """Convert to markdown report."""
        lines = []

        lines.append("# Eval Report")
        lines.append("")
        lines.append(f"**Suite:** {self.suite_name}")
        lines.append(f"**Budget:** {self.budget_name}")
        lines.append(f"**Timestamp:** {self.timestamp}")
        lines.append("")

        # Overall status
        status_emoji = "PASSED" if self.passed else "FAILED"
        lines.append(f"## Status: {status_emoji}")
        lines.append("")

        # Summary table
        lines.append("## Summary")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total Traces | {self.total_traces} |")
        lines.append(f"| Passed | {self.passed_traces} |")
        lines.append(f"| Failed | {self.failed_traces} |")
        lines.append(f"| Pass Rate | {self.pass_rate:.1f}% |")
        lines.append("")

        # Grade distribution
        lines.append("## Grade Distribution")
        lines.append("")
        lines.append("### Cost Grades")
        lines.append("")
        for grade in ["A", "B", "C", "D", "F"]:
            count = self.cost_grades.get(grade, 0)
            if count > 0:
                lines.append(f"- **{grade}**: {count}")
        lines.append("")

        lines.append("### Quality Grades")
        lines.append("")
        for grade in ["A", "B", "C", "D", "F"]:
            count = self.quality_grades.get(grade, 0)
            if count > 0:
                lines.append(f"- **{grade}**: {count}")
        lines.append("")

        # Individual results
        lines.append("## Results")
        lines.append("")

        for result in self.results:
            status = "PASS" if result.passed else "FAIL"
            lines.append(f"### {Path(result.trace_path).name} - {status}")
            lines.append("")
            lines.append(f"- **Run ID:** `{result.run_id[:16]}...`")
            lines.append(f"- **Cost Grade:** {result.cost_grade} | **Quality Grade:** {result.quality_grade}")
            lines.append(f"- **Tokens:** {result.tokens_total:,} | **USD:** ${result.usd_total:.4f} | **Latency:** {result.latency_total_ms:.0f}ms")

            if result.issues:
                lines.append("")
                lines.append("**Issues:**")
                for issue in result.issues:
                    lines.append(f"- {issue}")

            lines.append("")

        # Footer
        lines.append("---")
        lines.append("*Generated by HUAP Eval*")

        return "\n".join(lines)


class TraceEvaluator:
    """
    Evaluates traces against budget configurations.

    Usage:
        evaluator = TraceEvaluator(budget_config)
        result = evaluator.evaluate("trace.jsonl", scenario="default")
    """

    def __init__(self, budget: Optional[BudgetConfig] = None):
        self.budget = budget or get_default_budget_config()

    def evaluate(
        self,
        trace_path: Union[str, Path],
        scenario: Optional[str] = None,
    ) -> EvalResult:
        """
        Evaluate a single trace file.

        Args:
            trace_path: Path to trace JSONL file
            scenario: Optional scenario name for budget overrides

        Returns:
            EvalResult with scores and grades
        """
        trace_path = Path(trace_path)

        # Load trace
        trace_run = TraceRun.from_jsonl_file(str(trace_path))

        # Extract metrics from trace
        metrics = self._extract_metrics(trace_run)

        # Get budgets (with scenario override if applicable)
        cost_budget = self.budget.get_cost_budget(scenario)
        quality_budget = self.budget.get_quality_budget(scenario)

        # Evaluate cost
        cost_result = cost_budget.evaluate(
            tokens=metrics["tokens_total"],
            usd=metrics["usd_total"],
            latency_ms=metrics["latency_total_ms"],
        )

        # Evaluate quality
        quality_result = quality_budget.evaluate(
            policy_violations=metrics["policy_violations"],
            tool_errors=metrics["tool_errors"],
            metrics=metrics["quality_metrics"],
        )

        # Combine issues
        issues = []
        if not cost_result["passed"]:
            issues.append(f"Cost budget exceeded: {cost_result['max_usage_pct']*100:.1f}% of budget")
        issues.extend(quality_result.get("issues", []))

        # Calculate overall grade
        overall_grade = self._combine_grades(cost_result["grade"], quality_result["grade"])

        return EvalResult(
            trace_path=str(trace_path),
            run_id=trace_run.run_id,
            scenario=scenario,
            passed=cost_result["passed"] and quality_result["passed"],
            cost_passed=cost_result["passed"],
            quality_passed=quality_result["passed"],
            cost_grade=cost_result["grade"],
            quality_grade=quality_result["grade"],
            overall_grade=overall_grade,
            tokens_total=metrics["tokens_total"],
            usd_total=metrics["usd_total"],
            latency_total_ms=metrics["latency_total_ms"],
            policy_violations=metrics["policy_violations"],
            tool_errors=metrics["tool_errors"],
            quality_score=quality_result["quality_score"],
            quality_metrics=metrics["quality_metrics"],
            issues=issues,
        )

    def _extract_metrics(self, trace_run: TraceRun) -> Dict[str, Any]:
        """Extract metrics from a trace run."""
        tokens_total = 0
        usd_total = 0.0
        latency_total_ms = 0.0
        policy_violations = 0
        tool_errors = 0
        quality_metrics: Dict[str, float] = {}

        for event in trace_run.events:
            data = event.data if isinstance(event.data, dict) else event.data.model_dump()

            if event.name == EventName.COST_RECORD:
                tokens_total += data.get("tokens", 0)
                usd_total += data.get("usd_est", 0)
                latency_total_ms += data.get("latency_ms", 0)

            elif event.name == EventName.LLM_RESPONSE:
                usage = data.get("usage", {})
                tokens_total += usage.get("total_tokens", 0)
                latency_total_ms += data.get("duration_ms", 0)

            elif event.name == EventName.POLICY_CHECK:
                if data.get("decision") == "deny":
                    policy_violations += 1

            elif event.name == EventName.TOOL_RESULT:
                if data.get("status") == "error":
                    tool_errors += 1

            elif event.name == EventName.QUALITY_RECORD:
                metric = data.get("metric", "unknown")
                value = data.get("value", 0.0)
                quality_metrics[metric] = value

        # Estimate USD if not tracked via cost_record
        if usd_total == 0 and tokens_total > 0:
            # Rough estimate: $0.002 per 1K tokens
            usd_total = tokens_total * 0.000002

        # Default quality metrics if not present
        if "json_valid" not in quality_metrics:
            # Check if run completed successfully
            end_event = trace_run.end_event
            if end_event:
                end_data = end_event.data if isinstance(end_event.data, dict) else end_event.data.model_dump()
                if end_data.get("status") == "success":
                    quality_metrics["json_valid"] = 1.0
                else:
                    quality_metrics["json_valid"] = 0.0

        return {
            "tokens_total": tokens_total,
            "usd_total": usd_total,
            "latency_total_ms": latency_total_ms,
            "policy_violations": policy_violations,
            "tool_errors": tool_errors,
            "quality_metrics": quality_metrics,
        }

    def _combine_grades(self, cost_grade: str, quality_grade: str) -> str:
        """Combine cost and quality grades into overall grade."""
        grade_values = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}
        grade_letters = {4: "A", 3: "B", 2: "C", 1: "D", 0: "F"}

        cost_val = grade_values.get(cost_grade, 0)
        quality_val = grade_values.get(quality_grade, 0)

        # Weight quality slightly higher (60% quality, 40% cost)
        combined = (quality_val * 0.6) + (cost_val * 0.4)

        # Round to nearest grade
        rounded = round(combined)
        return grade_letters.get(rounded, "F")


class SuiteRunner:
    """
    Runs evaluation on a suite of traces.

    Usage:
        runner = SuiteRunner(budget_config)
        report = runner.run_suite("suites/smoke/")
    """

    def __init__(self, budget: Optional[BudgetConfig] = None):
        self.budget = budget or get_default_budget_config()
        self.evaluator = TraceEvaluator(budget=self.budget)

    def run_suite(
        self,
        suite_path: Union[str, Path],
        scenario_map: Optional[Dict[str, str]] = None,
    ) -> EvalReport:
        """
        Run evaluation on all traces in a suite directory.

        Args:
            suite_path: Path to directory containing trace files
            scenario_map: Optional mapping of trace filename -> scenario name

        Returns:
            EvalReport with all results
        """
        suite_path = Path(suite_path)
        scenario_map = scenario_map or {}

        report = EvalReport(
            suite_name=suite_path.name,
            budget_name=self.budget.name,
        )

        # Find all trace files
        trace_files = list(suite_path.glob("*.trace.jsonl"))
        trace_files.extend(suite_path.glob("*.jsonl"))

        for trace_file in sorted(trace_files):
            # Determine scenario
            scenario = scenario_map.get(trace_file.name)

            # Try to infer scenario from filename
            if scenario is None:
                for scenario_name in self.budget.scenarios.keys():
                    if scenario_name in trace_file.stem:
                        scenario = scenario_name
                        break

            # Evaluate
            try:
                result = self.evaluator.evaluate(trace_file, scenario=scenario)
                report.add_result(result)
            except Exception as e:
                # Create failed result
                result = EvalResult(
                    trace_path=str(trace_file),
                    run_id="unknown",
                    scenario=scenario,
                    passed=False,
                    cost_passed=False,
                    quality_passed=False,
                    cost_grade="F",
                    quality_grade="F",
                    overall_grade="F",
                    issues=[f"Failed to evaluate: {e}"],
                )
                report.add_result(result)

        return report

    def run_traces(
        self,
        trace_paths: List[Union[str, Path]],
        scenario: Optional[str] = None,
    ) -> EvalReport:
        """
        Run evaluation on a list of trace files.

        Args:
            trace_paths: List of paths to trace files
            scenario: Optional scenario name for all traces

        Returns:
            EvalReport with all results
        """
        report = EvalReport(
            suite_name="custom",
            budget_name=self.budget.name,
        )

        for trace_path in trace_paths:
            try:
                result = self.evaluator.evaluate(trace_path, scenario=scenario)
                report.add_result(result)
            except Exception as e:
                result = EvalResult(
                    trace_path=str(trace_path),
                    run_id="unknown",
                    scenario=scenario,
                    passed=False,
                    cost_passed=False,
                    quality_passed=False,
                    cost_grade="F",
                    quality_grade="F",
                    overall_grade="F",
                    issues=[f"Failed to evaluate: {e}"],
                )
                report.add_result(result)

        return report
