# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!-- markdownlint-disable MD024 -->

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
