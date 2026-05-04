<!-- type: explanation -->
# Spectral Forecastability

Spectral forecastability is the frequency-domain block inside the AMI-first
extended fingerprint. It summarizes whether a univariate series looks
frequency-concentrated, diffuse, or dominated by a small number of sample-scale
periods.

> [!IMPORTANT]
> This block stays subordinate to AMI information geometry. Spectral evidence
> can explain why informative horizons may exist, but it does not replace the
> lag-domain evidence from [ami_information_geometry.md](ami_information_geometry.md)
> and it does not claim forecast accuracy directly.

## What It Measures

For a finite univariate series, the shipped diagnostic computes a normalized
positive-frequency power spectrum and derives the bounded public result model
`SpectralForecastabilityResult`.

| Field | Meaning | Conservative reading |
| --- | --- | --- |
| `spectral_entropy` | Normalized spectral entropy on $[0, 1]$ | Higher values mean the spectrum is more diffuse and less concentrated |
| `spectral_predictability` | Deterministic complement of entropy, also on $[0, 1]$ | Higher values mean the spectrum is more concentrated, not that forecast skill is guaranteed |
| `dominant_periods` | Strongest inverse-frequency periods, in sample counts | These are candidate sample-scale periods, not calendar semantics |
| `spectral_concentration` | Unit-scale concentration summary relative to a uniform spectrum | Read as a structure indicator, not as a confidence score |
| `periodicity_hint` | Coarse label in `{none, weak, moderate, strong}` | A descriptive summary of apparent periodic structure |
| `notes` | Deterministic caveats emitted by the service | Review these before trusting the scalar values |

The entropy and predictability scores are linked by:

$$
H_{spec} = \frac{-\sum_k p_k \log p_k}{\log K},
\qquad
P_{spec} = 1 - H_{spec}
$$

where $p_k$ is normalized positive-frequency spectral mass and $K$ is the
number of retained positive-frequency bins.

## Why It Matters For Forecastability

Forecastability triage needs to separate lagged information from the mechanism
that may be producing it. The spectral block helps answer whether repeated AMI
structure could plausibly be driven by narrow-band or periodic behavior.

- It supports seasonality-oriented interpretation when AMI geometry already
  shows repeated informative horizons.
- It helps distinguish periodic structure from broadly noise-like frequency
  content.
- It gives the router one additive explanation source,
  `spectral_concentration`, without turning the repository into a
  framework-selection layer.

## What It Does Not Prove

- It does not prove that a seasonal model will outperform an autoregressive,
  nonlinear, or baseline model downstream.
- It does not identify a real-world calendar unit on its own.
- It does not prove that a dominant low-frequency component is usable seasonal
  structure rather than trend contamination.
- It does not replace rolling-origin evaluation or downstream model checking.

## Input Assumptions

- The input must be a finite one-dimensional series after public validation.
- Interpretation is strongest when the series is long enough to resolve several
  cycles of any candidate period.
- `dominant_periods` are expressed in sample counts because the public surface
  does not take a sampling interval.
- Spectral concentration is descriptive even when AMI geometry is unavailable.

## Failure Modes

- Very short series collapse to a conservative near-uniform summary with an
  explanatory note.
- Constant series return a degenerate low-information summary rather than a
  pseudo-periodic answer.
- Strong low-frequency energy can reflect trend contamination, which can make
  `periodicity_hint` look stronger than the true seasonal case warrants.
- Aliasing and coarse sampling can shift `dominant_periods` away from the
  mechanism you would expect from domain knowledge.

## Synthetic Example

The public workflow below uses a clean sample-count sine wave with light noise.
The expected reading is low `spectral_entropy`, high
`spectral_predictability`, and a `dominant_periods` entry close to `24`.

```python
import numpy as np

from forecastability import run_extended_forecastability_analysis

rng = np.random.default_rng(42)
t = np.arange(240)
series = np.sin(2 * np.pi * t / 24) + 0.15 * rng.normal(size=t.size)

result = run_extended_forecastability_analysis(series, max_lag=48, period=24)
print(result.fingerprint.spectral.model_dump())
```

Use the spectral block as supporting evidence. The AMI-first read still starts
with `result.fingerprint.information_geometry` and `result.profile`.

## Interpretation Table

| `periodicity_hint` | Typical reading | Forecastability implication |
| --- | --- | --- |
| `none` | Frequency content is diffuse or too weak to summarize as periodic | Do not infer seasonality from this block alone |
| `weak` | Some concentration is present, but the periodic case is fragile | Look for confirming AMI peaks before routing toward seasonal families |
| `moderate` | Periodic structure is plausible and supported by concentration | Seasonal or Fourier-style families may be worth a downstream check |
| `strong` | A small number of sample-scale periods dominate the spectrum | Treat as strong explanatory evidence, not as a winner declaration |

## References

- Claude E. Shannon, 1948, "A Mathematical Theory of Communication"
- Alan V. Oppenheim and Ronald W. Schafer, 1999, "Discrete-Time Signal Processing"
- T. Inouye et al., 1991, spectral entropy as a compact frequency-domain summary