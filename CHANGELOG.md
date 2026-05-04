# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!-- markdownlint-disable MD024 -->

## [Unreleased]

## [0.4.2] - 2026-05-04

> **AMI-first forecastability structure expansion.**
> This release extends the univariate forecastability fingerprint with additive
> spectral, ordinal, classical, and memory diagnostics, plus an extended
> routing/profile surface and CLI entry point. It remains a deterministic
> triage release: no model fitting, no framework-specific training helpers,
> and no causal-discovery expansion are added here.

### Added

- `run_extended_forecastability_analysis(...)` as the direct public entry point
  for the extended univariate fingerprint.
- `ExtendedForecastabilityAnalysisResult`,
  `ExtendedForecastabilityFingerprint`, and
  `ExtendedForecastabilityProfile` on the stable public facade and
  `forecastability.triage`.
- Additive spectral, ordinal, classical, and memory diagnostic blocks around
  the existing AMI-first fingerprint.
- `forecastability extended` CLI output surface for `json`, `markdown`, and
  `brief` rendering.
- Theory and usage docs for spectral forecastability, ordinal complexity,
  classical structure features, memory diagnostics, and the extended profile.

### Changed

- `run_triage(..., include_extended_fingerprint=True)` can now attach
  `extended_forecastability_analysis` for non-exogenous requests without
  changing the default triage contract.
- Deterministic routing now exposes `predictability_sources`,
  `recommended_model_families`, `avoid_model_families`, `signal_strength`, and
  `noise_risk` on `ExtendedForecastabilityProfile`.
- When AMI geometry is disabled or unavailable, the extended router switches to
  descriptive-only mode instead of emitting routing-grade family
  recommendations from secondary diagnostics alone.

### Notes

- The extended surface is **AMI-first**. The secondary diagnostics explain why
  a series may be forecastable; they do not replace lagged-information
  analysis.
- No downstream model fitting, forecasting-framework integration, or causal
  expansion ships in this release.

## [0.4.1] - 2026-05-03

> **Performance hardening, benchmark visibility, and fast-screening controls.**
> This release ships measurement infrastructure, correctness guards for significance services,
> work-avoidance for explicit method subsets, validation/scaling hygiene, a reduced eager import
> surface, and user-visible significance controls.  It does not yet eliminate the dominant
> surrogate/significance bottlenecks; those are identified and scoped for the next cycle.
>
> PCMCI and PCMCI-AMI remain supported but are explicitly defocused as confirmatory tools
> due to prohibitive runtime in practice.  Prefer `methods=["cross_ami", "gcmi"]` for
> fast initial screening; use `pcmci_ami_ci_test="parcorr"` when causal discovery is needed.

### Added

- `n_jobs_significance: int = 1` parameter on `run_covariant_analysis` — passes through to
  `compute_significance_bands_generic` so callers can opt into parallel surrogate evaluation.
- `yfinance` optional extra `[data]` — move `yfinance>=0.2` out of core dependencies into
  `pip install "dependence-forecastability[data]"` to reduce mandatory install weight.
- PCMCI/PCMCI-AMI defocus note in `docs/quickstart.md` and `docs/public_api.md` — explicitly
  documents confirmatory role, expense, and `parcorr` fast-path recommendation.

### Changed

- `n_surrogates` floor check in `run_covariant_analysis` and `run_lagged_exogenous_triage` now
  only enforces ≥ 99 when `significance_mode="phase"`; `significance_mode="none"` silently
  skips the check.
- `src/forecastability/__init__.py` reduced eager import surface: only the canonical core
  symbols (`run_triage`, `run_covariant_analysis`, `run_lagged_exogenous_triage`,
  `build_forecast_prep_contract`, primary request/result types, and `generate_ar1` /
  `generate_white_noise`) are imported at load time.  All other `__all__` symbols resolve
  lazily via `__getattr__`.
- Release title renamed from "Performance Bottleneck Elimination" to "Performance hardening,
  benchmark visibility, and fast-screening controls" to accurately reflect the delivered scope.
- Plan branch reference corrected from `feat/v0.4.1-performance-bottleneck-elimination` to
  `feat/performance-improvement`.

## [0.4.0] - 2026-04-29

> **Library-first slim release.** This release migrates all walkthrough and tutorial notebooks
> out of the core repository and into the companion
> [`forecastability-examples`](https://github.com/AdamKrysztopa/forecastability-examples)
> repository. The Python API is unchanged; no public symbol is removed or renamed.
> Rationale: [docs/plan/aux_documents/developer_instruction_repo_scope.md](docs/plan/aux_documents/developer_instruction_repo_scope.md).
>
> The v0.3.4 `ForecastPrepContract` sprint is demonstrated in the sibling repo's launch
> notebook
> [`walkthroughs/05_forecast_prep_to_models.ipynb`](https://github.com/AdamKrysztopa/forecastability-examples/blob/main/walkthroughs/05_forecast_prep_to_models.ipynb).

### Added

- Root `AGENTS.md` for Codex/agent-style coding tools — navigation order, routing rules, editing rules, and validation commands.
- `.github/copilot-instructions.md` for repo-wide GitHub Copilot guidance — triage-first routing rules and entry-point anchors.
- Path-specific instruction surfaces under `.github/instructions/` targeting Python source, notebooks, and planning docs.
- Expanded `llms.txt` as a concise routing surface for generic LLM consumers with an explicit forecasting-task routing rule.
- `examples/forecasting_triage_first.py` and `examples/forecasting_triage_then_handoff.md` — agent-facing triage-first examples that branch on `blocked` results.
- `scripts/run_triage_handoff_demo.py` — runnable triage-first demo with downstream hand-off framing.
- `docs/maintenance/llm_visibility_eval.md` — LLM-visibility evaluation harness with 5 benchmark prompts and pass/fail criteria.
- `forecastability-examples` sibling repository bootstrapped at <https://github.com/AdamKrysztopa/forecastability-examples> with its own `pyproject.toml`, locked `uv.lock`, two-axis CI matrix (`python ∈ {3.11, 3.12}` × `source ∈ {pinned, unpinned-main}`), and 15 migrated notebooks (git history preserved via `git filter-repo`).
- `docs/examples_index.md` — index of all migrated notebooks with destination URLs, issues table, and cross-references.
- `RELEASES.md` — paired release index listing sibling repo release tags alongside core release tags.
- `docs/development/local_workspace.md` and `scripts/bootstrap_local_workspace.sh` — documented local two-repo developer workflow.
- `forecastability.extensions` module: `TargetBaselineCurves`, `compute_target_baseline_by_horizon`, and `compute_k_sensitivity` — framework-agnostic causal-rivers analysis surface re-exported from the top-level `forecastability` namespace.
- `scripts/run_causal_rivers_analysis.py` and `configs/causal_rivers_analysis.yaml` — deterministic causal-rivers forecastability-triage script.
- `scripts/rebuild_causal_rivers_fixtures.py` — regression-fixture rebuild for the extensions surface.

### Changed

- README updated to include "Use this before model search" section framing downstream frameworks as post-triage consumers; adds "Tutorials, walkthroughs, and integrations" section pointing at the sibling repo.
- `pyproject.toml` keywords expanded with forecastability-triage, diagnostics, covariate, and hand-off discovery terms; `notebooks/` removed from sdist exclude list.
- `llms.txt`, `AGENTS.md`, and `.github/copilot-instructions.md` "Start Here" anchors updated: notebook entry removed, `docs/recipes/` and `docs/examples_index.md` added.
- `docs/reference/implementation_status.md` and `docs/explanation/surface_guide.md` notebook rows updated to sibling-repo links.
- `docs/recipes/forecast_prep_to_external_frameworks.md` gains forward-link table to sibling repo notebooks EX-NB-01 / EX-NB-02.

### Removed

- `notebooks/` directory — migrated to `forecastability-examples` with git history preserved.
- `outputs/notebook_runs/` directory — migrated and removed.
- `scripts/check_notebook_contract.py` and associated notebook-contract test files.
- Notebook CI plumbing (transition-banner sub-check and notebook-execution steps).

### Notes

- **Migration:** Notebook walkthroughs previously at `notebooks/walkthroughs/` and `notebooks/triage/` are now at <https://github.com/AdamKrysztopa/forecastability-examples>. Install and run them with `uv sync --frozen && uv run jupyter nbconvert --to notebook --execute walkthroughs/*.ipynb`.
- No runtime API-breaking changes. All v0.3.x public surfaces remain available under the same import paths.
- pAMI and all F1–F9 diagnostics remain project extensions, not paper-native guarantees.

## [0.3.6] - 2026-04-25

### Added

- `repo_contract.yaml` as the single machine-readable release-truth/docs-integrity contract surface.
- `scripts/check_repo_contract.py` and `scripts/sync_repo_contract.py --write` for deterministic contract validation and rewrites.
- `scripts/check_markdown_links.py` and `scripts/check_readme_surface.py` for internal docs-integrity and landing-surface policy checks.
- `scripts/check_published_release.py` for post-publish verification of PyPI version visibility and GitHub release-tag presence.
- `.github/workflows/repo-autofix.yml` for schedule/dispatch contract sync with PR-only write path.

### Changed

- CI now runs a dedicated `repo-contract` job with release-truth/docs-integrity checks.
- Release workflow now enforces tag/version parity, release-notes presence, and release-tag contract verification.
- PyPI publish workflow now executes post-publish verification using `scripts/check_published_release.py`.
- Regression fixtures/tests were expanded for repository-contract drift detection, idempotent sync behavior, and end-to-end checker smoke coverage.
- Root README landing surface and dependency-group naming now follow library-first contract policy (`notebook` -> `examples`).

### Notes

- This is a release-integrity automation update; no runtime API-breaking changes are introduced.

## [0.3.4] - 2026-04-24

### Added

- `ForecastPrepContract`, `LagRecommendation`, `CovariateRecommendation`,
  `FamilyRecommendation`, and `ForecastPrepBundle` typed result models
  (additive on `forecastability.utils.types`).
- `build_forecast_prep_contract(triage_result, *, horizon, target_frequency, ...)`
  use case (re-exported from `forecastability` and `forecastability.triage`).
- Framework-agnostic exporters `forecast_prep_contract_to_markdown(contract)` and
  `forecast_prep_contract_to_lag_table(contract)` (re-exported from `forecastability`
  and `forecastability.triage`). Pydantic `model_dump()` / `model_dump_json()` are
  documented as the canonical Python-dict and JSON export surfaces.
- Deterministic calendar feature service: `add_calendar_features=True` injects
  `_calendar__dayofweek`, `_calendar__month`, `_calendar__quarter`,
  `_calendar__is_weekend`, `_calendar__is_business_day`, and (when `calendar_locale`
  is set with the optional `[calendar]` extra installed) `_calendar__is_holiday`.
- Optional dependency extra: `[calendar]` (`holidays>=0.50`).
- Showcase script `scripts/run_showcase_forecast_prep.py` with a `--smoke` flag.
- Theory doc `docs/reference/forecast_prep_contract.md`.
- External-recipes doc `docs/recipes/forecast_prep_to_external_frameworks.md`
  with illustrative Darts / MLForecast / Nixtla mappings.

### Changed

- README install section documents the new `[calendar]` extra alongside the
  existing `[agent]`, `[causal]`, and `[transport]` extras.

### Notes

- The package remains **framework-agnostic**. No `darts`, `mlforecast`,
  `statsforecast`, or `nixtla` runtime, optional, dev, or CI dependency is
  introduced. Framework usage examples ship as illustrative recipes in
  `docs/recipes/**` and (from v0.4.0) in the sibling
  `forecastability-examples` repository. Rationale:
  [docs/plan/aux_documents/developer_instruction_repo_scope.md](docs/plan/aux_documents/developer_instruction_repo_scope.md).
- Existing public Pydantic field shapes are preserved. The Forecast Prep
  Contract is an additive surface.

## [0.3.3] - 2026-04-23

### Added

- `RoutingValidationCase`, `RoutingPolicyAudit`, `RoutingValidationBundle`, `RoutingValidationOutcome`, `RoutingValidationSourceKind`, and `RoutingPolicyAuditConfig` as additive typed routing-validation surfaces on `forecastability`.
- `run_routing_validation()` as the additive public routing-validation use case.
- `scripts/run_routing_validation_report.py` as the routing-validation markdown/JSON report generator, with `--smoke` and `--no-real-panel` flags.
- `docs/theory/routing_validation.md` covering the four audit outcomes, threshold-distance margin, rule-stability grid, calibrated confidence labels, and versioned scalars.

### Changed

- Routing confidence labels are widened additively so `abstain` is available alongside the existing `high`, `medium`, and `low` values. The new label is emitted only when the routing policy returns zero primary families.
- README, quickstart, and public API docs now document the routing-validation surface, the clean-checkout smoke report path, and the deterministic-first agent review example.

### Notes

- No v0.3.1 routing-rule semantics change is documented in this release. Any future change to `services/routing_policy_service.py` must be accompanied by a fixture refresh under `docs/fixtures/routing_validation_regression/expected/`.

## [0.3.2] - 2026-04-21

### Added

- `run_lagged_exogenous_triage()` — first-class lagged-exogenous triage facade classifying each
  exogenous driver by lag role and emitting a typed sparse lag map for forecasting tensor
  construction.
- `generate_lagged_exog_panel()` — synthetic panel generator for the lagged-exogenous triage
  surface (instantaneous, predictive-lagged, and uncorrelated driver archetypes).
- `LaggedExogBundle` — composite typed result: profile rows, selection rows, driver registry,
  and known-future driver list.
- `LaggedExogProfileRow` — one lag-domain diagnostic row covering standard cross-correlation,
  cross_ami (extended to `lag=0`), cross_pami, lag_role, tensor_role, and significance source.
- `LaggedExogSelectionRow` — one sparse selection row carrying `selected_for_tensor`,
  `selector_name`, and `tensor_role`.
- `LagRoleLabel` typed alias: `Literal["instant", "predictive"]` — chronological role at a lag.
- `TensorRoleLabel` typed alias: `Literal["diagnostic", "predictive", "known_future"]` —
  tensor-eligibility classification.
- `LagSelectorLabel` typed alias: `Literal["xcorr_top_k", "xami_sparse"]` — which selector
  produced the row.
- `LagSignificanceSource` typed alias: `Literal["phase_surrogate_xami",
  "phase_surrogate_xcorr", "not_computed"]`.
- `known_future_drivers` parameter on `run_lagged_exogenous_triage()` for explicit `lag=0`
  opt-in for features whose contemporaneous value is legitimately available at prediction time.
- Zero-lag ban enforced by default: `selected_for_tensor=True` is structurally impossible at
  `lag=0` without the `known_future_drivers` opt-in.
- Showcase script `scripts/run_showcase_lagged_exogenous.py` with `--smoke` and `--quiet` flags
  and strict agent-layer verification.
- CI smoke step added to `.github/workflows/smoke.yml` for the lagged-exogenous showcase.
- Release checklist extended with lagged-exogenous triage invariant checks.
- Theory document `docs/theory/lagged_exogenous_triage.md` covering role taxonomy, method
  semantics, sparse selector algorithm, known-future opt-in, and DTW omission rationale.
- Walkthrough notebook `notebooks/walkthroughs/03_lagged_exogenous_triage_showcase.ipynb`.

### Changed

- `cross_ami` lag profile extended to include `lag=0` so the contemporaneous MI diagnostic is
  visible alongside the predictive profile.
- README updated to present lagged-exogenous triage as a first-class workflow alongside
  univariate, covariant, and fingerprint surfaces.
- Public API and quickstart docs refreshed with lagged-exogenous triage entry points,
  known-future opt-in semantics, and cross-links.

### Migration notes

- No breaking import changes. All v0.3.0 and v0.3.1 surfaces remain unchanged.
- Integrators can adopt lagged-exogenous triage incrementally through
  `run_lagged_exogenous_triage()` without changing existing `run_triage()` or
  `run_covariant_analysis()` usage.
- `cross_ami` at `lag=0` is now included in the profile but was not emitted in v0.3.0/v0.3.1
  covariant bundles; existing integrations that skip `lag=0` rows are unaffected.

## [0.3.1] - 2026-04-19

### Added

- Geometry-backed fingerprint core for the v0.3.1 workflow: typed `AmiInformationGeometry` / `AmiGeometryCurvePoint` outputs, KSG-II + shuffle-surrogate AMI geometry service, and `signal_to_noise` as a first-class deterministic metric.
- Canonical `generate_fingerprint_archetypes()` helper for the shared univariate synthetic panel used by fingerprint examples and tests.
- Batch forecastability workbench surface: `run_batch_forecastability_workbench()`, typed next-step planning models, technical markdown output, and executive brief rendering for manager/product-owner workflows.

### Changed

- Refactored `run_forecastability_fingerprint()` to execute geometry first, build the fingerprint from corrected-profile outputs, and then route deterministically from the geometry-backed fingerprint.
- Extended fingerprint summaries, agent payloads, and live-agent strict fallback so geometry, fingerprint, and routing fields stay aligned across typed objects, markdown/JSON output, and agent-facing contracts.
- Added a batch example that runs triage, fingerprint routing, and deterministic A1/A3 agent handoff together from the shared synthetic panel.
- Updated theory/public API/quickstart/agent-layer docs to describe the geometry-backed fingerprint semantics and the new batch forecasting workbench.
- Clarified geometry horizon resolution semantics so explicit `max_horizon` is authoritative and `max_lag_frac` is only a fallback when explicit cap is absent.
- Extended `run_forecastability_fingerprint()` summary output with `evaluated_max_horizon` to distinguish requested lag cap from evaluated horizon count.

### Fixed

- Enforced directness-ratio range validation (`[0, 1]`, finite only) at both use-case and fingerprint-service entry seams to keep routing-threshold assumptions consistent.
- Added deterministic acceptance-mask algebra tests to lock strict `I_c(h) > m * tau(h)` behavior and prevent threshold-regression drift.

## [0.3.0] - 2026-04-17

### Added

- First-class covariant analysis facade in the stable package surface via `run_covariant_analysis` and covariant result models (`CovariantAnalysisBundle`, `CovariantSummaryRow`, `TransferEntropyResult`, `GcmiResult`, `CausalGraphResult`, `PcmciAmiResult`, `Phase0MiScore`).
- Unified covariant summary-table workflow covering `cross_ami`, `cross_pami`, `te`, `gcmi`, and optional causal methods (`pcmci`, `pcmci_ami`) with conditioning-scope metadata.
- Covariant showcase and walkthrough documentation path for benchmark-driven method comparison and interpretation.

### Changed

- README updated to present univariate triage and covariant-informative analysis as parallel first-class workflows.
- Public API and quickstart docs refreshed for v0.3.0 covariant entry points, method tokens, and optional causal install path.
- CI/release docs alignment extended for v0.3.0 covariant validation expectations.

### Fixed

- Replaced docs badge that relied on a missing GitHub Pages deployment environment with a stable in-repo docs badge.
- Replaced single-paper "based on" badge language with repository-consistent multi-paper plus original-method wording.

### Migration notes

- No breaking import changes for existing univariate triage integrations.
- Integrators can adopt covariant workflows incrementally through `run_covariant_analysis` without changing existing `run_triage` usage.

## [0.2.0] - 2026-04-14

### Changed

- Major source layout cleanup (hexagonal architecture preserved)
- Examples/scripts/notebooks reorganized and de-duplicated
- Full documentation sync with current code
- README total renovation (multi-paper triage focus)
- CI/CD hardened for PyPI releases

## [0.1.0] - 2026-04-13

### Release support contract

First PyPI release: `pip install dependence-forecastability` (distribution name `dependence-forecastability`; import namespace `forecastability` is unchanged).

| Surface | Support status |
| --- | --- |
| Deterministic core (`run_triage`, `run_batch_triage`, `ForecastabilityAnalyzer`, scorers) | **Stable** — primary public API |
| CLI (`forecastability triage`, `forecastability list-scorers`) | Supported |
| Dashboard (`forecastability-dashboard`) | Supported (optional) |
| FastAPI transport (`[transport]` extra) | Beta |
| Agent narration (`[agent]` extra) | Experimental |
| MCP server (`[transport]` extra) | Experimental |

pAMI and all F1–F9 diagnostics are project extensions, not paper-native guarantees.
F5 (Largest Lyapunov Exponent) is gated behind `experimental: true` and excluded from composite triage scores.

### Added

- Core AMI and pAMI forecastability analysis package with horizon-specific dependence curves and surrogate significance bands.
- Canonical and benchmark execution scripts with report artifact generation.
- Deterministic interpretation pipeline with Pattern A-E classification and recommendation outputs.
- Exogenous dependence analysis and scorer registry for multiple dependence metrics.
- Optional adapter surface for CLI, HTTP API/SSE, MCP server, and agent-based narration.
- **F1 — Forecastability Profile & Informative Horizon Set**: `ForecastabilityProfile` model and `ForecastabilityProfileService` — horizon-wise profile from AMI curve, surrogate-anchored informative horizons, non-monotone shape detection, model-selection recommendations (Catt 2026, arXiv:2603.27074).
- **F2 — Information-Theoretic Limit Diagnostics**: `TheoreticalLimitDiagnostics` model and service — MI ceiling under log loss, compression and DPI warnings; exploitation ratio reserved as schema placeholder (`supported: False`) (Catt 2026, arXiv:2603.27074).
- **F3 — Predictive Information Learning Curves**: `PredictiveInfoLearningCurve` model and `PredictiveInfoLearningCurveService` — EvoRate-style lookback curve via kNN MI in embedding dimension k, plateau detection, lookback recommendation, reliability warnings (Morawski et al. 2025, arXiv:2510.10744).
- **F4 — Spectral Predictability**: `SpectralPredictabilityScorer` implementing `SeriesDiagnosticScorer` — Welch PSD → spectral entropy → normalised predictability Ω (Wang et al. 2025, arXiv:2507.13556).
- **F5 — Largest Lyapunov Exponent** (experimental): `LyapunovExponentScorer` — Rosenstein LLE via delay embedding; gated behind `experimental: true`, never included in composite triage score (Wang et al. 2025, arXiv:2507.13556).
- **F6 — Entropy-Based Complexity Triage**: `PermutationEntropyScorer` + `SpectralEntropyScorer` implementing `SeriesDiagnosticScorer`, plus `ComplexityBandService` mapping (PE, SE) → complexity band (Ponce-Flores et al. 2020; Bandt & Pompe 2002).
- **F7 — Batch Multi-Signal Ranking**: Extended `run_batch_triage()` with optional diagnostic columns (spectral_predictability, permutation_entropy, complexity_band) from Phase 2 scorers (ForeCA-inspired; Goerg 2013).
- **F8 — Enhanced Exogenous Screening**: Inter-driver redundancy penalty with configurable `redundancy_alpha` + Benjamini-Hochberg FDR correction across drivers × horizons (CATS-inspired; Lu et al. 2024).
- **F9 — Benchmark & Reproducibility Expansion**: Diagnostic regression fixtures for F1-F6 (7 deterministic fixture series), frozen expected outputs with tolerance-aware comparison, rebuild/verify scripts, batch triage regression, exogenous benchmark extension for F8 fields.
- `SeriesDiagnosticScorer` protocol for univariate diagnostic scorers (spectral, entropy, Lyapunov), alongside existing `DependenceScorer`.
- Shared PSD/FFT utility `spectral_utils.py` — deterministic Welch PSD helper for spectral predictability and spectral entropy scorers.
- Triage extension examples (`examples/triage/`): 12 example scripts covering F1-F8 features and A1-A3 agent adapter demos.
- Triage extension notebooks (`notebooks/triage/`): 6 Jupyter notebooks — forecastability profile walkthrough, information limits, predictive info learning curves, spectral & entropy diagnostics, batch & exogenous workbench, agent-ready triage interpretation.
- Agent payload adapters: `triage_agent_payload_models.py` (9 Pydantic payload models + 9 factory functions), `triage_summary_serializer.py` (serialisation envelope with schema version), `triage_agent_interpretation_adapter.py` (deterministic interpretation + warning/experimental handling).
- Theory documentation for forecastability profiles, spectral predictability, entropy-based complexity, predictive information learning curves, and largest Lyapunov exponent.
- Release documentation: repeatable release checklist, v0.1.0 user-facing release notes, and PyPI publication flow guide.

### Changed

- Established the initial project baseline around paper-aligned AMI plus project-extension pAMI workflows.
- `run_triage()` output now includes forecastability profile, theoretical limit diagnostics, and (when enabled) spectral/entropy/learning-curve diagnostics.
- `TriageResult` model extended with optional diagnostic fields for F1-F6 outputs.
- `ScorerRegistry` now supports both `DependenceScorer` and `SeriesDiagnosticScorer` types with a `kind` discriminator.
- `BatchSummaryRow` extended with optional columns for new diagnostic scorers.
- `ExogenousScreeningWorkbenchConfig` extended with `redundancy_alpha` parameter.

### Fixed

- No fixes in the initial release.

### Deprecated

- No deprecations in the initial release.

### Removed

- No removals in the initial release.

### Migration notes

- No migration required for v0.1.0.
- Upgrade notes: [docs/releases/v0.1.0.md](docs/releases/v0.1.0.md)
