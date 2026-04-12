"""Fixture-driven benchmark reproducibility helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

from forecastability.aggregation import (
    add_terciles,
    compute_rank_associations,
    summarize_frequency_panels,
    summarize_terciles,
)

_REQUIRED_HORIZON_COLUMNS = frozenset(
    ["series_id", "frequency", "model_name", "horizon", "ami", "pami", "smape"]
)
_ARTIFACT_FILENAMES = (
    "rank_associations.csv",
    "ami_terciles.csv",
    "pami_terciles.csv",
    "frequency_panel_summary.csv",
    "benchmark_summary_table.csv",
)
_SORT_KEYS_BY_ARTIFACT: dict[str, list[str]] = {
    "rank_associations.csv": ["model_name", "horizon"],
    "ami_terciles.csv": ["frequency", "model_name", "horizon", "ami_tercile"],
    "pami_terciles.csv": ["frequency", "model_name", "horizon", "pami_tercile"],
    "frequency_panel_summary.csv": ["frequency", "model_name"],
    "benchmark_summary_table.csv": ["model_name"],
}


def _load_horizon_fixture(path: Path) -> pd.DataFrame:
    """Load and validate the raw fixture horizon table.

    Args:
        path: CSV file path for fixture horizon rows.

    Returns:
        Validated horizon table sorted by series, model, and horizon.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the table is empty or missing required columns.
    """
    if not path.exists():
        raise FileNotFoundError(f"Missing fixture horizon table: {path}")

    table = pd.read_csv(path)
    if table.empty:
        raise ValueError(f"Fixture horizon table is empty: {path}")

    missing = sorted(_REQUIRED_HORIZON_COLUMNS - set(table.columns))
    if missing:
        raise ValueError("Fixture horizon table is missing required columns: " + ", ".join(missing))

    return table.sort_values(["series_id", "model_name", "horizon"]).reset_index(drop=True)


def _build_benchmark_summary_table(rank_associations: pd.DataFrame) -> pd.DataFrame:
    """Aggregate rank-association rows to one summary row per model.

    Args:
        rank_associations: Output of ``compute_rank_associations``.

    Returns:
        DataFrame with model-level mean Spearman metrics and mean delta.
    """
    summary = (
        rank_associations.groupby("model_name", as_index=False)
        .agg(
            mean_spearman_ami_smape=("spearman_ami_smape", "mean"),
            mean_spearman_pami_smape=("spearman_pami_smape", "mean"),
            mean_delta_pami_minus_ami=("delta_pami_minus_ami", "mean"),
        )
        .sort_values(["mean_delta_pami_minus_ami", "model_name"], ascending=[False, True])
        .reset_index(drop=True)
    )

    preferred = []
    for delta in summary["mean_delta_pami_minus_ami"].tolist():
        if delta > 0.02:
            preferred.append("pami")
        elif delta < -0.02:
            preferred.append("ami")
        else:
            preferred.append("tie")

    summary["preferred_diagnostic"] = preferred
    return summary


def _sort_for_artifact(table: pd.DataFrame, artifact_name: str) -> pd.DataFrame:
    """Sort one artifact table into deterministic row order.

    Args:
        table: Artifact table to sort.
        artifact_name: Artifact filename used to select sort keys.

    Returns:
        Sorted and index-reset table.
    """
    sort_keys = _SORT_KEYS_BY_ARTIFACT.get(artifact_name)
    if not sort_keys:
        return table.reset_index(drop=True)
    return table.sort_values(sort_keys).reset_index(drop=True)


def build_fixture_benchmark_artifacts(
    horizon_table: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build benchmark summary artifacts from a raw horizon table.

    Args:
        horizon_table: Raw benchmark run rows.

    Returns:
        Tuple of artifact tables in output order:
            rank_associations,
            ami_terciles,
            pami_terciles,
            frequency_panel_summary,
            benchmark_summary_table.
    """
    rank_associations = _sort_for_artifact(
        compute_rank_associations(horizon_table), "rank_associations.csv"
    )
    ami_terciles = _sort_for_artifact(
        summarize_terciles(
            add_terciles(horizon_table, metric_col="ami", output_col="ami_tercile"),
            tercile_col="ami_tercile",
        ),
        "ami_terciles.csv",
    )
    pami_terciles = _sort_for_artifact(
        summarize_terciles(
            add_terciles(horizon_table, metric_col="pami", output_col="pami_tercile"),
            tercile_col="pami_tercile",
        ),
        "pami_terciles.csv",
    )
    frequency_panel_summary = _sort_for_artifact(
        summarize_frequency_panels(horizon_table), "frequency_panel_summary.csv"
    )
    benchmark_summary_table = _sort_for_artifact(
        _build_benchmark_summary_table(rank_associations), "benchmark_summary_table.csv"
    )
    return (
        rank_associations,
        ami_terciles,
        pami_terciles,
        frequency_panel_summary,
        benchmark_summary_table,
    )


def write_fixture_benchmark_artifacts(
    *,
    fixture_horizon_path: Path,
    output_dir: Path,
) -> list[Path]:
    """Rebuild and save benchmark fixture artifacts.

    Args:
        fixture_horizon_path: Path to raw fixture horizon-table CSV.
        output_dir: Destination directory for rebuilt artifacts.

    Returns:
        Ordered list of written artifact paths.
    """
    horizon_table = _load_horizon_fixture(fixture_horizon_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    artifact_tables = build_fixture_benchmark_artifacts(horizon_table)
    written: list[Path] = []
    for artifact_name, artifact_table in zip(_ARTIFACT_FILENAMES, artifact_tables, strict=True):
        out_path = output_dir / artifact_name
        artifact_table.to_csv(out_path, index=False)
        written.append(out_path)
    return written


def verify_fixture_benchmark_artifacts(
    *,
    actual_dir: Path,
    expected_dir: Path,
) -> None:
    """Verify rebuilt fixture artifacts against frozen expected CSVs.

    Args:
        actual_dir: Directory containing rebuilt artifact CSVs.
        expected_dir: Directory containing frozen expected CSVs.

    Raises:
        ValueError: If any artifact is missing or differs from expected content.
    """
    errors: list[str] = []

    for artifact_name in _ARTIFACT_FILENAMES:
        actual_path = actual_dir / artifact_name
        expected_path = expected_dir / artifact_name
        if not actual_path.exists():
            errors.append(f"Missing rebuilt artifact: {actual_path}")
            continue
        if not expected_path.exists():
            errors.append(f"Missing frozen expected artifact: {expected_path}")
            continue

        actual_table = _sort_for_artifact(pd.read_csv(actual_path), artifact_name)
        expected_table = _sort_for_artifact(pd.read_csv(expected_path), artifact_name)
        try:
            assert_frame_equal(
                actual_table,
                expected_table,
                check_exact=False,
                rtol=1e-9,
                atol=1e-9,
            )
        except AssertionError as exc:
            errors.append(f"{artifact_name}: {exc}")

    if errors:
        error_block = "\n".join(f"- {line}" for line in errors)
        raise ValueError(f"Fixture reproducibility verification failed:\n{error_block}")
