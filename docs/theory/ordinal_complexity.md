<!-- type: explanation -->
# Ordinal Complexity

Ordinal complexity is the rank-pattern block inside the AMI-first extended
fingerprint. It summarizes whether short local windows of the series reuse a
small family of orderings or span a broader, more noise-like ordinal state
space.

> [!IMPORTANT]
> Ordinal diagnostics are explanatory and conservative. They can support a
> claim that the series has repeated local ordering structure, but they do not
> replace lag-aware AMI evidence and they do not certify nonlinear forecast
> accuracy.

## What It Measures

The shipped `OrdinalComplexityResult` is built from ordinal embeddings with a
public embedding dimension and delay.

| Field | Meaning | Conservative reading |
| --- | --- | --- |
| `permutation_entropy` | Normalized entropy of the observed ordinal-pattern distribution | Lower values mean fewer orderings are reused more often |
| `weighted_permutation_entropy` | Optional variance-weighted entropy summary | Compare with unweighted entropy to see whether larger-amplitude patterns behave differently |
| `ordinal_redundancy` | Unit-scale redundancy proxy computed from ordinal entropy | Higher values indicate more repeated ordinal structure |
| `embedding_dimension` | Embedding size used to extract patterns | Larger values need longer series and more distinct patterns |
| `delay` | Step between samples inside each ordinal vector | This changes which local ordering regime is being summarized |
| `complexity_class` | Conservative label in `{degenerate, regular, structured_nonlinear, complex_but_redundant, noise_like, unclear}` | Treat this as the primary verbal summary |
| `notes` | Deterministic caveats about ties, sparsity, or degeneracy | Read these before trusting the scalar values |

Ties are handled explicitly. Rounded, discrete, or binary-valued series can
still be summarized, but tie-heavy data should be read through `notes` rather
than as strict permutation counts.

## Why It Matters For Forecastability

AMI geometry can show that dependence exists at useful horizons without telling
you whether the local state transitions look regular, redundant, or mostly
noise-like. The ordinal block adds that local-ordering perspective.

- It distinguishes repeated short-window orderings from diffuse ordinal
  behavior.
- It can support the router's `ordinal_redundancy` explanation source.
- It gives a rank-based view that is less sensitive to absolute scale than a
  raw amplitude summary.

## What It Does Not Prove

- It does not prove deterministic chaos, nonlinear identifiability, or the need
  for a neural model.
- It does not prove that tree, boosting, or other nonlinear families will win
  downstream.
- It does not replace AMI, pAMI, seasonality structure, or scale-based memory
  diagnostics.
- It does not justify routing on its own when AMI geometry is disabled.

## Input Assumptions

- The input must be a finite one-dimensional series after public validation.
- The series must be long enough to support the requested
  `embedding_dimension` and `delay`.
- Interpretation becomes fragile when the realized ordinal state count is sparse
  relative to the possible state space.
- Tie-heavy inputs remain valid but require more conservative reading.

## Failure Modes

- Constant series return `complexity_class = degenerate` with an explicit note.
- Too-short series return `complexity_class = unclear` because the embedding is
  not safely supported.
- Sparse ordinal occupancy can make entropy values look stable while the state
  coverage is still too weak for a strong class label.
- Heavy rounding or repeated values can flatten distinctions between genuinely
  different local mechanisms.

## Synthetic Example

The public example below uses a logistic-map style sequence as a mechanically
plausible nonlinear ordering pattern source. The expected read is not an exact
label, but a structured result rather than `noise_like`.

```python
import numpy as np

from forecastability import run_extended_forecastability_analysis

def logistic_map(n: int, r: float = 3.9, x0: float = 0.2) -> np.ndarray:
    values = np.empty(n, dtype=float)
    values[0] = x0
    for index in range(1, n):
        values[index] = r * values[index - 1] * (1 - values[index - 1])
    return values

series = logistic_map(500)[100:]
result = run_extended_forecastability_analysis(series, max_lag=24)
print(result.fingerprint.ordinal.model_dump())
```

Use the ordinal block as an explanatory layer. The primary routing read still
comes from the AMI-backed `profile` and from whether the result is
descriptive-only.

## Interpretation Table

| `complexity_class` | Typical reading | Forecastability implication |
| --- | --- | --- |
| `degenerate` | The series has too little ordinal variation to summarize meaningfully | Treat as a low-information edge case |
| `regular` | A small set of orderings dominates the local windows | Repeated local structure is present |
| `structured_nonlinear` | Rank-pattern structure is present without looking purely regular | A nonlinear follow-up may be worth checking after AMI evidence |
| `complex_but_redundant` | Diversity and reuse coexist | Structure is present, but the mechanism is not simple |
| `noise_like` | Ordinal patterns look broadly diffuse | Do not infer nonlinear benefit from this block |
| `unclear` | Sample support or tie structure is too weak for a stable label | Defer to other diagnostics |

## References

- Christoph Bandt and Bernd Pompe, 2002, "Permutation Entropy"
- Karsten Keller and colleagues, tie-aware and weighted ordinal-pattern extensions
- Holger Kantz and Thomas Schreiber, 2004, nonlinear time-series analysis context