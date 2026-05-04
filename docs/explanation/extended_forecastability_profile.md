<!-- type: explanation -->
# ExtendedForecastabilityProfile

`ExtendedForecastabilityProfile` is the planned human-facing routing summary for the extended fingerprint surface.

> [!IMPORTANT]
> `ExtendedForecastabilityProfile` is additive, not a replacement contract. The extended fingerprint remains AMI-first, and the profile extends the existing `ForecastabilityProfile` rather than replacing it.

## Purpose

The role of `ExtendedForecastabilityProfile` is to keep the existing AMI-derived profile intact while adding a small, explicit layer of explanation-oriented routing fields on top. That preserves the repository identity as deterministic forecastability triage: the profile tells you what kind of structure appears to be present and which model-family directions are plausible starting points, but it does not fit models or claim forecast winners.

## How It Extends The Existing Contract

In the current scaffold, `ExtendedForecastabilityProfile` literally extends `ForecastabilityProfile`.

- the inherited fields keep the existing AMI-centric profile contract intact: horizons, AMI values, epsilon, informative horizons, peak horizon, monotonicity flag, summary, and horizon-review guidance
- the additive fields layer on deterministic routing context: `signal_strength`, `predictability_sources`, `noise_risk`, `recommended_model_families`, `avoid_model_families`, and `explanation`

This is the approved naming and compatibility direction for `0.4.2`: `ExtendedForecastabilityProfile`, not a silent replacement of `ForecastabilityProfile`.

## Scope In This Repository

- preserve the existing `ForecastabilityProfile` contract as the AMI-first foundation
- attach extended routing semantics only after the extended fingerprint has composed its diagnostic blocks
- keep the profile deterministic and JSON-friendly for downstream reporting and adapter layers
- stay aligned with hexagonal/SOLID boundaries where independent diagnostic services feed a composition layer, and a use case or routing layer derives the profile

## Non-Goals

- redefining or weakening the existing AMI profile semantics
- embedding forecast-model fitting logic inside the profile contract
- turning the profile into an adapter-owned reporting object
- using the profile as a substitute for richer walkthrough material in this repository

## Planned Public Surfaces

- `ExtendedForecastabilityProfile` on the additive stable facade and `forecastability.triage`
- `ExtendedForecastabilityAnalysisResult.profile` as the main consumer-facing placement of the profile
- the planned `run_extended_forecastability_analysis(...)` use case once later phases add end-to-end behavior

For the inherited AMI-centric profile fields, see [../theory/forecastability_profile.md](../theory/forecastability_profile.md).

## Later Phases

Phase 0 currently provides the additive typed contract and this explanation stub. The deterministic routing rules, profile-population logic, and richer usage examples land in later phases of the [v0.4.2 expansion plan](../plan/v0_4_2_forecastability_structure_expansion_ultimate_plan.md).

Richer walkthroughs and notebooks for this surface belong in the sibling `forecastability-examples` repository rather than the core repo.