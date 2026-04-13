"""Agent payload models demo: triage result → agent-ready payload.

Demonstrates how the A1 agent payload adapter layer converts deterministic
triage results into JSON-serialisable payloads for agentic consumers.

This example covers:
* Single-series triage → TriageAgentPayload conversion
* Batch triage → per-series F7BatchRankPayload list
* Exogenous screening → per-driver F8ExogDriverPayload list
* JSON serialisation and pretty-print inspection
* Matplotlib comparison figure: raw diagnostics vs payload fields

Usage:
    uv run python examples/triage/agent_payload_models_demo.py
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path

import numpy as np

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from forecastability.adapters.agents.triage_agent_payload_models import (
    F7BatchRankPayload,
    F8ExogDriverPayload,
    f7_batch_rank_payload,
    f8_exog_driver_payload,
    triage_agent_payload,
)
from forecastability.config import ExogenousScreeningWorkbenchConfig
from forecastability.triage.batch_models import BatchSeriesRequest, BatchTriageRequest
from forecastability.triage.models import TriageRequest
from forecastability.types import ExogenousBenchmarkResult
from forecastability.use_cases.run_batch_triage import run_batch_triage
from forecastability.use_cases.run_exogenous_screening_workbench import (
    run_exogenous_screening_workbench,
)
from forecastability.use_cases.run_triage import run_triage

_HORIZONS = [1, 2, 3, 4, 5]


# ---------------------------------------------------------------------------
# Helper series generators
# ---------------------------------------------------------------------------


def _make_ar_series(phi: float, n: int, seed: int) -> np.ndarray:
    """Generate an AR(1) series.

    Args:
        phi: Autoregressive coefficient.
        n: Number of observations.
        seed: Random seed for reproducibility.

    Returns:
        1-D numpy array of length n.
    """
    rng = np.random.default_rng(seed)
    series = np.zeros(n, dtype=float)
    series[0] = rng.standard_normal()
    for i in range(1, n):
        series[i] = phi * series[i - 1] + rng.standard_normal()
    return series


def _make_seasonal_series(period: int, n: int, seed: int) -> np.ndarray:
    """Generate a seasonal series with additive noise.

    Args:
        period: Dominant seasonal period.
        n: Number of observations.
        seed: Random seed for reproducibility.

    Returns:
        1-D numpy array of length n.
    """
    rng = np.random.default_rng(seed)
    t = np.arange(n, dtype=float)
    return (
        np.sin(2.0 * np.pi * t / period)
        + 0.5 * np.sin(2.0 * np.pi * t / (period / 2))
        + 0.2 * rng.standard_normal(n)
    )


def _make_white_noise(n: int, seed: int) -> np.ndarray:
    """Generate Gaussian white noise.

    Args:
        n: Number of observations.
        seed: Random seed for reproducibility.

    Returns:
        1-D numpy array of length n.
    """
    return np.random.default_rng(seed).standard_normal(n)


# ---------------------------------------------------------------------------
# Exogenous screening stub
# ---------------------------------------------------------------------------


def _build_driver_profiles() -> dict[str, dict[int, tuple[float, float, float]]]:
    """Build deterministic per-horizon exogenous dependence profiles for 4 drivers.

    Returns:
        Nested dict: driver_name → horizon → (raw_mi, conditioned_mi, directness_ratio).
    """
    return {
        "strong_driver": {
            1: (0.27, 0.21, 0.78),
            2: (0.25, 0.19, 0.76),
            3: (0.23, 0.18, 0.78),
            4: (0.20, 0.15, 0.75),
            5: (0.18, 0.13, 0.72),
        },
        "weak_driver": {
            1: (0.04, 0.02, 0.50),
            2: (0.03, 0.02, 0.67),
            3: (0.03, 0.01, 1.40),
            4: (0.02, 0.01, 1.50),
            5: (0.02, 0.01, 1.50),
        },
        "redundant_driver": {
            1: (0.17, 0.11, 0.65),
            2: (0.16, 0.10, 0.63),
            3: (0.15, 0.09, 0.60),
            4: (0.14, 0.09, 0.64),
            5: (0.13, 0.08, 0.62),
        },
        "noise_driver": {
            1: (0.01, 0.005, 2.10),
            2: (0.01, 0.005, 1.95),
            3: (0.008, 0.004, 2.20),
            4: (0.007, 0.004, 1.80),
            5: (0.006, 0.003, 2.00),
        },
    }


def _build_stub_pair_evaluator(
    *,
    profiles: dict[str, dict[int, tuple[float, float, float]]],
) -> Callable[..., ExogenousBenchmarkResult]:
    """Build a deterministic evaluator injected into the screening workbench.

    Args:
        profiles: Nested dict of pre-set dependence profiles per driver per horizon.

    Returns:
        Callable matching the pair_evaluator interface expected by the workbench.
    """

    def _pair_evaluator(
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

        profile = profiles[exog_name]
        warning_horizons = [h for h in horizons if profile[h][2] > 1.0]
        return ExogenousBenchmarkResult(
            case_id=case_id,
            target_name=target_name,
            exog_name=exog_name,
            horizons=horizons,
            raw_cross_mi_by_horizon={h: profile[h][0] for h in horizons},
            conditioned_cross_mi_by_horizon={h: profile[h][1] for h in horizons},
            directness_ratio_by_horizon={h: profile[h][2] for h in horizons},
            origins_used_by_horizon={h: 4 for h in horizons},
            warning_horizons=warning_horizons,
            metadata={"stubbed": 1},
        )

    return _pair_evaluator


# ---------------------------------------------------------------------------
# Main sections
# ---------------------------------------------------------------------------


def _section1_single_triage() -> tuple[object, object]:
    """Run single-series triage and convert to TriageAgentPayload.

    Returns:
        Tuple of (TriageResult, TriageAgentPayload).
    """
    print("\n" + "=" * 60)
    print("Section 1: Single-series triage → TriageAgentPayload")
    print("=" * 60)

    series = _make_seasonal_series(period=12, n=600, seed=42)
    request = TriageRequest(series=series, max_lag=20, n_surrogates=99, random_state=42)
    result = run_triage(request)
    payload = triage_agent_payload(result, series_id="seasonal_ar1")

    print(f"blocked:              {payload.blocked}")
    print(f"readiness_status:     {payload.readiness_status}")
    print(f"forecastability_class:{payload.forecastability_class}")
    print(f"directness_class:     {payload.directness_class}")

    if payload.f1_profile is not None:
        p1 = payload.f1_profile
        print(f"\nF1 informative_horizons: {p1.informative_horizons}")
        print(f"F1 profile_shape_label:  {p1.profile_shape_label}")
        print(f"F1 model_now:            {p1.model_now}")

    if payload.f2_limits is not None:
        p2 = payload.f2_limits
        print(f"\nF2 ceiling (first 5):    {p2.theoretical_ceiling_by_horizon[:5]}")
        print(f"F2 ceiling_summary:      {p2.ceiling_summary}")

    if payload.f6_complexity is not None:
        p6 = payload.f6_complexity
        print(f"\nF6 complexity_band:      {p6.complexity_band}")
        print(f"F6 permutation_entropy:  {p6.permutation_entropy:.4f}")
        print(f"F6 spectral_entropy:     {p6.spectral_entropy:.4f}")

    print(f"\nwarnings: {payload.warnings}")

    json_payload = json.loads(payload.model_dump_json())
    json_path = Path("outputs/json/agent_payload_seasonal_ar1.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")
    print(f"\nJSON saved to {json_path}")

    return result, payload


def _section2_batch_triage() -> list[F7BatchRankPayload]:
    """Run batch triage and convert each result to F7BatchRankPayload.

    Returns:
        List of F7BatchRankPayload, one per series.
    """
    print("\n" + "=" * 60)
    print("Section 2: Batch triage → F7BatchRankPayload list")
    print("=" * 60)

    batch_request = BatchTriageRequest(
        items=[
            BatchSeriesRequest(
                series_id="strong_ar1",
                series=_make_ar_series(0.8, 500, 10).tolist(),
            ),
            BatchSeriesRequest(
                series_id="weak_ar1",
                series=_make_ar_series(0.3, 500, 20).tolist(),
            ),
            BatchSeriesRequest(
                series_id="white_noise",
                series=_make_white_noise(500, 30).tolist(),
            ),
            BatchSeriesRequest(
                series_id="seasonal",
                series=_make_seasonal_series(12, 500, 40).tolist(),
            ),
            BatchSeriesRequest(
                series_id="persistent_ar1",
                series=_make_ar_series(0.95, 500, 50).tolist(),
            ),
        ],
        max_lag=20,
        n_surrogates=99,
        random_state=42,
    )

    response = run_batch_triage(batch_request)
    f7_payloads = [f7_batch_rank_payload(item) for item in response.items]

    print(f"{'Rank':<6} {'Series ID':<16} {'Outcome':<10} {'F-Class':<12} {'Complexity':<12}")
    print("-" * 60)
    for p in f7_payloads:
        rank_str = str(p.batch_rank) if p.batch_rank is not None else "-"
        print(
            f"{rank_str:<6} {p.series_id:<16} {p.outcome:<10}"
            f" {str(p.forecastability_class or '-'):<12} {str(p.complexity_band or '-'):<12}"
        )

    json_path = Path("outputs/json/agent_payload_batch.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps([p.model_dump() for p in f7_payloads], indent=2),
        encoding="utf-8",
    )
    print(f"\nJSON saved to {json_path}")

    return f7_payloads


def _section3_exog_screening() -> list[F8ExogDriverPayload]:
    """Run exogenous screening and convert each driver to F8ExogDriverPayload.

    Returns:
        List of F8ExogDriverPayload, one per driver.
    """
    print("\n" + "=" * 60)
    print("Section 3: Exogenous screening → F8ExogDriverPayload list")
    print("=" * 60)

    profiles = _build_driver_profiles()
    pair_evaluator = _build_stub_pair_evaluator(profiles=profiles)

    config = ExogenousScreeningWorkbenchConfig.model_validate(
        {
            "horizons": _HORIZONS,
            "n_origins": 4,
            "random_state": 42,
            "n_surrogates": 99,
            "min_pairs_raw": 6,
            "min_pairs_partial": 6,
            "redundancy_alpha": 0.5,
            "apply_bh_correction": False,
        }
    )

    n = 200
    target = np.linspace(0.0, 1.0, n, dtype=float)
    drivers = {
        name: np.linspace(i, i + 1.0, n, dtype=float)
        for i, name in enumerate(sorted(profiles), start=1)
    }

    result = run_exogenous_screening_workbench(
        target,
        drivers,
        target_name="demo_target",
        config=config,
        pair_evaluator=pair_evaluator,
    )

    f8_payloads = [f8_exog_driver_payload(s) for s in result.driver_summaries]

    print(f"{'Driver':<20} {'Recommendation':<14} {'Mean Usefulness':>16} {'Redundant':>10}")
    print("-" * 64)
    for p in sorted(f8_payloads, key=lambda x: x.driver_rank):
        print(
            f"{p.driver_name:<20} {p.recommendation:<14}"
            f" {p.mean_usefulness_score:>16.4f} {str(p.redundancy_flag):>10}"
        )

    json_path = Path("outputs/json/agent_payload_exog_screening.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps([p.model_dump() for p in f8_payloads], indent=2),
        encoding="utf-8",
    )
    print(f"\nJSON saved to {json_path}")

    return f8_payloads


def _section4_figures(
    *,
    triage_result: object,
    single_payload: object,
    f7_payloads: list[F7BatchRankPayload],
    f8_payloads: list[F8ExogDriverPayload],
) -> None:
    """Build and save a 2×2 diagnostic summary figure.

    Args:
        triage_result: Domain TriageResult from single-series triage.
        single_payload: TriageAgentPayload for the single series.
        f7_payloads: Per-series F7BatchRankPayload list from batch triage.
        f8_payloads: Per-driver F8ExogDriverPayload list from exog screening.
    """
    print("\n" + "=" * 60)
    print("Section 4: Figures")
    print("=" * 60)

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    # --- [0,0] F1 AMI profile ---
    ax00 = axes[0, 0]
    profile = getattr(triage_result, "forecastability_profile", None)
    p1 = getattr(single_payload, "f1_profile", None)
    if profile is not None and p1 is not None:
        inf_set = set(p1.informative_horizons)
        colors_f1 = ["#2ecc71" if h in inf_set else "#e74c3c" for h in profile.horizons]
        ax00.plot(profile.horizons, profile.values.tolist(), color="steelblue", lw=2)
        for h, c in zip(profile.horizons, colors_f1, strict=True):
            ax00.axvline(h, color=c, alpha=0.3, lw=8)
        ax00.axhline(
            profile.epsilon,
            color="black",
            linestyle="--",
            lw=1.5,
            label=f"ε={profile.epsilon:.3f}",
        )
        ax00.set_title("F1: Forecastability Profile", fontsize=10)
        ax00.set_xlabel("Horizon")
        ax00.set_ylabel("AMI F(h; I_t)")
        ax00.legend(fontsize=9)
    else:
        ax00.text(0.5, 0.5, "No profile data", ha="center", va="center", transform=ax00.transAxes)
        ax00.set_title("F1: Forecastability Profile", fontsize=10)

    # --- [0,1] F6×F4 entropy scatter ---
    ax01 = axes[0, 1]
    fc_color_map: dict[str | None, str] = {
        "high": "green",
        "medium": "orange",
        "low": "red",
        None: "gray",
    }
    for p in f7_payloads:
        pe = p.diagnostic_vector.get("permutation_entropy")
        sp = p.spectral_predictability
        if pe is not None and sp is not None:
            color = fc_color_map.get(p.forecastability_class, "gray")
            ax01.scatter(sp, pe, color=color, s=80, zorder=3)
            ax01.annotate(
                p.series_id,
                (sp, pe),
                textcoords="offset points",
                xytext=(5, 3),
                fontsize=8,
            )
    legend_elements_f6 = [
        Patch(facecolor="green", label="high"),
        Patch(facecolor="orange", label="medium"),
        Patch(facecolor="red", label="low"),
        Patch(facecolor="gray", label="unknown"),
    ]
    ax01.legend(handles=legend_elements_f6, title="F-class", fontsize=8)
    ax01.set_title("F6×F4: Entropy vs Spectral Predictability", fontsize=10)
    ax01.set_xlabel("Spectral Predictability")
    ax01.set_ylabel("Permutation Entropy")

    # --- [1,0] F7 batch ranking bars ---
    ax10 = axes[1, 0]
    outcome_color_map = {"ok": "steelblue", "blocked": "orange", "failed": "gray"}
    sorted_f7 = sorted(
        f7_payloads, key=lambda x: x.batch_rank if x.batch_rank is not None else 9999
    )
    bar_labels = [p.series_id for p in sorted_f7]
    bar_values = [p.batch_rank if p.batch_rank is not None else 0 for p in sorted_f7]
    bar_colors = [outcome_color_map.get(p.outcome, "gray") for p in sorted_f7]
    ax10.barh(bar_labels, bar_values, color=bar_colors, alpha=0.85)
    ax10.set_xlabel("Rank")
    ax10.set_title("F7: Batch Ranking", fontsize=10)
    legend_f7 = [
        Patch(facecolor="steelblue", label="ok"),
        Patch(facecolor="orange", label="blocked"),
        Patch(facecolor="gray", label="failed"),
    ]
    ax10.legend(handles=legend_f7, fontsize=8)

    # --- [1,1] F8 driver usefulness bars ---
    ax11 = axes[1, 1]
    rec_color_map = {"keep": "green", "review": "orange", "reject": "red"}
    sorted_f8 = sorted(f8_payloads, key=lambda x: x.driver_rank)
    f8_names = [p.driver_name + (" *" if p.redundancy_flag else "") for p in sorted_f8]
    f8_scores = [p.mean_usefulness_score for p in sorted_f8]
    f8_colors = [rec_color_map.get(p.recommendation, "gray") for p in sorted_f8]
    ax11.barh(f8_names, f8_scores, color=f8_colors, alpha=0.85)
    ax11.set_xlabel("Mean Usefulness Score")
    ax11.set_title("F8: Driver Usefulness (* = redundant)", fontsize=10)
    legend_f8 = [
        Patch(facecolor="green", label="keep"),
        Patch(facecolor="orange", label="review"),
        Patch(facecolor="red", label="reject"),
    ]
    ax11.legend(handles=legend_f8, fontsize=8)

    fig.suptitle(
        "Agent Payload Layer — A1 Diagnostic Summary",
        fontsize=14,
        fontweight="bold",
    )
    plt.tight_layout()

    figure_path = Path("outputs/figures/agent/agent_payload_diagnostic_summary.png")
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(figure_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Figure saved to {figure_path}")


def main() -> None:
    """Run the full A1 agent payload demo."""
    Path("outputs/figures/agent").mkdir(parents=True, exist_ok=True)
    Path("outputs/json").mkdir(parents=True, exist_ok=True)

    triage_result, single_payload = _section1_single_triage()
    f7_payloads = _section2_batch_triage()
    f8_payloads = _section3_exog_screening()
    _section4_figures(
        triage_result=triage_result,
        single_payload=single_payload,
        f7_payloads=f7_payloads,
        f8_payloads=f8_payloads,
    )

    print("\nDemo complete.")


if __name__ == "__main__":
    main()
