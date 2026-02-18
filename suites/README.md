# HUAP Test Suites

This directory contains support files for CI evaluation.

## Structure

```
suites/
└── smoke/              # Quick smoke test support files
    ├── diff_policy.yaml
    ├── budgets.yaml
    └── README.md
```

## Smoke Suite

The `smoke/` suite contains configuration for quick regression checks:

| File | Description |
|------|-------------|
| `diff_policy.yaml` | Thresholds for regression detection |
| `budgets.yaml` | Cost/quality budgets for evaluation |

## Running Tests

### Local

```bash
# Run the hello workflow and produce a trace
export HUAP_LLM_MODE=stub
huap trace run hello examples/graphs/hello.yaml --out traces/hello.jsonl

# Replay and verify determinism
huap trace replay traces/hello.jsonl --mode exec --verify

# Evaluate the trace
huap eval trace traces/hello.jsonl
```

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
