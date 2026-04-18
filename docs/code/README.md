<!-- type: reference -->
# Code reference

This section documents the `forecastability` package public API and provides user
manuals for the analyzer classes.

The package exposes two primary classes:

- **`ForecastabilityAnalyzer`** — method-independent analyzer with a scorer registry.
  Supports AMI, pAMI, Pearson, Spearman, Kendall, and distance correlation out of the
  box. Custom scorers are registered at runtime via `register_scorer()`.

- **`ForecastabilityAnalyzerExog`** — extends the base analyzer with an optional
  exogenous input. When `exog=None` the behavior is identical to `ForecastabilityAnalyzer`
  (AMI / pAMI). When `exog` is supplied the analyzer switches to cross mode and computes
  CrossMI and pCrossAMI curves, mirroring the CCF / partial-CCF analogy.

Both classes expose `compute_raw()`, `compute_partial()`, and
`compute_significance_generic()`, and return structured `AnalyzeResult` containers.

---

## Documents

| File | Description |
|---|---|
| [module_map.md](module_map.md) | Module-by-module reference for every public symbol in `src/forecastability` |
| [covariant_walkthrough.md](covariant_walkthrough.md) | Live covariant walkthrough notebook contract, section map, and stable artifact paths |
| [exog_analyzer.md](exog_analyzer.md) | `ForecastabilityAnalyzerExog` user manual v1.0 — quick start, terminology, operating modes, synthetic data generators, and a complete runnable test script |
| [exog_analyzer_real_data.md](exog_analyzer_real_data.md) | `ForecastabilityAnalyzerExog` user manual v1.1 — real-world datasets, loading snippets, SNR interpretation table, significance bands, and actual run results (2026-03-14) |
| [exog_benchmark_workflow.md](exog_benchmark_workflow.md) | Fixed exogenous benchmark slice workflow, leakage boundary, outputs, and interpretation policy |
| [covariant_showcase.md](covariant_showcase.md) | Developer reference for the V3-F09 covariant showcase script |
