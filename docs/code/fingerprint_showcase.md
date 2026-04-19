<!-- type: reference -->
# Fingerprint Showcase

Developer reference for the v0.3.1 fingerprint showcase script and its
notebook-facing reporting helpers.

## Purpose

`scripts/run_showcase_fingerprint.py` is the canonical end-to-end integration
surface for the geometry-backed forecastability fingerprint release. It uses the
prepared synthetic archetypes from `forecastability.utils.synthetic` and runs the
full deterministic chain:

1. `run_forecastability_fingerprint()`
2. `compute_linear_information_curve()`
3. strict A1 payload generation
4. strict A2 envelope serialisation
5. strict A3 deterministic interpretation
6. showcase report/figure/table rendering
7. verification that the agent-facing outputs still match the deterministic bundle

The companion notebook is
[../../notebooks/walkthroughs/02_forecastability_fingerprint_showcase.ipynb](../../notebooks/walkthroughs/02_forecastability_fingerprint_showcase.ipynb).

## Usage

```bash
uv run scripts/run_showcase_fingerprint.py
uv run scripts/run_showcase_fingerprint.py --smoke
uv run scripts/run_showcase_fingerprint.py --quiet
```

## Artifact contract

The script writes to `outputs/*/showcase_fingerprint/`.

| Artifact | Path |
| --- | --- |
| Corrected-profile figure grid | `outputs/figures/showcase_fingerprint/fingerprint_profiles.png` |
| Fingerprint-metric overview | `outputs/figures/showcase_fingerprint/fingerprint_metrics.png` |
| Summary table | `outputs/tables/showcase_fingerprint/fingerprint_summary.csv` |
| Routing table | `outputs/tables/showcase_fingerprint/fingerprint_routing.csv` |
| Human-readable report | `outputs/reports/showcase_fingerprint/showcase_report.md` |
| Verification report | `outputs/reports/showcase_fingerprint/verification.md` |
| JSON manifest | `outputs/json/showcase_fingerprint/showcase_manifest.json` |

Each canonical series also receives bundle, A1 payload, A2 envelope, and A3
interpretation JSON files under `outputs/json/showcase_fingerprint/`.

## Helper module

The script and notebook share
`forecastability.reporting.fingerprint_showcase`.

That module owns only presentation-layer behavior:

- `build_fingerprint_showcase_record()` for strict A1/A2/A3 packaging
- `showcase_summary_frame()` and `routing_table_frame()` for stable tables
- `save_showcase_profile_grid()` and `save_metric_overview()` for stable figures
- `verify_showcase_records()` for deterministic alignment checks
- `build_showcase_report()` and `build_verification_markdown()` for markdown artifacts

It must not recompute geometry, retune thresholds, or override routing.

## Scope boundary

The fingerprint showcase remains intentionally:

- univariate-first,
- AMI-first,
- deterministic by default,
- heuristic at the routing layer rather than exact-model selection.

The final plain-language section in the markdown report is a communication
surface only. It translates the mathematics for humans after the numbers are
already fixed.
