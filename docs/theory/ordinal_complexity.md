<!-- type: explanation -->
# Ordinal Complexity

The F02 ordinal complexity block is now implemented as a deterministic summary of repeated order-pattern structure in a univariate series.

> [!IMPORTANT]
> The extended fingerprint remains AMI-first. Ordinal diagnostics explain whether forecastability appears to be supported by repeated ordering patterns or nonlinear ordinal redundancy; they do not replace lag-aware AMI evidence.

## What The Current Diagnostic Computes

The implemented service builds ordinal embeddings with configurable embedding dimension and delay, encodes their rank-order patterns, and reports:

- `permutation_entropy`: normalized entropy of the observed ordinal-pattern distribution
- `weighted_permutation_entropy`: an optional variance-weighted version of the same summary
- `ordinal_redundancy`: a unit-scale redundancy proxy computed as `1 - permutation_entropy`
- `complexity_class`: a conservative label such as `regular`, `structured_nonlinear`, `complex_but_redundant`, `noise_like`, `degenerate`, or `unclear`
- `notes`: caveats about ties, sparse embeddings, or degeneracy

Ties are handled explicitly with an average-rank policy and a tie-aware normalization of the ordinal state count. That matters for rounded, binary, or otherwise discrete-valued series where many embeddings are not strict permutations.

## How To Read The Main Fields

- Lower `permutation_entropy` means the series reuses a smaller subset of ordering patterns.
- Higher `ordinal_redundancy` means more repeated ordinal structure is present.
- The gap between unweighted and weighted entropy helps separate purely frequent patterns from patterns that also carry larger amplitude variation.

In deterministic triage terms, this block is useful when the AMI profile suggests informative horizons but you also want to know whether the local ordering patterns look regular, nonlinear-but-structured, or mostly noise-like.

## Conservative Sentinel Behavior

> [!WARNING]
> Short or degenerate ordinal outputs are conservative sentinel summaries. Interpret them through `notes` and `complexity_class`, not through the raw scalar fields alone.

The implemented service stays conservative in exactly the cases that are easiest to over-read:

- Constant series return a degenerate result with `complexity_class = degenerate`, `ordinal_redundancy = 1.0`, and an explicit note.
- Series that are too short for the requested embedding return `complexity_class = unclear` with short-sample notes.
- Sparse pattern counts relative to the ordinal state space force `complexity_class = unclear` even when scalar entropy values can still be computed.
- Tie-heavy inputs emit an explicit note so the reader does not mistake tie-aware ranks for strict permutation counts.

This is deliberate. The current implementation prefers a conservative label over a false sense of ordinal precision.

## What This Block Is Good For

- distinguishing repeated regular orderings from noise-like ordinal behavior
- highlighting nonlinear-looking structure that survives a purely rank-based view
- adding an explanatory block inside `ExtendedForecastabilityFingerprint.ordinal`

## Non-Goals

- certifying chaos, determinism, or nonlinear identifiability from one scalar summary
- replacing AMI/pAMI, surrogate-aware lag analysis, or classical diagnostics
- recommending one true best nonlinear model family
- documenting `run_extended_forecastability_analysis(...)` as a shipped public workflow before that later phase exists
- placing richer notebook walkthroughs in this repository

## Current Repository Scope

- the stable result model `OrdinalComplexityResult`
- the implemented ordinal diagnostic block used by the extended fingerprint composer
- theory and interpretation guidance for the shipped F02 behavior

F06 and later routing/use-case layers remain outside this page.

Richer walkthroughs and notebooks for ordinal-complexity interpretation belong in the sibling `forecastability-examples` repository rather than the core repo.