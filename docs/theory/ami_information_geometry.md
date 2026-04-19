<!-- type: explanation -->
# AMI Information Geometry

The v0.3.1 fingerprint workflow is driven by a dedicated AMI Information
Geometry engine. This layer computes the corrected AMI profile, threshold
profile, accepted horizons, and geometry-level signal diagnostics that the
fingerprint and routing layers consume downstream.

## Core Semantics

For horizons `h = 1, ..., H`, the service estimates raw AMI with a KSG-II
estimator using the Chebyshev metric and median aggregation over `k_list`.

Release-aligned defaults:

- `k_list = (3, 5, 8)`
- `n_surrogates = 200` in the service config
- one-shot tiny jitter for deterministic tie handling
- shuffle surrogates for bias and threshold estimation

## Corrected Profile

For each horizon:

$$
I_c(h) = \max(I(h) - bias(h), 0)
$$

where:

- `I(h)` is the raw KSG-II estimate
- `bias(h)` is the mean of the shuffle-surrogate AMI values
- `tau(h)` is the 90th percentile of the shuffle-surrogate AMI values

The public typed output is `AmiInformationGeometry`, and each horizon is stored
as an `AmiGeometryCurvePoint` with:

- `ami_raw`
- `ami_bias`
- `ami_corrected`
- `tau`
- `accepted`
- `valid`
- `caution`

## Acceptance Rule

The canonical v0.3.1 acceptance mask is:

$$
I_c(h) > 3\tau(h)
$$

This mask drives:

- `geometry.informative_horizons`
- `geometry.information_horizon`
- fingerprint `information_mass`
- fingerprint `information_horizon`

No downstream layer should redefine this rule locally.

## `signal_to_noise`

`signal_to_noise` is a corrected-profile quality metric:

$$
S = \frac{\sum_h \max(I_c(h)-\tau(h), 0)}{\sum_h I_c(h) + \epsilon}
$$

It is bounded to `[0, 1]` and returns `0.0` when the corrected-profile
denominator is effectively zero.

## Structure Classification

The geometry layer classifies the corrected profile into:

- `none`
- `monotonic`
- `periodic`
- `mixed`

Rules:

1. `none` if `signal_to_noise` is below the configured null threshold or if no
   horizons satisfy `I_c(h) > 3tau(h)`.
2. `periodic` if accepted repeated peaks survive the corrected-profile
   prominence and spacing checks.
3. `monotonic` if no qualifying repeated peaks remain and the signal decays in
   the corrected profile.
4. `mixed` otherwise.

## Architectural Boundary

The geometry service is deterministic domain logic.

- It computes science.
- It does not render plots.
- It does not read/write CSV files.
- It does not choose model families.
- It does not talk to LLMs or provider SDKs.

That separation is what lets the same geometry outputs survive unchanged through
the fingerprint builder, routing policy, reporting helpers, and agent payloads.
