<!-- type: explanation -->
# Classical Structure Features

Classical structure features are the cheap decomposition-style summaries inside
the AMI-first extended fingerprint. They summarize autocorrelation, trend, and
optional sample-period seasonality without claiming to be a full forecasting
decomposition.

> [!IMPORTANT]
> This block is explanatory. It can clarify whether forecastability appears to
> align with trend, seasonality, or short-memory structure, but it does not
> replace AMI geometry and it does not identify a winning downstream model.

## What It Measures

The shipped `ClassicalStructureResult` exposes the following public fields.

| Field | Meaning | Conservative reading |
| --- | --- | --- |
| `acf1` | Lag-1 autocorrelation when it can be computed safely | A quick short-memory signal, not a full dependence model |
| `acf_decay_rate` | Early-lag autocorrelation decay summary | Read as a coarse shape indicator |
| `seasonal_strength` | Optional seasonality strength on the detrended series | Only available when `period` is supplied and usable |
| `trend_strength` | Variance-explained strength of a deterministic linear trend | High values can mean nonstationary drift rather than useful forecastability |
| `residual_variance_ratio` | Variance remaining after the lightweight deterministic summaries are removed | Lower values mean the cheap structure summaries explain more variance |
| `stationarity_hint` | Conservative label in `{likely_stationary, trend_nonstationary, seasonal, unclear}` | Treat as a summary hint, not as a formal stationarity test |
| `notes` | Deterministic caveats about short series, constant data, or seasonal gating | Review these before comparing scalar values across series |

## Why It Matters For Forecastability

Forecastability triage needs to tell apart several common stories that can all
produce informative horizons.

- High `acf1` and slower `acf_decay_rate` can support a short-memory
  autoregressive reading.
- High `trend_strength` can explain AMI persistence that is really drift or a
  differencing candidate.
- Non-null `seasonal_strength` can support a seasonal interpretation when the
  caller has already supplied a plausible period.

That makes this block useful as a cheap explanatory bridge between AMI geometry
and downstream hand-off decisions.

## What It Does Not Prove

- It does not prove stationarity or nonstationarity in the formal test-theory
  sense.
- It does not infer a seasonal period automatically.
- It does not prove that a seasonal, trend, or autoregressive family will be
  best downstream.
- It does not replace rolling-origin validation or residual analysis.

## Input Assumptions

- The input must be a finite one-dimensional series after public validation.
- `seasonal_strength` is intentionally gated on a positive user-supplied
  `period`.
- Seasonal interpretation is stronger when at least two full cycles are present.
- These summaries assume a lightweight deterministic decomposition, not a
  fully tuned statistical model.

## Failure Modes

- Very short series return `unclear` with missing numeric fields rather than
  unstable estimates.
- Constant series also return conservative missing-field summaries.
- A wrong supplied `period` can make `seasonal_strength` look weaker or more
  ambiguous than the domain truth.
- Strong trend can inflate dependence-looking summaries that should instead be
  treated as preprocessing or differencing cues.

## Synthetic Example

The example below mixes a linear trend, a known sample-period seasonal term,
and light noise. The expected reading is non-null `seasonal_strength`, elevated
`trend_strength`, and a `stationarity_hint` that stays cautionary rather than
purely stationary.

```python
import numpy as np

from forecastability import run_extended_forecastability_analysis

rng = np.random.default_rng(42)
t = np.arange(240)
series = 0.03 * t + 0.8 * np.sin(2 * np.pi * t / 12) + 0.2 * rng.normal(size=t.size)

result = run_extended_forecastability_analysis(series, max_lag=36, period=12)
print(result.fingerprint.classical.model_dump())
```

This remains descriptive structure evidence. The public route still starts with
AMI geometry and then asks whether the classical block helps explain it.

## Interpretation Table

| `stationarity_hint` | Typical reading | Forecastability implication |
| --- | --- | --- |
| `likely_stationary` | No dominant trend or seasonal warning is detected | Short-memory or local nonlinear structure may matter more than drift |
| `trend_nonstationary` | Trend dominates the lightweight decomposition | Consider preprocessing, differencing, or trend-aware downstream baselines |
| `seasonal` | User-supplied period is supported by the seasonal summary | Seasonal or Fourier-style downstream families may be worth checking |
| `unclear` | Sample support or decomposition quality is too weak for a stronger label | Defer to AMI, spectral, and other diagnostics |

## References

- George E. P. Box, Gwilym M. Jenkins, Gregory C. Reinsel, and Greta M. Ljung, ARIMA and autocorrelation foundations
- Rob J. Hyndman and George Athanasopoulos, decomposition and seasonality guidance
- Peter J. Brockwell and Richard A. Davis, classical time-series structure summaries