# Environment & Configuration

## Supported Python Versions

| Python | Status |
|--------|--------|
| 3.10 | Tested in CI |
| 3.11 | Tested in CI |
| 3.12 | Tested in CI |
| 3.9 and below | Not supported |

## Operating Systems

- **Linux** — primary CI environment (Ubuntu latest)
- **macOS** — supported, used by maintainers
- **Windows** — supported (UTF-8 encoding fixes included)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HUAP_LLM_MODE` | `stub` | Set to `stub` for deterministic testing (no real API calls). Set to `live` to use real LLM providers. |
| `HUAP_ROUTER_ENABLED` | `0` | Set to `1` to enable the specialist model router (picks the best model per task). |
| `OPENAI_API_KEY` | — | Required only when `HUAP_LLM_MODE=live`. Not needed for stub mode, CI, or demos. |

## Stub Mode vs Live Mode

**Stub mode** (`HUAP_LLM_MODE=stub`, the default) replaces all LLM calls with deterministic canned responses. This is what CI uses, and what you should use for:

- Running the test suite (`pytest`)
- Running demos (`huap demo`, `huap flagship`)
- Trace replay and diff verification
- Golden baseline evaluation

**Live mode** (`HUAP_LLM_MODE=live`) makes real API calls to OpenAI (or a routed provider). Use this when you want actual LLM output. Requires `OPENAI_API_KEY` to be set.

## Dependencies

Core dependencies (installed automatically with `huap-core`):

- `click>=8.0` — CLI framework
- `pydantic>=2.0` — data models and validation
- `pyyaml>=6.0` — YAML graph spec parsing
- `openai>=1.0.0` — LLM client (used even in stub mode for type compatibility)

Dev dependencies (installed with `huap-core[dev]`):

- `pytest` + `pytest-asyncio` — test suite
- `ruff` — linting and formatting

Optional plugin packages:

- `hu-plugins-hindsight` — Hindsight memory backend (required for full test suite)
- `hu-plugins-cmp` — Commonplace toolpack
