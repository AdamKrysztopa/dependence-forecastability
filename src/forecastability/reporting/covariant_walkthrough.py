"""Notebook-facing plotting and tabulation helpers for the covariant walkthrough.

The walkthrough notebook stays responsible for orchestrating analyses via
``run_covariant_analysis()`` and for presenting result-driven commentary. This
module only reshapes already-computed outputs and renders stable figures/tables.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from forecastability.diagnostics.transfer_entropy import compute_transfer_entropy_curve
from forecastability.utils.types import (
    CausalGraphResult,
    CovariantAnalysisBundle,
    CovariantInterpretationResult,
    PcmciAmiResult,
)

_METRIC_LABELS: dict[str, str] = {
    "cross_ami": "CrossAMI",
    "cross_pami": "CrosspAMI",
    "transfer_entropy": "Transfer entropy",
    "gcmi": "GCMI",
}


def _save_figure(fig: plt.Figure, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _metric_grid(
    bundle: CovariantAnalysisBundle,
    *,
    metric: str,
) -> pd.DataFrame:
    frame = summary_table_frame(bundle)
    pivot = frame.pivot(index="driver", columns="lag", values=metric)
    pivot = pivot.reindex(bundle.driver_names)
    return pivot.sort_index(axis="columns")


def summary_table_frame(bundle: CovariantAnalysisBundle) -> pd.DataFrame:
    """Convert a covariant bundle summary table to a notebook-friendly DataFrame."""
    return pd.DataFrame([row.model_dump(mode="json") for row in bundle.summary_table])


def driver_role_frame(interpretation: CovariantInterpretationResult) -> pd.DataFrame:
    """Convert driver-role assignments to a notebook-friendly DataFrame."""
    return pd.DataFrame(
        [
            {
                "driver": role.driver,
                "role": role.role,
                "best_lag": role.best_lag,
                "methods_supporting": ", ".join(role.methods_supporting) or "-",
                "warnings": " | ".join(role.warnings) or "-",
            }
            for role in interpretation.driver_roles
        ]
    )


def synthetic_benchmark_role_frame() -> pd.DataFrame:
    """Return the documented ground-truth roles for ``generate_covariant_benchmark``."""
    return pd.DataFrame(
        [
            {
                "driver": "driver_direct",
                "ground_truth_role": "Lagged linear direct parent",
                "canonical_lag": "2",
            },
            {
                "driver": "driver_mediated",
                "ground_truth_role": "Lagged parent with mediated structure",
                "canonical_lag": "1",
            },
            {
                "driver": "driver_redundant",
                "ground_truth_role": "Strong but redundant covariate",
                "canonical_lag": "not a parent",
            },
            {
                "driver": "driver_noise",
                "ground_truth_role": "AR(1) noise control",
                "canonical_lag": "not a parent",
            },
            {
                "driver": "driver_contemp",
                "ground_truth_role": "Contemporaneous parent",
                "canonical_lag": "0",
            },
            {
                "driver": "driver_nonlin_sq",
                "ground_truth_role": "Quadratic nonlinear parent",
                "canonical_lag": "1",
            },
            {
                "driver": "driver_nonlin_abs",
                "ground_truth_role": "Absolute-value nonlinear parent",
                "canonical_lag": "1",
            },
        ]
    )


def conditioning_scope_frame(bundle: CovariantAnalysisBundle) -> pd.DataFrame:
    """Return the per-method conditioning semantics carried by the bundle rows."""
    if not bundle.summary_table:
        return pd.DataFrame(columns=["method", "scope", "meaning"])

    conditioning = bundle.summary_table[0].lagged_exog_conditioning

    def _scope_value(value: str | None) -> str:
        return value if value is not None else "not_requested"

    meanings = {
        "none": "Unconditioned pairwise dependence",
        "target_only": "Conditions on target history only",
        "full_mci": "Full MCI conditioning on multivariate history",
        "not_requested": "Method not requested",
    }
    rows = [
        {
            "method": "cross_ami",
            "scope": _scope_value(conditioning.cross_ami),
            "meaning": meanings[_scope_value(conditioning.cross_ami)],
        },
        {
            "method": "cross_pami",
            "scope": _scope_value(conditioning.cross_pami),
            "meaning": meanings[_scope_value(conditioning.cross_pami)],
        },
        {
            "method": "transfer_entropy",
            "scope": _scope_value(conditioning.transfer_entropy),
            "meaning": meanings[_scope_value(conditioning.transfer_entropy)],
        },
        {
            "method": "gcmi",
            "scope": _scope_value(conditioning.gcmi),
            "meaning": meanings[_scope_value(conditioning.gcmi)],
        },
        {
            "method": "pcmci",
            "scope": _scope_value(conditioning.pcmci),
            "meaning": meanings[_scope_value(conditioning.pcmci)],
        },
        {
            "method": "pcmci_ami",
            "scope": _scope_value(conditioning.pcmci_ami),
            "meaning": meanings[_scope_value(conditioning.pcmci_ami)],
        },
    ]
    return pd.DataFrame(rows)


def save_metric_heatmap(
    bundle: CovariantAnalysisBundle,
    *,
    metric: str,
    output_path: Path,
    title: str | None = None,
) -> pd.DataFrame:
    """Render a driver-by-lag heatmap for one bundle metric and save it to disk."""
    if metric not in _METRIC_LABELS:
        raise ValueError(f"Unknown metric '{metric}'. Expected one of {sorted(_METRIC_LABELS)}")

    grid = _metric_grid(bundle, metric=metric).fillna(0.0)
    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    image = ax.imshow(grid.to_numpy(), aspect="auto", cmap="viridis")
    ax.set_title(title or f"{_METRIC_LABELS[metric]} by driver and lag")
    ax.set_xlabel("Lag")
    ax.set_ylabel("Driver")
    ax.set_xticks(np.arange(grid.shape[1]), labels=[str(int(col)) for col in grid.columns])
    ax.set_yticks(np.arange(grid.shape[0]), labels=list(grid.index))
    plt.setp(ax.get_yticklabels(), fontsize=8)

    for row_index, driver_name in enumerate(grid.index):
        for col_index, lag in enumerate(grid.columns):
            value = float(grid.loc[driver_name, lag])
            ax.text(
                col_index,
                row_index,
                f"{value:.2f}",
                ha="center",
                va="center",
                color="white" if value >= float(grid.to_numpy().max()) * 0.45 else "black",
                fontsize=7,
            )

    fig.colorbar(image, ax=ax, shrink=0.85, label=_METRIC_LABELS[metric])
    _save_figure(fig, output_path)
    return grid


def save_directionality_plot(
    *,
    source: np.ndarray,
    target: np.ndarray,
    output_path: Path,
    max_lag: int,
    random_state: int,
    min_pairs: int = 50,
    source_name: str = "source",
    target_name: str = "target",
) -> pd.DataFrame:
    """Plot forward and reverse transfer-entropy curves for one directional pair."""
    forward = compute_transfer_entropy_curve(
        source,
        target,
        max_lag=max_lag,
        min_pairs=min_pairs,
        random_state=random_state,
    )
    reverse = compute_transfer_entropy_curve(
        target,
        source,
        max_lag=max_lag,
        min_pairs=min_pairs,
        random_state=random_state,
    )

    lags = np.arange(1, max_lag + 1, dtype=int)
    frame = pd.DataFrame(
        {
            "lag": lags,
            f"te_{source_name}_to_{target_name}": forward,
            f"te_{target_name}_to_{source_name}": reverse,
        }
    )

    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    ax.plot(
        lags,
        forward,
        marker="o",
        linewidth=2.0,
        label=f"TE({source_name} -> {target_name})",
        color="tab:blue",
    )
    ax.plot(
        lags,
        reverse,
        marker="s",
        linewidth=1.8,
        label=f"TE({target_name} -> {source_name})",
        color="tab:orange",
    )
    ax.set_title("Directional transfer entropy by lag")
    ax.set_xlabel("Lag")
    ax.set_ylabel("Transfer entropy")
    ax.set_xticks(lags)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    _save_figure(fig, output_path)
    return frame


def causal_parent_frame(
    graph: CausalGraphResult,
    *,
    target_name: str,
) -> pd.DataFrame:
    """Return a tidy table of causal parents for one target."""
    parents = graph.parents.get(target_name, [])
    return pd.DataFrame(
        [{"source": source, "lag": lag} for source, lag in parents],
        columns=["source", "lag"],
    )


def save_causal_parent_heatmap(
    graph: CausalGraphResult,
    *,
    target_name: str,
    driver_names: list[str],
    output_path: Path,
    max_lag: int,
    title: str,
) -> pd.DataFrame:
    """Render a parent-selection heatmap for one target's incoming links."""
    parents = causal_parent_frame(graph, target_name=target_name)
    lags = list(range(0, max_lag + 1))
    grid = pd.DataFrame(0, index=driver_names, columns=lags, dtype=int)

    for source, lag in zip(parents["source"], parents["lag"], strict=True):
        if source in grid.index and int(lag) in grid.columns:
            grid.loc[source, int(lag)] = 1

    fig, ax = plt.subplots(figsize=(10.0, 4.5))
    image = ax.imshow(grid.to_numpy(), aspect="auto", cmap="Greens", vmin=0, vmax=1)
    ax.set_title(title)
    ax.set_xlabel("Lag")
    ax.set_ylabel("Driver")
    ax.set_xticks(np.arange(grid.shape[1]), labels=[str(lag) for lag in grid.columns])
    ax.set_yticks(np.arange(grid.shape[0]), labels=list(grid.index))
    plt.setp(ax.get_yticklabels(), fontsize=8)
    for row_index, driver_name in enumerate(grid.index):
        for col_index, lag in enumerate(grid.columns):
            ax.text(
                col_index,
                row_index,
                str(int(grid.loc[driver_name, lag])),
                ha="center",
                va="center",
                color="black",
                fontsize=8,
            )
    fig.colorbar(image, ax=ax, shrink=0.85, ticks=[0, 1], label="Selected parent")
    _save_figure(fig, output_path)
    return grid


def phase0_scores_frame(result: PcmciAmiResult) -> pd.DataFrame:
    """Return the Phase 0 MI scores sorted from strongest to weakest."""
    frame = pd.DataFrame(
        [
            {"source": row.source, "lag": row.lag, "target": row.target, "mi_value": row.mi_value}
            for row in result.phase0_mi_scores
        ]
    )
    return frame.sort_values("mi_value", ascending=False, ignore_index=True)


def save_phase0_overview(
    result: PcmciAmiResult,
    *,
    output_path: Path,
    top_n: int = 12,
) -> pd.DataFrame:
    """Render Phase 0 pruning diagnostics and save the resulting figure."""
    frame = phase0_scores_frame(result)
    top = frame.head(top_n).copy()
    top["label"] = top.apply(lambda row: f"{row['source']}@{int(row['lag'])}", axis=1)

    fig, axes = plt.subplots(1, 2, figsize=(14.0, 4.6))
    score_ax, count_ax = axes

    score_ax.barh(top["label"], top["mi_value"], color="tab:blue", alpha=0.85)
    score_ax.axvline(
        result.ami_threshold,
        color="tab:red",
        linestyle="--",
        linewidth=1.3,
        label=f"AMI threshold = {result.ami_threshold:.3f}",
    )
    score_ax.invert_yaxis()
    score_ax.set_title(f"PCMCI-AMI Phase 0: top {len(top)} MI scores")
    score_ax.set_xlabel("Phase 0 MI")
    score_ax.grid(alpha=0.3, axis="x")
    score_ax.legend(fontsize=8)

    count_ax.bar(
        ["kept", "pruned"],
        [result.phase0_kept_count, result.phase0_pruned_count],
        color=["tab:green", "tab:gray"],
        alpha=0.85,
    )
    count_ax.set_title("PCMCI-AMI Phase 0 pruning counts")
    count_ax.set_ylabel("Candidate links")
    count_ax.grid(alpha=0.3, axis="y")

    _save_figure(fig, output_path)
    return frame


def write_frame_csv(frame: pd.DataFrame, *, output_path: Path) -> None:
    """Persist a DataFrame to a stable CSV artifact path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
