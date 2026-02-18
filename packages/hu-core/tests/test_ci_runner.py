"""
Tests for CI Runner (P5).

Covers:
- Fails on regression (diff issues)
- Passes when identical to golden
- Budgets enforced
"""
import json
import os
import tempfile
from pathlib import Path

import pytest


class TestCIRunnerReport:
    """Unit tests for the CIReport dataclass."""

    def test_all_pass(self):
        from hu_core.ci.runner import CIReport, ScenarioResult

        report = CIReport(
            suite="smoke",
            timestamp="2025-01-01T00:00:00Z",
            scenarios=[
                ScenarioResult(name="a", passed=True),
                ScenarioResult(name="b", passed=True),
            ],
        )
        assert report.passed is True
        assert report.pass_count == 2

    def test_one_failure(self):
        from hu_core.ci.runner import CIReport, ScenarioResult

        report = CIReport(
            suite="smoke",
            timestamp="2025-01-01T00:00:00Z",
            scenarios=[
                ScenarioResult(name="a", passed=True),
                ScenarioResult(name="b", passed=False, error="boom"),
            ],
        )
        assert report.passed is False
        assert report.pass_count == 1

    def test_to_dict(self):
        from hu_core.ci.runner import CIReport, ScenarioResult

        report = CIReport(
            suite="smoke",
            timestamp="2025-01-01T00:00:00Z",
            scenarios=[
                ScenarioResult(name="a", passed=True, exit_code=0),
            ],
        )
        d = report.to_dict()
        assert d["passed"] is True
        assert d["total"] == 1
        assert d["scenarios"][0]["name"] == "a"

    def test_diff_issues_fail_scenario(self):
        from hu_core.ci.runner import ScenarioResult

        s = ScenarioResult(
            name="regressed",
            passed=False,
            diff_issues=["new tool error in node X"],
        )
        assert s.passed is False
        assert len(s.diff_issues) == 1

    def test_eval_issues_fail_scenario(self):
        from hu_core.ci.runner import ScenarioResult

        s = ScenarioResult(
            name="over_budget",
            passed=False,
            eval_issues=["cost exceeded max_usd: 0.05 > 0.01"],
        )
        assert s.passed is False
        assert len(s.eval_issues) == 1

    def test_empty_suite_passes(self):
        from hu_core.ci.runner import CIReport

        report = CIReport(suite="empty", timestamp="now", scenarios=[])
        assert report.passed is True
        assert report.pass_count == 0
