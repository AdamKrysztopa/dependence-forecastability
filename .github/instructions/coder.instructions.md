---
applyTo: "src/**,tests/**,scripts/**,configs/**,pyproject.toml"
---
<!-- type: reference -->

# Coder Agent

You are the implementation agent for the AMI → pAMI Forecastability Analysis project.
Your role is to write, edit, and refactor all Python source code, tests, and configuration
files according to the engineering rules and repository structure defined in the project plan.

## Tooling constraints

- **Python 3.11** — no f-strings with walrus, no 3.12+ syntax
- **`uv`** for dependency management — never use `pip`, `poetry`, or `conda`
- **`ruff`** for linting and formatting — never introduce `black`, `isort`, or `flake8`
- **`ty`** for type checking — never introduce `mypy` or `pyright`
- During implementation, prefer the smallest relevant pytest target for the behavior you changed
- Reserve the repository-wide `uv run pytest -q -ra` run for explicit final verification or when the user asks for it
- Use **Context7 MCP first** when you need dependency, framework, or library documentation
- Assume the Context7 API key is loaded from `.env`; never hardcode, log, or commit secrets
- If Context7 cannot verify an API you are changing, fall back to the primary upstream docs and say that you did so
- Do not wrap pytest in shell plumbing such as `2>&1`, `| tail -20`, `| grep`, `| head`, `| tee`, or redirections; rely on pytest output and exit status directly

## Repository structure

```text
src/forecastability/
├── __init__.py
├── config.py          # Pydantic config models
├── types.py           # Pydantic schema and result models
├── validation.py      # Input validation helpers
├── datasets.py        # Canonical series loaders
├── metrics.py         # compute_ami, compute_pami_linear_residual
├── surrogates.py      # phase_surrogate, surrogate_bands
├── rolling_origin.py  # RollingOriginSplit, generate_splits
├── models.py          # ETS, naive, and seasonal naive wrappers
├── aggregation.py     # cross-series aggregation and tercile logic
├── interpretation.py  # InterpretationResult, pattern_classify
├── plots.py           # all matplotlib figure builders
├── reporting.py       # report and LinkedIn post generators
└── pipeline.py        # canonical example end-to-end runner

scripts/
├── run_canonical_triage.py
├── run_benchmark_panel.py
└── build_report_artifacts.py

configs/
├── canonical_examples.yaml
├── benchmark_panel.yaml
└── interpretation_rules.yaml
```

## Implementation run order

Complete tasks in this order — each builds on the previous:

| Task | Modules |
|------|---------|
| 1 | `validation.py`, `config.py`, `types.py` |
| 2 | `metrics.py`, `surrogates.py` + tests |
| 3 | `datasets.py`, `pipeline.py`, `plots.py`, `reporting.py` |
| 4 | `aggregation.py`, `interpretation.py` + canonical scripts |
| 5 | `rolling_origin.py`, `models.py` + benchmark runner |
| 6 | `build_report_artifacts.py`, LinkedIn output, finalise tests |

## Engineering rules

- Type hints on every function signature — no `Any` without a comment
- Google-style docstrings on every public function and class
- No blind `except Exception` — catch specific exceptions only
- Cognitive complexity ≤ 7 per function; split helpers into private `_` functions
- No boolean positional arguments — use keyword-only args with `*`
- Avoid long `try` blocks — wrap only the call that can raise
- Deterministic random state: accept `random_state: int` parameters, never `numpy.Generator`
- Use Pydantic `BaseModel` (or `RootModel` when appropriate) for structured data containers
- Avoid generic `dict`/`TypedDict`/`dataclass` for domain schemas, configs, and result payloads
- All artifacts saved to `outputs/` subdirectories; never write to `src/` or `tests/`
- Reproducibility through YAML config files; hardcoded constants are a code smell
- Treat code quality as **SOLID plus hexagonal architecture**
- Preserve all frozen public interfaces and notebook invariants (frozen `__all__` exports, backward-compatible signatures)
- Keep dependency direction inward: `adapters -> ports -> use_cases -> domain`
- Do not let domain or use-case code depend directly on CLI, filesystem, plotting, or third-party transport concerns
- Prefer constructor-injected collaborators behind narrow interfaces over hidden global coupling
- Keep existing facade entry points stable while moving internal behavior behind use cases and adapters

## Hexagonal implementation target

- `domain/` holds business rules, invariants, and pure calculations
- `use_cases/` coordinates application workflows and enforces sequencing
- `ports/` defines the interfaces required by the use cases
- `adapters/` implements filesystem, plotting, config loading, and external-library integration
- Existing public classes and package-level functions remain the stable facade until the refactor is complete

When adding or moving logic, prefer extraction in this order:
1. Isolate pure domain logic first.
2. Wrap side effects behind a port.
3. Move orchestration into a use case.
4. Keep the legacy public API delegating into the new seam.

## Critical implementation rules

### metrics.py
- AMI computed **per horizon h separately** using kNN MI estimator with `n_neighbors=8`
- `min_pairs=30` for `compute_ami`, `min_pairs=50` for `compute_pami_linear_residual`
- `random_state` must be an `int` — sklearn 1.8 does not accept `numpy.Generator` objects
- Use `np.trapezoid` for AUC (NOT `np.trapz` — removed in NumPy 2.x)

### surrogates.py
- Surrogates are **phase-randomised** (FFT amplitude-preserving) — preserve power spectrum
- `n_surrogates ≥ 99`; both `lower_band` and `upper_band` must be populated
- Significance bands: 2.5th and 97.5th percentiles (α = 5%, two-sided)

### rolling_origin.py
- `split.origin_index == split.train.size` for every split — verify this invariant
- `split.test.size == horizon` for every split
- AMI and pAMI must be computed on `split.train` **only** — never on the full series

### interpretation.py
- Patterns A–E must match exactly:
  - **A**: AMI high + pAMI high → rich structured models justified
  - **B**: AMI high + pAMI low/medium → mediated dependence → compact models
  - **C**: AMI medium → uncertain → seasonal or regularised models
  - **D**: AMI low + pAMI low → both weak → baseline methods
  - **E**: AMI high but sMAPE ≥ naive → exploitability mismatch → investigate

### config.py
- All threshold constants (`auc_high_threshold`, `directness_high_threshold`, etc.)
  must be loaded from `configs/interpretation_rules.yaml` — not hardcoded

## Test requirements

Required test files in `tests/`:

| File | Coverage |
|------|----------|
| `test_validation.py` | Input validators, edge cases, type errors |
| `test_metrics.py` | AMI output shape, pAMI residualisation sanity |
| `test_surrogates.py` | Band coverage, n_surrogates constraint |
| `test_rolling_origin.py` | Origin invariant, test size, no leakage |
| `test_interpretation.py` | Pattern A–E classification, directness_ratio bounds |
| `test_pipeline.py` | Sine wave has high AMI; stock returns have low AMI |

Behavioural tests (must pass):
- Sine wave: `forecastability_class == 'high'`
- Stock returns (simulated IID): `forecastability_class == 'low'`
- Structured examples: `n_sig_pami <= n_sig_ami` for sine and air_passengers

## Common pitfalls to avoid

- `np.trapz` → use `np.trapezoid` (NumPy ≥ 2.0)
- Passing `numpy.Generator` as `random_state` to sklearn → pass `int` instead
- Computing AMI inside rolling-origin loop on full series → leakage
- Hardcoding thresholds instead of loading from YAML
- `directness_ratio > 1.0` → numerical issue; add a diagnostic warning
- Missing `__init__.py` exports causing import errors in scripts
```
