"""Example: build a synthetic CSV panel and run the CSV geometry adapter.

Usage:
    uv run python examples/univariate/fingerprint/ami_information_geometry_csv_example.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from forecastability import generate_fingerprint_archetypes, run_ami_geometry_csv_batch

OUTPUT_ROOT = Path("outputs/examples/ami_geometry_csv")
INPUT_CSV_PATH = OUTPUT_ROOT / "inputs" / "synthetic_fingerprint_panel.csv"


def _build_example_frame() -> pd.DataFrame:
    """Build a one-series-per-column CSV frame from deterministic synthetic series."""
    series_map = generate_fingerprint_archetypes(n=420, seed=42)
    frame = pd.DataFrame({name: pd.Series(values) for name, values in series_map.items()})

    # Demonstrate column-wise NaN dropping and conservative short-series skipping.
    frame.loc[frame.index[-20:], "white_noise"] = np.nan
    short_column = pd.Series([float(value) for value in series_map["white_noise"][:40]])
    frame["too_short_after_dropna"] = short_column
    return frame


def main() -> None:
    """Write a synthetic CSV panel, run the adapter, and print validated outcomes."""
    frame = _build_example_frame()
    INPUT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(INPUT_CSV_PATH, index=False)

    result = run_ami_geometry_csv_batch(
        INPUT_CSV_PATH,
        output_root=OUTPUT_ROOT,
        max_lag=24,
        n_surrogates=99,
        random_state=42,
    )

    print("AMI Information Geometry CSV example")
    print(f"  input_csv: {INPUT_CSV_PATH}")
    print(f"  analyzed_series: {len(result.analyzed_items)}")
    print(f"  skipped_series: {len(result.skipped_items)}")
    print(f"  summary_csv: {result.summary_csv_path}")
    print(f"  figure: {result.figure_path}")
    print(f"  markdown: {result.markdown_path}")

    print("\nPer-series outcomes:")
    for item in result.items:
        if item.bundle is None:
            print(f"  - {item.series_id}: skipped ({item.skip_reason})")
            continue
        bundle = item.bundle
        print(
            "  - "
            f"{item.series_id}: structure={bundle.fingerprint.information_structure}, "
            f"signal_to_noise={bundle.geometry.signal_to_noise:.3f}, "
            f"families={list(bundle.recommendation.primary_families)}"
        )


if __name__ == "__main__":
    main()
