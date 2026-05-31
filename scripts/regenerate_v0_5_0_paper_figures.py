"""Regenerate the two v0.5.0 Medium-article figures (RVH-F16.1).

Outputs (deterministic; idempotent):
    docs/medium/v0.5.0-hardening-figures/calibration_precision_v0_5_0.png
    docs/medium/v0.5.0-hardening-figures/archetype_suite_groundtruth.png

The script reads exact numerics from the committed audit JSON at
``docs/calibration/v0_5_0_routing_confidence_audit.json`` so the figures stay
in sync with the source artifact. No triage runs are executed.

Usage::

    uv run python scripts/regenerate_v0_5_0_paper_figures.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple

import matplotlib.pyplot as plt
import numpy as np

_REPO_ROOT = Path(__file__).resolve().parent.parent
_AUDIT_PATH = _REPO_ROOT / "docs" / "calibration" / "v0_5_0_routing_confidence_audit.json"
_FIGURES_DIR = _REPO_ROOT / "docs" / "medium" / "v0.5.0-hardening-figures"

# Ground-truth confidence labels for the 10 synthetic archetypes; mirrors
# ``docs/calibration/v0_5_0_routing_confidence.md`` and the script
# ``scripts/run_routing_confidence_calibration.py``.
_ARCHETYPES: tuple[tuple[str, str], ...] = (
    ("White noise", "LOW"),
    ("AR(1) phi=0.3", "MEDIUM"),
    ("AR(1) phi=0.8", "HIGH"),
    ("AR(2) phi=[0.6, 0.3]", "HIGH"),
    ("Sine + AR(1)", "HIGH"),
    ("Logistic map r=3.9", "HIGH"),
    ("Random walk", "HIGH"),
    ("Seasonal AR(1) period=12", "HIGH"),
    ("MA(1) theta=0.5", "MEDIUM"),
    ("Heavy-noise AR(1) phi=0.1", "LOW"),
)

_LABEL_COLOURS: dict[str, str] = {
    "HIGH": "#2E7D32",
    "MEDIUM": "#F9A825",
    "LOW": "#C62828",
}


class _ThresholdRow(NamedTuple):
    label: str
    threshold: float
    achieved_precision: float
    target_precision: float
    n_samples: int


def _load_threshold_rows(audit_path: Path) -> list[_ThresholdRow]:
    """Parse the committed calibration audit JSON into typed rows."""
    raw = json.loads(audit_path.read_text(encoding="utf-8"))
    return [
        _ThresholdRow(
            label=str(row["label"]).upper(),
            threshold=float(row["threshold"]),
            achieved_precision=float(row["achieved_precision"]),
            target_precision=float(row["target_precision"]),
            n_samples=int(row["n_samples"]),
        )
        for row in raw["thresholds"]
    ]


def _plot_calibration_precision(rows: list[_ThresholdRow], output_path: Path) -> None:
    """Render the HIGH/MEDIUM/LOW achieved-precision bar chart."""
    fig, ax = plt.subplots(figsize=(8.0, 5.0))

    labels = [row.label for row in rows]
    achieved = [row.achieved_precision for row in rows]
    targets = [row.target_precision for row in rows]
    samples = [row.n_samples for row in rows]
    colours = [_LABEL_COLOURS[label] for label in labels]

    x_positions = np.arange(len(labels))
    bar_width = 0.55
    bars = ax.bar(
        x_positions,
        achieved,
        width=bar_width,
        color=colours,
        edgecolor="black",
        linewidth=0.8,
        alpha=0.85,
        zorder=2,
    )

    # Target precision overlay; LOW has target=0.0 which we mark "no target".
    for x, target in zip(x_positions, targets, strict=True):
        if target > 0.0:
            ax.hlines(
                target,
                x - bar_width / 2,
                x + bar_width / 2,
                colors="black",
                linestyles="--",
                linewidth=1.6,
                zorder=3,
            )

    # Annotate achieved precision and sample count on each bar.
    for bar, achieved_value, n in zip(bars, achieved, samples, strict=True):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height + 0.015,
            f"{achieved_value:.3f}\n(n={n})",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Achieved precision (in-sample)")
    ax.set_ylim(0.0, 1.10)
    ax.set_yticks(np.linspace(0.0, 1.0, 11))
    ax.set_title(
        "v0.5.0 routing-confidence precision audit\n"
        "10 archetypes × 100 noise replicates (N=400)",
        fontsize=12,
    )
    ax.grid(axis="y", linestyle=":", alpha=0.6, zorder=1)
    ax.set_axisbelow(True)

    # Legend: explain dashed target line.
    target_proxy = plt.Line2D(
        [0],
        [0],
        color="black",
        linestyle="--",
        linewidth=1.6,
        label="Target precision",
    )
    ax.legend(handles=[target_proxy], loc="lower right", frameon=False)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _plot_archetype_suite(output_path: Path) -> None:
    """Render the 10-archetype list as a horizontal categorical chart."""
    fig, ax = plt.subplots(figsize=(8.5, 5.5))

    # Plot top-to-bottom in declared order.
    archetypes_top_down = list(_ARCHETYPES)
    names = [a[0] for a in archetypes_top_down]
    labels = [a[1] for a in archetypes_top_down]

    y_positions = np.arange(len(names))[::-1]
    colours = [_LABEL_COLOURS[label] for label in labels]

    ax.barh(
        y_positions,
        np.ones(len(names)),
        color=colours,
        edgecolor="black",
        linewidth=0.7,
        alpha=0.85,
    )

    for y, name, label in zip(y_positions, names, labels, strict=True):
        ax.text(
            0.02,
            y,
            name,
            ha="left",
            va="center",
            fontsize=11,
            color="white" if label != "MEDIUM" else "black",
            fontweight="bold",
        )
        ax.text(
            0.98,
            y,
            label,
            ha="right",
            va="center",
            fontsize=10,
            color="white" if label != "MEDIUM" else "black",
            fontstyle="italic",
        )

    ax.set_xlim(0.0, 1.0)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ("top", "right", "left", "bottom"):
        ax.spines[spine].set_visible(False)
    ax.set_title(
        "Synthetic archetype suite — ground-truth confidence labels\n"
        "Used by the v0.5.0 routing-confidence precision audit",
        fontsize=12,
    )

    # Legend.
    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=_LABEL_COLOURS[label], edgecolor="black")
        for label in ("HIGH", "MEDIUM", "LOW")
    ]
    ax.legend(
        legend_handles,
        ("HIGH (strong forecastable structure)", "MEDIUM (weak structure)", "LOW (near-noise)"),
        loc="lower center",
        bbox_to_anchor=(0.5, -0.08),
        ncol=3,
        frameon=False,
        fontsize=9,
    )

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    """Regenerate both Medium-article figures from committed sources."""
    _FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    rows = _load_threshold_rows(_AUDIT_PATH)
    _plot_calibration_precision(
        rows,
        _FIGURES_DIR / "calibration_precision_v0_5_0.png",
    )
    _plot_archetype_suite(
        _FIGURES_DIR / "archetype_suite_groundtruth.png",
    )

    print(f"Wrote: {_FIGURES_DIR / 'calibration_precision_v0_5_0.png'}")
    print(f"Wrote: {_FIGURES_DIR / 'archetype_suite_groundtruth.png'}")


if __name__ == "__main__":
    main()
