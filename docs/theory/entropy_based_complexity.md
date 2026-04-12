<!-- type: explanation -->
# Entropy-Based Complexity Triage (F6)

**Paper grounding:**
- Bandt, C. & Pompe, B. (2002). *Permutation entropy: a natural complexity measure for time series.* Physical Review Letters, 88(17), 174102.
- Ponce-Flores, M. et al. (2020). *Time series complexity and the predictability of international stock markets.* Entropy, 22(10), 1150.
- Wang, Y. et al. (2025). *Spectral predictability and complexity diagnostics.* arXiv:2507.13556.

---

## Purpose

Entropy-based complexity triage provides **complementary, pre-model diagnostics**
that characterise the ordinal and spectral disorder of a time series.  These
measures do not replace the AMI/pAMI forecastability analysis; they contextualise
it by answering:

> "Is the dynamics regular, moderately structured, or noise-like?"

A high AMI at short lags combined with **low complexity** typically signals a
regular, easily modelled structure.  High AMI combined with **high complexity**
suggests nonlinear or chaotic dynamics where conventional models may underperform.

> [!WARNING]
> Complexity measures are **complementary triage tools**, not sole decision-makers.
> The forecastability ceiling is set by the AMI curve, not by entropy values.

---

## Permutation Entropy

### Definition

Given a time series $\{y_t\}$ and embedding order $m \geq 2$, construct
delay-coordinate vectors:

$$
\mathbf{x}_t = (y_t,\; y_{t+1},\; \dots,\; y_{t+m-1})
$$

For each vector, record the **ordinal pattern** (rank permutation) $\pi \in S_m$
by stable-sorting the elements (ties broken by position, not randomly).

The **permutation entropy** is:

$$
H_{\mathrm{perm}} = -\sum_{\pi \in S_m} p(\pi)\,\log p(\pi)
$$

Normalised to $[0, 1]$ by dividing by the maximum possible entropy $\log(m!)$:

$$
H_{\mathrm{perm}}^{\mathrm{norm}} = \frac{H_{\mathrm{perm}}}{\log(m!)}
$$

* $H_{\mathrm{perm}}^{\mathrm{norm}} \approx 0$ — highly regular ordinal structure
  (e.g.\ pure sine wave, where only $\leq 2$ of $m!$ patterns appear).
* $H_{\mathrm{perm}}^{\mathrm{norm}} \approx 1$ — all ordinal patterns appear
  equiprobably (white-noise-like behaviour).

### Tie-breaking rule

When elements within a window are **equal**, ties are broken by the element's
**position** in the window (i.e.\ `numpy.argsort` with `kind="stable"`).  This
rule is fixed and deterministic; it is documented here to ensure reproducibility
and to distinguish our implementation from alternatives that use random jitter.

### Embedding order selection

The embedding order $m$ is chosen from series length $n$:

| $n$          | $m$ |
|---|---|
| $n \geq 1000$ | 5 |
| $100 \leq n < 1000$ | 4 |
| $n < 100$ | 3 |

> [!NOTE]
> For $m = 5$ the number of possible ordinal patterns is $5! = 120$.  Reliable
> frequency estimates require $n \geq m! \times C$ for some constant $C$; the
> Bandt & Pompe (2002) practical recommendation is $n \geq 5 \times m!$, which
> gives $n \geq 600$ for $m = 5$.  The threshold of 1 000 used here is
> conservative and stated explicitly in reliability warnings.

### Sample-size guidelines

| $m$ | Reliable for |
|---|---|
| 3 | $n \geq 20$ |
| 4 | $n \geq 100$ |
| 5 | $n \geq 1000$ |

When the series is too short for the chosen $m$, the implementation emits a
`pe_reliability_warning` field in `ComplexityBandResult`.

---

## Spectral Entropy

### Definition

Given a normalised power-spectral-density (PSD) vector $\mathbf{p}$ (computed
via Welch's method, mean-centred), the **spectral entropy** is:

$$
H_{\mathrm{SE}} = -\sum_i p_i \log p_i
$$

Normalised by $\log(N_{\mathrm{bins}})$ where $N_{\mathrm{bins}}$ is the
number of frequency bins:

$$
H_{\mathrm{SE}}^{\mathrm{norm}} = \frac{H_{\mathrm{SE}}}{\log(N_{\mathrm{bins}})}
$$

> [!WARNING]
> Normalise by the **number of frequency bins**, not by $\log(n)$.
> Normalising by sample size makes the metric sample-size-dependent.

* $H_{\mathrm{SE}}^{\mathrm{norm}} \approx 0$ — spectrally concentrated signal
  (dominant frequency, strong periodicity).
* $H_{\mathrm{SE}}^{\mathrm{norm}} \approx 1$ — flat spectrum (white noise).

---

## Complexity Band Classification

The two normalised entropy values $\hat{H}_{\mathrm{PE}}$ and
$\hat{H}_{\mathrm{SE}}$ are combined into a **composite score**:

$$
c = \frac{\hat{H}_{\mathrm{PE}} + \hat{H}_{\mathrm{SE}}}{2}
$$

Band assignment:

| Composite score $c$ | Band | Interpretation |
|---|---|---|
| $c < 0.40$ | `low` | Regular / periodic; simple models likely sufficient |
| $0.40 \leq c \leq 0.65$ | `medium` | Moderate disorder; structured models recommended |
| $c > 0.65$ | `high` | Stochastic / chaotic-like; nonlinear models may help |

The thresholds 0.40 and 0.65 are **heuristic and configurable** via the
`low_threshold` and `high_threshold` parameters of `build_complexity_band()`.

> [!IMPORTANT]
> Entropy is **amplitude-blind** — PE and SE measure ordinal / spectral disorder
> but not signal magnitude.  A high-amplitude but strictly periodic signal will
> still appear as `low` complexity.  Always interpret complexity bands alongside
> the AMI/pAMI forecastability profile.

---

## What Entropy Is Not

| Claim | Correct? |
|---|---|
| "High PE means the series is not forecastable" | **No** — nonlinear predictability can survive high ordinal entropy |
| "Low SE means the series is easily modelled" | **Partially** — it means linear structure is present, but nonlinearities may still matter |
| "Complexity band can replace AMI triage" | **No** — it is a complementary diagnostic, not a substitute |
| "PE detects chaotic attractors reliably at n < 500" | **No** — bias is significant; use as indicative only |

---

## Implementation Notes

| Component | Location |
|---|---|
| `_compute_permutation_entropy()` | `forecastability/scorers.py` |
| `_permutation_entropy_scorer()` | `forecastability/scorers.py` |
| `_spectral_entropy_scorer()` | `forecastability/scorers.py` |
| `ComplexityBandResult` (domain model) | `forecastability/triage/complexity_band.py` |
| `build_complexity_band()` (service) | `forecastability/services/complexity_band_service.py` |
| Registered as `"permutation_entropy"` / `"spectral_entropy"` | `default_registry()` in `scorers.py` |
| Integrated in `TriageResult.complexity_band` | `forecastability/triage/run_triage.py` Stage 7 |

---

## Limitations and Failure Modes

1. **Amplitude blindness**: PE is invariant to monotone transformations of the
   values. Two series with very different amplitudes but the same ordinal patterns
   yield identical PE.

2. **Short series bias**: At $n < 100$ with $m = 4$, many ordinal patterns are
   never observed, artificially deflating entropy.  Always check
   `ComplexityBandResult.pe_reliability_warning`.

3. **Non-stationarity**: PE and SE assume at least weak stationarity.  For
   strongly trending or regime-switching series, pre-detrend or interpret with
   caution.

4. **PSD estimation**: Welch's method uses overlapping segments.  The default
   segment length is `min(n, 256)`.  Very short series may produce coarse
   spectral estimates.

5. **Complementarity is not independence**: PE and SE are correlated for many
   processes.  A series near the diagonal of the PE–SE plane is genuinely
   ambiguous; do not over-interpret band boundaries.
