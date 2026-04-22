"""Tests for the CSV AMI Information Geometry adapter."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from forecastability.adapters.csv import (
    CsvGeometryBatchResult,
    run_ami_geometry_csv_batch,
)
from forecastability.utils.synthetic import (
    generate_ar1_monotonic,
    generate_seasonal_periodic,
    generate_white_noise,
)


def _write_input_csv(csv_path: Path) -> None:
    """Create a deterministic one-series-per-column CSV fixture."""
    frame = pd.DataFrame(
        {
            "white_noise": pd.Series(generate_white_noise(n=320, seed=42)),
            "ar1_monotonic": pd.Series(generate_ar1_monotonic(n=320, seed=42)),
            "seasonal_periodic": pd.Series(generate_seasonal_periodic(n=320, seed=42)),
            "too_short": pd.Series(generate_white_noise(n=40, seed=7)),
        }
    )
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(csv_path, index=False)


def test_csv_runner_emits_artifacts_and_skips_short_series(tmp_path: Path) -> None:
    """The CSV adapter should analyze valid columns and skip short ones conservatively."""
    input_csv = tmp_path / "input" / "synthetic_panel.csv"
    output_root = tmp_path / "outputs"
    _write_input_csv(input_csv)

    result = run_ami_geometry_csv_batch(
        input_csv,
        output_root=output_root,
        max_lag=12,
        n_surrogates=99,
        random_state=42,
    )

    assert isinstance(result, CsvGeometryBatchResult)
    assert result.summary_csv_path.exists()
    assert result.figure_path.exists()
    assert result.markdown_path.exists()

    analyzed_ids = {item.series_id for item in result.analyzed_items}
    skipped_ids = {item.series_id for item in result.skipped_items}
    assert {"white_noise", "ar1_monotonic", "seasonal_periodic"} <= analyzed_ids
    assert "too_short" in skipped_ids

    summary_frame = pd.read_csv(result.summary_csv_path)
    assert set(summary_frame["series_id"]) == {
        "white_noise",
        "ar1_monotonic",
        "seasonal_periodic",
        "too_short",
    }

    seasonal_row = summary_frame.loc[summary_frame["series_id"] == "seasonal_periodic"].iloc[0]
    assert seasonal_row["status"] == "analyzed"
    assert seasonal_row["information_structure"] == "periodic"

    short_row = summary_frame.loc[summary_frame["series_id"] == "too_short"].iloc[0]
    assert short_row["status"] == "skipped"

    for item in result.analyzed_items:
        assert item.bundle_json_path is not None
        assert item.bundle_json_path.exists()


def test_csv_runner_handles_non_numeric_column_after_nan_drop(tmp_path: Path) -> None:
    """A non-numeric column should be skipped with a stable warning string."""
    input_csv = tmp_path / "input" / "nonnumeric_panel.csv"
    output_root = tmp_path / "outputs"
    frame = pd.DataFrame(
        {
            "ar1_monotonic": pd.Series(generate_ar1_monotonic(n=320, seed=42)),
            "labels": ["bad"] * 320,
        }
    )
    input_csv.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(input_csv, index=False)

    result = run_ami_geometry_csv_batch(
        input_csv,
        output_root=output_root,
        max_lag=12,
        n_surrogates=99,
        random_state=42,
    )

    skipped = next(item for item in result.skipped_items if item.series_id == "labels")
    assert skipped.skip_reason == "no_numeric_values_after_nan_drop"
    assert any("labels: no_numeric_values_after_nan_drop" == warning for warning in result.warnings)
