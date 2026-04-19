<!-- type: explanation -->
# Forecastability Fingerprint

`ForecastabilityFingerprint` is the compact public summary layer used by the
v0.3.1 fingerprint workflow. It sits *above* the AMI Information Geometry
engine and *below* routing, reporting, and agent adapters.

> [!IMPORTANT]
> The fingerprint is not a replacement for the AMI curve. It is a deterministic
> summary of geometry-backed horizon-wise AMI behavior.

## Position in the Stack

```mermaid
flowchart LR
    A["Input series"] --> B["AMI Information Geometry"]
    B --> C["Linear-information baseline"]
    B --> D["ForecastabilityFingerprint"]
    C --> D
    D --> E["RoutingRecommendation"]
    D --> F["Rendering / JSON / agents"]
```

The authoritative implementation lives in:

- `forecastability.services.ami_information_geometry_service`
- `forecastability.services.fingerprint_service`
- `forecastability.services.routing_policy_service`

## Public Fields

The fingerprint keeps the original four public fields and now mirrors
`signal_to_noise` from the geometry layer.

### `information_mass`

`information_mass` is computed on the **corrected** AMI profile and only over
the geometry-accepted horizons:

$$
M = \frac{1}{\max(1, H_{valid})} \sum_{h=1}^{H} I_c(h)\,\mathbf{1}[I_c(h) > 3\tau(h)]
$$

Interpretation:

- low mass: little usable predictive information survives correction/thresholding
- high mass: stronger and/or broader usable signal across the evaluated horizon grid

### `information_horizon`

`information_horizon` is the latest accepted horizon:

$$
H_{info} = \max \{ h : I_c(h) > 3\tau(h) \}
$$

with `0` when no horizons satisfy the geometry rule.

### `information_structure`

The public structure taxonomy remains:

- `none`
- `monotonic`
- `periodic`
- `mixed`

The label is sourced from the corrected profile, not from raw AMI. The
deterministic precedence is:

`none` > `periodic` > `monotonic` > `mixed`

### `nonlinear_share`

`nonlinear_share` measures how much accepted corrected AMI exceeds a linear
Gaussian-information baseline:

$$
I_G(h) = -\frac{1}{2}\log(1-\rho(h)^2)
$$

$$
E(h) = \max(I_c(h) - I_G(h), 0)
$$

$$
N = \frac{\sum_{h \in \mathcal{H}_{geom}} E(h)}
         {\sum_{h \in \mathcal{H}_{geom}} I_c(h) + \epsilon}
$$

Horizons with invalid `I_G(h)` are excluded conservatively from both numerator
and denominator.

### `signal_to_noise`

`signal_to_noise` is mirrored into the fingerprint object, but it remains a
geometry-quality metric:

$$
S = \frac{\sum_h \max(I_c(h)-\tau(h), 0)}{\sum_h I_c(h) + \epsilon}
$$

Interpretation:

- low value: corrected AMI exists, but little clears the surrogate threshold margin
- high value: corrected AMI rises clearly above the surrogate background

## What the Fingerprint Does Not Mean

The fingerprint does **not** identify the one true best model.

- `information_mass` is not `signal_to_noise`
- `signal_to_noise` is not `nonlinear_share`
- `nonlinear_share` is not `1 - directness_ratio`
- routing is heuristic model-family guidance, not an empirical winner guarantee

## Geometry Coupling

The v0.3.1 fingerprint no longer rebuilds threshold semantics locally.

- accepted horizons come from `AmiInformationGeometry.curve[*].accepted`
- `information_horizon` and `information_mass` use the same acceptance mask
- structure comes from the geometry classifier
- `signal_to_noise` is copied from geometry without reinterpretation

That keeps the deterministic core aligned across Python objects, markdown
reports, JSON output, and agent payloads.

## Batch Operationalization

The batch forecastability workbench introduced on top of the fingerprint stack
does not add new mathematics. It operationalizes the same deterministic
geometry, fingerprint, and routing outputs in a portfolio workflow.

- batch triage still ranks readiness and signal quality separately
- per-series next-step plans are derived from the same routed families and caution flags
- executive reports are communication surfaces only and must stay downstream of the deterministic bundle
