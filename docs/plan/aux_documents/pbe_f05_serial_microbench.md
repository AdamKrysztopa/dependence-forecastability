# PBE-F05 serial micro-benchmark — measured negative result

**Date:** 2026-05-01  
**Branch:** `feat/performance-improvement`  
**Machine:** local macOS, Python 3.11, `forecastability` 0.4.0 (plan-time)  
**Method:** identical synthetic input (`generate_white_noise(n=400, seed=42)`),
`n_jobs=1`, 5 repeats per call, `time.perf_counter()` median + min, sklearn warm.

## Significance bands (serial path)

| Path | Args | Before F05 (median / min) | After F05 (median / min) | Δ median |
| --- | --- | ---: | ---: | ---: |
| `compute_significance_bands` (legacy AMI) | `metric_name="ami"`, `max_lag=16`, `n_surrogates=99` | 1.6710 s / 1.6617 s | 1.6745 s / 1.6719 s | +0.2% |
| `compute_significance_bands_generic` (raw) | `which="raw"`, `max_lag=16`, `n_surrogates=99`, no exog | 1.6682 s / 1.6621 s | 1.6800 s / 1.6766 s | +0.7% |
| `compute_significance_bands_generic` (raw + exog) | `which="raw"`, `max_lag=16`, `n_surrogates=99`, exog white noise | 1.6779 s / 1.6691 s | 1.6909 s / 1.6882 s | +0.8% |
| `compute_significance_bands_generic` (partial) | `which="partial"`, `max_lag=8`, `n_surrogates=99` | 1.0859 s / 1.0855 s | 1.1024 s / 1.0998 s | +1.5% |
| `compute_significance_bands_transfer_entropy` | `max_lag=8`, `n_surrogates=99`, `min_pairs=50` | 1.1043 s / 1.0959 s | (parity-equivalent kernel; not re-measured) | n/a |

## Parent-process hotspot wall (n_jobs=-1 default)

| Target | Before | After | Δ |
| --- | ---: | ---: | ---: |
| `callable.forecastability.run_triage` (medium) | 4.1975 s | 4.3047 s | +2.55% |
| `callable.forecastability.triage.run_batch_triage` (medium) | 8.5330 s | 8.6450 s | +1.31% |
| `callable.use_cases.run_covariant_analysis.cross_ami` (medium) | 0.6635 s | 0.6277 s | −5.41% |

## Interpretation

PBE-F05 as scoped (preallocated result matrices, hoisted `_scale_series(exog)`,
hoisted parameter validation, prescaled inner-loop helper) does **not** meet
the wall-time budget defined in the plan (≥20% faster than the May 1 medians).
The deltas above are within run-to-run noise on the serial path and within
process-pool wait noise on the parallel path. The `cross_ami` modest improvement
is consistent with the exog-scaling hoist (one `_scale_series` call instead of
99 in the surrogate loop) but is the only visible effect.

The dominant serial cost is `sklearn.feature_selection.mutual_info_regression`
called `n_surrogates × max_lag` times per band (≈1.05 ms each → ≈1.66 s for
99 × 16 = 1584 calls). Parent-process timing under `n_jobs=-1` is dominated by
process-pool wait, exactly as the plan anticipated.

Per the F05 acceptance clause:

> If these budgets are not met, the PR must include serial or child-process
> profiles proving where the remaining cost lives before any broader rewrite
> is approved.

This file documents that evidence. The F05 changes still ship as **hygiene**:
they close a soft validation gap (`which`, `n_jobs`, `min_pairs`,
`exog.shape`), preallocate matrices for cleaner memory profile, factor out
`_compute_raw_curve_prescaled` / `_compute_partial_curve_prescaled` boundaries
that future PBE-F08/F12 deterministic parallel work can build on, and remain
**bit-identical** to the prior implementation under fixed seeds (the legacy
fixed-seed regression in `tests/test_surrogates.py` and the new generic
fixed-seed regression in `tests/test_significance_service.py` both pass).

## Next steps for measured speedup

A real >20% wall-time reduction on the legacy AMI/pAMI surrogate path requires
replacing sklearn's `mutual_info_regression` with a batched kNN MI kernel
(reuse Chebyshev neighbor structures across surrogates and/or horizons). That
work has significant semantic risk (must preserve the KSG estimand under
fixed-seed parity oracles) and is therefore deferred — it is **not** included
in this F05 PR. It should be tracked as a follow-up under the same release
plan once a parity test harness exists.
