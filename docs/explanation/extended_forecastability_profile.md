<!-- type: explanation -->
# ExtendedForecastabilityProfile

`ExtendedForecastabilityProfile` is the implemented human-facing routing
summary produced by the deterministic extended forecastability router.

> [!IMPORTANT]
> `ExtendedForecastabilityProfile` is additive, not a replacement contract.
> The extended fingerprint remains AMI-first, and the profile extends the
> existing `ForecastabilityProfile` rather than replacing it.

## Purpose

The role of `ExtendedForecastabilityProfile` is to keep the existing AMI-derived
profile intact while adding a small, explicit layer of explanation-oriented
routing fields on top. That preserves the repository identity as deterministic
forecastability triage: the profile tells you what kind of structure appears to
be present and which model-family directions are plausible starting points, but
it does not fit models or claim forecast winners.

## How It Extends The Existing Contract

`ExtendedForecastabilityProfile` literally extends `ForecastabilityProfile`.

- the inherited fields keep the existing AMI-centric profile contract intact
- the additive fields layer on deterministic routing context: `signal_strength`,
  `predictability_sources`, `noise_risk`, `recommended_model_families`,
  `avoid_model_families`, and `explanation`

This is the approved naming and compatibility direction for the live Phase 2
surface: `ExtendedForecastabilityProfile`, not a silent replacement of
`ForecastabilityProfile`.

## Inherited AMI Profile Fields

The inherited fields retain the same public meanings as the base
`ForecastabilityProfile`, with one caveat: `summary` and `model_now` become
descriptive-only strings when AMI routing is unavailable.

| Field | Role inside the extended profile |
| --- | --- |
| `horizons` | 1-based lag indices reused from the AMI profile |
| `values` | Raw AMI profile values, preserved as the inherited ndarray-style contract |
| `epsilon` | Threshold used to define informative horizons |
| `informative_horizons` | Horizons where the inherited AMI profile stays at or above `epsilon` |
| `peak_horizon` | Lag index with the strongest inherited AMI signal |
| `is_non_monotone` | Whether the inherited AMI profile rises after its first horizon |
| `summary` | One-sentence AMI-centered summary, or a descriptive-only fallback when routing is withheld |
| `model_now` | Immediate AMI-centered action string, or a descriptive-only fallback when routing is withheld |
| `review_horizons` | Horizons worth downstream modeling review |
| `avoid_horizons` | Horizons that the inherited profile marks as low value |

For the full inherited contract, see
[../theory/forecastability_profile.md](../theory/forecastability_profile.md).

## Additive Routing Fields

The additive fields are the part introduced by the extended routing surface.

| Field | Meaning | Practical reading |
| --- | --- | --- |
| `signal_strength` | High-level label in `{low, medium, high, unclear}` | Coarse overall strength of the forecastability story |
| `predictability_sources` | Sorted tuple of source labels | Which interpretable mechanisms appear to support the profile |
| `noise_risk` | Heuristic label in `{low, medium, high, unclear}` | How cautious to stay about expensive downstream search |
| `recommended_model_families` | Deterministic shortlist of plausible family directions | Starting points only, not a winner declaration |
| `avoid_model_families` | Family directions the router argues against | Reasons to stay conservative |
| `explanation` | Ordered explanation bullets supporting the route | Human-readable rationale for the profile |

The current source labels have fixed meanings.

| `predictability_sources` label | Meaning |
| --- | --- |
| `lag_dependence` | AMI geometry suggests useful lagged dependence |
| `spectral_concentration` | The spectral block sees concentrated frequency structure |
| `seasonality` | Classical or AMI evidence supports a seasonal story |
| `trend` | The classical block sees a meaningful trend component |
| `ordinal_redundancy` | The ordinal block sees repeated local ordering structure |
| `long_memory` | The memory block sees persistence that merits longer-window follow-up |

## Why The Router Is Conditional On AMI Geometry

Routing-grade family direction in this repository is anchored to AMI geometry.
When `information_geometry` is disabled or unavailable, the router still
reports descriptive structure from the spectral, ordinal, classical, and memory
blocks, but it switches to a diagnostic-only profile:

- `routing_metadata["descriptive_only"] = True`
- `recommended_model_families` and `avoid_model_families` stay empty
- the summary and explanation say why routing-grade recommendations were withheld

That keeps the AMI-first contract explicit instead of pretending the secondary
diagnostics alone are sufficient for routing decisions.

Minimal example:

```python
from forecastability import generate_ar1, run_extended_forecastability_analysis

series = generate_ar1(n_samples=300, phi=0.8, random_state=42)
result = run_extended_forecastability_analysis(
    series,
    max_lag=24,
    include_ami_geometry=False,
)

print(result.routing_metadata["descriptive_only"])
print(result.profile.recommended_model_families)
print(result.profile.summary)
```

The expected shape is `True`, an empty family list, and a summary that says the
result is descriptive-only because AMI geometry was intentionally withheld.

## Where It Appears

- `ExtendedForecastabilityAnalysisResult.profile` from `run_extended_forecastability_analysis(...)`
- `TriageResult.extended_forecastability_analysis.profile` when `run_triage(..., include_extended_fingerprint=True)` is used on a non-exogenous request

## Why Exogenous Triage Does Not Attach It

The current extended router is target-only. For `goal="exogenous"` requests,
`run_triage(..., include_extended_fingerprint=True)` leaves
`extended_forecastability_analysis` unset rather than implying that an
exogenous-aware extended routing surface exists.

## Non-Goals

- redefining or weakening the existing AMI profile semantics
- embedding forecast-model fitting logic inside the profile contract
- inventing routing recommendations from non-AMI blocks alone
- turning the profile into downstream framework integration

## Public Surfaces

- `ExtendedForecastabilityProfile` on the additive stable facade and `forecastability.triage`
- `ExtendedForecastabilityAnalysisResult.profile` as the main consumer-facing placement of the profile
- `run_extended_forecastability_analysis(...)` as the direct public use case

Richer walkthroughs and notebooks for this surface belong in the sibling
`forecastability-examples` repository rather than the core repo.
