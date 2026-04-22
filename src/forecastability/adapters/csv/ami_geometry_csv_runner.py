"""CSV batch adapter for geometry-backed forecastability fingerprint analysis.

This adapter owns outer-layer concerns only:

* reading one-series-per-column CSV inputs,
* dropping missing values column-wise,
* delegating deterministic computation to the fingerprint use case,
* writing summary CSV, bundle JSON, and plot artifacts.

No thresholding, routing, or AMI estimation logic is implemented here.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

import matplotlib
import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from forecastability.reporting.fingerprint_reporting import (
    build_fingerprint_markdown,
    build_fingerprint_summary_row,
    save_fingerprint_bundle_json,
)
from forecastability.services.ami_information_geometry_service import (
    AmiInformationGeometryConfig,
)
from forecastability.services.fingerprint_service import FingerprintThresholdConfig
from forecastability.services.routing_policy_service import RoutingPolicyConfig
from forecastability.use_cases.run_forecastability_fingerprint import (
    run_forecastability_fingerprint,
)
from forecastability.utils.types import FingerprintBundle

CsvGeometryStatus = Literal["analyzed", "skipped"]


class CsvGeometryBatchItem(BaseModel):
    """One per-column result emitted by the CSV geometry adapter."""

    model_config = ConfigDict(frozen=True)

    series_id: str
    status: CsvGeometryStatus
    n_observations: int
    bundle: FingerprintBundle | None = None
    skip_reason: str | None = None
    bundle_json_path: Path | None = None


class CsvGeometryBatchResult(BaseModel):
    """Composite result for a one-series-per-column CSV geometry run."""

    model_config = ConfigDict(frozen=True)

    input_csv_path: Path
    summary_csv_path: Path
    figure_path: Path
    markdown_path: Path
    items: list[CsvGeometryBatchItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @property
    def analyzed_items(self) -> list[CsvGeometryBatchItem]:
        """Return items that completed deterministic analysis."""
        return [item for item in self.items if item.status == "analyzed"]

    @property
    def skipped_items(self) -> list[CsvGeometryBatchItem]:
        """Return items that were skipped before deterministic analysis."""
        return [item for item in self.items if item.status == "skipped"]


def _coerce_numeric_series(frame: pd.DataFrame, column: str) -> np.ndarray:
    """Return one numeric series after column-wise NaN dropping."""
    numeric = pd.to_numeric(frame[column], errors="coerce")
    return numeric.dropna().to_numpy(dtype=float)


def _item_from_skip(
    *,
    series_id: str,
    n_observations: int,
    reason: str,
) -> CsvGeometryBatchItem:
    """Build a skipped item with a stable reason string."""
    return CsvGeometryBatchItem(
        series_id=series_id,
        status="skipped",
        n_observations=n_observations,
        skip_reason=reason,
    )


def _item_summary_row(item: CsvGeometryBatchItem) -> dict[str, str | int | float]:
    """Render one flat row for the batch summary CSV."""
    row: dict[str, str | int | float] = {
        "series_id": item.series_id,
        "status": item.status,
        "n_observations": item.n_observations,
        "skip_reason": item.skip_reason or "",
    }
    if item.bundle is None:
        return row

    row.update(build_fingerprint_summary_row(item.bundle))
    row["bundle_json_path"] = str(item.bundle_json_path) if item.bundle_json_path else ""
    return row


def _write_summary_csv(items: list[CsvGeometryBatchItem], output_path: Path) -> None:
    """Write the flat summary CSV in deterministic column order."""
    rows = [_item_summary_row(item) for item in items]
    frame = pd.DataFrame(rows)
    preferred_columns = [
        "series_id",
        "status",
        "n_observations",
        "skip_reason",
        "target_name",
        "signal_to_noise",
        "geometry_information_horizon",
        "geometry_information_structure",
        "information_mass",
        "information_horizon",
        "information_structure",
        "nonlinear_share",
        "directness_ratio",
        "confidence",
        "primary_families",
        "n_cautions",
        "bundle_json_path",
    ]
    ordered_columns = [column for column in preferred_columns if column in frame.columns]
    trailing_columns = [column for column in frame.columns if column not in ordered_columns]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.loc[:, ordered_columns + trailing_columns].to_csv(output_path, index=False)


def _save_markdown_report(items: list[CsvGeometryBatchItem], output_path: Path) -> None:
    """Write a stable markdown report for the CSV run."""
    sections = [
        "# AMI Information Geometry CSV Batch",
        "",
        f"- analyzed_series: {sum(item.status == 'analyzed' for item in items)}",
        f"- skipped_series: {sum(item.status == 'skipped' for item in items)}",
        "",
    ]

    for item in items:
        sections.append(f"## {item.series_id}")
        sections.append(f"- status: {item.status}")
        sections.append(f"- n_observations: {item.n_observations}")
        if item.bundle is None:
            sections.append(f"- skip_reason: {item.skip_reason or 'unknown'}")
            sections.append("")
            continue
        sections.append(build_fingerprint_markdown(item.bundle))
        sections.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(sections), encoding="utf-8")


def _configure_matplotlib_backend_for_batch_plots() -> None:
    """Configure a deterministic non-interactive backend for file-only plotting.

    The CSV adapter must be safe for headless script execution while avoiding
    backend changes at import time, which would interfere with notebooks.
    """
    if "matplotlib.pyplot" in sys.modules:
        return

    backend = str(matplotlib.get_backend()).lower()
    notebook_backend_tokens = (
        "module://matplotlib_inline",
        "nbagg",
        "widget",
        "ipympl",
    )
    if any(token in backend for token in notebook_backend_tokens):
        return

    matplotlib.use("Agg", force=False)


def _save_placeholder_figure(output_path: Path) -> None:
    """Write a stable placeholder figure when no analyzable series exist."""
    _configure_matplotlib_backend_for_batch_plots()
    import matplotlib.pyplot as plt

    fig, axis = plt.subplots(figsize=(8.0, 3.5))
    axis.text(
        0.5,
        0.5,
        "No analyzable series were available after column-wise NaN dropping.",
        ha="center",
        va="center",
        fontsize=10,
    )
    axis.set_axis_off()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _plot_geometry_panel(bundles: list[FingerprintBundle], output_path: Path) -> None:
    """Save one multi-panel geometry figure for the analyzed series."""
    if not bundles:
        _save_placeholder_figure(output_path)
        return

    _configure_matplotlib_backend_for_batch_plots()
    import matplotlib.pyplot as plt

    n_cols = min(2, max(1, len(bundles)))
    n_rows = int(np.ceil(len(bundles) / n_cols))
    fig, axes = plt.subplots(
        n_rows,
        n_cols,
        figsize=(7.2 * n_cols, 3.8 * n_rows),
        squeeze=False,
        sharex=False,
        sharey=False,
    )
    flat_axes = list(axes.flat)

    for axis, bundle in zip(flat_axes, bundles, strict=False):
        curve = bundle.geometry.curve
        horizons = [point.horizon for point in curve if point.valid]
        ami_raw = [point.ami_raw or 0.0 for point in curve if point.valid]
        ami_corrected = [point.ami_corrected or 0.0 for point in curve if point.valid]
        tau = [point.tau or 0.0 for point in curve if point.valid]
        accepted_horizons = [point.horizon for point in curve if point.valid and point.accepted]
        accepted_values = [
            point.ami_corrected or 0.0 for point in curve if point.valid and point.accepted
        ]

        axis.plot(horizons, ami_raw, label="AMI raw", color="steelblue", linewidth=1.5)
        axis.plot(
            horizons,
            ami_corrected,
            label="AMI corrected",
            color="darkorange",
            linewidth=1.7,
        )
        axis.plot(
            horizons,
            tau,
            label="tau(h)",
            color="dimgray",
            linestyle="--",
            linewidth=1.2,
        )
        axis.plot(
            horizons,
            [3.0 * value for value in tau],
            label="3*tau(h)",
            color="firebrick",
            linestyle=":",
            linewidth=1.1,
        )
        if accepted_horizons:
            axis.scatter(
                accepted_horizons,
                accepted_values,
                color="forestgreen",
                s=24,
                zorder=3,
                label="accepted",
            )

        axis.set_title(
            (
                f"{bundle.target_name}\n"
                f"structure={bundle.geometry.information_structure}, "
                f"SNR={bundle.geometry.signal_to_noise:.3f}"
            ),
            fontsize=10,
        )
        axis.set_xlabel("Horizon")
        axis.set_ylabel("AMI / threshold")
        axis.grid(alpha=0.25)

    for axis in flat_axes[len(bundles) :]:
        axis.set_axis_off()

    handles, labels = flat_axes[0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="upper center", ncols=min(5, len(labels)))
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.93))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _write_bundle_json(
    *,
    bundle: FingerprintBundle,
    output_dir: Path,
) -> Path:
    """Persist one full bundle as JSON and return the written path."""
    output_path = output_dir / f"{bundle.target_name}.json"
    save_fingerprint_bundle_json(bundle, output_path=output_path)
    return output_path


def run_ami_geometry_csv_batch(
    csv_path: Path,
    *,
    output_root: Path,
    max_lag: int = 24,
    n_surrogates: int = 99,
    random_state: int = 42,
    geometry_config: AmiInformationGeometryConfig | None = None,
    fingerprint_config: FingerprintThresholdConfig | None = None,
    routing_config: RoutingPolicyConfig | None = None,
    write_bundle_json: bool = True,
) -> CsvGeometryBatchResult:
    """Run geometry-backed fingerprint analysis for every CSV column.

    Args:
        csv_path: Input CSV path with one target series per column.
        output_root: Root directory where CSV, markdown, figure, and JSON outputs land.
        max_lag: Maximum analyzed horizon.
        n_surrogates: Number of shuffle surrogates used by the geometry engine.
        random_state: Deterministic seed used for jitter and surrogates.
        geometry_config: Optional geometry configuration override.
        fingerprint_config: Optional downstream fingerprint threshold override.
        routing_config: Optional routing policy override.
        write_bundle_json: Whether to write one bundle JSON file per analyzed series.

    Returns:
        Typed summary of the batch run and emitted artifact paths.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    frame = pd.read_csv(csv_path)
    summary_csv_path = output_root / "tables" / "ami_geometry_summary.csv"
    figure_path = output_root / "figures" / "ami_geometry_profiles.png"
    markdown_path = output_root / "reports" / "ami_geometry_batch.md"
    json_dir = output_root / "json"

    items: list[CsvGeometryBatchItem] = []
    warnings: list[str] = []

    for column in frame.columns:
        values = _coerce_numeric_series(frame, column)
        if values.size == 0:
            reason = "no_numeric_values_after_nan_drop"
            warnings.append(f"{column}: {reason}")
            items.append(_item_from_skip(series_id=column, n_observations=0, reason=reason))
            continue

        try:
            bundle = run_forecastability_fingerprint(
                values,
                target_name=column,
                max_lag=max_lag,
                n_surrogates=n_surrogates,
                random_state=random_state,
                geometry_config=geometry_config,
                fingerprint_config=fingerprint_config,
                routing_config=routing_config,
            )
        except ValueError as exc:
            reason = str(exc)
            warnings.append(f"{column}: {reason}")
            items.append(
                _item_from_skip(series_id=column, n_observations=int(values.size), reason=reason)
            )
            continue

        bundle_json_path = None
        if write_bundle_json:
            bundle_json_path = _write_bundle_json(bundle=bundle, output_dir=json_dir)

        items.append(
            CsvGeometryBatchItem(
                series_id=column,
                status="analyzed",
                n_observations=int(values.size),
                bundle=bundle,
                bundle_json_path=bundle_json_path,
            )
        )

    _write_summary_csv(items, summary_csv_path)
    _save_markdown_report(items, markdown_path)
    _plot_geometry_panel(
        [item.bundle for item in items if item.bundle is not None],
        figure_path,
    )

    return CsvGeometryBatchResult(
        input_csv_path=csv_path,
        summary_csv_path=summary_csv_path,
        figure_path=figure_path,
        markdown_path=markdown_path,
        items=items,
        warnings=warnings,
    )
