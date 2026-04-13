# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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

### Changed
- `run_triage()` output now includes forecastability profile, theoretical limit diagnostics, and (when enabled) spectral/entropy/learning-curve diagnostics.
- `TriageResult` model extended with optional diagnostic fields for F1-F6 outputs.
- `ScorerRegistry` now supports both `DependenceScorer` and `SeriesDiagnosticScorer` types with a `kind` discriminator.
- `BatchSummaryRow` extended with optional columns for new diagnostic scorers.
- `ExogenousScreeningWorkbenchConfig` extended with `redundancy_alpha` parameter.

### Fixed
- No fixes in this release.

### Deprecated
- No deprecations in this release.

### Removed
- No removals in this release.

## [0.1.0] - 2026-04-12

### Added
- Core AMI and pAMI forecastability analysis package with horizon-specific dependence curves and surrogate significance bands.
- Canonical and benchmark execution scripts with report artifact generation.
- Deterministic interpretation pipeline with Pattern A-E classification and recommendation outputs.
- Exogenous dependence analysis and scorer registry for multiple dependence metrics.
- Optional adapter surface for CLI, HTTP API/SSE, MCP server, and agent-based narration.

### Changed
- Established the initial project baseline around paper-aligned AMI plus project-extension pAMI workflows.

### Fixed
- No fixes in the initial release.

### Deprecated
- No deprecations in the initial release.

### Removed
- No removals in the initial release.

### Migration notes
- No migration required for v0.1.0.
- Upgrade notes: [docs/releases/v0.1.0.md](docs/releases/v0.1.0.md)