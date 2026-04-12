<!-- type: reference -->
# dependence-forecastability - Progress Tracker

_Last updated: 2026-04-12_

Source backlog: [dependence_forecastability_detailed_backlog.md](dependence_forecastability_detailed_backlog.md)

> [!IMPORTANT]
> `dependence_forecastability_detailed_backlog.md` remains the authoritative backlog and is intentionally retained.
> This progress tracker records branch delivery status only, because P1-P3 are not fully implemented.

## Implemented items on `feat/dependence-forecastability-backlog`

| Backlog item id/title | Status | Scope delivered | Commit hash | Notes |
|---|---|---|---|---|
| #1 Publish a real versioned release story | done | Added tag-driven release automation in `.github/workflows/release.yml`, added explicit upgrade notes artifact `docs/releases/v0.1.0.md`, and linked current version plus change history from docs surfaces (`CHANGELOG.md`, `docs/versioning.md`, `docs/README.md`). | `41d2e73 + this commit` | Release path is now automated on `v*` tags with dist artifacts published to GitHub Releases. |
| #2 Add a visible production-readiness contract | done | Added `docs/production_readiness.md` with maturity zones, safe defaults, and failure/non-goal framing. | `247ced2` | Deterministic versus optional agentic paths are explicitly separated. |
| #3 Rework the README first screen | done | Restructured top-level README entry path and first-run framing for quicker orientation. | `bc23ebf` | Reduced concept density before first executable path. |
| #4 Add an opinionated quickstart ladder | done | Added `docs/quickstart.md` covering CLI, notebook, Python API, HTTP API, and optional routes. | `a7a5cec` | Single shared-signal progression documented across routes. |
| #5 Add explicit benchmark/result cards | done | Added `docs/results_summary.md` with compact evidence-first outcomes and limitations. | `7aa5f87` | Decision-focused summary layer now exists outside notebooks. |
| #6 Improve packaging metadata and install trust | done | Added dedicated PyPI publication readiness artifacts: trusted-publishing workflow and release publication flow note, while preserving prior packaging metadata and install matrix work. | `09bac87 + this commit` | Decision recorded: publish to PyPI via GitHub OIDC trusted publishing (no repository PyPI token secret). |
| #7 Create a "Why use this?" comparison page | done | Added `docs/why_use_this.md` with component selection matrix and caveats. | `8fbdf5d` | Component-choice guidance is now centralized. |
| #8 Add a use-case pack for manufacturing / reliability / PdM | done | Added `docs/use_cases_industrial.md` with scenario-to-decision mapping. | `8fbdf5d` | Uses operational, non-sensational framing. |
| #9 Turn "agentic" into a carefully framed optional layer | done | Added `docs/agent_layer.md` documenting deterministic-first and optional narration contract. | `bd16de9` | Includes strict-mode and grounding boundaries. |
| #10 Add one hardened API contract page | done | Added `docs/api_contract.md` covering schemas, SSE sequence, and failure semantics. | `b410661` | Integration contract is now explicit and version-aware. |
| #11 Add interface-level contract tests | done | Added shared deterministic triage fixtures (`tests/conftest.py`), adapter protocol/behavior contract tests (`tests/test_adapter_interface_contracts.py`), and schema-level CLI/API/MCP parity tests on identical inputs (`tests/test_transport_schema_parity.py`). | `this commit` | Event emission ordering is now pinned for both full and blocked triage paths. |
| #12 Add reproducibility fixtures for benchmark examples | done | Added tiny deterministic benchmark fixture data and frozen expected artifacts under `docs/fixtures/benchmark_examples/`, plus fixture rebuild/verify flow (`src/forecastability/reproducibility.py`, `scripts/rebuild_benchmark_fixture_artifacts.py`) and focused reproducibility tests (`tests/test_benchmark_reproducibility.py`). | `this commit` | Repro command: `uv run python scripts/rebuild_benchmark_fixture_artifacts.py --verify`. |
| #13 Add observability and auditability guidance | done | Added `docs/observability.md` with event payload, checkpoint semantics, and audit/logging guidance. | `0413cc5` | Operational tracing workflow is documented for production usage. |
| #14 Batch dataset / signal screening mode | done | Added deterministic batch triage models and use case with per-series failure isolation and deterministic ranking (`src/forecastability/triage/batch_models.py`, `src/forecastability/triage/run_batch_triage.py`), exposed CLI batch mode with exportable summary/failure CSV tables (`src/forecastability/adapters/cli.py`), and added focused tests for mixed good/bad batches, ranking behavior, and export table schemas (`tests/test_triage_batch_mode.py`). | `this commit` | CLI entrypoint: `forecastability triage-batch --batch-json <path>`. |
| #15 Multi-series comparison reports | done | Added standardized multi-series comparison reporting built on #14 batch outputs (`src/forecastability/triage/comparison_report.py`) with AMI/pAMI AUC, directness ratio, significance coverage, and horizon drop-off tables/plots, plus deeper-modeling recommendation summary; added a dedicated artifact generation script (`scripts/run_multi_series_comparison_report.py`) and focused tests for table schemas and recommendation logic (`tests/test_triage_comparison_report.py`). | `this commit` | Generation command: `uv run python scripts/run_multi_series_comparison_report.py --batch-json <path>`. |

## Remaining backlog context

P1-P3 are not fully implemented. Keep all remaining planning and acceptance tracking in [dependence_forecastability_detailed_backlog.md](dependence_forecastability_detailed_backlog.md).