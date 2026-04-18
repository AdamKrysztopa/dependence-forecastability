<!-- type: explanation -->
# Forecastability Fingerprint (V3_1-F02)

This page documents the theory and design contract for the
`ForecastabilityFingerprint` summary layer introduced in V3_1-F02.

The fingerprint converts horizon-wise AMI profile evidence into a compact,
typed result that is easier to route into model-family guidance.

> [!IMPORTANT]
> The paper-native core is AMI. pAMI and fingerprint-based routing are project
> extensions in this repository.

## Why This Object Exists

The AMI profile is horizon-specific:

$$
AMI(h) = I(X_t; X_{t+h}), \quad h = 1, \dots, H
$$

It is statistically rich but operationally verbose. `ForecastabilityFingerprint`
provides a deterministic summary so that downstream routing and interpretation
can consume one compact object with stable semantics.

`ForecastabilityFingerprint` is defined in
`forecastability.utils.types.ForecastabilityFingerprint` and built by
`forecastability.services.fingerprint_service.build_fingerprint`.

## Core Fields

The fingerprint reports four primary fields.

### `information_mass` (M)

Normalized masked area under the informative AMI profile:

$$
M = \frac{1}{\max(1, H)} \sum_{h=1}^{H} AMI(h)\,\mathbf{1}[h \in \mathcal{H}_{info}]
$$

Interpretation:

- low `M`: weak aggregate usable dependence
- high `M`: stronger and/or broader informative dependence

### `information_horizon` (H*)

Latest informative horizon:

$$
H^* = \max(\mathcal{H}_{info})
$$

with `H* = 0` when `H_info` is empty.

Interpretation:

- short horizon: predictive information decays quickly
- long horizon: information persists farther into the forecast horizon

### `information_structure`

Shape label over informative-horizon AMI values:

- `none`
- `periodic`
- `monotonic`
- `mixed`

Deterministic tie-break precedence is:

`none` > `periodic` > `monotonic` > `mixed`

### `nonlinear_share`

Fraction of informative AMI that exceeds a Gaussian linear-information baseline.
For each horizon:

$$
I_G(h) = -\frac{1}{2}\log\bigl(1 - \rho(h)^2\bigr)
$$

$$
E(h) = \max\bigl(AMI(h) - I_G(h), 0\bigr)
$$

Aggregate ratio:

$$
N = \frac{\sum E(h)}{\sum AMI(h) + \varepsilon}
$$

where the sums are taken over valid informative horizons used in the nonlinear
baseline computation.

> [!IMPORTANT]
> Important denominator fix: the denominator includes only informative horizons
> where `I_G(h)` is valid. Horizons with invalid `I_G(h)` are excluded from both
> numerator and denominator to avoid dilution or inflation from undefined linear
> baseline values.

## Informative Horizons `H_info`

The informative horizon set is:

$$
\mathcal{H}_{info} = \{ h \in \{1,\dots,H\} : AMI(h) \ge \tau_{AMI} \;\land\; h \in H_{sig} \}
$$

where:

- $\tau_{AMI}$ is the AMI floor (`ami_floor`)
- $H_{sig}$ is the set of surrogate-significant horizons

Operationally in V3_1-F02 this is implemented as:

- `AMI(h) >= ami_floor`
- and horizon `h` is in `significant_horizons`

If `H_info` is empty, the service returns:

- `information_mass = 0.0`
- `information_horizon = 0`
- `information_structure = "none"`
- `nonlinear_share = 0.0`

## Structure Classification Rules

The structure classifier is deterministic and follows this sequence:

1. `none` when no informative horizons exist.
2. `periodic` when informative-horizon AMI has repeated peaks that pass
   prominence criteria and spacing stability checks.
3. `monotonic` when informative-horizon AMI is approximately non-increasing
   within the configured monotonicity tolerance.
4. `mixed` otherwise.

Periodic checks use both absolute and relative prominence thresholds:

$$
\text{prominence} \ge \max(\text{peak\_prominence\_abs},\; \text{peak\_prominence\_rel} \cdot \max AMI_{info})
$$

Spacing stability is controlled by `spacing_tolerance` on inter-peak spacing,
and periodic inference is gated by `min_horizons_for_periodic`.

## Surrogate-Gated vs Floor-Only Usage

V3_1-F02 supports two practical usage modes, demonstrated in
`examples/fingerprint/minimal_fingerprint.py`.

### Surrogate-gated mode (default analysis semantics)

- `significant_horizons` comes from surrogate significance (`sig_raw_lags`)
- informative horizons require both significance and floor
- conservative: linear processes may correctly yield sparse or empty `H_info`

### Floor-only mode (shape-inspection mode)

- caller treats every horizon with `AMI(h) >= ami_floor` as significant
- bypasses surrogate gating to inspect geometric profile shape
- useful for pedagogical comparisons and diagnostic exploration

> [!NOTE]
> Floor-only mode is a deliberate diagnostic simplification. It is not a
> substitute for significance-gated interpretation in decision workflows.

## Scope Boundary and Semantics

- AMI framing is paper-native.
- pAMI and fingerprint summarization are repository extensions.
- `directness_ratio` remains a separate field from `nonlinear_share` and is
  passed through by the fingerprint service when provided.

These distinctions prevent conflating mediated-lag structure (`directness`) with
linear-vs-nonlinear dependence share (`nonlinear_share`).
