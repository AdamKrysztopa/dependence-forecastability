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
| [pami_residual_backends.md](pami_residual_backends.md) | Residual backend options, benchmark deltas versus linear, and known failure modes |
| [interpretation_patterns.md](interpretation_patterns.md) | Pattern-based interpretation logic used in reporting |

## Scope boundary

- Paper-native: AMI and its benchmark framing.
- Project extension: pAMI, exogenous cross-dependence, method-independent scorer registry.
