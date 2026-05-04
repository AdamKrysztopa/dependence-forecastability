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

- the inherited fields keep the existing AMI-centric profile contract intact: horizons, AMI values, epsilon, informative horizons, peak horizon, monotonicity flag, summary, and horizon-review guidance
- the additive fields layer on deterministic routing context: `signal_strength`, `predictability_sources`, `noise_risk`, `recommended_model_families`, `avoid_model_families`, and `explanation`

This is the approved naming and compatibility direction for the live Phase 2
surface: `ExtendedForecastabilityProfile`, not a silent replacement of
`ForecastabilityProfile`.

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

For the inherited AMI-centric profile fields, see [../theory/forecastability_profile.md](../theory/forecastability_profile.md).

Richer walkthroughs and notebooks for this surface belong in the sibling
`forecastability-examples` repository rather than the core repo.