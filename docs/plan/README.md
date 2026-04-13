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

Supporting deliverables: triage examples (`examples/triage/`), walkthrough notebooks (`notebooks/triage/`), theory docs (`docs/theory/`), and end-to-end agent integration.

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
