<!-- type: reference -->
# Notebook Guide

This repository maintains two long-lived notebook families.

_Last verified for release 0.2.0 consolidation on 2026-04-14._

## Notebook Families

| Family | Role | Start here |
| --- | --- | --- |
| `notebooks/walkthroughs/` | Guided, story-first walkthroughs for onboarding and demonstrations | `00_air_passengers_showcase.ipynb` |
| `notebooks/triage/` | Focused deep dives into specific diagnostics and payloads | Use only after the walkthroughs |

## Canonical Learning Path

1. Start with [../../notebooks/walkthroughs/00_air_passengers_showcase.ipynb](../../notebooks/walkthroughs/00_air_passengers_showcase.ipynb).
2. Continue through walkthrough notebooks `01` to `04` in order.
3. Move to `notebooks/triage/` only when you want method-specific depth.

## Walkthrough Notebooks

| Notebook | Role |
| --- | --- |
| [../../notebooks/walkthroughs/00_air_passengers_showcase.ipynb](../../notebooks/walkthroughs/00_air_passengers_showcase.ipynb) | First-stop product showcase |
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
