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
- Root-level notebook files are transitional redirect shims only.
- Legacy top-level [../../notebooks/03_agentic_triage.ipynb](../../notebooks/03_agentic_triage.ipynb) and [../../notebooks/04_agentic_screening.ipynb](../../notebooks/04_agentic_screening.ipynb) are explicitly transitional during migration.

## Transitional Scope Note

This C1 policy freeze is documentation-only. It does not move, rename, or renumber notebook files.

## Durable Walkthrough Narratives

| Durable docs page | Current notebook surface |
|---|---|
| [canonical_forecastability.md](canonical_forecastability.md) | [../../notebooks/01_canonical_forecastability.ipynb](../../notebooks/01_canonical_forecastability.ipynb) |
| [exogenous_analysis.md](exogenous_analysis.md) | [../../notebooks/02_exogenous_analysis.ipynb](../../notebooks/02_exogenous_analysis.ipynb) |
| [agentic_triage.md](agentic_triage.md) | [../../notebooks/03_agentic_triage.ipynb](../../notebooks/03_agentic_triage.ipynb) |

## Triage Notebook Role Split

- Walkthrough consumer notebook: [../../notebooks/03_agentic_triage.ipynb](../../notebooks/03_agentic_triage.ipynb)
- Deterministic payload/serializer/interpretation deep dive: [../../notebooks/triage/10_agent_ready_triage_interpretation.ipynb](../../notebooks/triage/10_agent_ready_triage_interpretation.ipynb)
