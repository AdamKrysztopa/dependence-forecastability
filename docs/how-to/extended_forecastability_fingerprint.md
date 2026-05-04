<!-- type: how-to -->
# Extended Forecastability Fingerprint

Use this page when you want to read the currently implemented AMI-first extended fingerprint surface without assuming the later-phase routing use case already exists.

> [!IMPORTANT]
> The extended fingerprint is AMI-first. The spectral, ordinal, classical, and memory blocks explain likely sources of forecastability; they do not replace lagged-information analysis and they do not perform model fitting.

## Current Status

The repository now implements the broad Phase 1 fingerprint blocks:

- F01 spectral forecastability
- F02 ordinal complexity
- F03 classical structure
- F04 memory structure
- F05 extended fingerprint composition

What is still not implemented is the later-phase public routing/use-case layer, including `run_extended_forecastability_analysis(...)`. This page therefore documents how to read the shipped fingerprint surface today, not a later end-to-end public analysis workflow.

## Purpose

Use the extended fingerprint when you want one deterministic, explanation-oriented bundle that keeps AMI geometry at the center while adding cheap secondary structure signals around it.

## Scope

- read AMI geometry first, because it remains the primary lagged-information evidence
- use spectral, ordinal, classical, and memory blocks as explanatory context around that AMI evidence
- keep the currently implemented reading path at the fingerprint level rather than claiming the routing profile is already populated by a public use case
- keep any downstream model-family guidance outside this core repository and after triage rather than inside the fingerprint surface

## Non-Goals

- skipping straight to downstream fitting or benchmark comparisons
- treating the extended fingerprint as a replacement for `run_triage()`
- treating the unimplemented `run_extended_forecastability_analysis(...)` path as already shipped
- expecting notebook-first showcase material in this repository

## What Is Implemented Now

- `ExtendedForecastabilityFingerprint` as the composite structure surface
- AMI-first composition that keeps `information_geometry` when feasible and independently computes `spectral`, `ordinal`, `classical`, and `memory`
- graceful degradation when AMI geometry is infeasible for short or degenerate inputs
- `None` preservation for disabled optional blocks inside the composite result

The stable facade currently exposes the extended result models. The implemented block composition lives below that facade in the service layer; the top-level public use case remains a later phase.

## How To Read The Fingerprint Today

1. Start with the existing AMI information geometry and the inherited `ForecastabilityProfile` fields.
2. Read `spectral`, `ordinal`, `classical`, and `memory` only as additive explanations for why forecastability may exist.
3. Treat `notes` and categorical labels as part of the result contract, especially for short, constant, sparse, or otherwise conservative outputs.
4. Hand any downstream modeling work off after triage, not inside this core repository.

## Current Composition Rules

- shared validation requires a finite one-dimensional input series
- `max_lag` is validated before optional lag-aware blocks run
- `period` is validated before the classical block runs, even if that block is later disabled
- `seasonal_strength` is only computed when `period` is supplied
- disabling a block preserves `None` in the corresponding fingerprint field instead of fabricating a placeholder result

## Theory Cross-References

- [../theory/spectral_forecastability.md](../theory/spectral_forecastability.md)
- [../theory/ordinal_complexity.md](../theory/ordinal_complexity.md)
- [../theory/classical_structure.md](../theory/classical_structure.md)
- [../theory/memory_structure.md](../theory/memory_structure.md)

## Later Phases

Later phases are expected to populate `ExtendedForecastabilityProfile`, `ExtendedForecastabilityAnalysisResult`, and the public routing/use-case path. When richer examples, walkthroughs, and notebooks are added, they belong in the sibling `forecastability-examples` repository rather than in this core repo.
