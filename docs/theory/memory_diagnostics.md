<!-- type: explanation -->
# Memory Diagnostics

Memory diagnostics are the scale-based persistence summaries inside the AMI-first
extended fingerprint. They use a detrended-fluctuation-style path to describe
whether persistence appears short, persistent, anti-persistent, or too unstable
to classify.

> [!IMPORTANT]
> This block is intentionally conservative. It can support a claim that
> persistence survives across scale, but it does not prove long memory, unit
> roots, or forecast accuracy.

## What It Measures

The shipped `MemoryStructureResult` exposes a small, explicit public contract.

| Field | Meaning | Conservative reading |
| --- | --- | --- |
| `dfa_alpha` | Detrended fluctuation slope estimate when the fit is usable | A scale-based persistence summary, not a standalone model parameter |
| `hurst_proxy` | Hurst-style proxy when the DFA slope stays in the interpretable range | Withheld when interpretation would be unsafe |
| `memory_type` | Coarse label in `{anti_persistent, short_memory, persistent, long_memory_candidate, unclear}` | The primary human-facing summary of the block |
| `scale_range` | Inclusive minimum and maximum DFA scales used by the fit | Helps you judge how much scale support the slope used |
| `notes` | Deterministic caveats about fit quality, short series, or nonstationary contamination | Review these before treating the slope as stable |

## Why It Matters For Forecastability

Lagged information can come from persistence that extends beyond a few early
lags. The memory block adds a scale-based view that AMI geometry and classical
autocorrelation summaries do not provide directly.

- It distinguishes anti-persistent, near-short-memory, and more persistent
  regimes in a lightweight deterministic way.
- It can support the router's `long_memory` explanation source.
- It warns when persistence-looking behavior may actually reflect trend or
  broader nonstationary contamination.

## What It Does Not Prove

- It does not prove fractional integration or a true long-memory process.
- It does not replace formal stationarity testing or downstream residual checks.
- It does not imply that a long-window model will outperform simpler baselines.
- It does not justify routing-grade family recommendations when AMI geometry is
  disabled or unavailable.

## Input Assumptions

- The input must be a finite one-dimensional series after public validation.
- Interpretation improves when the series is long enough to support several
  valid DFA scales.
- `hurst_proxy` is only exposed when the fitted slope stays in a range the
  implementation treats as interpretable.
- The block is descriptive even when the scale-based fit warns about stability.

## Failure Modes

- Constant series return `memory_type = unclear` with missing slope fields.
- Too few valid scales force an `unclear` summary and an explicit note.
- `dfa_alpha > 1.0` is treated as a warning about possible trend or
  nonstationarity contamination, not as stronger evidence of memory.
- Short series can make the scale fit unstable even when the raw series looks
  persistent by eye.

## Synthetic Example

The example below uses a high-persistence AR(1) proxy. The expected outcome is
not a guaranteed `long_memory_candidate`, but a persistence-oriented reading
that stays caveat-heavy rather than claiming true long memory.

```python
from forecastability import generate_ar1, run_extended_forecastability_analysis

series = generate_ar1(n_samples=800, phi=0.95, random_state=42)
result = run_extended_forecastability_analysis(series, max_lag=40)
print(result.fingerprint.memory.model_dump())
```

Read the output with `notes` first. If the service warns about scale support or
nonstationarity, keep the interpretation descriptive.

## Interpretation Table

| `memory_type` | Typical reading | Forecastability implication |
| --- | --- | --- |
| `anti_persistent` | Reversions dominate across scale | Long memory is not the main story |
| `short_memory` | Scale behavior is close to short-memory baselines | Short-lag or seasonal structure may matter more |
| `persistent` | Persistence survives across scales without a stronger long-memory claim | Long-window downstream checks may be reasonable |
| `long_memory_candidate` | Persistence is strong enough to justify follow-up, but still caveat-heavy | Treat as a hand-off prompt, not as proof |
| `unclear` | Fit quality, sample length, or contamination prevents a stable label | Defer to other diagnostics |

## References

- C.-K. Peng et al., 1994, detrended fluctuation analysis for scale-based persistence
- Jan W. Kantelhardt et al., 2001, DFA interpretation guidance
- J. Feder, fractals and Hurst-style persistence context