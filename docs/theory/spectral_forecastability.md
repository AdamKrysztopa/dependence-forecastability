<!-- type: explanation -->
# Spectral Forecastability

This Phase 0 page reserves the theory surface for the spectral block in the planned extended forecastability fingerprint.

> [!IMPORTANT]
> The extended fingerprint remains AMI-first. Spectral diagnostics explain whether periodic or frequency-concentrated structure may be contributing to forecastability; they do not replace lagged-information analysis.

## Purpose

Spectral forecastability is intended to summarize whether a univariate series concentrates power into a small number of frequencies rather than spreading it diffusely across the spectrum. In this repository, that signal is a deterministic triage aid: it helps explain why a series may be forecastable before any downstream model search begins.

## Scope In This Repository

- add a cheap, deterministic spectral summary layer beside the existing AMI information geometry
- document the future `SpectralForecastabilityResult` block used inside `ExtendedForecastabilityFingerprint`
- keep the interpretation limited to structure detection, not forecast scoring or model fitting
- stay compatible with service and use-case boundaries where an inner diagnostic service feeds a higher-level composition/use-case layer

## Non-Goals

- replacing AMI or pAMI as the primary lagged-information evidence
- proving that a particular seasonal model will win downstream
- turning the core package into a generic feature-extraction or model-selection zoo
- hosting notebook-first walkthroughs in this repository

## Planned Public Surfaces

- `SpectralForecastabilityResult` on the additive stable facade and `forecastability.triage`
- `ExtendedForecastabilityFingerprint.spectral` as the spectral block in the composite fingerprint
- future documentation for `compute_spectral_forecastability(...)` and the planned `run_extended_forecastability_analysis(...)` entry point once post-Phase-0 behavior is implemented

## Phase Status

Phase 0 currently establishes the typed contract and documentation stub. Detailed math notes, validation heuristics, caveats around detrending and dominant-period extraction, and richer interpretation examples land in later phases of the [v0.4.2 expansion plan](../plan/v0_4_2_forecastability_structure_expansion_ultimate_plan.md).

Richer walkthroughs and notebooks for this surface belong in the sibling `forecastability-examples` repository rather than the core repo.