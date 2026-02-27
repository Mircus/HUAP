# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x (beta) | Yes |

## Reporting a Vulnerability

If you discover a security vulnerability in HUAP, please report it responsibly:

1. **Do NOT open a public issue.**
2. Email **security@huap.dev** with:
   - A description of the vulnerability
   - Steps to reproduce
   - Impact assessment (if known)
3. You will receive an acknowledgement within 48 hours.
4. We will work with you to understand the scope and develop a fix before any public disclosure.

## Scope

HUAP Core is a local-first framework. The primary attack surface includes:

- **Graph execution** — user-supplied YAML specs and `run:` import paths
- **Safe eval** — AST-based condition evaluator (no `exec`/`eval` of arbitrary code)
- **Trace files** — JSONL output that may contain sensitive data from agent runs
- **Plugin loading** — dynamic imports from plugin packages

## Best Practices

- Never commit API keys or credentials to trace files
- Use `HUAP_LLM_MODE=stub` for CI and testing (no real API calls)
- Review `run:` import paths in YAML specs before executing untrusted graphs
