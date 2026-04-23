<!-- type: reference -->
# Notebook Guide

This repository maintains two long-lived notebook families.

_Last verified for the v0.3.3 routing validation walkthrough update on 2026-04-23._

## Canonical Notebook

The canonical walkthrough notebook is
[../../notebooks/walkthroughs/00_air_passengers_showcase.ipynb](../../notebooks/walkthroughs/00_air_passengers_showcase.ipynb).

## Notebook Families

| Family | Role | Start here |
| --- | --- | --- |
| `notebooks/walkthroughs/` | Guided, story-first walkthroughs for onboarding and demonstrations | `00_air_passengers_showcase.ipynb` |
| `notebooks/triage/` | Focused deep dives into specific diagnostics and payloads | Use only after the canonical walkthrough |

## Suggested Learning Path

1. Start with the canonical notebook: [../../notebooks/walkthroughs/00_air_passengers_showcase.ipynb](../../notebooks/walkthroughs/00_air_passengers_showcase.ipynb).
2. Continue with [../../notebooks/walkthroughs/01_covariant_informative_showcase.ipynb](../../notebooks/walkthroughs/01_covariant_informative_showcase.ipynb).
3. Continue with [../../notebooks/walkthroughs/02_forecastability_fingerprint_showcase.ipynb](../../notebooks/walkthroughs/02_forecastability_fingerprint_showcase.ipynb) for the geometry-backed routing and agent-summary surface.
4. Continue with [../../notebooks/walkthroughs/03_lagged_exogenous_triage_showcase.ipynb](../../notebooks/walkthroughs/03_lagged_exogenous_triage_showcase.ipynb) for sparse lag-domain triage and known-future opt-in.
5. Continue with [../../notebooks/walkthroughs/04_routing_validation_showcase.ipynb](../../notebooks/walkthroughs/04_routing_validation_showcase.ipynb) for the four audit outcomes, threshold margin, rule-stability, and release-report artifact reading.
6. Continue through the remaining walkthrough notebooks in order.
7. Move to `notebooks/triage/` when you want method-specific depth.

## Walkthrough Notebooks

| Notebook | Role |
| --- | --- |
| [../../notebooks/walkthroughs/00_air_passengers_showcase.ipynb](../../notebooks/walkthroughs/00_air_passengers_showcase.ipynb) | Canonical walkthrough |
| [../../notebooks/walkthroughs/01_covariant_informative_showcase.ipynb](../../notebooks/walkthroughs/01_covariant_informative_showcase.ipynb) | Covariant informative walkthrough: pairwise, directional, and causal comparisons on the synthetic benchmark |
| [../../notebooks/walkthroughs/02_forecastability_fingerprint_showcase.ipynb](../../notebooks/walkthroughs/02_forecastability_fingerprint_showcase.ipynb) | Fingerprint walkthrough: prepared univariate archetypes, geometry, routing, and strict deterministic agent summary |
| [../../notebooks/walkthroughs/03_lagged_exogenous_triage_showcase.ipynb](../../notebooks/walkthroughs/03_lagged_exogenous_triage_showcase.ipynb) | Lagged-exogenous walkthrough: role taxonomy, sparse lag selection, and known-future opt-in |
| [../../notebooks/walkthroughs/04_routing_validation_showcase.ipynb](../../notebooks/walkthroughs/04_routing_validation_showcase.ipynb) | Routing-validation walkthrough: four audit outcomes, threshold margin, rule-stability, synthetic and real-panel reading, and report/bundle artifacts |
| [../../notebooks/walkthroughs/01_canonical_forecastability.ipynb](../../notebooks/walkthroughs/01_canonical_forecastability.ipynb) | Canonical AMI and pAMI walkthrough |
| [../../notebooks/walkthroughs/02_exogenous_analysis.ipynb](../../notebooks/walkthroughs/02_exogenous_analysis.ipynb) | Exogenous analysis walkthrough |
| [../../notebooks/walkthroughs/03_triage_end_to_end.ipynb](../../notebooks/walkthroughs/03_triage_end_to_end.ipynb) | End-to-end triage walkthrough |
| [../../notebooks/walkthroughs/04_screening_end_to_end.ipynb](../../notebooks/walkthroughs/04_screening_end_to_end.ipynb) | Screening workflow walkthrough |

## Triage Deep Dives

| Notebook | Focus |
| --- | --- |
| [../../notebooks/triage/01_forecastability_profile_walkthrough.ipynb](../../notebooks/triage/01_forecastability_profile_walkthrough.ipynb) | Forecastability profile |
| [../../notebooks/triage/02_information_limits_and_compression.ipynb](../../notebooks/triage/02_information_limits_and_compression.ipynb) | Information limits and compression |
| [../../notebooks/triage/03_predictive_information_learning_curves.ipynb](../../notebooks/triage/03_predictive_information_learning_curves.ipynb) | Predictive-information learning curves |
| [../../notebooks/triage/04_spectral_and_entropy_diagnostics.ipynb](../../notebooks/triage/04_spectral_and_entropy_diagnostics.ipynb) | Spectral and entropy diagnostics |
| [../../notebooks/triage/05_batch_and_exogenous_workbench.ipynb](../../notebooks/triage/05_batch_and_exogenous_workbench.ipynb) | Batch and exogenous workbench |
| [../../notebooks/triage/06_agent_ready_triage_interpretation.ipynb](../../notebooks/triage/06_agent_ready_triage_interpretation.ipynb) | Agent-ready payload and interpretation deep dive |

## Notebook Policy

- Keep long-lived notebooks in `walkthroughs/` or `triage/` only.
- Do not move runtime logic out of `src/forecastability/` into notebook-local helpers.
- Treat `notebooks/triage/outputs/` as notebook-local scratch output, not as a public artifact contract.

> [!NOTE]
> Legacy notebook narrative docs have been archived so the active docs path points directly to the live notebooks.
