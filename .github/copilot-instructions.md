<!-- type: reference -->
# GitHub Copilot Instructions

AMI → pAMI Forecastability Analysis — a Python 3.11 research package that reproduces
horizon-specific AMI from the referenced paper and extends it with pAMI.

**Be concise and direct. Write code to disk without explanation unless asked. Warn about statistical violations or data-leakage risks before implementing.**

For Python-specific rules (typing, engineering patterns, testing), see [coder.instructions.md](./instructions/coder.instructions.md).
For the multi-agent workflow and stage-gate sequence, see [AGENT_FLOW.md](./AGENT_FLOW.md).

---

## Tech Stack

- **Python 3.11** with full type hints
- **numpy / pandas** for all numeric and tabular work — vectorised idioms, no hand-written loops
- **scikit-learn** kNN MI estimator (`n_neighbors=8`, `random_state: int`)
- **Pydantic** for config models and result containers
- For structured payloads/schemas, prefer Pydantic models over raw `dict`, `TypedDict`, or `dataclass`
- **matplotlib** for all figures (save to `outputs/figures/`)
- **PyYAML** for config loading from `configs/`
- **pytest** exclusively for testing

## Tooling

- **`uv`** for all dependency operations — never `pip`, `poetry`, or `conda`
- **`ruff`** for lint and format — never `black`, `isort`, or `flake8`
- **`ty`** for type checking — never `mypy` or `pyright`
- **Context7 MCP** for library docs — use it first for dependency and framework APIs; fall back to official upstream sources only when Context7 does not cover the library

## External Documentation Policy

- Resolve third-party library and framework questions through **Context7 MCP first**
- The Context7 API key is expected to be loaded from `.env` into the environment; never hardcode, print, or commit secrets
- If Context7 is unavailable for a dependency-critical change, say so explicitly instead of pretending the docs were verified
- When Context7 and upstream docs disagree, prefer the primary upstream docs for the final decision and note the discrepancy

## Architecture

- Follow **SOLID and hexagonal architecture**
- Keep deterministic forecastability logic separate from infrastructure concerns
- Domain code must not depend on plotting, CLI, persistence, APIs, MCP, agent frameworks, or environment access
- Use cases orchestrate domain behavior through ports; adapters isolate frameworks and external libraries
- Entrypoints and scripts should wire dependencies, not hold business rules
- Preserve the public contract in [docs/plan/solid_refactor_contract.md](../docs/plan/solid_refactor_contract.md)
- Prefer additive, migration-safe refactors behind existing facades

## Configuration

- Secrets and keys live in `.env`
- Access environment configuration through a dedicated settings layer
- Never hardcode secrets, tokens, endpoints, or model names inline

## Commands

```bash
uv sync                          # install dependencies
uv run ruff check .              # lint
uv run ruff format .             # format
uv run ty check                  # type check
uv run pytest                    # run tests
```

## Test Command Policy

- Run pytest directly; do not pipe pytest output through `grep`.
- Preferred compact command: `uv run pytest -q -ra`
- Do not use commands like `uv run pytest ... | grep ...` because they can suppress output and produce false "No output was produced by the command" messages.

## Agents

Custom agents are defined in `.github/agents/`. Use `@orchestrator` for end-to-end tasks.

| Agent | File | Invoke when… |
|---|---|---|
| `orchestrator` | `agents/orchestrator.agent.md` | Driving a full feature or pipeline stage end-to-end |
| `coder` | `agents/coder.agent.md` | Writing or editing Python source, tests, configs |
| `tester` | `agents/tester.agent.md` | Running lint, type-check, and tests; confirming stage gates |
| `statistician` | `agents/statistician.agent.md` | Auditing metrics, surrogates, rolling-origin, hypotheses |
| `analyst` | `agents/analyst.agent.md` | Running scripts and interpreting outputs |
| `reporter` | `agents/reporter.agent.md` | Writing `outputs/reports/` markdown |
| `documenter` | `agents/documenter.agent.md` | Authoring `docs/`, Mermaid diagrams, ADRs, MkDocs config |
| `software_architect` | `agents/software_architect.agent.md` | Reviewing generic code quality, architecture, and refactor plans |

Path-scoped instructions (auto-injected by Copilot based on file glob):

| File | Applies to |
|---|---|
| `instructions/coder.instructions.md` | `src/**`, `tests/**`, `scripts/**`, `configs/**` |
| `instructions/statistician.instructions.md` | `src/forecastability/**`, `tests/**` |
| `instructions/analyst.instructions.md` | `scripts/**`, `outputs/**`, `configs/**` |
| `instructions/reporter.instructions.md` | `outputs/reports/**` |
| `instructions/documenter.instructions.md` | `docs/**`, `README.md`, `.github/**/*.md` |
| `instructions/software_architect.instructions.md` | `src/**`, `tests/**`, `scripts/**`, `configs/**`, `pyproject.toml` |
