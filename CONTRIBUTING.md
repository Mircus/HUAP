# Contributing to HUAP Core

Thank you for your interest in contributing to HUAP Core!

---

## Getting Started

1. Fork the repository
2. Clone your fork
3. Install development dependencies:

```bash
cd packages/hu-core
pip install -e ".[dev]"
```

---

## Development Workflow

### Run Tests

```bash
export HUAP_LLM_MODE=stub
pytest packages/hu-core/tests/
```

### Lint Code

```bash
ruff check packages/hu-core/
ruff format packages/hu-core/
```

### Build Package

```bash
cd packages/hu-core
pip install build
python -m build
```

---

## Pull Request Process

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes
3. Add tests for new functionality
4. Run tests and lint
5. Update documentation if needed
6. Submit a pull request

---

## Code Style

- Use type hints
- Follow PEP 8
- Document public APIs
- Keep functions small and focused

---

## Commit Messages

Use conventional commits:

```
feat: add new tool category
fix: correct hash normalization
docs: update getting started guide
test: add replay verification tests
```

---

## What We're Looking For

- Bug fixes
- Documentation improvements
- New example pods
- Performance improvements
- Test coverage

---

## What's Out of Scope

- Product-specific features (OAuth integrations, verticals)
- Breaking API changes without discussion
- Large refactors without prior approval

---

## Questions?

Open an issue for discussion before starting large changes.

---

**Thank you for contributing!**
