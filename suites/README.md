# HUAP Test Suites

This directory contains trace files for CI evaluation.

## Structure

```
suites/
├── smoke/              # Quick smoke tests (run on every PR)
│   ├── soma_plan.trace.jsonl
│   └── tool_success.trace.jsonl
├── integration/        # Full integration tests
└── regression/         # Regression test baselines
```

## Smoke Suite

The `smoke/` suite contains minimal tests that verify core functionality:

| Trace | Description | Budget Scenario |
|-------|-------------|-----------------|
| `soma_plan.trace.jsonl` | SOMA workout plan generation | `soma_plan` |
| `tool_success.trace.jsonl` | Basic tool execution | default |

## Running Tests

### Local

```bash
# Run smoke suite
huap ci check suites/smoke --budgets budgets/default.yaml

# Evaluate a single trace
huap eval trace suites/smoke/soma_plan.trace.jsonl --scenario soma_plan

# View trace events
huap trace view suites/smoke/soma_plan.trace.jsonl
```

### CI

Tests run automatically on pull requests via GitHub Actions.
See `.github/workflows/huap-ci.yml`.

## Adding New Tests

1. **Record a trace:**
   ```bash
   huap trace run <pod> <graph> --out suites/smoke/<name>.trace.jsonl
   ```

2. **Verify it passes:**
   ```bash
   huap eval trace suites/smoke/<name>.trace.jsonl
   ```

3. **Commit as baseline:**
   ```bash
   git add suites/smoke/<name>.trace.jsonl
   git commit -m "Add <name> smoke test"
   ```

## Budget Scenarios

Scenarios can be specified per-trace to apply different budget thresholds:

- `soma_plan` - Stricter limits for SOMA generation (10K tokens, $0.10)
- `tool_retry` - Allows one tool error (for retry testing)
- `complex_analysis` - Higher limits for complex workflows

See `budgets/default.yaml` for full configuration.
