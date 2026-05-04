<!-- type: explanation -->
# Memory Structure

This Phase 0 page reserves the theory surface for the memory-structure block in the planned extended forecastability fingerprint.

> [!IMPORTANT]
> The extended fingerprint remains AMI-first. Memory diagnostics explain whether persistence appears to survive across scale; they do not replace lag-wise AMI evidence and they do not claim forecast accuracy directly.

## Purpose

Memory structure is intended to add a conservative long-memory proxy around the AMI-first fingerprint, using DFA- and Hurst-style summaries only as explanatory evidence about persistence across scale. In this repository, the role of the block is to help distinguish short-memory decay from longer-lived dependence patterns during deterministic forecastability triage.

## Scope In This Repository

- document the planned `MemoryStructureResult` contract for DFA alpha, Hurst proxy, memory label, and scale-range metadata
- keep the interpretation narrow and caveat-heavy, especially around short series and nonstationary inputs
- support the `ExtendedForecastabilityFingerprint.memory` block without pulling the repo toward model fitting or optional heavy dependencies
- preserve a clean service/use-case boundary where the diagnostic remains an inner computation surface and routing stays downstream

## Non-Goals

- acting as a full long-memory estimator, unit-root test, or fractional-integration proof
- replacing AMI, pAMI, or classical seasonal/trend evidence
- silently normalizing away nonstationarity warnings for the sake of a cleaner route
- shipping notebook walkthroughs in this repository

## Planned Public Surfaces

- `MemoryStructureResult` on the additive stable facade and `forecastability.triage`
- `ExtendedForecastabilityFingerprint.memory` as the memory block in the composite fingerprint
- future documentation for `compute_memory_structure(...)` and the planned `run_extended_forecastability_analysis(...)` use case once later phases deepen the implementation

## Phase Status

Phase 0 currently delivers the typed contract and this docs stub. The caveat-heavy interpretation guidance for DFA scaling, scale-range defaults, and persistence classification lands in later phases of the [v0.4.2 expansion plan](../plan/v0_4_2_forecastability_structure_expansion_ultimate_plan.md).

Richer walkthroughs and notebooks for memory-structure interpretation belong in the sibling `forecastability-examples` repository rather than the core repo.