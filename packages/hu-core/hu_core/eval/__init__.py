"""
HUAP Eval System - Budget gates and quality scoring.

Provides:
- BudgetConfig for cost/quality budget configuration
- TraceEvaluator for scoring traces against budgets
- SuiteRunner for batch evaluation
- EvalReport for structured results

Usage:
    from hu_core.eval import BudgetConfig, TraceEvaluator, SuiteRunner

    # Load budget config
    budget = BudgetConfig.from_file("budgets/default.yaml")

    # Evaluate a single trace
    evaluator = TraceEvaluator(budget)
    result = evaluator.evaluate("trace.jsonl", scenario="soma_plan")

    # Run a suite
    runner = SuiteRunner(budget)
    report = runner.run_suite("suites/smoke/")
    print(report.to_markdown())
"""
from .budgets import (
    BudgetConfig,
    CostBudget,
    QualityBudget,
    get_default_budget_config,
)
from .scoring import (
    TraceEvaluator,
    SuiteRunner,
    EvalResult,
    EvalReport,
)

__all__ = [
    # Budget configuration
    "BudgetConfig",
    "CostBudget",
    "QualityBudget",
    "get_default_budget_config",
    # Evaluation
    "TraceEvaluator",
    "SuiteRunner",
    "EvalResult",
    "EvalReport",
]
