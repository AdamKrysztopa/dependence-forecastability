<!-- type: reference -->
# ADR-001: Batched Phase-Surrogate Generation and Evaluation Design

## Status

Accepted

## Context

Phase-surrogate significance bands are computed in `run_triage`, `run_covariant_analysis`,
and `run_lagged_exogenous_triage`. The procedure generates `n_surrogates` synthetic null
time series by randomizing FFT phases, scores each surrogate through the AMI or cross-AMI
lag profile, then takes a percentile threshold to form the significance band.

The current implementation in `compute_significance_bands_generic`:

1. Generates surrogates one at a time in a serial loop.
2. For each surrogate, runs the full pipeline: FFT → uniform random phase draw
   (conjugate-symmetric) → inverse FFT → real part → AMI/lag profile.
3. Collects all surrogate profiles into a matrix and computes a percentile threshold.

**Observed bottleneck.** The serial loop re-enters the KSG estimator `n_surrogates` times
with a single `(past, future)` pair. The kNN index is rebuilt on every call. For
`n_surrogates=199` and `max_lag=30` on a 1,000-sample series, this produces 5,970 separate
kNN evaluations, each constructing and querying an independent index.

**Open design questions before any batched refactor:**

- Must the exact phase-randomization null be preserved?
- Should the surrogate matrix be materialized in full or streamed?
- For covariate analysis: can the same target-series surrogates be reused across multiple
  drivers, or does that introduce Monte Carlo dependence between per-driver p-values?
- The `DependenceScorer` callback interface is scalar, not batch — how should a batched
  kernel compose with it?

## Decision

**1. Do not reuse target surrogates across drivers by default.**

Each driver's significance band draws independent phase surrogates of the target series.
Reusing the same target-surrogate stream for driver A and driver B introduces Monte Carlo
dependence between their null distributions: the per-driver p-values are no longer
independent, making joint interpretation unreliable with standard per-driver thresholds.

> [!WARNING]
> Shared target-surrogate reuse is only permissible if the metadata field
> `common_target_surrogate_stream: bool` is explicitly set to `True` in the
> significance-band result and interpretation rules are updated to use a joint significance
> threshold rather than per-driver thresholds.

**2. Preserve the exact phase-surrogate null exactly.**

Any batched implementation must reproduce the existing null procedure without approximation:
real FFT → uniform phase draw on [0, 2π] (conjugate-symmetric) → inverse FFT → real part.
No relaxation of this null is acceptable unless accompanied by fixture rebuilds and a
Monte Carlo parity gate confirming distributional equivalence.

> [!IMPORTANT]
> A fixed-seed batched run must match the existing significance bands within floating-point
> tolerance for the same `random_state`. This is the acceptance criterion for any future
> implementation of PBE-F23 (batched kNN MI kernel).

**3. Prefer full matrix materialization at current scale.**

For `n_surrogates <= 499`, the full surrogate-profile matrix is materialized before
percentile computation because:

- Memory cost is modest: `199 × 30 × float64 ≈ 48 KB` per `(target, driver)` pair.
- Full materialization enables vectorized percentile computation via NumPy.
- Streaming yields a benefit only when `n_surrogates > 1000` or when profiling identifies
  materialization as a memory bottleneck — neither is currently true.

**4. Batched kNN MI evaluation is not yet implemented.**

The batched kNN kernel that would process all surrogates for a given lag in a single
index-build-and-query pass is tracked in PBE-F23. This ADR records the design constraints
so that the future implementation is built on a correct statistical foundation.

**5. `common_target_surrogate_stream` metadata flag.**

If a future implementation reuses target surrogates across drivers for performance reasons,
the significance-band result metadata must carry `common_target_surrogate_stream: True`.
Interpretation logic must then emit a warning when per-driver p-values are interpreted
against independent thresholds.

## Consequences

**Statistical correctness vs generation cost.**
Independent surrogate draws per driver are statistically clean: each driver's null
distribution is drawn independently. The cost is `O(n_drivers × n_surrogates)` surrogate
generation and scoring. A shared surrogate stream halves generation cost for two-driver
analysis but couples the null distributions — acceptable only with the metadata flag and
updated interpretation rules.

**Batched kNN semantics.**
When PBE-F23 is implemented, it must preserve KSG neighbor semantics exactly, including
tie-breaking behavior and the `k` parameter. Any deviation invalidates comparisons with
non-batched runs and requires fixture rebuilds.

**`common_target_surrogate_stream=True` triggers cascade.**
If this flag is ever set to `True` in a release:

- All regression fixture snapshots that compare per-driver significance values must be
  rebuilt.
- The regression test suite must be updated to permit the resulting numerical differences.
- The interpretation rules in `configs/interpretation_rules.yaml` must be updated to warn
  on joint comparisons.

> [!NOTE]
> The default is `common_target_surrogate_stream=False`. No fixture rebuild is needed
> unless this default is changed.

**Streaming surrogates (future).**
If surrogate streaming is later introduced — for example to cap peak memory in long-series
or high-`n_surrogates` scenarios — streaming must still respect the phase-randomization
null exactly and must carry the same `random_state` reproducibility guarantee.
