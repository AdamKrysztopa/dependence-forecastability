"""Exogenous driver redundancy screening example (F8).

Demonstrates the two F8 extensions to the exogenous screening workbench:

1. **Profile-shape redundancy penalty** (redundancy_alpha>0) — penalises
   drivers whose horizon-usefulness profile closely mirrors an already-selected
   driver.  Promotes a diverse, non-redundant driver set.

2. **Benjamini–Hochberg FDR correction** (apply_bh_correction=True) — applies
   a one-sided binomial test per driver (H0: ≤5 % of horizons are informative),
   then applies BH at a 10 % FDR level.  Drivers that fail BH are marked as
   statistically uninformative across the horizon range.

Scenario
--------
A macroeconomic target series is screened against six candidate exogenous drivers:

* ``industrial_production`` — strong at near-term horizons
* ``credit_spread``         — strong, but profile mirrors industrial_production
* ``consumer_confidence``  — strong at mid-term horizons
* ``oil_price``             — moderate at all horizons
* ``exchange_rate``         — near-zero usefulness (noise)
* ``noise_series``          — pure noise (BH should reject this)

After redundancy-penalised selection: credit_spread (redundant to
industrial_production) should receive a high redundancy_score, confirming that
it adds little *unique* information once industrial_production is selected.

Outputs
-------
* ``outputs/figures/exog_screening/f8_usefulness_heatmap.png``
  — driver × horizon usefulness heatmap, annotated with redundancy_score and
    bh_significant flags.
* ``outputs/figures/exog_screening/f8_driver_ranking_bar.png``
  — horizontal bar chart of mean_usefulness_score per driver, coloured by
    recommendation (keep/review/reject), with BH and redundancy annotations.

Usage
-----
    uv run python scripts/archive/run_exogenous_driver_redundancy_screening.py
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import numpy as np

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib.colors as mcolors  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from forecastability.use_cases.run_exogenous_screening_workbench import (  # noqa: E402
    run_exogenous_screening_workbench,
)
from forecastability.utils.config import ExogenousScreeningWorkbenchConfig  # noqa: E402
from forecastability.utils.types import ExogenousBenchmarkResult  # noqa: E402

_logger = logging.getLogger(__name__)
_OUTPUT_DIR = Path("outputs/figures/exog_screening")
_HORIZONS = list(range(1, 13))  # h=1..12

# ---------------------------------------------------------------------------
# Hardcoded driver profiles
# ---------------------------------------------------------------------------

# Profiles: (raw_cross_mi, conditioned_cross_mi, directness_ratio) per horizon
# directness_ratio > 1.0 → warning horizon
_DRIVER_PROFILES: dict[str, dict[int, tuple[float, float, float]]] = {
    "industrial_production": {
        1: (0.28, 0.22, 0.79),
        2: (0.26, 0.20, 0.77),
        3: (0.24, 0.18, 0.75),
        4: (0.20, 0.15, 0.75),
        5: (0.16, 0.11, 0.69),
        6: (0.13, 0.09, 0.69),
        7: (0.10, 0.07, 0.70),
        8: (0.09, 0.06, 0.67),
        9: (0.07, 0.05, 0.71),
        10: (0.06, 0.04, 0.67),
        11: (0.05, 0.03, 0.60),
        12: (0.04, 0.02, 0.50),
    },
    "credit_spread": {  # mirrors industrial_production closely → high redundancy
        1: (0.27, 0.21, 0.78),
        2: (0.25, 0.19, 0.76),
        3: (0.23, 0.17, 0.74),
        4: (0.19, 0.14, 0.74),
        5: (0.15, 0.10, 0.67),
        6: (0.12, 0.08, 0.67),
        7: (0.09, 0.06, 0.67),
        8: (0.08, 0.05, 0.63),
        9: (0.06, 0.04, 0.67),
        10: (0.05, 0.03, 0.60),
        11: (0.04, 0.02, 0.50),
        12: (0.03, 0.01, 0.33),
    },
    "consumer_confidence": {  # strong at mid-term, weak at near-term → complementary
        1: (0.09, 0.07, 0.78),
        2: (0.12, 0.09, 0.75),
        3: (0.16, 0.13, 0.81),
        4: (0.21, 0.17, 0.81),
        5: (0.25, 0.20, 0.80),
        6: (0.27, 0.21, 0.78),
        7: (0.24, 0.19, 0.79),
        8: (0.20, 0.15, 0.75),
        9: (0.15, 0.11, 0.73),
        10: (0.11, 0.08, 0.73),
        11: (0.08, 0.05, 0.63),
        12: (0.05, 0.03, 0.60),
    },
    "oil_price": {  # moderate across all horizons
        1: (0.12, 0.09, 0.75),
        2: (0.12, 0.09, 0.75),
        3: (0.11, 0.08, 0.73),
        4: (0.11, 0.08, 0.73),
        5: (0.10, 0.07, 0.70),
        6: (0.10, 0.07, 0.70),
        7: (0.09, 0.06, 0.67),
        8: (0.09, 0.06, 0.67),
        9: (0.08, 0.05, 0.63),
        10: (0.08, 0.05, 0.63),
        11: (0.07, 0.04, 0.57),
        12: (0.07, 0.04, 0.57),
    },
    "exchange_rate": {  # near-zero, some warning horizons
        1: (0.03, 0.02, 0.67),
        2: (0.03, 0.02, 0.67),
        3: (0.02, 0.01, 0.50),
        4: (0.02, 0.03, 1.50),
        5: (0.01, 0.02, 2.00),
        6: (0.01, 0.01, 1.00),
        7: (0.02, 0.01, 0.50),
        8: (0.01, 0.01, 1.00),
        9: (0.01, 0.01, 1.00),
        10: (0.02, 0.01, 0.50),
        11: (0.01, 0.01, 1.00),
        12: (0.01, 0.01, 1.00),
    },
    "noise_series": {  # pure noise — BH should reject
        1: (0.01, 0.01, 1.00),
        2: (0.01, 0.02, 2.00),
        3: (0.01, 0.01, 1.00),
        4: (0.01, 0.01, 1.00),
        5: (0.01, 0.02, 2.00),
        6: (0.01, 0.01, 1.00),
        7: (0.01, 0.01, 1.00),
        8: (0.01, 0.02, 2.00),
        9: (0.01, 0.01, 1.00),
        10: (0.01, 0.01, 1.00),
        11: (0.01, 0.02, 2.00),
        12: (0.01, 0.01, 1.00),
    },
}

_N = 200
_TARGET = np.zeros(_N, dtype=np.float64)
_DRIVERS = {name: np.zeros(_N, dtype=np.float64) for name in _DRIVER_PROFILES}

# ---------------------------------------------------------------------------
# Stub pair evaluator
# ---------------------------------------------------------------------------


def _build_stub_evaluator(
    profiles: dict[str, dict[int, tuple[float, float, float]]],
) -> object:
    """Build a deterministic stub pair evaluator from profile data.

    Args:
        profiles: Mapping of driver name to per-horizon
            ``(raw_cross_mi, conditioned_cross_mi, directness_ratio)`` tuples.

    Returns:
        A callable with the same signature as
        ``run_exogenous_rolling_origin_evaluation``.
    """

    def _evaluator(
        target: np.ndarray,
        exog: np.ndarray,
        *,
        case_id: str,
        target_name: str,
        exog_name: str,
        horizons: list[int],
        n_origins: int,
        random_state: int,
        n_surrogates: int,
        min_pairs_raw: int,
        min_pairs_partial: int,
        analysis_scope: str,
        project_extension: bool,
    ) -> ExogenousBenchmarkResult:
        del target, exog, n_origins, random_state, n_surrogates
        del min_pairs_raw, min_pairs_partial, analysis_scope, project_extension
        spec = profiles[exog_name]
        warning_horizons = [h for h in horizons if spec[h][2] > 1.0]
        return ExogenousBenchmarkResult(
            case_id=case_id,
            target_name=target_name,
            exog_name=exog_name,
            horizons=horizons,
            raw_cross_mi_by_horizon={h: spec[h][0] for h in horizons},
            conditioned_cross_mi_by_horizon={h: spec[h][1] for h in horizons},
            directness_ratio_by_horizon={h: spec[h][2] for h in horizons},
            origins_used_by_horizon={h: 6 for h in horizons},
            warning_horizons=warning_horizons,
            metadata={"stub": 1},
        )

    return _evaluator


# ---------------------------------------------------------------------------
# Config builders
# ---------------------------------------------------------------------------


def _build_config_baseline() -> ExogenousScreeningWorkbenchConfig:
    """Build baseline config with redundancy and BH disabled."""
    return ExogenousScreeningWorkbenchConfig.model_validate(
        {
            "horizons": _HORIZONS,
            "n_origins": 6,
            "random_state": 42,
            "n_surrogates": 99,
            "min_pairs_raw": 10,
            "min_pairs_partial": 10,
            "redundancy_alpha": 0.0,
            "apply_bh_correction": False,
            "recommendation": {
                "keep_min_mean_usefulness": 0.08,
                "keep_min_peak_usefulness": 0.12,
                "review_min_mean_usefulness": 0.04,
                "review_min_peak_usefulness": 0.06,
            },
        }
    )


def _build_config_f8() -> ExogenousScreeningWorkbenchConfig:
    """Build F8 config with redundancy penalty and BH correction enabled."""
    return ExogenousScreeningWorkbenchConfig.model_validate(
        {
            "horizons": _HORIZONS,
            "n_origins": 6,
            "random_state": 42,
            "n_surrogates": 99,
            "min_pairs_raw": 10,
            "min_pairs_partial": 10,
            "redundancy_alpha": 0.5,
            "apply_bh_correction": True,
            "bh_fdr_alpha": 0.10,
            "recommendation": {
                "keep_min_mean_usefulness": 0.08,
                "keep_min_peak_usefulness": 0.12,
                "review_min_mean_usefulness": 0.04,
                "review_min_peak_usefulness": 0.06,
            },
        }
    )


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------

_REC_COLOURS: dict[str, str] = {
    "keep": "#2ca02c",
    "review": "#ff7f0e",
    "reject": "#d62728",
}


def _plot_usefulness_heatmap(
    result_baseline: object,
    result_f8: object,
    output_path: Path,
) -> None:
    """Save side-by-side usefulness heatmaps (baseline vs F8).

    Args:
        result_baseline: Baseline workbench result.
        result_f8: F8 workbench result.
        output_path: Destination PNG path.
    """
    from forecastability.utils.types import ExogenousScreeningWorkbenchResult

    baseline: ExogenousScreeningWorkbenchResult = result_baseline  # type: ignore[assignment]
    f8: ExogenousScreeningWorkbenchResult = result_f8  # type: ignore[assignment]

    driver_order = [
        s.driver_name for s in sorted(baseline.driver_summaries, key=lambda s: s.overall_rank)
    ]
    horizons = baseline.horizons

    def _usefulness_matrix(result: ExogenousScreeningWorkbenchResult) -> np.ndarray:
        rows_map: dict[str, dict[int, float]] = {}
        for row in result.horizon_usefulness_rows:
            rows_map.setdefault(row.driver_name, {})[row.horizon] = row.usefulness_score
        return np.array(
            [[rows_map[d].get(h, 0.0) for h in horizons] for d in driver_order],
            dtype=np.float64,
        )

    mat_base = _usefulness_matrix(baseline)
    mat_f8 = _usefulness_matrix(f8)

    f8_summary_map = {s.driver_name: s for s in f8.driver_summaries}

    fig, axes = plt.subplots(1, 2, figsize=(16, 5), sharey=True)
    cmap = plt.get_cmap("YlOrRd")
    norm = mcolors.Normalize(vmin=0.0, vmax=0.2)

    for ax, mat, title in (
        (axes[0], mat_base, "Baseline"),
        (axes[1], mat_f8, "F8: Redundancy-Penalised + BH"),
    ):
        im = ax.imshow(mat, aspect="auto", cmap=cmap, norm=norm)
        ax.set_xticks(range(len(horizons)))
        ax.set_xticklabels([str(h) for h in horizons])
        ax.set_xlabel("Horizon h")
        ax.set_title(title, fontsize=11)

    # Y-tick labels — plain for baseline, annotated for F8
    axes[0].set_yticks(range(len(driver_order)))
    axes[0].set_yticklabels(driver_order, fontsize=9)

    f8_ylabels: list[str] = []
    for name in driver_order:
        summary = f8_summary_map.get(name)
        label = name
        if summary is not None:
            r = summary.redundancy_score
            bh = summary.bh_significant
            suffix_parts: list[str] = []
            if r is not None and r > 0.0:
                suffix_parts.append(f"R={r:.2f}")
            if bh:
                suffix_parts.append("★")
            if suffix_parts:
                label = f"{name} [{', '.join(suffix_parts)}]"
        f8_ylabels.append(label)

    axes[1].set_yticks(range(len(driver_order)))
    axes[1].set_yticklabels(f8_ylabels, fontsize=9)

    fig.colorbar(im, ax=axes, orientation="vertical", label="Usefulness score", shrink=0.8)
    fig.suptitle(
        "F8: Usefulness Heatmap — Baseline (left) vs Redundancy-Penalised + BH (right)",
        fontsize=12,
    )
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    _logger.info("Saved heatmap to %s", output_path)


def _plot_driver_ranking_bar(
    result_f8: object,
    output_path: Path,
) -> None:
    """Save horizontal bar chart of F8 driver ranking.

    Args:
        result_f8: F8 workbench result.
        output_path: Destination PNG path.
    """
    from forecastability.utils.types import ExogenousScreeningWorkbenchResult

    f8: ExogenousScreeningWorkbenchResult = result_f8  # type: ignore[assignment]

    summaries = sorted(f8.driver_summaries, key=lambda s: s.mean_usefulness_score)
    names = [s.driver_name for s in summaries]
    scores = [s.mean_usefulness_score for s in summaries]
    colours = [_REC_COLOURS.get(s.recommendation, "#7f7f7f") for s in summaries]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(names, scores, color=colours)

    for bar, summary in zip(bars, summaries, strict=True):
        x_right = bar.get_width()
        annotations: list[str] = []
        if summary.bh_significant:
            annotations.append("★ BH-significant")
        r = summary.redundancy_score
        if r is not None and r > 0.1:
            annotations.append(f"[R={r:.2f}]")
        if annotations:
            ax.text(
                x_right + 0.002,
                bar.get_y() + bar.get_height() / 2,
                "  ".join(annotations),
                va="center",
                ha="left",
                fontsize=8,
                color="#333333",
            )

    legend_patches = [Patch(color=colour, label=label) for label, colour in _REC_COLOURS.items()]
    ax.legend(handles=legend_patches, loc="lower right", fontsize=9)
    ax.set_xlabel("Mean usefulness score")
    ax.set_title("F8: Driver Ranking — Redundancy-Penalised + BH Correction", fontsize=11)
    ax.set_xlim(0, max(scores) * 1.35 if scores else 0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    _logger.info("Saved ranking bar chart to %s", output_path)


# ---------------------------------------------------------------------------
# Comparison table printer
# ---------------------------------------------------------------------------


def _print_comparison_table(
    result_baseline: object,
    result_f8: object,
) -> None:
    """Print side-by-side baseline vs F8 driver summary to stdout.

    Args:
        result_baseline: Baseline workbench result.
        result_f8: F8 workbench result.
    """
    from forecastability.utils.types import ExogenousScreeningWorkbenchResult

    baseline: ExogenousScreeningWorkbenchResult = result_baseline  # type: ignore[assignment]
    f8: ExogenousScreeningWorkbenchResult = result_f8  # type: ignore[assignment]

    base_map = {s.driver_name: s for s in baseline.driver_summaries}
    f8_map = {s.driver_name: s for s in f8.driver_summaries}
    all_drivers = sorted(base_map)

    header = (
        f"{'Driver':<26} {'Base rec':<10} {'Base mean':>10}  "
        f"{'F8 rec':<10} {'F8 mean':>9}  {'BH':>4}  {'R-score':>7}"
    )
    separator = "-" * len(header)
    print("\nF8 vs Baseline driver comparison")
    print(separator)
    print(header)
    print(separator)
    for name in all_drivers:
        b = base_map.get(name)
        f = f8_map.get(name)
        b_rec = b.recommendation if b else "—"
        b_mean = f"{b.mean_usefulness_score:.4f}" if b else "—"
        f_rec = f.recommendation if f else "—"
        f_mean = f"{f.mean_usefulness_score:.4f}" if f else "—"
        bh = "yes" if (f and f.bh_significant) else "no"
        r = f"{f.redundancy_score:.3f}" if (f and f.redundancy_score is not None) else "—"
        print(f"{name:<26} {b_rec:<10} {b_mean:>10}  {f_rec:<10} {f_mean:>9}  {bh:>4}  {r:>7}")
    print(separator)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run F8 exogenous driver redundancy screening demo and save figures."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    stub = _build_stub_evaluator(_DRIVER_PROFILES)
    config_baseline = _build_config_baseline()
    config_f8 = _build_config_f8()

    _logger.info("Running baseline screening (no redundancy, no BH)…")
    result_baseline = run_exogenous_screening_workbench(
        _TARGET,
        _DRIVERS,
        target_name="macro_target",
        config=config_baseline,
        pair_evaluator=stub,  # type: ignore[arg-type]
    )

    _logger.info("Running F8 screening (redundancy_alpha=0.5, BH at 10%%)…")
    result_f8 = run_exogenous_screening_workbench(
        _TARGET,
        _DRIVERS,
        target_name="macro_target",
        config=config_f8,
        pair_evaluator=stub,  # type: ignore[arg-type]
    )

    _print_comparison_table(result_baseline, result_f8)

    heatmap_path = _OUTPUT_DIR / "f8_usefulness_heatmap.png"
    _plot_usefulness_heatmap(result_baseline, result_f8, heatmap_path)

    ranking_path = _OUTPUT_DIR / "f8_driver_ranking_bar.png"
    _plot_driver_ranking_bar(result_f8, ranking_path)

    _logger.info("Done. Outputs:")
    _logger.info("  %s", heatmap_path)
    _logger.info("  %s", ranking_path)


if __name__ == "__main__":
    main()
