<!-- type: explanation -->

# Spectral Predictability (F4)

## Background

Spectral predictability measures how much of a time series' variance is
concentrated in a small number of frequency components.  A periodic or
trend-dominated series has a peaked power spectral density (PSD); white noise
has a flat one.  This feature was formalised as the Ω metric in Wang et al.
(2025) and is implemented here as Feature F4 of the AMI → pAMI pipeline.

Reference: Wang et al. (2025) *Automated Forecastability Assessment via Mutual
Information*, arXiv:2507.13556.

## Core Formula

Spectral entropy (base *a*) is defined over the normalised PSD vector **p**:

$$H_a = -\sum_i p_i \log_a p_i$$

Spectral predictability normalises by the maximum entropy of a uniform
distribution over $N_{\mathrm{bins}}$ bins:

$$\Omega(\mathbf{y}) = 1 - \frac{H_a(\mathbf{y})}{\log_a(N_{\mathrm{bins}})}$$

Ω = 1 when the entire power is in one bin (perfectly periodic); Ω → 0 when
the spectrum is uniform (white noise).

## Implementation Notes

### PSD Estimation

- Welch method via `scipy.signal.welch`.
- Default `nperseg = min(n, 256)`; configurable via the `nperseg` parameter.
- Mean-detrending (`detrend="constant"`) applied by default; `"linear"` or
  `"none"` available.

### Normalisation

Entropy is divided by `log(N_bins)`, **not** `log(n)`.  Using `log(n)` would
make Ω depend on series length even for identically distributed processes,
which undermines cross-series comparability.

### Base

Natural logarithm (`base=e`) is used throughout to keep the implementation
consistent with other information-theoretic measures in this project.

### Zero-Power Handling

PSD bins are clipped to `1e-12` before normalisation to avoid `log(0)`.
This is done inside `compute_normalised_psd` before returning the probability
vector `p`.

## Interpretation

| Ω range   | Interpretation |
|-----------|----------------|
| ≥ 0.70    | High spectral predictability — concentrated spectrum; strong periodic or trend structure. |
| 0.40–0.70 | Moderate spectral predictability — mixed frequency content; some exploitable structure. |
| < 0.40    | Low spectral predictability — flat spectrum; dynamics resemble white noise. |

A divergence between Ω (a purely *linear* spectral measure) and AMI (a
*nonlinear* dependence measure) is informative: if AMI is high but Ω is low,
the predictability likely arises from nonlinear structure that linear spectral
analysis misses.

## Limitations

> [!WARNING]
> - **Inconsistent periodogram**: Raw periodogram estimates are statistically
>   inconsistent.  Welch's method reduces variance but cannot eliminate all
>   bias, especially for short or non-stationary series.
> - **Non-stationarity**: The Welch PSD assumes wide-sense stationarity.
>   Non-stationary series (e.g. trending revenue data) should be detrended
>   before analysis.  Use `detrend="linear"` as a first pass.
> - **Short series**: For n < 128, the Welch estimate uses very few segments
>   and the resulting Ω values are unreliable.  Treat them as coarse indicators
>   only.
> - **Linear structure only**: Ω captures spectral (linear) structure.  It is
>   insensitive to nonlinear dependence such as conditional heteroskedasticity
>   or chaos.  Pair with AMI for a more complete picture.

## Citation

Wang, A. et al. (2025). *Automated Forecastability Assessment via Mutual
Information*. arXiv:2507.13556.
