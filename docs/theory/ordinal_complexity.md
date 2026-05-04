<!-- type: explanation -->
# Ordinal Complexity

This Phase 0 page reserves the theory surface for the ordinal-pattern block in the planned extended forecastability fingerprint.

> [!IMPORTANT]
> The extended fingerprint remains AMI-first. Ordinal diagnostics explain whether forecastability appears to be supported by repeated ordering patterns or nonlinear ordinal redundancy; they do not replace lag-aware AMI evidence.

## Purpose

Ordinal complexity is intended to summarize how structured or redundant the ordering patterns of a series look under deterministic embedding choices. In this repository, the goal is not to declare a series chaotic or solved, but to provide a cheap explanation layer around AMI-first triage when rank-order structure is materially present.

## Scope In This Repository

- document the planned `OrdinalComplexityResult` contract for permutation-entropy-style summaries
- explain how permutation entropy, weighted permutation entropy, and ordinal redundancy support the extended fingerprint
- keep the output tied to deterministic triage semantics instead of downstream benchmark performance
- preserve clean service and use-case boundaries so ordinal diagnostics stay composable with the rest of the fingerprint

## Non-Goals

- certifying chaos, determinism, or nonlinear identifiability from one scalar summary
- replacing AMI/pAMI, surrogate-aware lag analysis, or classical diagnostics
- recommending one true best nonlinear model family
- placing richer notebook walkthroughs in this repository

## Planned Public Surfaces

- `OrdinalComplexityResult` on the additive stable facade and `forecastability.triage`
- `ExtendedForecastabilityFingerprint.ordinal` as the ordinal-complexity block
- future documentation for `compute_ordinal_complexity(...)` and the planned `run_extended_forecastability_analysis(...)` use case once later phases land

## Phase Status

Phase 0 currently defines the typed result surface and this docs stub only. The deeper treatment of embedding choices, degeneracy handling, and interpretation examples is deferred to later phases of the [v0.4.2 expansion plan](../plan/v0_4_2_forecastability_structure_expansion_ultimate_plan.md).

Richer walkthroughs and notebooks for ordinal-complexity interpretation belong in the sibling `forecastability-examples` repository rather than the core repo.