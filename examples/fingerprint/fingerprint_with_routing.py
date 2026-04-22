"""Comprehensive fingerprint + routing example — V3_1-F05.

Demonstrates the full V3_1 forecastability fingerprint pipeline via the public
``forecastability`` API:

1. Generates five synthetic archetypes (white noise, AR(1) monotonic, seasonal
   periodic, nonlinear mixed, mediated directness drop).
2. Runs the full use-case ``run_forecastability_fingerprint()`` for each
   archetype — this integrates AMI information geometry, fingerprint building,
   and deterministic routing in one call.
3. Renders a full markdown summary per archetype using
   ``build_fingerprint_markdown()``.
4. Prints a compact summary table built from ``build_fingerprint_summary_row()``.
5. Saves per-archetype JSON to ``outputs/json/fingerprint_{name}.json``.
6. Saves a combined panel report to ``outputs/reports/fingerprint_panel.md``.

Usage::

    uv run python examples/fingerprint/fingerprint_with_routing.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from forecastability import (
    FingerprintBundle,
    build_fingerprint_markdown,
    build_fingerprint_panel_markdown,
    build_fingerprint_summary_row,
    run_forecastability_fingerprint,
    save_fingerprint_bundle_json,
)
from forecastability.utils.synthetic import (
    generate_fingerprint_archetypes,
    generate_mediated_directness_drop,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

N_SAMPLES: int = 600
MAX_LAG: int = 24
N_SURROGATES: int = 99
RANDOM_STATE: int = 42

OUTPUT_JSON_DIR = Path("outputs/json")
OUTPUT_REPORTS_DIR = Path("outputs/reports")

# ---------------------------------------------------------------------------
# Archetype registry
# ---------------------------------------------------------------------------


def _build_archetypes() -> list[tuple[str, np.ndarray]]:
    """Build the canonical synthetic example panel from the shared helper module."""
    series_map = generate_fingerprint_archetypes(n=N_SAMPLES, seed=RANDOM_STATE)
    series_map["mediated_directness_drop"] = generate_mediated_directness_drop(
        N_SAMPLES,
        seed=RANDOM_STATE,
    )[1]
    return list(series_map.items())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run fingerprint pipeline for all archetypes and render reports."""
    bundles: list[FingerprintBundle] = []
    archetypes = _build_archetypes()

    for name, series in archetypes:
        print(f"\n{'=' * 60}")
        print(f"Archetype: {name}")
        print(f"{'=' * 60}")

        bundle = run_forecastability_fingerprint(
            series=series,
            target_name=name,
            max_lag=MAX_LAG,
            n_surrogates=N_SURROGATES,
            random_state=RANDOM_STATE,
        )
        bundles.append(bundle)

        # Print full markdown summary
        md = build_fingerprint_markdown(bundle)
        print(md)

        # Save JSON
        json_path = OUTPUT_JSON_DIR / f"fingerprint_{name}.json"
        save_fingerprint_bundle_json(bundle, output_path=json_path)
        print(f"JSON saved → {json_path}")

    # Compact summary table
    print("\n" + "=" * 60)
    print("Summary Table")
    print("=" * 60)
    header_fields = [
        "target_name",
        "signal_to_noise",
        "geometry_information_structure",
        "information_mass",
        "information_horizon",
        "information_structure",
        "nonlinear_share",
        "directness_ratio",
        "confidence",
        "primary_families",
        "n_cautions",
    ]
    col_width = 22
    header_row = "  ".join(f"{f:<{col_width}}" for f in header_fields)
    print(header_row)
    print("-" * len(header_row))
    for bundle in bundles:
        row = build_fingerprint_summary_row(bundle)
        values = []
        for f in header_fields:
            v = row[f]
            if isinstance(v, float):
                values.append(f"{v:<{col_width}.4f}")
            else:
                values.append(f"{str(v):<{col_width}}")
        print("  ".join(values))

    # Save combined panel markdown
    panel_md = build_fingerprint_panel_markdown(bundles)
    panel_path = OUTPUT_REPORTS_DIR / "fingerprint_panel.md"
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    panel_path.write_text(panel_md, encoding="utf-8")
    print(f"\nPanel report saved → {panel_path}")


if __name__ == "__main__":
    main()
