<!-- type: reference -->
# SOLID Refactor Compatibility Contract

This document defines which public interfaces are **frozen** during the
SOLID refactor described in [solid_refactor_backlog.md](solid_refactor_backlog.md).
No SOLID ticket may be merged if it violates a constraint listed here.

See also: [acceptance_criteria.md](acceptance_criteria.md),
[must_have.md](must_have.md), [should_have.md](should_have.md).

---

## Frozen Public Interfaces

### Classes

| Symbol | Constraints |
|---|---|
| `ForecastabilityAnalyzer` | Constructor signature, all public method names, and signatures are frozen. |
| `ForecastabilityAnalyzerExog` | Constructor signature, all public method names, and signatures are frozen. |

Both classes must remain importable as:

```python
from forecastability import ForecastabilityAnalyzer, ForecastabilityAnalyzerExog
```

### Dataclass

`AnalyzeResult` — all field names and types are frozen. New optional fields may
be added only if they carry a default value and do not alter existing field positions.

### Pipeline functions

Both functions in `forecastability.pipeline` are frozen by name and signature:

- `run_rolling_origin_evaluation`
- `run_exogenous_rolling_origin_evaluation`

### `__init__.py` exports

Every symbol listed in `src/forecastability/__init__.py` `__all__` is part of the
compatibility contract and **must not be renamed, removed, or re-typed**:

<details>
<summary>Full <code>__all__</code> listing (as of contract date)</summary>

```
AnalyzeResult, ar1_theoretical_ami,
BackendComparisonResult, BenchmarkDataConfig,
CanonicalExampleResult, CanonicalSummary, CMIConfig,
default_registry, DependenceScorer, Diagnostics,
ExogenousBenchmarkConfig, ExogenousBenchmarkResult,
ForecastabilityAnalyzer, ForecastabilityAnalyzerExog,
ForecastResult, generate_ar1, generate_white_noise,
InterpretationResult, MetricConfig, MetricCurve,
ModelConfig, OutputConfig,
RobustnessStudyConfig, RobustnessStudyResult, RollingOriginConfig,
SampleSizeStressResult, ScorerInfo, ScorerRegistry,
SensitivityConfig, SeriesEvaluationResult,
UncertaintyConfig, validate_time_series
```

</details>

### Notebook import patterns

Notebooks consume the public surface via patterns such as:

```python
from forecastability import (
    ForecastabilityAnalyzer,
    ForecastabilityAnalyzerExog,
    AnalyzeResult,
    CMIConfig,
    RollingOriginConfig,
    ...
)
```

These patterns must continue to resolve without error after any refactor commit.

---

## Notebook Freeze Rule

**Notebook files (`.ipynb`) must remain byte-for-byte unchanged throughout the
SOLID refactor.** A clean git-diff on any `.ipynb` is a hard requirement — not a
preference. Automatic formatting, cell reordering, or metadata changes are all
violations.

Scope: `notebooks/01_canonical_forecastability.ipynb`,
`notebooks/02_exogenous_analysis.ipynb`, and any future notebook files.

---

## Additive-Only Rule (MoSCoW: MUST)

All new internal code introduced during the refactor **must be additive**:

- **MUST** — introduce new modules (`services/`, `use_cases/`, `assemblers/`,
  `ports/`, `state.py`) without touching existing public symbols.
- **MUST** — delegate from the existing façade classes/functions to the new
  internal modules; do not replace the façade.
- **MUST NOT** — rename any public symbol.
- **MUST NOT** — remove any public symbol.
- **MUST NOT** — change any public method or constructor signature.
- **SHOULD** — keep new internal modules small, typed, and low-complexity.
- **COULD** — add optional fields to existing Pydantic/dataclass models when
  backward-compatible defaults are provided.

---

## Verification Gates

Every SOLID ticket is done only when all three gates pass without errors or
warnings:

```bash
uv run pytest -q -ra
uv run ruff check .
uv run ty check
```

In addition, the following must hold in the working tree before any commit:

- `git diff --name-only | grep '\.ipynb'` returns empty (no notebook changes).
- All symbols in `__all__` remain importable via the package root.
- Existing test assertions are unmodified (no test-deletes as a workaround).

---

## Relationship to Planning Files

| File | Role |
|---|---|
| [solid_refactor_backlog.md](solid_refactor_backlog.md) | Ticket-level tasks and implementation briefs |
| [acceptance_criteria.md](acceptance_criteria.md) | Baseline preservation and extension discipline |
| [must_have.md](must_have.md) | MoSCoW MUST items for the broader roadmap |
| [should_have.md](should_have.md) | MoSCoW SHOULD items |
| [could_have.md](could_have.md) | MoSCoW COULD items |
| This file | Frozen-interface contract enforced across all SOLID tickets |
