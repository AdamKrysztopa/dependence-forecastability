<!-- type: reference -->
# Notebook Taxonomy and Ownership

This repository freezes notebook policy to exactly two long-lived families:

- `notebooks/walkthroughs/`
- `notebooks/triage/`

## Family Roles

| Family | Ownership role | Purpose |
|---|---|---|
| `notebooks/walkthroughs/` | Curated end-to-end surfaces | Guided user and maintainer flows for canonical operational paths |
| `notebooks/triage/` | Deterministic deep dives | Focused method analysis, diagnostics, and evidence-oriented exploration |

## Architecture Alignment (SOLID + Hexagonal)

- Notebooks are consumers and demonstrators, not runtime implementation surfaces.
- Runtime logic belongs in `src/forecastability/` and follows `adapters -> use_cases -> domain` boundaries.
- Notebook-local experimentation must not replace shared runtime orchestration, domain rules, or adapter behavior.

## Deprecation Policy for Root-Level Notebook Paths

- No new long-lived notebooks may be added at `notebooks/` root.
- Root-level notebook files are redirect shims pointing to the corresponding `notebooks/walkthroughs/` notebooks.

## Durable Walkthrough Narratives

| Durable docs page | Notebook surface |
|---|---|
| [canonical_forecastability.md](canonical_forecastability.md) | [../../notebooks/walkthroughs/01_canonical_forecastability.ipynb](../../notebooks/walkthroughs/01_canonical_forecastability.ipynb) |
| [exogenous_analysis.md](exogenous_analysis.md) | [../../notebooks/walkthroughs/02_exogenous_analysis.ipynb](../../notebooks/walkthroughs/02_exogenous_analysis.ipynb) |
| [agentic_triage.md](agentic_triage.md) | [../../notebooks/walkthroughs/03_triage_end_to_end.ipynb](../../notebooks/walkthroughs/03_triage_end_to_end.ipynb) |
| [screening_end_to_end.md](screening_end_to_end.md) | [../../notebooks/walkthroughs/04_screening_end_to_end.ipynb](../../notebooks/walkthroughs/04_screening_end_to_end.ipynb) |

## Triage Deep-Dive Notebooks

Focused method analysis and diagnostics. Each page is a concise reference for the corresponding `notebooks/triage/` notebook.

| Durable docs page | Notebook surface | Key focus |
|---|---|---|
| [triage_01_forecastability_profile.md](triage_01_forecastability_profile.md) | [../../notebooks/triage/01_forecastability_profile_walkthrough.ipynb](../../notebooks/triage/01_forecastability_profile_walkthrough.ipynb) | F1 horizon-specific AMI/pAMI profile and forecastability class |
| [triage_02_information_limits.md](triage_02_information_limits.md) | [../../notebooks/triage/02_information_limits_and_compression.ipynb](../../notebooks/triage/02_information_limits_and_compression.ipynb) | F2 information ceiling and compression ratio |
| [triage_03_predictive_learning_curves.md](triage_03_predictive_learning_curves.md) | [../../notebooks/triage/03_predictive_information_learning_curves.ipynb](../../notebooks/triage/03_predictive_information_learning_curves.ipynb) | N3 predictive information learning curves |
| [triage_04_spectral_entropy.md](triage_04_spectral_entropy.md) | [../../notebooks/triage/04_spectral_and_entropy_diagnostics.ipynb](../../notebooks/triage/04_spectral_and_entropy_diagnostics.ipynb) | N4 spectral predictability and entropy complexity |
| [triage_05_batch_exogenous.md](triage_05_batch_exogenous.md) | [../../notebooks/triage/05_batch_and_exogenous_workbench.ipynb](../../notebooks/triage/05_batch_and_exogenous_workbench.ipynb) | N5 batch ranking and exogenous screening workbench |
| [triage_06_agent_triage.md](triage_06_agent_triage.md) | [../../notebooks/triage/06_agent_ready_triage_interpretation.ipynb](../../notebooks/triage/06_agent_ready_triage_interpretation.ipynb) | Agent-ready payload serialization and interpretation patterns |

## Triage Notebook Role Split

- Walkthrough consumer notebook: [../../notebooks/walkthroughs/03_triage_end_to_end.ipynb](../../notebooks/walkthroughs/03_triage_end_to_end.ipynb)
- Deterministic payload/serializer/interpretation deep dive: [../../notebooks/triage/06_agent_ready_triage_interpretation.ipynb](../../notebooks/triage/06_agent_ready_triage_interpretation.ipynb)
