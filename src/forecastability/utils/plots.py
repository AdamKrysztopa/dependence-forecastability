"""Plotting utilities for canonical AMI/pAMI analysis."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from forecastability.utils.io_models import CanonicalPayload
from forecastability.utils.types import CanonicalExampleResult


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _annotate_peak(ax: plt.Axes, lags: np.ndarray, values: np.ndarray) -> None:
    """Annotate the global peak of a metric curve with its lag index."""
    if values.size == 0:
        return
    peak_idx = int(np.argmax(values))
    peak_lag = int(lags[peak_idx])
    peak_val = float(values[peak_idx])
    ax.annotate(
        f"h={peak_lag}",
        xy=(peak_lag, peak_val),
        xytext=(peak_lag + max(1, lags.size // 20), peak_val),
        fontsize=8,
        color="black",
        arrowprops={"arrowstyle": "->", "lw": 0.8, "color": "black"},
        va="center",
    )


def plot_ami_with_band(result: CanonicalExampleResult, *, save_path: Path) -> None:
    """Plot AMI with 95% surrogate threshold (dashed) and peak annotation."""
    fig, ax = plt.subplots(figsize=(10, 4))
    lags = np.arange(1, result.ami.values.size + 1)
    ax.plot(lags, result.ami.values, lw=2, label="AMI(h)")
    if result.ami.upper_band is not None:
        ax.plot(
            lags,
            result.ami.upper_band,
            ls="--",
            lw=1,
            color="grey",
            label="95% surrogate threshold",
        )
    _annotate_peak(ax, lags, result.ami.values)
    ax.set_title(f"{result.series_name} - AMI")
    ax.set_xlabel("Lag h")
    ax.grid(alpha=0.3)
    ax.legend()
    _save(fig, save_path)


def plot_pami_with_band(result: CanonicalExampleResult, *, save_path: Path) -> None:
    """Plot pAMI with peak annotation (surrogate band removed — trivially near zero)."""
    fig, ax = plt.subplots(figsize=(10, 4))
    lags = np.arange(1, result.pami.values.size + 1)
    ax.plot(lags, result.pami.values, lw=2, color="tab:red", label="pAMI(h)")
    _annotate_peak(ax, lags, result.pami.values)
    ax.set_title(f"{result.series_name} - pAMI")
    ax.set_xlabel("Lag h")
    ax.grid(alpha=0.3)
    ax.legend()
    _save(fig, save_path)


def plot_ami_pami_overlay(result: CanonicalExampleResult, *, save_path: Path) -> None:
    """Plot AMI and pAMI overlay."""
    fig, ax = plt.subplots(figsize=(10, 4))
    lags_ami = np.arange(1, result.ami.values.size + 1)
    lags_pami = np.arange(1, result.pami.values.size + 1)
    ax.plot(lags_ami, result.ami.values, lw=2, label="AMI")
    ax.plot(lags_pami, result.pami.values, lw=2, label="pAMI", color="tab:red")
    _annotate_peak(ax, lags_ami, result.ami.values)
    _annotate_peak(ax, lags_pami, result.pami.values)
    ax.set_title(f"{result.series_name} - AMI vs pAMI")
    ax.set_xlabel("Lag")
    ax.grid(alpha=0.3)
    ax.legend()
    _save(fig, save_path)


def plot_ami_minus_pami(result: CanonicalExampleResult, *, save_path: Path) -> None:
    """Plot AMI minus pAMI on shared lag support."""
    n = min(result.ami.values.size, result.pami.values.size)
    lags = np.arange(1, n + 1)
    diff = result.ami.values[:n] - result.pami.values[:n]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(lags, diff, lw=2, color="tab:green")
    ax.axhline(0.0, color="black", lw=1)
    ax.set_title(f"{result.series_name} - AMI minus pAMI")
    ax.set_xlabel("Lag")
    ax.grid(alpha=0.3)
    _save(fig, save_path)


def plot_canonical_result(
    result: CanonicalExampleResult,
    *,
    save_path: Path,
) -> None:
    """Plot canonical multi-panel figure with series + AMI + pAMI."""
    fig, axs = plt.subplots(3, 1, figsize=(11, 10))

    axs[0].plot(result.series, lw=1.5)
    axs[0].set_title(f"{result.series_name} - representative series")
    axs[0].grid(alpha=0.3)

    lags_ami = np.arange(1, result.ami.values.size + 1)
    axs[1].plot(lags_ami, result.ami.values, lw=2, label="AMI(h)")
    if result.ami.upper_band is not None:
        axs[1].plot(
            lags_ami,
            result.ami.upper_band,
            ls="--",
            lw=1,
            color="grey",
            label="95% surrogate threshold",
        )
    _annotate_peak(axs[1], lags_ami, result.ami.values)
    axs[1].set_title("AMI - nonlinear ACF interpretation")
    axs[1].legend()
    axs[1].grid(alpha=0.3)

    lags_pami = np.arange(1, result.pami.values.size + 1)
    axs[2].plot(lags_pami, result.pami.values, lw=2, color="tab:red", label="pAMI(h)")
    _annotate_peak(axs[2], lags_pami, result.pami.values)
    axs[2].set_title("pAMI - nonlinear PACF interpretation")
    axs[2].legend()
    axs[2].grid(alpha=0.3)

    plt.tight_layout()
    _save(fig, save_path)


def save_all_canonical_plots(
    result: CanonicalExampleResult,
    *,
    output_dir: Path,
) -> dict[str, Path]:
    """Save all required plots for a canonical result."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "multi_panel": output_dir / f"{result.series_name}.png",
        "ami": output_dir / f"{result.series_name}_ami.png",
        "pami": output_dir / f"{result.series_name}_pami.png",
        "overlay": output_dir / f"{result.series_name}_overlay.png",
        "difference": output_dir / f"{result.series_name}_ami_minus_pami.png",
    }

    plot_canonical_result(result, save_path=paths["multi_panel"])
    plot_ami_with_band(result, save_path=paths["ami"])
    plot_pami_with_band(result, save_path=paths["pami"])
    plot_ami_pami_overlay(result, save_path=paths["overlay"])
    plot_ami_minus_pami(result, save_path=paths["difference"])
    return paths


def plot_canonical_panel_summary(
    payloads: Sequence[CanonicalPayload],
    *,
    save_path: Path,
) -> None:
    """Plot a cross-series canonical summary figure."""
    if not payloads:
        raise ValueError("payloads must contain at least one canonical payload")

    labels = [payload.series_name.replace("_", " ").title() for payload in payloads]
    auc_ami = np.array([float(payload.summary.auc_ami) for payload in payloads], dtype=float)
    directness_ratio = np.array(
        [float(payload.summary.directness_ratio) for payload in payloads],
        dtype=float,
    )
    n_sig_ami = np.array([int(payload.summary.n_sig_ami) for payload in payloads], dtype=float)
    n_sig_pami = np.array([int(payload.summary.n_sig_pami) for payload in payloads], dtype=float)
    forecastability_classes = [payload.interpretation.forecastability_class for payload in payloads]
    modeling_regimes = [payload.interpretation.modeling_regime for payload in payloads]

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    scatter_ax, counts_ax = axes
    palette: dict[str, str] = {
        "high": "tab:green",
        "medium": "tab:orange",
        "low": "tab:red",
    }

    ordered_classes = list(dict.fromkeys(forecastability_classes))
    for forecastability_class in ordered_classes:
        class_indices = [
            index
            for index, class_name in enumerate(forecastability_classes)
            if class_name == forecastability_class
        ]
        point_sizes = 90 + n_sig_ami[class_indices] * 18.0
        scatter_ax.scatter(
            auc_ami[class_indices],
            directness_ratio[class_indices],
            s=point_sizes,
            alpha=0.85,
            edgecolors="black",
            linewidths=0.5,
            color=palette.get(forecastability_class, "tab:blue"),
            label=forecastability_class.title(),
        )

    for label, auc_value, directness_value in zip(labels, auc_ami, directness_ratio, strict=True):
        scatter_ax.annotate(
            label,
            xy=(float(auc_value), float(directness_value)),
            xytext=(6, 6),
            textcoords="offset points",
            fontsize=8,
        )

    scatter_ax.axhline(1.0, color="tab:purple", ls="--", lw=1, alpha=0.7)
    scatter_ax.axhline(0.5, color="grey", ls=":", lw=1, alpha=0.7)
    scatter_ax.set_title("Canonical panel: dependence strength vs directness")
    scatter_ax.set_xlabel("AMI AUC")
    scatter_ax.set_ylabel("Directness ratio (pAMI AUC / AMI AUC)")
    scatter_ax.grid(alpha=0.3)
    scatter_ax.legend(title="Forecastability")

    y_positions = np.arange(len(payloads), dtype=float)
    counts_ax.barh(
        y_positions - 0.18,
        n_sig_ami,
        height=0.35,
        label="Significant AMI lags",
        color="tab:blue",
        alpha=0.8,
    )
    counts_ax.barh(
        y_positions + 0.18,
        n_sig_pami,
        height=0.35,
        label="Significant pAMI lags",
        color="tab:red",
        alpha=0.8,
    )
    counts_ax.set_yticks(y_positions)
    counts_ax.set_yticklabels(labels)
    counts_ax.invert_yaxis()
    counts_ax.set_title("Lag significance footprint by series")
    counts_ax.set_xlabel("Count of significant lags")
    counts_ax.grid(alpha=0.3, axis="x")
    counts_ax.legend(loc="lower right")

    max_sig = float(max(float(n_sig_ami.max()), float(n_sig_pami.max()), 1.0))
    counts_ax.set_xlim(0, max_sig + 3.5)
    for y_position, ami_count, pami_count, directness_value, modeling_regime in zip(
        y_positions,
        n_sig_ami,
        n_sig_pami,
        directness_ratio,
        modeling_regimes,
        strict=True,
    ):
        counts_ax.text(
            max(float(ami_count), float(pami_count)) + 0.2,
            float(y_position),
            f"DR={float(directness_value):.2f} | {modeling_regime}",
            va="center",
            fontsize=8,
        )

    fig.suptitle("Canonical triage cross-series summary", fontsize=13)
    plt.tight_layout()
    _save(fig, save_path)


def plot_rank_association_bars(
    rank_associations: pd.DataFrame,
    *,
    save_path: Path,
) -> None:
    """Plot per-model mean rank association deltas."""
    fig, ax = plt.subplots(figsize=(10, 4))
    summary = (
        rank_associations.groupby("model_name", as_index=False)["delta_pami_minus_ami"]
        .mean()
        .sort_values("delta_pami_minus_ami")
    )
    ax.bar(summary["model_name"], summary["delta_pami_minus_ami"], color="tab:orange")
    ax.axhline(0.0, color="black", lw=1)
    ax.set_title("Mean Spearman delta (pAMI - AMI) by model")
    ax.set_ylabel("Delta rank association")
    ax.tick_params(axis="x", rotation=20)
    ax.grid(alpha=0.3, axis="y")
    _save(fig, save_path)


def plot_frequency_panel(
    frequency_summary: pd.DataFrame,
    *,
    save_path: Path,
) -> None:
    """Plot mean sMAPE by frequency and model."""
    fig, ax = plt.subplots(figsize=(11, 5))
    frequencies = sorted(frequency_summary["frequency"].unique())
    models = sorted(frequency_summary["model_name"].unique())
    width = 0.8 / max(len(models), 1)
    base_x = np.arange(len(frequencies))

    for idx, model in enumerate(models):
        subset = frequency_summary[frequency_summary["model_name"] == model]
        y = []
        for freq in frequencies:
            row = subset[subset["frequency"] == freq]
            y.append(float(row["mean_smape"].iloc[0]) if not row.empty else np.nan)
        ax.bar(base_x + idx * width, y, width=width, label=model)

    ax.set_xticks(base_x + width * (len(models) - 1) / 2)
    ax.set_xticklabels(frequencies)
    ax.set_title("Frequency-wise benchmark panel (mean sMAPE)")
    ax.set_ylabel("Mean sMAPE")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    _save(fig, save_path)


def plot_smape_vs_ami(
    horizon_table: pd.DataFrame,
    *,
    metric: str = "ami",
    horizons: list[int] | None = None,
    save_path: Path,
) -> None:
    """Scatter plot of sMAPE vs AMI (or pAMI) per forecaster, one subplot per model.

    Each point is one (series, horizon) observation.  Spearman ρ is annotated in
    each panel.  This reproduces the per-forecaster scatter figure from the paper.

    Args:
        horizon_table: Output of ``build_horizon_table`` with columns
            ``[series_id, frequency, model_name, horizon, ami, pami, smape]``.
        metric: ``"ami"`` or ``"pami"`` — which metric to use on the X-axis.
        horizons: If given, filter to only these horizon values before plotting.
            Useful to restrict to short-horizon (h=1) or a representative subset.
        save_path: Destination path for the figure.
    """
    from scipy.stats import spearmanr

    if metric not in {"ami", "pami"}:
        raise ValueError("metric must be 'ami' or 'pami'")

    data = horizon_table.copy()
    if horizons is not None:
        data = data[data["horizon"].isin(horizons)]

    models = sorted(data["model_name"].unique())
    n_models = len(models)

    fig, axes = plt.subplots(1, n_models, figsize=(5 * n_models, 4), sharey=False, squeeze=False)

    for col, model in enumerate(models):
        ax = axes[0, col]
        subset = data[data["model_name"] == model].dropna(subset=[metric, "smape"])

        x = subset[metric].to_numpy()
        y = subset["smape"].to_numpy()

        # colour by frequency for visual grouping
        freq_order = ["yearly", "quarterly", "monthly", "weekly", "daily", "hourly"]
        palette = plt.cm.tab10  # type: ignore[attr-defined]
        freq_colors = {f: palette(i / len(freq_order)) for i, f in enumerate(freq_order)}

        for freq in freq_order:
            mask = subset["frequency"] == freq
            if mask.any():
                ax.scatter(
                    subset.loc[mask, metric],
                    subset.loc[mask, "smape"],
                    s=10,
                    alpha=0.45,
                    color=freq_colors[freq],
                    label=freq,
                    rasterized=True,
                )

        # Spearman annotation
        if len(x) >= 3:
            rho, pval = spearmanr(x, y)
            pval_str = "< 0.001" if pval < 0.001 else f"= {pval:.3f}"
            ax.text(
                0.95,
                0.97,
                f"ρ = {rho:.3f}\n(p {pval_str})",
                transform=ax.transAxes,
                ha="right",
                va="top",
                fontsize=8,
                bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "alpha": 0.7},
            )

        # trend line
        if len(x) >= 3:
            coeffs = np.polyfit(x, y, 1)
            x_line = np.linspace(x.min(), x.max(), 100)
            ax.plot(x_line, np.polyval(coeffs, x_line), color="black", lw=1.2, ls="--")

        horizon_label = (
            f"h ∈ {{{','.join(map(str, sorted(horizons)))}}}"
            if horizons is not None
            else "all horizons"
        )
        ax.set_xlabel(metric.upper() + f"  [{horizon_label}]")
        ax.set_ylabel("sMAPE" if col == 0 else "")
        ax.set_title(model.replace("_", " ").title())
        ax.grid(alpha=0.3)

    # shared legend (first row of patches collected from first axis)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        title="Frequency",
        loc="upper center",
        ncol=min(6, len(handles)),
        bbox_to_anchor=(0.5, 1.02),
        fontsize=8,
    )
    fig.suptitle(
        f"sMAPE vs {metric.upper()} per forecaster  (M4 benchmark)",
        y=1.06,
        fontsize=12,
    )
    plt.tight_layout()
    _save(fig, save_path)


def plot_exog_benchmark_curves(
    horizon_table: pd.DataFrame,
    *,
    save_path: Path,
) -> None:
    """Plot raw versus conditioned cross-dependence for each exogenous case."""
    cases = horizon_table["case_id"].drop_duplicates().tolist()
    if not cases:
        raise ValueError("horizon_table must contain at least one case")

    fig, axes = plt.subplots(
        len(cases),
        1,
        figsize=(10, max(4, 3.5 * len(cases))),
        sharex=True,
        squeeze=False,
    )
    for idx, case_id in enumerate(cases):
        ax = axes[idx, 0]
        subset = horizon_table[horizon_table["case_id"] == case_id].sort_values("horizon")
        ax.plot(subset["horizon"], subset["raw_cross_mi"], lw=2, label="Raw CrossMI")
        ax.plot(
            subset["horizon"],
            subset["conditioned_cross_mi"],
            lw=2,
            color="tab:red",
            label="Conditioned pCrossAMI",
        )
        warning_rows = subset[subset["warning_directness_gt_one"] == 1]
        if not warning_rows.empty:
            ax.scatter(
                warning_rows["horizon"],
                warning_rows["conditioned_cross_mi"],
                color="tab:orange",
                zorder=3,
                label="directness_ratio > 1.0 warning",
            )
        ax.set_title(case_id)
        ax.set_ylabel("Dependence")
        ax.grid(alpha=0.3)
        ax.legend()

    axes[-1, 0].set_xlabel("Horizon")
    _save(fig, save_path)
