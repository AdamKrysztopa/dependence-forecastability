<!-- type: explanation -->
# Classical Structure

This Phase 0 page reserves the theory surface for the classical-structure block in the planned extended forecastability fingerprint.

> [!IMPORTANT]
> The extended fingerprint remains AMI-first. Classical diagnostics explain whether forecastability appears to align with cheap trend, seasonality, and autocorrelation summaries; they do not replace the primary lagged-information analysis.

## Purpose

Classical structure is intended to capture the simplest deterministic summaries that often matter before any model family is considered: lag-1 autocorrelation, early-lag decay, optional seasonal strength, trend strength, and residual-variance context. In this repository, the goal is to explain structure sources during forecastability triage, not to perform decomposition-driven model fitting.

## Scope In This Repository

- document the planned `ClassicalStructureResult` contract used by the extended fingerprint
- explain why cheap classical summaries remain useful even in an AMI-first workflow
- keep the semantics at the level of structure detection and routing evidence
- stay consistent with service and use-case boundaries where a dedicated diagnostic service feeds a higher-level fingerprint builder

## Non-Goals

- replacing AMI/pAMI or the existing `ForecastabilityProfile`
- claiming that classical structure implies a particular downstream winner
- shipping automatic differencing, decomposition fitting, or framework-specific helpers from the core repo
- moving examples or walkthrough notebooks into this repository

## Planned Public Surfaces

- `ClassicalStructureResult` on the additive stable facade and `forecastability.triage`
- `ExtendedForecastabilityFingerprint.classical` as the classical structure block
- future documentation for `compute_classical_structure(...)` and the planned `run_extended_forecastability_analysis(...)` entry point after Phase 0 scaffolding

## Phase Status

Phase 0 currently provides the typed result model and this minimal theory stub. More detailed guidance on trend strength, seasonality strength, ACF-derived summaries, and interpretation thresholds lands in later phases of the [v0.4.2 expansion plan](../plan/v0_4_2_forecastability_structure_expansion_ultimate_plan.md).

Richer walkthroughs and notebooks for classical-structure reading belong in the sibling `forecastability-examples` repository rather than the core repo.