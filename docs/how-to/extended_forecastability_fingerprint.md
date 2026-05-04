<!-- type: how-to -->
# Extended Forecastability Fingerprint

Use this page as the Phase 0 reading-order stub for the planned extended forecastability fingerprint.

> [!IMPORTANT]
> The extended fingerprint is AMI-first. The spectral, ordinal, classical, and memory blocks explain likely sources of forecastability; they do not replace lagged-information analysis and they do not perform model fitting.

## Current Status

The repository currently ships the typed result models for the extended fingerprint surface and scaffolded service entry points. The end-to-end public use case is planned, but not yet implemented, so this page documents how the surface is intended to be read rather than presenting a completed walkthrough.

## Purpose

Use the extended fingerprint when you want one deterministic, explanation-oriented bundle that keeps AMI geometry at the center while adding cheap secondary structure signals around it.

## Scope

- read AMI geometry first, because it remains the primary lagged-information evidence
- use spectral, ordinal, classical, and memory blocks as explanatory context around that AMI evidence
- read the human-facing routing layer through `ExtendedForecastabilityProfile`, which additively extends the existing `ForecastabilityProfile`
- keep any downstream model-family guidance at the level of starting families, not fitted winners

## Non-Goals

- skipping straight to downstream fitting or benchmark comparisons
- treating the extended fingerprint as a replacement for `run_triage()`
- treating any routed family list as a guaranteed best model
- expecting notebook-first showcase material in this repository

## Planned Public Surfaces

- `ExtendedForecastabilityFingerprint` as the composite structure surface
- `ExtendedForecastabilityProfile` as the human-facing routing summary layered on top of the existing profile contract
- `ExtendedForecastabilityAnalysisResult` as the planned top-level result container
- the planned `run_extended_forecastability_analysis(...)` entry point once post-Phase-0 implementation lands

## Intended Reading Order

1. Start with the existing AMI information geometry and the inherited `ForecastabilityProfile` fields.
2. Read `spectral`, `ordinal`, `classical`, and `memory` only as additive explanations for why forecastability may exist.
3. Use `ExtendedForecastabilityProfile` to summarize signal strength, predictability sources, noise risk, and conservative family guidance.
4. Hand any downstream modeling work off to external forecasting tooling after triage, not inside this core repository.

## Later Phases

This stub will deepen once the build logic and public use case land. When richer examples, walkthroughs, and notebooks are added, they belong in the sibling `forecastability-examples` repository rather than in this core repo.