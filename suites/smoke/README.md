# Smoke Suite

This directory contains baseline traces for CI regression testing.

## Usage

```bash
# Record a new baseline
export HUAP_LLM_MODE=stub
huap trace run hello sequential --out suites/smoke/hello_baseline.jsonl

# Replay and verify
huap trace replay suites/smoke/hello_baseline.jsonl --mode exec --verify

# Diff against candidate
huap trace diff suites/smoke/hello_baseline.jsonl runs/candidate.jsonl
```

## Files

- `hello_baseline.jsonl` - Baseline trace for hello-pod
- `diff_policy.yaml` - Thresholds for regression detection
- `budgets.yaml` - Cost/quality budgets for evaluation

## CI Integration

```yaml
# GitHub Actions example
- name: Run smoke tests
  run: |
    export HUAP_LLM_MODE=stub
    huap trace replay suites/smoke/hello_baseline.jsonl --verify
```
