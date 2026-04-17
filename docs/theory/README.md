<!-- type: explanation -->
# Theory

Theory docs for AMI (paper-native) and pAMI (project extension).

## Baseline source

- arXiv:2601.10006 (Catt, 2026): https://arxiv.org/pdf/2601.10006
- Paper validates horizon-specific AMI as a frequency-conditional triage signal.

## Project interpretation

This repository keeps the paper's AMI framing and extends it with pAMI to separate:
- total lag dependence (AMI), and
- direct lag dependence after conditioning (pAMI).

## Document map

| File | Purpose |
|---|---|
| [foundations.md](foundations.md) | Definitions, feasibility constraints, significance logic, and extension boundaries |
| [forecastability_profile.md](forecastability_profile.md) | Forecastability Profile model, informative horizon set, epsilon resolution, and DPI diagnostic |
| [covariant_informative_walkthrough.md](covariant_informative_walkthrough.md) | Why the covariant walkthrough needs pairwise, directional, and causal sections on the same benchmark |
| [covariant_summary_table.md](covariant_summary_table.md) | Unified `(driver, lag)` screening table for the covariant surface |
| [covariant_role_assignment.md](covariant_role_assignment.md) | Deterministic role assignment from covariant bundle evidence |
| [gcmi.md](gcmi.md) | Gaussian-copula mutual information background and project usage |
| [pcmci_plus.md](pcmci_plus.md) | PCMCI+ and PCMCI-AMI causal-discovery background |
| [pami_residual_backends.md](pami_residual_backends.md) | Residual backend options, benchmark deltas versus linear, and known failure modes |
| [interpretation_patterns.md](interpretation_patterns.md) | Pattern-based interpretation logic used in reporting |
| [spectral_predictability.md](spectral_predictability.md) | Spectral predictability Ω, Welch PSD normalisation, linear/nonlinear divergence diagnostic |
| [entropy_based_complexity.md](entropy_based_complexity.md) | Permutation entropy, spectral entropy, complexity band mapping, PE-SE plane interpretation |

> [!NOTE]
> Triage method docs (predictive info learning curves, largest Lyapunov exponent) live in [`../triage_methods/`](../triage_methods/).

## Scope boundary

- Paper-native: AMI and its benchmark framing.
- Project extension: pAMI, exogenous cross-dependence, method-independent scorer registry.
- Triage features: forecastability profiles (F1), IT limit diagnostics (F2), predictive info learning curves (F3), spectral predictability (F4), Lyapunov exponent (F5, experimental), entropy-based complexity (F6), batch ranking (F7), exogenous screening extensions (F8).

## Paper references

| Paper | Key contribution to this project |
|---|---|
| Catt (2026), [arXiv:2601.10006](https://arxiv.org/abs/2601.10006) | Original AMI paper — horizon-specific mutual information for forecastability triage |
| Catt (2026), [arXiv:2603.27074](https://arxiv.org/abs/2603.27074) | Forecastability profiles, information-theoretic limits, pAMI extension |
| Morawski et al. (2025), [arXiv:2510.10744](https://arxiv.org/abs/2510.10744) | Predictive information learning curves (EvoRate-style lookback analysis) |
| Wang et al. (2025), [arXiv:2507.13556](https://arxiv.org/abs/2507.13556) | Spectral predictability score, Lyapunov exponent diagnostics |
| Ponce-Flores et al. (2020) | Complexity band classification and forecasting link |
| Bandt & Pompe (2002) | Permutation entropy — foundational method for entropy-based complexity |
