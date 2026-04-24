<!-- type: reference -->
# Plan Docs

Baseline framing, invariants, and mathematical definitions still live in the main documentation set:
- [README.md](../../README.md)
- [docs/theory/foundations.md](../theory/foundations.md)

## Planning surface

| File | Purpose | Status |
|---|---|---|
| [development_plan.md](development_plan.md) | Phased development plan for the triage extension epic | **Complete** |
| [acceptance_criteria.md](acceptance_criteria.md) | Done criteria shared by all roadmap items | Complete |
| **[cleaning_plan.md](cleaning_plan.md)** | **Hexagonal realignment, type-check cleanup, packaging** | **Active** |
| **[pypi_release_plan.md](pypi_release_plan.md)** | **PyPI publication: naming, metadata, artifact validation, Trusted Publishing** | **Active** |
| **[v0_3_4_forecast_prep_contract_ultimate_plan.md](v0_3_4_forecast_prep_contract_ultimate_plan.md)** | **v0.3.4 — forecast-prep contract: framework-agnostic full plan (consolidated; absorbs the earlier 2026-04-24 scope-revision overlay)** | **Shipped (v0.3.4)** |
| [aux_documents/v0_3_4_forecast_prep_contract_ultimate_plan.md](aux_documents/v0_3_4_forecast_prep_contract_ultimate_plan.md) | v0.3.4 — original draft with framework runners and `[darts]` / `[mlforecast]` extras | Superseded — audit trail |
| **[v0_3_5_documentation_quality_improvement_revision_2026_04_24.md](v0_3_5_documentation_quality_improvement_revision_2026_04_24.md)** | **v0.3.5 — docs hygiene + reorganization: Invariant E, notebook transition banner, `docs/` Diátaxis bucketing, markdownlint + lychee CI** | **Active plan (no separate ultimate-plan file ships)** |
| **[v0_4_0_examples_repo_split_ultimate_plan.md](v0_4_0_examples_repo_split_ultimate_plan.md)** | **v0.4.0 — library-first slim release: notebook migration to sibling examples repo, cross-repo CI handshake, sprint-showcase notebooks** | **Active** |
| [aux_documents/developer_instruction_repo_scope.md](aux_documents/developer_instruction_repo_scope.md) | Reviewer scope directive (driver document for v0.3.4 revision, v0.3.5 revision, v0.4.0) | Reference |

## Completed — triage extension epic

All nine feature groups (F1–F9) from the development plan have been implemented and verified:

- **F1** Forecastability profile & complexity bands
- **F2** Information limits & compression diagnostics
- **F3** Entropy–complexity plane mapping
- **F4** Spectral predictability & Lyapunov exponents
- **F5** Predictive-information learning curves
- **F6** Exogenous driver analysis & redundancy screening
- **F7** Batch triage ranking & multi-signal diagnostics
- **F8** Agent adapters (MCP server, dashboard, CLI)
- **F9** Robustness study & benchmark panel

Supporting deliverables: univariate examples (`examples/univariate/`), covariant-informative examples (`examples/covariant_informative/`), walkthrough notebooks (`notebooks/walkthroughs/` and `notebooks/triage/`), theory docs (`docs/theory/`), and end-to-end agent integration.

## Source epic

The math-grounded feature backlog that fed the development plan:
- [`not_planed/triage_extension_epic_math_grounded.md`](not_planed/triage_extension_epic_math_grounded.md)

## Planning policy

- The triage extension epic is **complete**; current focus is packaging, cleanup, and release.
- The [cleaning plan](cleaning_plan.md) tracks hexagonal realignment and type-checker compliance.
- The [PyPI release plan](pypi_release_plan.md) tracks naming, metadata, artifact validation, and Trusted Publishing.
- All paper functionality from arXiv:2601.10006 is preserved as a non-negotiable baseline.
- Extensions do not weaken or replace the paper-aligned workflow.
- High-risk estimators remain behind explicit experimental flags.
