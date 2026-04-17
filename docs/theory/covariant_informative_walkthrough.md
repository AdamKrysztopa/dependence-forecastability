<!-- type: explanation -->
# Covariant Informative Walkthrough

Theory-facing explanation for the live covariant walkthrough notebook:
[../../notebooks/walkthroughs/01_covariant_informative_showcase.ipynb](../../notebooks/walkthroughs/01_covariant_informative_showcase.ipynb)

## Why the walkthrough exists

The covariant benchmark is intentionally built so that not every strong
pairwise driver is a structural parent. The target is influenced by:

- a lagged direct driver
- a mediated driver
- a contemporaneous driver
- two nonlinear drivers

The system also contains:

- a redundant driver that is strongly associated but not causal
- a pure-noise driver

That mix makes a single dependence score insufficient. The notebook therefore
walks through multiple methods on the same benchmark so the user can see which
claims survive stronger conditioning.

## What each section is testing

| Section | Theoretical question |
| --- | --- |
| CrossAMI | Which drivers share lagged information with the target? |
| CrosspAMI | Which of those signals survive conditioning on the target's own past? |
| GCMI | Does the dependence remain after rank-Gaussianisation and monotone marginal distortion? |
| TE | Does the dependence look directional rather than symmetric? |
| PCMCI+ | Which links survive multivariate conditional-independence testing? |
| PCMCI-AMI | Can an AMI screen prune the search space before causal discovery without changing the interpretation goal? |

## Conditioning hierarchy

The walkthrough is built around the fact that the methods do not condition on
the same information set.

| Method | Scope | Interpretation |
| --- | --- | --- |
| `cross_ami` | `none` | Pairwise lagged dependence only |
| `gcmi` | `none` | Pairwise lagged dependence after Gaussian-copula transform |
| `cross_pami` | `target_only` | Removes the target's own autoregressive history |
| `transfer_entropy` | `target_only` | Directional, but still does not condition on other drivers |
| `pcmci` | `full_mci` | Multivariate causal filtering |
| `pcmci_ami` | `full_mci` | Multivariate causal filtering after AMI-based pruning |

This is the central reason the notebook contains a dedicated limitation section:
pairwise and target-only methods are informative screens, not final causal
arbiters.

## Why the benchmark includes nonlinear drivers

`driver_nonlin_sq` and `driver_nonlin_abs` are designed so that linear
correlation-style methods can miss them while information-theoretic methods can
still detect dependence. In the walkthrough:

- `cross_ami` can detect the dependence
- `gcmi` can stay weak because the dependence is not monotone
- `pcmci` with linear `parcorr` should be treated cautiously for those drivers

That is why the notebook pairs the method figures with the deterministic role
assignment from `interpret_covariant_bundle()`.

## Why TE and PCMCI are both needed

Transfer entropy and PCMCI+ answer different questions:

- TE asks whether information flow is directional under target-only
  conditioning.
- PCMCI+ asks whether a link survives multivariate conditional-independence
  testing.

In practice, TE is useful for screening directionality, while PCMCI+ is needed
to separate direct, mediated, redundant, and contemporaneous links.

## v0.3.0 limitation carried by the notebook

The walkthrough must keep the limitation explicit:

> Exogenous autohistory is not conditioned out in CrossMI, pCrossAMI, or TE in
> v0.3.0.

The follow-up design is tracked in
[../plan/v0_3_1_lagged_exogenous_triage_plan.md](../plan/v0_3_1_lagged_exogenous_triage_plan.md).

## Related references

- [covariant_summary_table.md](covariant_summary_table.md)
- [covariant_role_assignment.md](covariant_role_assignment.md)
- [gcmi.md](gcmi.md)
- [pcmci_plus.md](pcmci_plus.md)
- [../code/covariant_walkthrough.md](../code/covariant_walkthrough.md)
