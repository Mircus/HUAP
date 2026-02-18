# Smoke Suite

This directory contains CI support files for smoke testing.

## Usage

```bash
# Record a baseline trace
export HUAP_LLM_MODE=stub
huap trace run hello examples/graphs/hello.yaml --out traces/hello.jsonl

# Replay and verify determinism
huap trace replay traces/hello.jsonl --mode exec --verify

# Diff against a candidate run
huap trace diff traces/hello.jsonl traces/candidate.jsonl
```

## Files

- `diff_policy.yaml` — Thresholds for regression detection
- `budgets.yaml` — Cost/quality budgets for evaluation

## CI Integration

```yaml
# GitHub Actions example
- name: Run smoke tests
  run: |
    export HUAP_LLM_MODE=stub
    huap trace run hello examples/graphs/hello.yaml --out /tmp/smoke.jsonl
    huap trace replay /tmp/smoke.jsonl --mode exec --verify
```
