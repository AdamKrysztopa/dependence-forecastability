<!-- type: reference -->
# ADR-002: Completing the Hexagonal Migration — Dissolving Legacy Flat Packages into the Rings

## Status

Accepted

Date: 2026-06-17

Branch: `refactor/finish-hex-migration`

## Context

The v0.5.0 review-hardening release (commit `507b64c`) introduced the hexagonal
ring folders — `domain/`, `ports/`, `services/`, `use_cases/`, `api/`, and
`adapters/` — under `forecastability/`. That work created the *shape* of a
hexagonal architecture but did not finish the move: roughly 19k LOC still live
in the legacy flat packages `metrics/`, `kernels/`, `pipeline/`, `reporting/`,
`triage/`, `diagnostics/`, and `utils/`.

The unfinished state is worse than cosmetic. The legacy packages and the rings
are in **mutual-import cycles** — rings import legacy modules and legacy modules
import rings — so the hexagonal dependency rule (dependencies point inward only;
`domain/` and `ports/` import no first-party code outward) is violated in *both*
directions.

The architecture boundary test (`tests/test_architecture_boundaries.py`) did not
catch this. It checked only that the rings avoid forbidden **external** infra
imports; it never inspected **first-party** edges between rings and legacy
packages, so the cycles leaked through unflagged. The full diagnosis is recorded
in [`docs/architecture-review-2026-06-17.md`](../architecture-review-2026-06-17.md).

> [!IMPORTANT]
> The boundary test's blind spot — external-only checks — is the root reason the
> v0.5.0 hex shape passed CI while the dependency rule was being violated. Closing
> that gap (first-party outward-import detection plus layer-cycle detection) is the
> terminal slice of this migration, not an optional extra.

## Decision

Complete the migration using the **Strangler-Fig** pattern: dissolve the legacy
flat packages into the rings **incrementally, one import cycle per slice**, with
CI green after every slice. Public legacy import paths keep **deprecation shims**
(the established `triage/lyapunov.py` shim pattern) through **v0.6.0**.

> [!WARNING]
> Do **not** change `api/__init__.py` exported symbol identities or its `__all__`.
> The public-API surface is frozen for the duration of this migration; only the
> internal physical location of implementations moves.

### Target module map

This map is the authoritative destination for every legacy module.

#### `kernels/`

- `kernels/` → `adapters/kernels/` — pure-compute adapters implementing the
  `ports.kernels` protocols.

#### `metrics/`

- Estimator core (`compute_ami`, `compute_pami_linear_residual`, `_lag_design`)
  → `services/`.
- Scorer `Protocol` and types (`DependenceScorer`, `ScorerInfo`)
  → `ports/scorers.py`.
- Registry + concrete scorers → `services/scorers.py`.

#### `pipeline/`

- `analyzer`, `pipeline`, `rolling_origin` → `use_cases/`. The Pipe-and-Filter
  shape is preserved verbatim; only the location changes.

#### `triage/`

- The 12 files that are already domain shims stay as-is.
- `extended_forecastability.py` models → `domain/models/`.
- `batch_models.py` → `domain/models/`.
- `comparison_report.py` (assembly) → `use_cases/`.
- `lag_aware_mod_mrmr.py` → `services/`.
- `triage/__init__.py` stays a thin public facade.

#### `diagnostics/`

- Estimator math (`cmi`, `cmi_ksg`, `gcmi`, `knn_cmi_ci_test`,
  `predictive_information_gain`, `surrogates`, `spectral_utils`)
  → `services/diagnostics/`.
- `*_regression.py` validation harnesses → `use_cases/diagnostics/`.

#### `reporting/`

- `reporting/` → `adapters/reporting/` — matplotlib / Markdown presentation.
- The interpretation rule → `services/`, implementing `InterpretationPort`.

#### `utils/` (split by dependency direction)

- **True leaf** (`aggregation`, `datasets`, `reproducibility`, `state`,
  `synthetic`) → new `forecastability/shared/`.
- `plots` → `adapters/`.
- **Domain-aware** (`types`, `validation`, `config`, `io_models`, `robustness`)
  relocate inward (`domain/value_objects`, `use_cases`, `adapters`) with shims at
  the old public paths.

#### `ports/` inversions

- Scorer contracts move **into** `ports/`.
- `TriageEvent` and result value-objects repoint to `domain/`.

### Slice order

| Slice | Scope |
|---|---|
| **S0** | Guardrail + this ADR. |
| **S1** | `domain/` ← `triage` models (including the `utils.types` repoint). |
| **S2** | `utils/` split (leaf → `shared/`; plots → `adapters/`; domain-aware inward). |
| **S3** | `ports/` inversions (scorer contracts in; `TriageEvent` + result VOs repoint to `domain/`). |
| **S4** | `services/` ↔ `diagnostics`/`metrics`/`triage` + `use_cases/` ↔ `pipeline`. |
| **S5** | Cycle-detection enforced: un-`xfail` the boundary test and remove the `comparison_report.py` boundary-test TODO exclusion. |

## Consequences

**Independently testable ring core.** Once the cycles are broken, `domain/` and
`ports/` import no first-party code outward, so the ring core can be unit-tested
without dragging in legacy packages. The boundary test is upgraded to enforce
two new invariants: (a) no first-party outward imports from `domain/` and
`ports/`, and (b) no layer cycles anywhere in the ring graph.

**Cost: shim maintenance through v0.6.0.** Every public legacy import path carries
a deprecation shim until v0.6.0. This is deliberate churn — large but mechanical,
done one slice at a time, with CI green after each slice.

> [!NOTE]
> The migration touches a lot of files but changes no behavior. The churn is
> physical relocation plus shims, not redesign.

### Invariants preserved (verbatim)

- Frozen-Pydantic boundaries — unchanged at every public boundary.
- Serial-vs-parallel determinism — `SeedSequence.spawn` propagation and bit
  identity preserved.
- No math, estimator, or numeric change of any kind.
- Public-API names frozen — `api/__init__.py` symbol identities and `__all__`
  unchanged.

### Deferred (non-gating)

`pipeline/analyzer.py`'s direct `import adapters` → constructor port injection is
a **behavior-preserving follow-up**. It is explicitly out of scope for this
migration and does not gate any slice.

> [!IMPORTANT]
> S5 is the only slice that flips an enforcement gate. Until S5 lands, the
> boundary test may legitimately `xfail` on first-party cycles; after S5 those
> cycles must be gone and the gate is hard.
