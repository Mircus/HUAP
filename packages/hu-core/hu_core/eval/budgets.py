"""
HUAP Budget Configuration and Gates.

Provides:
- BudgetConfig for loading cost/quality budgets from YAML/JSON
- CostBudget for token, USD, and latency limits
- QualityBudget for quality metric thresholds
- Budget gate evaluation
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@dataclass
class CostBudget:
    """
    Cost budget thresholds.

    Defines limits for:
    - tokens_max: Maximum total tokens
    - usd_max: Maximum estimated USD cost
    - latency_p95_ms: Maximum P95 latency in milliseconds
    """
    tokens_max: int = 100000
    usd_max: float = 1.0
    latency_p95_ms: float = 30000.0  # 30 seconds

    # Grade thresholds (percentage of max for each grade)
    grade_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "A": 0.5,   # <= 50% of budget
        "B": 0.75,  # <= 75% of budget
        "C": 0.9,   # <= 90% of budget
        "D": 1.0,   # <= 100% of budget
        # F: > 100% of budget
    })

    def evaluate(self, tokens: int, usd: float, latency_ms: float) -> Dict[str, Any]:
        """
        Evaluate cost metrics against budget.

        Returns:
            Dict with pass/fail status and grade
        """
        # Calculate usage percentages
        tokens_pct = tokens / self.tokens_max if self.tokens_max > 0 else 0
        usd_pct = usd / self.usd_max if self.usd_max > 0 else 0
        latency_pct = latency_ms / self.latency_p95_ms if self.latency_p95_ms > 0 else 0

        # Use max percentage for grading
        max_pct = max(tokens_pct, usd_pct, latency_pct)

        # Determine grade
        grade = "F"
        for g, threshold in sorted(self.grade_thresholds.items(), key=lambda x: x[1]):
            if max_pct <= threshold:
                grade = g
                break

        # Check pass/fail
        passed = max_pct <= 1.0

        return {
            "passed": passed,
            "grade": grade,
            "tokens": tokens,
            "tokens_max": self.tokens_max,
            "tokens_pct": tokens_pct,
            "usd": usd,
            "usd_max": self.usd_max,
            "usd_pct": usd_pct,
            "latency_ms": latency_ms,
            "latency_max_ms": self.latency_p95_ms,
            "latency_pct": latency_pct,
            "max_usage_pct": max_pct,
        }


@dataclass
class QualityBudget:
    """
    Quality/verification budget thresholds.

    Defines requirements for:
    - policy_violations_max: Maximum allowed policy violations (0 = hard fail)
    - tool_errors_max: Maximum allowed tool errors
    - required_metrics: Metrics that must meet minimum thresholds
    - min_quality_score: Minimum overall quality score (0.0-1.0)
    """
    policy_violations_max: int = 0  # Hard fail on any violation
    tool_errors_max: int = 0
    min_quality_score: float = 0.8

    # Required metrics and their minimum values
    required_metrics: Dict[str, float] = field(default_factory=lambda: {
        "json_valid": 1.0,  # Must be 100% valid JSON
        "required_fields_present": 1.0,  # Must have all required fields
    })

    # Optional metrics with preferred thresholds
    preferred_metrics: Dict[str, float] = field(default_factory=lambda: {
        "critique_closed": 0.9,  # 90% of critiques should be closed
    })

    # Grade thresholds
    grade_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "A": 0.95,
        "B": 0.85,
        "C": 0.75,
        "D": 0.65,
        # F: < 0.65
    })

    def evaluate(
        self,
        policy_violations: int,
        tool_errors: int,
        metrics: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Evaluate quality metrics against budget.

        Returns:
            Dict with pass/fail status and grade
        """
        issues = []
        hard_fail = False

        # Check policy violations (hard fail)
        if policy_violations > self.policy_violations_max:
            hard_fail = True
            issues.append(f"Policy violations: {policy_violations} > {self.policy_violations_max}")

        # Check tool errors
        if tool_errors > self.tool_errors_max:
            issues.append(f"Tool errors: {tool_errors} > {self.tool_errors_max}")

        # Check required metrics
        for metric, min_val in self.required_metrics.items():
            actual = metrics.get(metric, 0.0)
            if actual < min_val:
                issues.append(f"{metric}: {actual:.2f} < {min_val:.2f}")

        # Calculate quality score
        scores = []

        # Add required metrics scores
        for metric, min_val in self.required_metrics.items():
            actual = metrics.get(metric, 0.0)
            scores.append(min(actual / min_val, 1.0) if min_val > 0 else 1.0)

        # Add preferred metrics scores (only if actually recorded in trace)
        for metric, target in self.preferred_metrics.items():
            if metric in metrics:
                actual = metrics[metric]
                scores.append(min(actual / target, 1.0) if target > 0 else 1.0)

        # Penalty for tool errors
        if self.tool_errors_max > 0:
            error_score = 1.0 - (tool_errors / (self.tool_errors_max * 2))
            scores.append(max(0, error_score))

        # Calculate average score
        quality_score = sum(scores) / len(scores) if scores else 1.0

        # Check minimum quality score
        if quality_score < self.min_quality_score:
            issues.append(f"Quality score: {quality_score:.2f} < {self.min_quality_score:.2f}")

        # Determine grade
        grade = "F"
        if not hard_fail:
            for g, threshold in sorted(self.grade_thresholds.items(), key=lambda x: -x[1]):
                if quality_score >= threshold:
                    grade = g
                    break
            if grade == "F" and quality_score >= 0.65:
                grade = "D"

        # Pass if no hard fail and score meets minimum
        passed = not hard_fail and quality_score >= self.min_quality_score and len(issues) == 0

        return {
            "passed": passed,
            "hard_fail": hard_fail,
            "grade": grade,
            "quality_score": quality_score,
            "min_quality_score": self.min_quality_score,
            "policy_violations": policy_violations,
            "policy_violations_max": self.policy_violations_max,
            "tool_errors": tool_errors,
            "tool_errors_max": self.tool_errors_max,
            "metrics": metrics,
            "issues": issues,
        }


@dataclass
class BudgetConfig:
    """
    Complete budget configuration.

    Combines cost and quality budgets with scenario-specific overrides.
    """
    name: str = "default"
    version: str = "0.1"
    cost: CostBudget = field(default_factory=CostBudget)
    quality: QualityBudget = field(default_factory=QualityBudget)

    # Scenario-specific overrides
    scenarios: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def get_cost_budget(self, scenario: Optional[str] = None) -> CostBudget:
        """Get cost budget, with optional scenario override."""
        if scenario and scenario in self.scenarios:
            override = self.scenarios[scenario].get("cost", {})
            return CostBudget(
                tokens_max=override.get("tokens_max", self.cost.tokens_max),
                usd_max=override.get("usd_max", self.cost.usd_max),
                latency_p95_ms=override.get("latency_p95_ms", self.cost.latency_p95_ms),
            )
        return self.cost

    def get_quality_budget(self, scenario: Optional[str] = None) -> QualityBudget:
        """Get quality budget, with optional scenario override."""
        if scenario and scenario in self.scenarios:
            override = self.scenarios[scenario].get("quality", {})
            return QualityBudget(
                policy_violations_max=override.get("policy_violations_max", self.quality.policy_violations_max),
                tool_errors_max=override.get("tool_errors_max", self.quality.tool_errors_max),
                min_quality_score=override.get("min_quality_score", self.quality.min_quality_score),
                required_metrics=override.get("required_metrics", self.quality.required_metrics),
                preferred_metrics=override.get("preferred_metrics", self.quality.preferred_metrics),
            )
        return self.quality

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BudgetConfig":
        """Create BudgetConfig from dictionary."""
        cost_data = data.get("cost", {})
        quality_data = data.get("quality", {})

        cost = CostBudget(
            tokens_max=cost_data.get("tokens_max", 100000),
            usd_max=cost_data.get("usd_max", 1.0),
            latency_p95_ms=cost_data.get("latency_p95_ms", 30000.0),
        )

        quality = QualityBudget(
            policy_violations_max=quality_data.get("policy_violations_max", 0),
            tool_errors_max=quality_data.get("tool_errors_max", 0),
            min_quality_score=quality_data.get("min_quality_score", 0.8),
            required_metrics=quality_data.get("required_metrics", {}),
            preferred_metrics=quality_data.get("preferred_metrics", {}),
        )

        return cls(
            name=data.get("name", "default"),
            version=data.get("version", "0.1"),
            cost=cost,
            quality=quality,
            scenarios=data.get("scenarios", {}),
        )

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "BudgetConfig":
        """Load BudgetConfig from YAML or JSON file."""
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Budget config not found: {path}")

        content = path.read_text()

        if path.suffix in (".yaml", ".yml"):
            if not HAS_YAML:
                raise ImportError("PyYAML required for YAML config files: pip install pyyaml")
            data = yaml.safe_load(content)
        else:
            data = json.loads(content)

        return cls.from_dict(data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "cost": {
                "tokens_max": self.cost.tokens_max,
                "usd_max": self.cost.usd_max,
                "latency_p95_ms": self.cost.latency_p95_ms,
            },
            "quality": {
                "policy_violations_max": self.quality.policy_violations_max,
                "tool_errors_max": self.quality.tool_errors_max,
                "min_quality_score": self.quality.min_quality_score,
                "required_metrics": self.quality.required_metrics,
                "preferred_metrics": self.quality.preferred_metrics,
            },
            "scenarios": self.scenarios,
        }

    def to_yaml(self) -> str:
        """Convert to YAML string."""
        if not HAS_YAML:
            raise ImportError("PyYAML required: pip install pyyaml")
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


def get_default_budget_config() -> BudgetConfig:
    """Get the default budget configuration."""
    return BudgetConfig(
        name="default",
        version="0.1",
        cost=CostBudget(
            tokens_max=50000,
            usd_max=0.50,
            latency_p95_ms=15000.0,
        ),
        quality=QualityBudget(
            policy_violations_max=0,
            tool_errors_max=0,
            min_quality_score=0.8,
            required_metrics={
                "json_valid": 1.0,
            },
            preferred_metrics={
                "critique_closed": 0.9,
            },
        ),
        scenarios={
            "hello": {
                "cost": {
                    "tokens_max": 10000,
                    "usd_max": 0.10,
                },
            },
            "tool_retry": {
                "quality": {
                    "tool_errors_max": 1,  # Allow one retry
                },
            },
        },
    )
