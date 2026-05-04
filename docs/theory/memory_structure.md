<!-- type: explanation -->
# Memory Structure

The F04 memory structure block is now implemented as a conservative detrended-fluctuation summary of persistence across scale.

> [!IMPORTANT]
> The extended fingerprint remains AMI-first. Memory diagnostics explain whether persistence appears to survive across scale; they do not replace lag-wise AMI evidence and they do not claim forecast accuracy directly.

## What The Current Diagnostic Computes

The implemented service uses a detrended fluctuation analysis style path:

- build the cumulative demeaned profile of the input series
- evaluate fluctuations across a deterministic geometric grid of scales
- fit a line to the log-scale versus log-fluctuation relationship
- report `dfa_alpha`, `hurst_proxy`, `memory_type`, `scale_range`, and `notes`

`memory_type` is intentionally coarse:

- `anti_persistent` for clearly sub-0.5 behavior
- `short_memory` near 0.5
- `persistent` for moderate persistence
- `long_memory_candidate` only when the slope remains at or below 1.0 but clearly above the short-memory band
- `unclear` whenever the fit is too unstable or the interpretation is not safe

When `dfa_alpha <= 1.0`, the service also exposes `hurst_proxy = dfa_alpha`. For `dfa_alpha > 1.0`, it withholds that proxy and emits an explicit warning note instead of pretending the value is a safe Hurst-style estimate.

## Conservative Sentinel Behavior

> [!WARNING]
> Short or degenerate memory outputs are conservative sentinel summaries. Interpret them through `notes` and `memory_type`, not through the raw scalar fields alone.

This matters in exactly the cases where DFA is easiest to overstate:

- Constant series return `dfa_alpha = None`, `hurst_proxy = None`, `scale_range = None`, and `memory_type = unclear`.
- If too few valid scales survive, the diagnostic returns the same conservative `unclear` shape with an explicit short-series note.
- Limited scale coverage or weak log-log fit quality produces a fit-stability note.
- `dfa_alpha > 1.0` is treated as a warning about nonstationarity or trend contamination, not as evidence of stronger long memory.

## What This Block Is Good For

- separating anti-persistent, near-short-memory, and more persistent regimes in a lightweight deterministic way
- warning when persistence-looking behavior may really be nonstationary contamination
- adding a scale-based explanatory block inside `ExtendedForecastabilityFingerprint.memory`

## Non-Goals

- acting as a full long-memory estimator, unit-root test, or fractional-integration proof
- replacing AMI, pAMI, or classical seasonal/trend evidence
- silently normalizing away nonstationarity warnings for the sake of a cleaner route
- documenting `run_extended_forecastability_analysis(...)` as a shipped public workflow before that later phase exists
- shipping notebook walkthroughs in this repository

## Current Repository Scope

- the stable result model `MemoryStructureResult`
- the implemented memory diagnostic block used by the extended fingerprint composer
- theory and interpretation guidance for the shipped F04 behavior

F06 and later routing/use-case layers remain outside this page.

Richer walkthroughs and notebooks for memory-structure interpretation belong in the sibling `forecastability-examples` repository rather than the core repo.