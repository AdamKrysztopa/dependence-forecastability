<!-- type: explanation -->
# Forecastability Profile & Informative Horizon Set

## Overview

The **Forecastability Profile** is a structured summary of how much predictive
information $I(Y_{t+h};\,\mathcal{I}_t)$ is available at each forecast horizon $h$.
It describes the full horizon-wise relationship between the target series and the
available information set, from lag 1 to a user-specified maximum lag $H$.
The profile is a read-only, frozen Pydantic model — `ForecastabilityProfile` — whose
fields are populated once from the AMI curve already computed by the pipeline.
No new estimation occurs during profile construction.

The profile compresses the AMI curve into a set of actionable fields: the set of
horizons where forecastability clears a significance threshold (the
*informative horizon set* $\mathcal{H}_\varepsilon$), the peak horizon, structural
shape flags, and model-selection recommendations.  A practitioner interacts with the
profile instead of the raw numeric array to avoid re-implementing the threshold logic
in downstream code.

The profile is the primary deliverable of Feature F1 in the triage pipeline.
It is constructed by `forecastability_profile_service.build_forecastability_profile()`
and is exposed on the `TriageResult` returned by `run_triage()`.

---

## Mathematical Foundation

**Forecastability at horizon $h$** is defined as the mutual information between the
future target and the current information set (Catt, 2026):

$$
F(h;\,\mathcal{I}_t) = I(Y_{t+h};\,\mathcal{I}_t) = H(Y_{t+h}) - H(Y_{t+h} \mid \mathcal{I}_t)
$$

where $H(\cdot)$ is differential entropy and $H(\cdot\mid\cdot)$ is conditional
differential entropy.  $F(h;\,\mathcal{I}_t) \ge 0$ with equality only when
$Y_{t+h}$ is independent of $\mathcal{I}_t$.

**The forecastability profile** is the map

$$
h \mapsto F(h;\,\mathcal{I}_t), \quad h \in \{1, \dots, H\}
$$

This map is represented in the model by the paired lists `horizons` and `values`.

**The informative horizon set** is the subset of lags where forecastability exceeds
threshold $\varepsilon$:

$$
\mathcal{H}_\varepsilon = \bigl\{h : F(h;\,\mathcal{I}_t) \ge \varepsilon\bigr\}
$$

A practitioner should target model evaluation exclusively at horizons in
$\mathcal{H}_\varepsilon$ — lags outside this set carry no detectable predictive
signal above the noise floor.

> **Reference:** Peter Catt (2026), "Forecastability: An Information-Theoretic
> Framework," arXiv:2603.27074.

---

## How $\varepsilon$ (epsilon) Is Determined

Epsilon is resolved through a two-path decision, executed inside
`forecastability_profile_service._determine_epsilon()`:

1. **When surrogates are computed** — $\varepsilon$ is set to the minimum AMI value
   among lags whose AMI exceeds the 97.5th percentile of the surrogate distribution.
   Concretely, the significant lags (`sig_raw_lags`) are identified by
   `significance_service`, and epsilon is:

   $$\varepsilon = \min_{j \in \text{sig\_raw\_lags}} F(h_j;\,\mathcal{I}_t)$$

   This anchors $\varepsilon$ to the noise floor estimated from phase-randomised
   surrogates.  When no lags clear the surrogate band,
   $\varepsilon$ is set above the curve maximum so that
   `informative_horizons` is empty.

2. **When no surrogates are available** — $\varepsilon$ falls back to the
   `default_epsilon` parameter (default `0.05` nats), or to an explicit
   caller-supplied override.

> [!IMPORTANT]
> Define $\varepsilon$ relative to the surrogate upper band, not as a global
> absolute constant.  An absolute threshold risks including noise lags or
> excluding genuinely informative ones as signal strength varies across series.
> Use surrogates whenever sample size permits ($n \ge 200$, `n_surrogates >= 99`).

---

## Data-Processing Inequality (DPI) Diagnostic

The Data-Processing Inequality states that applying a lossy transformation $T$ to
the information set cannot increase forecastability:

$$
F(h;\,T(\mathcal{I}_t)) \le F(h;\,\mathcal{I}_t)
$$

This has a direct practical implication when comparing profiles across feature
representations.  If a derived feature — for example, a box-aggregated or
coarsely discretised version of the raw series — yields strictly lower profile
values than the unaggregated series, the transformation has destroyed predictive
information.  The profile makes this audit straightforward: compare the `values`
arrays element-wise across two runs; any lag where the derived profile exceeds the
raw profile by more than estimation noise is a data-leakage candidate, not a
genuine gain.

The DPI does not imply that $F(h;\,T(\mathcal{I}_t)) = 0$ is the expected outcome;
useful transforms (e.g. log of a multiplicative process) may preserve nearly all
forecastability.  The DPI is a ceiling constraint, not a pessimistic prediction.

---

## Profile Fields Reference

| Field | Type | Description |
|---|---|---|
| `horizons` | `list[int]` | 1-based lag indices $[1, \dots, H]$ |
| `values` | `np.ndarray` | AMI values — $F(h)$ for each horizon |
| `epsilon` | `float` | Resolved threshold $\varepsilon$ for $\mathcal{H}_\varepsilon$ |
| `informative_horizons` | `list[int]` | $\mathcal{H}_\varepsilon$ — horizons where $F(h) \ge \varepsilon$ |
| `peak_horizon` | `int` | $h^* = \arg\max_h F(h)$ (1-based index) |
| `is_non_monotone` | `bool` | `True` if $F(h)$ increases at any $h > 1$ |
| `summary` | `str` | One-sentence human-readable profile description |
| `model_now` | `str` | Immediate model-complexity recommendation (HIGH / MEDIUM / LOW / NONE) |
| `review_horizons` | `list[int]` | All informative horizons — model building targets |
| `avoid_horizons` | `list[int]` | Non-informative horizons — exclude from model feature sets |

The model is frozen (`model_config = ConfigDict(frozen=True)`); fields cannot be
mutated after construction, which guarantees that cached profiles remain consistent
with their source AMI run.

---

## Non-Monotone Profiles

A strictly decreasing forecastability profile — $F(1) \ge F(2) \ge \cdots$ — holds
for simple AR processes and many white-noise-corrupted signals.  However, it is
**not** a universal requirement.  Seasonal and quasi-periodic processes routinely
exhibit higher AMI at seasonal lags than at short lags.  For example, a monthly
series with strong annual seasonality may have $F(12) > F(5)$, producing a
non-monotone profile with a secondary peak at $h = 12$.

`is_non_monotone` flags this shape for downstream consumers without judgement.
Routines that assume monotone decay (such as naive exponential smoothers) should
inspect this flag before applying simplifying assumptions.  Do not treat a
`True` value as an estimation artefact or an error — it is correct and expected for
seasonal series.

---

## Known Limitations

> [!WARNING]
> **Spectral surrogates and periodic series**: The default surrogate method
> (phase randomisation) preserves the amplitude spectrum of the series.  For
> near-deterministic periodic signals (e.g. pure sinusoids), the surrogates carry
> nearly identical spectral structure, making it impossible to detect forecastability
> above the null.  Such series will exhibit `informative_horizons = []` and
> `model_now = "NONE"` even when they are perfectly predictable.  This is a known
> power-zero failure mode of spectral surrogate tests, not a defect in the profile
> logic.

> [!NOTE]
> The kNN MI estimator (`n_neighbors=8`) is consistent but has finite-sample
> variance.  At small $n$ (< 200) or at very long lags where signal decays,
> individual AMI values may be noise-lifted slightly above $\varepsilon$.  Expect
> occasional false-positive horizons in `informative_horizons`, especially for
> AR(1) processes at long lags.

---

## Estimator Reuse

The profile reuses AMI values produced by `ForecastabilityAnalyzer.analyze()`,
which runs a kNN MI estimator with `n_neighbors=8`.  No separate estimation step
executes during profile construction.  Reliability and variance properties of all
profile fields inherit entirely from the underlying MI estimator; improving
estimator accuracy (e.g. raising `n_surrogates`, increasing the sample size, or
choosing a better-matched `n_neighbors`) propagates automatically to the profile.

---

## Example

```python
import numpy as np
from forecastability.datasets import generate_ar1
from forecastability.triage import TriageRequest, run_triage

series = generate_ar1(n=300, phi=0.7, random_state=0)
result = run_triage(TriageRequest(series=series, n_surrogates=99, random_state=42, max_lag=20))
profile = result.forecastability_profile

print(profile.informative_horizons)   # e.g. [1, 2]
print(profile.peak_horizon)           # 1
print(profile.model_now)              # HIGH — Complex structured models ...
```

The `TriageRequest` parameters that most affect profile content:

| Parameter | Effect on profile |
|---|---|
| `max_lag` | Sets $H$ — the length of the `horizons` and `values` arrays |
| `n_surrogates` | Controls surrogate-band accuracy for epsilon resolution |
| `random_state` | Seeds both the MI estimator and the surrogate generator for reproducibility |
| `default_epsilon` | Fallback threshold when surrogates are not requested |
