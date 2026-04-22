"""Lagged-exogenous plotting helpers.

These rendering adapters consume :class:`LaggedExogBundle` rows as-is and only
visualise already-computed lag profiles and selections.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from forecastability.utils.types import LaggedExogBundle, LaggedExogProfileRow


def _rows_for_driver(bundle: LaggedExogBundle, *, driver: str) -> list[LaggedExogProfileRow]:
    """Return lag-profile rows for one driver sorted by lag."""
    rows = [row for row in bundle.profile_rows if row.driver == driver]
    return sorted(rows, key=lambda row: row.lag)


def _selected_predictive_lags(bundle: LaggedExogBundle, *, driver: str) -> set[int]:
    """Return selected predictive lag indices for a driver.

    The plotting layer only reads selection flags already produced by the
    use-case output and does not infer role semantics.
    """
    return {
        row.lag
        for row in bundle.selected_lags
        if row.driver == driver and row.selected_for_tensor and row.lag >= 1
    }


def _selected_lag_zero(bundle: LaggedExogBundle, *, driver: str) -> bool:
    """Return whether lag 0 is selected for a driver in the bundle output."""
    return any(
        row.driver == driver and row.selected_for_tensor and row.lag == 0
        for row in bundle.selected_lags
    )


def _extract_metric_values(
    rows: Sequence[LaggedExogProfileRow],
    *,
    metric_name: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Extract lag/value vectors for one profile metric."""
    lags = np.array([row.lag for row in rows], dtype=int)
    if metric_name == "correlation":
        values = np.array(
            [float(row.correlation) if row.correlation is not None else np.nan for row in rows],
            dtype=float,
        )
    elif metric_name == "cross_ami":
        values = np.array(
            [float(row.cross_ami) if row.cross_ami is not None else np.nan for row in rows],
            dtype=float,
        )
    else:
        raise ValueError(f"Unsupported metric_name: {metric_name!r}")
    return lags, values


def _plot_metric_profile(
    ax: Axes,
    *,
    lags: np.ndarray,
    values: np.ndarray,
    metric_label: str,
    line_color: str,
    selected_predictive_lags: set[int],
    lag_zero_selected: bool,
) -> None:
    """Render one lag profile with lag-0 and selected-lag highlights."""
    ax.plot(
        lags,
        values,
        color=line_color,
        marker="o",
        linewidth=1.8,
        markersize=4.5,
        label=metric_label,
    )
    ax.axhline(0.0, color="black", linewidth=0.7, alpha=0.5)

    if np.any(lags >= 1):
        ax.axvline(
            0.5,
            color="gray",
            linestyle="--",
            linewidth=1.0,
            alpha=0.8,
            label="lag=0 boundary",
        )

    lag_zero_mask = lags == 0
    if lag_zero_mask.any():
        lag_zero_value = float(values[lag_zero_mask][0])
        if np.isfinite(lag_zero_value):
            ax.scatter(
                [0],
                [lag_zero_value],
                marker="s",
                s=56,
                color="tab:orange",
                edgecolors="black",
                linewidths=0.7,
                zorder=5,
                label="lag=0 row",
            )
            if lag_zero_selected:
                ax.scatter(
                    [0],
                    [lag_zero_value],
                    marker="D",
                    s=80,
                    facecolors="none",
                    edgecolors="tab:red",
                    linewidths=1.3,
                    zorder=6,
                    label="lag=0 selected",
                )

    if selected_predictive_lags:
        selected_mask = np.isin(lags, list(selected_predictive_lags)) & np.isfinite(values)
        if selected_mask.any():
            ax.scatter(
                lags[selected_mask],
                values[selected_mask],
                marker="*",
                s=150,
                color="gold",
                edgecolors="black",
                linewidths=0.7,
                zorder=6,
                label="selected predictive lag",
            )

    ax.set_xticks(lags)
    ax.grid(alpha=0.3)


def _driver_order(
    bundle: LaggedExogBundle,
    *,
    driver_order: Sequence[str] | None,
) -> list[str]:
    """Resolve driver plotting order and validate membership."""
    resolved = list(bundle.driver_names if driver_order is None else driver_order)
    if not resolved:
        raise ValueError("driver_order resolved to an empty list")

    unknown = [driver for driver in resolved if driver not in bundle.driver_names]
    if unknown:
        raise ValueError(f"driver_order contains unknown driver names: {unknown}")
    return resolved


def build_lagged_exog_profile_figure(
    bundle: LaggedExogBundle,
    *,
    driver_order: Sequence[str] | None = None,
) -> Figure:
    """Build a correlogram-first lag-profile figure from a lagged-exog bundle.

    Args:
        bundle: Output from ``run_lagged_exogenous_triage``.
        driver_order: Optional explicit driver order for panel rows.

    Returns:
        Matplotlib figure with one row per driver and two columns:
        correlation profile and cross-AMI profile.
    """
    drivers = _driver_order(bundle, driver_order=driver_order)

    fig, axes = plt.subplots(
        nrows=len(drivers),
        ncols=2,
        figsize=(12.5, max(3.2, 2.8 * len(drivers))),
        squeeze=False,
        sharex=False,
    )

    axes[0, 0].set_title("Cross-correlation profile")
    axes[0, 1].set_title("Cross-AMI profile")

    for row_idx, driver in enumerate(drivers):
        rows = _rows_for_driver(bundle, driver=driver)
        if not rows:
            raise ValueError(f"No profile rows found for driver {driver!r}")

        selected_predictive = _selected_predictive_lags(bundle, driver=driver)
        lag_zero_selected = _selected_lag_zero(bundle, driver=driver)

        lags_corr, corr_values = _extract_metric_values(rows, metric_name="correlation")
        lags_ami, ami_values = _extract_metric_values(rows, metric_name="cross_ami")

        corr_ax = axes[row_idx, 0]
        ami_ax = axes[row_idx, 1]

        _plot_metric_profile(
            corr_ax,
            lags=lags_corr,
            values=corr_values,
            metric_label="correlogram",
            line_color="tab:blue",
            selected_predictive_lags=selected_predictive,
            lag_zero_selected=lag_zero_selected,
        )
        _plot_metric_profile(
            ami_ax,
            lags=lags_ami,
            values=ami_values,
            metric_label="cross_ami",
            line_color="tab:green",
            selected_predictive_lags=selected_predictive,
            lag_zero_selected=lag_zero_selected,
        )

        corr_ax.set_ylabel(f"{driver}\nscore")

    for ax in axes[-1, :]:
        ax.set_xlabel("Lag")

    handles: list[Artist] = []
    labels: list[str] = []
    for ax in axes[0, :]:
        ax_handles, ax_labels = ax.get_legend_handles_labels()
        for handle, label in zip(ax_handles, ax_labels, strict=True):
            if label not in labels:
                labels.append(label)
                handles.append(handle)
    if handles:
        fig.legend(handles, labels, loc="upper center", ncol=min(4, len(labels)))

    fig.suptitle("Lagged exogenous profiles: correlogram and cross-AMI", y=1.02)
    fig.tight_layout()
    return fig


def save_lagged_exog_profile_figure(
    bundle: LaggedExogBundle,
    *,
    output_path: Path,
    driver_order: Sequence[str] | None = None,
) -> Path:
    """Save the lagged-exogenous profile figure to disk.

    Args:
        bundle: Output from ``run_lagged_exogenous_triage``.
        output_path: Destination path.
        driver_order: Optional explicit driver order for panel rows.

    Returns:
        The same ``output_path`` for convenience chaining.
    """
    fig = build_lagged_exog_profile_figure(bundle, driver_order=driver_order)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return output_path


def save_lagged_exog_selection_heatmap(
    bundle: LaggedExogBundle,
    *,
    output_path: Path,
    driver_order: Sequence[str] | None = None,
) -> Path:
    """Save a selected-lag heatmap derived from ``bundle.selected_lags``."""
    drivers = _driver_order(bundle, driver_order=driver_order)
    lag_values = np.arange(0, bundle.max_lag + 1, dtype=int)
    matrix = np.zeros((len(drivers), lag_values.size), dtype=float)

    driver_index = {driver: idx for idx, driver in enumerate(drivers)}
    for row in bundle.selected_lags:
        if not row.selected_for_tensor:
            continue
        if row.driver not in driver_index:
            continue
        if row.lag < 0 or row.lag > bundle.max_lag:
            continue
        matrix[driver_index[row.driver], row.lag] = 1.0

    fig, ax = plt.subplots(
        figsize=(max(8.0, 4.0 + 0.7 * lag_values.size), max(3.2, 2.0 + 0.5 * len(drivers)))
    )
    image = ax.imshow(matrix, aspect="auto", cmap="YlGn", vmin=0.0, vmax=1.0)
    ax.set_title("Selected lag map for downstream tensor hand-off")
    ax.set_xlabel("Lag")
    ax.set_ylabel("Driver")
    ax.set_xticks(np.arange(lag_values.size), labels=[str(int(lag)) for lag in lag_values])
    ax.set_yticks(np.arange(len(drivers)), labels=drivers)

    if lag_values.size >= 2:
        ax.axvline(0.5, color="gray", linestyle="--", linewidth=1.0, alpha=0.8)

    for row_idx, _driver in enumerate(drivers):
        for col_idx, _lag in enumerate(lag_values):
            value = int(matrix[row_idx, col_idx])
            ax.text(
                col_idx,
                row_idx,
                str(value),
                ha="center",
                va="center",
                fontsize=8,
                color="black",
            )

    fig.colorbar(image, ax=ax, shrink=0.8, ticks=[0.0, 1.0], label="selected_for_tensor")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return output_path
