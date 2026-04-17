<!-- type: explanation -->
# Covariant Role Assignment

Explains the seven-rule priority algorithm in
`_assign_role` inside
[src/forecastability/services/covariant_interpretation_service.py](../../src/forecastability/services/covariant_interpretation_service.py).

_Last verified for V3-F09 on 2026-04-17._

---

## Background

After `run_covariant_analysis` produces a `CovariantAnalysisBundle`, the
deterministic interpretation service assigns each candidate driver a **role
tag** — a single label that summarises the driver's relationship to the target
series given the available evidence.  The assignment is intentionally rigid:
rules are evaluated in a fixed priority order and the first matching rule wins.
No probabilistic weighting or post-hoc override is performed.

The role tag feeds two downstream aggregates:

- **`forecastability_class`** (`high` / `medium` / `low`) — derived from
  whether any driver earns `direct_driver` or `nonlinear_driver`.
- **`directness_class`** (`high` / `medium` / `low` / `mixed`) — derived from
  the balance between direct-like and mediated-like drivers in the bundle.

Together these two classes select a **modeling regime** from the
$12 \times \{high, medium, low, mixed\}$ lookup table in the service.

---

## The Seven Roles

| Role tag | Scientific meaning |
|---|---|
| `noise_or_weak` | All effect-size metrics are sub-threshold and no lag is surrogate-significant.  The driver does not meaningfully share information with the target at any tested lag. |
| `direct_driver` | PCMCI+ or PCMCI-AMI identified the driver as a lagged causal parent of the target under full multivariate conditioning (MCI test).  This is the strongest causal claim the toolkit makes. |
| `contemporaneous` | PCMCI+ identified the driver as a *lag-0* causal parent only.  A genuine instantaneous coupling that cannot be detected by cross-AMI (which is lag-indexed). |
| `nonlinear_driver` | Cross-AMI is above the noise floor ($I_h \geq 0.03$) but GCMI is below the noise floor ($I_{GCMI} < 0.01$) and at least two lags are surrogate-significant.  This pattern indicates a nonlinear coupling that linear GCMI misses but AMI detects.  No PCMCI causal evidence is available. |
| `redundant` | Both AMI and GCMI are strong ($\geq 0.10$) *and* another lagged parent already exists in the causal graph.  The driver covaries with the target but its information is already captured by another confirmed driver. |
| `mediated_driver` | AMI is strong ($\geq 0.10$) but cross-pAMI is small relative to AMI ($\tilde{I} / I < 0.30$), indicating that most of the observed dependence is indirect — passing through intermediate variables.  Requires at least one causal method in the bundle. |
| `inconclusive` | Evidence exists (e.g. surrogate-significant lags) but the driver does not satisfy any canonical pattern.  Manual review is required. |

---

## Rule Priority Ordering

```
Rule 1  noise_or_weak        ← exits early for genuine noise
Rule 2  direct_driver        ← strongest evidence, causal methods
Rule 3  contemporaneous      ← lag-0 causal, PCMCI only
Rule 4  nonlinear_driver     ← nonlinear signature, surrogate-guarded
Rule 5  redundant            ← redundancy check, requires other parent
Rule 6  mediated_driver      ← mediation claim, requires causal method
Rule 7  inconclusive         ← fallback
```

**Why order matters.**

_Rules 4 and 5 are deliberately sequenced before Rule 6._  A driver that
satisfies both the nonlinear-driver condition (Rule 4) and the redundant
condition (Rule 5) could also satisfy the mediated-driver condition if
`max_pami / max_ami < 0.30`.  Assigning `redundant` before `mediated_driver`
prevents a driver that is genuinely redundant (another causal parent already
covers it) from being relabelled as mediated just because pAMI is low.

_Rule 1 must precede all other rules._  It uses `not any_sig` as a hard gate.
If any lag is surrogate-significant, the driver cannot be dismissed as noise
even when all numeric thresholds are sub-threshold; it falls through to the
most appropriate rule given the remaining evidence, or ultimately to
`inconclusive`.  Swapping Rule 1 into a later position would let a
spuriously-significant driver silently disappear.

_Rules 2 and 3 are ordered by causal strength._  Lagged PCMCI parenthood
(Rule 2) subsumes contemporaneous-only parenthood (Rule 3) because a driver
that appears as both lagged *and* lag-0 parent is already classified as
`direct_driver`.  Rule 3 only fires when *all* PCMCI links for a driver are
at lag 0.

---

## Numeric Thresholds

| Constant | Value | Role(s) governed |
|---|---|---|
| `STRONG_MI_NUMERIC` | 0.10 | direct_driver gate, redundant, mediated_driver |
| `NOISE_AMI_CEIL` | 0.03 | noise_or_weak ceiling |
| `NONLINEAR_AMI_MIN` | 0.03 | nonlinear_driver minimum AMI |
| `GCMI_NOISE_FLOOR` | 0.01 | nonlinear_driver GCMI ceiling |
| `MEDIATION_RATIO` | 0.30 | mediated_driver pAMI/AMI ratio cap |

These defaults were approved by the project statistician.  They can be
overridden via keyword arguments to `interpret_covariant_bundle()`, but
**not** through the CLI or the showcase script, which use the module defaults.

---

## The Bonferroni Guard on `nonlinear_driver`

Phase-randomised surrogate tests are run independently for each lag in the
range $[1, \text{max\_lag}]$.  With `max_lag=5` and a nominal $\alpha = 0.05$
level, the expected number of false positives under the null hypothesis of no
dependence is $5 \times 0.05 = 0.25$, meaning one spurious significant lag is
entirely plausible over a single run.

Rule 4 therefore requires `sig_count >= 2` — *at least two lags must be
above the surrogate band*.  A single significant lag is insufficient to claim
`nonlinear_driver`.  This acts as a Bonferroni-style correction against the
per-lag false-positive rate without introducing an explicit multiple-testing
procedure.

The guard interacts with `--n`:

- At the default `n=1500`, weak nonlinear couplings (such as `driver_nonlin_abs`
  with $\beta \approx 0.35$ in the synthetic benchmark) frequently produce only
  zero or one significant lag.  The role degrades to `noise_or_weak` or
  `inconclusive`.
- At `n >= 5000`, statistical power is sufficient for the multi-lag requirement
  to be met reliably on both `driver_nonlin_sq` and `driver_nonlin_abs`.

---

## Why `mediated_driver` Requires a Causal Method (`has_causal`)

Cross-pAMI (pCrossAMI) is conditioned on the **target's own history only**:

$$\tilde{I}(X^{\text{driver}}, X^{\text{target}}_{t+h} \mid X^{\text{target}}_{t+1}, \ldots, X^{\text{target}}_{t+h-1})$$

This conditioning removes autocorrelation from the target side but does **not**
condition on other drivers.  Consequently, a low pAMI/AMI ratio could arise
because:

1. The driver is genuinely mediated through intermediate variables (true
   mediation), or
2. The driver covaries with another strong driver that is already explaining
   most target variance (shared latent cause, not mediation).

Without PCMCI+ or PCMCI-AMI, which condition on the full reconstructed parent
set, these two cases cannot be distinguished.  Claiming mediation without any
causal method in the bundle would therefore be scientifically unsupported.

> [!IMPORTANT]
> pAMI is a project extension and approximate direct-dependence diagnostic.
> It is not exact conditional mutual information and is not a causal proof.
> See [wording_policy.md](../wording_policy.md).

When no causal method is present (`has_causal=False`), a driver that would
otherwise satisfy the mediated-driver condition falls through to `inconclusive`.

---

## Power Limitations for Weak Couplings

The synthetic benchmark includes `driver_nonlin_abs`, a weak absolute-value
nonlinear driver with coupling strength $\beta \approx 0.35$.  At the default
`n=1500`, the surrogate test lacks sufficient power to consistently identify
two or more significant lags for this driver.

Accepted outcomes in the benchmark verifier are therefore:

```
driver_nonlin_abs: {"nonlinear_driver", "direct_driver", "noise_or_weak", "inconclusive"}
```

This is not a defect in the algorithm.  It is an honest acknowledgement that
surrogate significance is optional and conditional on feasible sample size, and
requires at least 99 surrogates.  See [wording_policy.md](../wording_policy.md).

Practitioners encountering a weak driver at `inconclusive` or `noise_or_weak`
should either increase series length or accept the result as power-limited.

---

## Triage Mode vs Full Mode

**Full mode** — the bundle contains `pcmci_graph` or `pcmci_ami_result` (or both).
Rules 2, 3, 5, and 6 can fire.  `has_causal=True` gates Rule 6.

**Triage mode** — the bundle has neither PCMCI result.  Rules 2, 3, and 6 can
never fire because their PCMCI-based conditions are always `False` and
`has_causal=False`.  In this mode:

- Drivers that would be `direct_driver` under full mode fall through to Rule 4
  (if nonlinear evidence exists) or to `inconclusive`.
- `mediated_driver` is never assigned; drivers with a low pAMI/AMI ratio land
  on `inconclusive`.
- `contemporaneous` is never assigned; lag-0 drivers that lack AMI signal land
  on `noise_or_weak`.

The ground-truth verifier in `run_showcase_covariant.py` detects whether the
bundle is in triage mode (`has_causal=False`) and relaxes accepted role sets
accordingly: every driver's accepted set gains `inconclusive` in triage mode.
The `driver_noise` constraint (must never appear in `primary_drivers`) applies
in both modes.

```
Full mode:   direct_driver, contemporaneous, nonlinear_driver,
             redundant, mediated_driver available
Triage mode: nonlinear_driver, noise_or_weak, redundant available;
             inconclusive replaces causal-evidence-dependent outcomes
```

---

## Downstream Aggregates

`_derive_forecastability_class` inspects driver roles and returns:

| Condition | `forecastability_class` |
|---|---|
| Any driver is `direct_driver` or `nonlinear_driver` | `high` |
| All drivers are `noise_or_weak` | `low` |
| Otherwise | `medium` |

`_derive_directness_class` counts non-noise drivers by role family:

| Condition | `directness_class` |
|---|---|
| Majority direct-like (`direct_driver`, `contemporaneous`) | `high` |
| Majority mediated-like (`mediated_driver`, `redundant`) | `low` |
| Equal direct and mediated counts, both > 0 | `mixed` |
| Otherwise | `medium` |

The $(forecastability\_class, directness\_class)$ pair selects a modeling regime
label from a $4 \times 3$ lookup table.  The regime is informational guidance;
it does not alter the role tags.

---

## Cross-References

- [covariant_summary_table.md](covariant_summary_table.md) — per-row metric layout
- [pcmci_plus.md](pcmci_plus.md) — PCMCI+ MCI test and conditioning semantics
- [pami_residual_backends.md](pami_residual_backends.md) — pAMI conditioning limitation
- Source: [covariant_interpretation_service.py](../../src/forecastability/services/covariant_interpretation_service.py)
- Tests: [test_covariant_interpretation_service.py](../../tests/test_covariant_interpretation_service.py)
