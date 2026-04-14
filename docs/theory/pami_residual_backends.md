<!-- type: explanation -->
# pAMI Residual Backends: Trade-offs and Failure Modes

This page explains how residual backends affect pAMI estimates in this project.

## Scope

- AMI remains paper-aligned.
- pAMI remains a project extension based on residualization + nonlinear MI.
- Backend comparison is diagnostic, not proof that one backend is universally superior.

## Available residual backends

| Backend | Strengths | Limitations | Best use |
|---|---|---|---|
| `linear_residual` | Fast, stable, interpretable baseline | Misses nonlinear mediation | Default benchmark and production-safe baseline |
| `rf_residual` | Captures nonlinear interactions with moderate tuning burden | Higher variance and compute than linear | Nonlinear systems where linear residualization under-fits |
| `extra_trees_residual` | Strong nonlinear fit with variance reduction from randomized splits | Can still overfit noisy short series; less interpretable | Stress-testing nonlinear mediation robustness |

## Benchmark comparison path (against linear baseline)

Use the robustness study pipeline to compare all configured backends against `linear_residual`.

1. Configure backends in `configs/robustness_study.yaml`.
2. Run `MPLBACKEND=Agg uv run python scripts/archive/run_robustness_study.py`.
3. Inspect `outputs/tables/robustness_backend_comparison.csv`.

The backend table includes direct deltas versus linear baseline:

- `auc_pami_delta_vs_linear`
- `directness_ratio_delta_vs_linear`
- `n_sig_pami_delta_vs_linear`

Interpret these as effect-size diagnostics, not absolute truth.

## Failure modes to monitor

| Failure mode | Observable symptom | Typical cause | Mitigation |
|---|---|---|---|
| Numerical inflation | `directness_ratio > 1.0` | estimator instability, finite-sample effects | Treat as warning; verify with multiple backends and sample-size stress |
| Short-sample fragility | large backend deltas on small fractions | insufficient support for residualization | enforce minimum length and inspect stress table stability |
| Overfitting in nonlinear backends | sharp pAMI spikes at isolated lags only for tree backends | backend fits noise in conditioning space | compare against linear baseline and require ranking stability |
| False confidence from one backend | decision changes when backend changes | model class mismatch or noisy data | require cross-backend agreement before acting on lag recommendations |

## Decision guidance

- Keep `linear_residual` as baseline for all backend studies.
- Prefer stable lag rankings and small directness-ratio range over raw pAMI magnitude.
- Escalate only when nonlinear backends improve diagnostic consistency across datasets.
