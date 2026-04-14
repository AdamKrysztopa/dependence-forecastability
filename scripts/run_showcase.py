"""Unified showcase runner: all forecastability surfaces on Air Passengers.

Demonstrates every public API surface on the Air Passengers dataset:

  M1. run_triage                     — deterministic fast triage
  M2. run_canonical_example          — full AMI/pAMI pipeline with significance bands
  M3. ForecastabilityAnalyzer        — multi-scorer comparison
  M4. run_rolling_origin_evaluation  — rolling-origin benchmark (skippable)
  F1. ForecastabilityProfile         — horizon-level informative structure
  F2. TheoreticalLimitDiagnostics    — information-theoretic predictability ceiling
  F3. PredictiveInfoLearningCurve    — optimal lookback via mutual-info saturation
  F4. SpectralPredictabilityResult   — PSD-based spectral structure score
  F5. LargestLyapunovExponentResult  — chaos proxy (EXPERIMENTAL)
  F6. ComplexityBandResult           — entropy-based complexity classification
  BONUS. Holistic AI interpretation of all ten diagnostics (opt-in)

Usage::

    uv run scripts/run_showcase.py
    uv run scripts/run_showcase.py --no-rolling
    uv run scripts/run_showcase.py --no-rolling --agent

Artifacts are written to outputs/figures/showcase/ and
outputs/reports/showcase/.
"""

from __future__ import annotations

import argparse
import logging
import os
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

# Set non-interactive backend before any matplotlib import.
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np
from pydantic import BaseModel, ConfigDict

from forecastability.pipeline import run_canonical_example, run_rolling_origin_evaluation
from forecastability.pipeline.analyzer import AnalyzeResult, ForecastabilityAnalyzer
from forecastability.triage.models import AnalysisGoal, TriageRequest, TriageResult
from forecastability.use_cases.run_triage import run_triage
from forecastability.utils.datasets import load_air_passengers
from forecastability.utils.plots import plot_canonical_result, save_all_canonical_plots
from forecastability.utils.types import CanonicalExampleResult, SeriesEvaluationResult

if TYPE_CHECKING:
    from forecastability.triage.complexity_band import ComplexityBandResult
    from forecastability.triage.forecastability_profile import ForecastabilityProfile
    from forecastability.triage.lyapunov import LargestLyapunovExponentResult
    from forecastability.triage.predictive_info_learning_curve import PredictiveInfoLearningCurve
    from forecastability.triage.spectral_predictability import SpectralPredictabilityResult
    from forecastability.triage.theoretical_limit_diagnostics import TheoreticalLimitDiagnostics

_logger = logging.getLogger(__name__)

_SEP = "═" * 50
_SERIES_NAME = "air_passengers"


# ---------------------------------------------------------------------------
# Structured output model for holistic agent
# ---------------------------------------------------------------------------


class ShowcaseExplanation(BaseModel):
    """Holistic LLM interpretation of all showcase diagnostics.

    Attributes:
        overall_forecastability: High-level assessment, e.g. "high", "medium", "low".
        key_findings: One bullet per method (up to 10 total).
        unified_recommendation: Actionable guidance for a practitioner.
        narrative: Human-facing story, 150–250 words.
        caveats: Warnings, e.g. that F5 is experimental.
    """

    model_config = ConfigDict(frozen=True)

    overall_forecastability: str
    key_findings: list[str]
    unified_recommendation: str
    narrative: str
    caveats: list[str]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the showcase runner.

    Returns:
        Parsed namespace with fields: no_bands, no_rolling, agent,
        random_state, output_root.
    """
    parser = argparse.ArgumentParser(description="AMI forecastability showcase — Air Passengers")
    parser.add_argument("--no-bands", action="store_true", help="skip surrogate bands (faster)")
    parser.add_argument("--no-rolling", action="store_true", help="skip rolling origin (~30s)")
    parser.add_argument("--agent", action="store_true", help="enable LLM agentic interpretation")
    parser.add_argument("--random-state", type=int, default=42, help="reproducibility seed")
    parser.add_argument("--output-root", type=str, default="outputs", help="output root dir")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Directory helpers
# ---------------------------------------------------------------------------


def _ensure_dirs(*, output_root: Path) -> tuple[Path, Path]:
    """Create and return the figures and reports subdirectories.

    Args:
        output_root: Root output directory.

    Returns:
        Tuple of (figures_dir, reports_dir).
    """
    figures_dir = output_root / "figures" / "showcase"
    reports_dir = output_root / "reports" / "showcase"
    figures_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    return figures_dir, reports_dir


# ---------------------------------------------------------------------------
# Console formatting
# ---------------------------------------------------------------------------


def _print_section(title: str) -> None:
    """Print a decorated section header to stdout.

    Args:
        title: Title text to display between separators.
    """
    print(f"\n{_SEP}\n{title}\n{_SEP}")


# ---------------------------------------------------------------------------
# Method 1 — run_triage
# ---------------------------------------------------------------------------


def _run_method1(ts: np.ndarray, *, random_state: int) -> TriageResult:
    """Execute deterministic triage on *ts* and print a summary.

    Args:
        ts: Target time series array.
        random_state: Reproducibility seed.

    Returns:
        Completed :class:`TriageResult`.
    """
    _print_section("Method 1 — Deterministic Triage  (run_triage)")

    request = TriageRequest(
        series=ts,
        goal=AnalysisGoal.univariate,
        max_lag=40,
        n_surrogates=99,
        random_state=random_state,
    )
    result = run_triage(request)

    interp = result.interpretation
    ar = result.analyze_result

    readiness = result.readiness.status.value
    fc_class = interp.forecastability_class if interp else "n/a"
    dir_class = interp.directness_class if interp else "n/a"
    regime = interp.modeling_regime if interp else "n/a"
    sig_lags = ar.sig_raw_lags.tolist() if ar is not None else []
    recommendation = result.recommendation or "n/a"

    print(f"  Series: {_SERIES_NAME}  n={ts.size}")
    print(f"  Readiness: {readiness}")
    print(f"  Forecastability: {fc_class}  |  Directness: {dir_class}")
    print(f"  Regime: {regime}")
    print(f"  Significant lags (AMI): {sig_lags}")
    print(f"  Recommendation: {recommendation}")

    return result


def _plot_triage_summary(result: TriageResult, *, save_path: Path) -> None:
    """Save a classification summary figure for the triage result.

    Shows the AMI curve from run_triage with primary lags marked and a
    classification legend.  Replaces the uninformative sig-count bar chart
    that always shows zeros when significance bands are not computed.

    Args:
        result: Completed triage result.
        save_path: Destination path for the figure.
    """
    ar = result.analyze_result
    interp = result.interpretation
    fc_class = interp.forecastability_class if interp else "n/a"
    dir_class = interp.directness_class if interp else "n/a"
    regime = interp.modeling_regime if interp else "n/a"
    primary_lags = interp.primary_lags if interp else []
    readiness = result.readiness.status.value

    fig, ax = plt.subplots(figsize=(9, 4))

    if ar is not None and ar.raw.size > 0:
        lags = np.arange(1, ar.raw.size + 1)
        ax.plot(lags, ar.raw, lw=1.8, color="tab:blue", label="AMI(h)")
        if ar.partial.size > 0:
            p_lags = np.arange(1, ar.partial.size + 1)
            ax.plot(p_lags, ar.partial, lw=1.5, color="tab:red", ls="--", label="pAMI(h)")
        for lag in primary_lags:
            if 1 <= lag <= ar.raw.size:
                ax.axvline(lag, color="orange", lw=1.0, ls=":", alpha=0.8)
        if primary_lags:
            ax.axvline(
                primary_lags[0],
                color="orange",
                lw=1.0,
                ls=":",
                alpha=0.8,
                label=f"primary lags {primary_lags[:4]}",
            )
        ax.set_xlabel("Lag (h)")
        ax.set_ylabel("Mutual information")
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)
    else:
        ax.text(
            0.5,
            0.5,
            "no AMI curve available",
            ha="center",
            va="center",
            transform=ax.transAxes,
            color="grey",
        )
        ax.axis("off")

    ax.set_title(
        f"Air Passengers — run_triage result\n"
        f"fc: {fc_class}  |  dir: {dir_class}  |  regime: {regime}  |  readiness: {readiness}",
        fontsize=10,
    )
    plt.tight_layout()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → saved {save_path}")


# ---------------------------------------------------------------------------
# Method 2 — run_canonical_example
# ---------------------------------------------------------------------------


def _run_method2(
    ts: np.ndarray,
    *,
    skip_bands: bool,
    random_state: int,
    figures_dir: Path,
) -> CanonicalExampleResult:
    """Run the canonical AMI/pAMI pipeline and save plots.

    Args:
        ts: Target time series array.
        skip_bands: When ``True`` surrogate significance bands are omitted.
        random_state: Reproducibility seed.
        figures_dir: Directory for saving canonical plots.

    Returns:
        Completed :class:`CanonicalExampleResult`.
    """
    _print_section("Method 2 — Canonical AMI / pAMI  (run_canonical_example)")

    result = run_canonical_example(
        _SERIES_NAME,
        ts,
        max_lag_ami=40,
        max_lag_pami=40,
        n_neighbors=8,
        n_surrogates=99,
        alpha=0.05,
        random_state=random_state,
        pami_backend="linear_residual",
        skip_bands=skip_bands,
    )

    ami_sig = result.ami.significant_lags
    pami_sig = result.pami.significant_lags
    n_sig_ami = int(ami_sig.size) if ami_sig is not None else 0
    n_sig_pami = int(pami_sig.size) if pami_sig is not None else 0
    auc_ami = float(np.trapezoid(result.ami.values))
    auc_pami = float(np.trapezoid(result.pami.values))

    print(f"  Significant AMI lags: {n_sig_ami}  |  Significant pAMI lags: {n_sig_pami}")
    print(f"  AMI AUC: {auc_ami:.3f}  |  pAMI AUC: {auc_pami:.3f}")

    canonical_dir = figures_dir / "canonical"
    paths = save_all_canonical_plots(result, output_dir=canonical_dir)

    # Copy the multi-panel figure to the expected showcase name.
    multi_panel_src = paths.get("multi_panel")
    canonical_dst = figures_dir / "canonical_result.png"
    if multi_panel_src and multi_panel_src.exists():
        import shutil

        shutil.copy(multi_panel_src, canonical_dst)
    else:
        plot_canonical_result(result, save_path=canonical_dst)
    print(f"  → saved {canonical_dst}")

    return result


# ---------------------------------------------------------------------------
# Method 3 — ForecastabilityAnalyzer
# ---------------------------------------------------------------------------


def _run_method3(ts: np.ndarray, *, random_state: int) -> AnalyzeResult:
    """Run ForecastabilityAnalyzer and print comparison summary.

    Args:
        ts: Target time series array.
        random_state: Reproducibility seed.

    Returns:
        Completed :class:`AnalyzeResult`.
    """
    _print_section("Method 3 — ForecastabilityAnalyzer  (multi-scorer)")

    analyzer = ForecastabilityAnalyzer(n_surrogates=99, random_state=random_state, method="mi")
    result = analyzer.analyze(ts, max_lag=40, compute_surrogates=False)

    auc_ami = float(np.trapezoid(result.raw))
    auc_pami = float(np.trapezoid(result.partial))
    peak_ami = float(np.max(result.raw))
    peak_pami = float(np.max(result.partial))

    print(f"  AMI AUC: {auc_ami:.3f}  peak: {peak_ami:.4f}")
    print(f"  pAMI AUC: {auc_pami:.3f}  peak: {peak_pami:.4f}")
    print(f"  Recommendation: {result.recommendation}")

    return result


def _plot_analyzer_comparison(result: AnalyzeResult, *, save_path: Path) -> None:
    """Save overlaid AMI vs pAMI figure from ForecastabilityAnalyzer output.

    Args:
        result: Analyzer result with raw and partial curves.
        save_path: Destination path for the figure.
    """
    lags_raw = np.arange(1, result.raw.size + 1)
    lags_partial = np.arange(1, result.partial.size + 1)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(lags_raw, result.raw, lw=2, label="AMI(h)")
    ax.plot(lags_partial, result.partial, lw=2, color="tab:red", linestyle="--", label="pAMI(h)")
    ax.set_title("Air Passengers — AMI vs pAMI (ForecastabilityAnalyzer)")
    ax.set_xlabel("Lag (h)")
    ax.set_ylabel("Mutual information")
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → saved {save_path}")


# ---------------------------------------------------------------------------
# Method 4 — rolling origin
# ---------------------------------------------------------------------------


def _run_method4(ts: np.ndarray, *, random_state: int) -> SeriesEvaluationResult:
    """Run rolling-origin evaluation and print a sMAPE by horizon summary.

    Args:
        ts: Target time series array.
        random_state: Reproducibility seed.

    Returns:
        Completed :class:`SeriesEvaluationResult`.
    """
    _print_section("Method 4 — Rolling Origin Benchmark  (run_rolling_origin_evaluation)")

    result = run_rolling_origin_evaluation(
        ts,
        series_id=_SERIES_NAME,
        frequency="monthly",
        horizons=[1, 6, 12],
        n_origins=20,
        seasonal_period=12,
        random_state=random_state,
    )

    for fr in result.forecast_results:
        row = "  ".join(f"h={h}: {fr.smape_by_horizon[h]:.2f}%" for h in fr.horizons)
        print(f"  {fr.model_name}: {row}")

    return result


def _plot_rolling_errors(result: SeriesEvaluationResult, *, save_path: Path) -> None:
    """Save a bar chart of sMAPE by horizon for each model in *result*.

    Args:
        result: Rolling-origin evaluation result.
        save_path: Destination path for the figure.
    """
    horizons = sorted({h for fr in result.forecast_results for h in fr.horizons})
    x = np.arange(len(horizons))
    width = 0.8 / max(len(result.forecast_results), 1)

    fig, ax = plt.subplots(figsize=(9, 5))
    for idx, fr in enumerate(result.forecast_results):
        vals = [fr.smape_by_horizon.get(h, 0.0) for h in horizons]
        offset = (idx - len(result.forecast_results) / 2 + 0.5) * width
        ax.bar(x + offset, vals, width, label=fr.model_name)

    ax.set_xticks(x)
    ax.set_xticklabels([f"h={h}" for h in horizons])
    ax.set_ylabel("sMAPE (%)")
    ax.set_title("Air Passengers — Rolling Origin sMAPE by Horizon")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → saved {save_path}")


# ---------------------------------------------------------------------------
# F1 — Forecastability Profile
# ---------------------------------------------------------------------------


def _run_f1_profile(triage_result: TriageResult) -> ForecastabilityProfile | None:
    """Extract the forecastability profile from the completed triage result.

    Does not rerun triage — wraps the profile already computed by M1.

    Args:
        triage_result: Completed triage result from Method 1.

    Returns:
        :class:`ForecastabilityProfile` or ``None`` if unavailable.
    """
    _print_section("F1 — Forecastability Profile")
    profile = triage_result.forecastability_profile
    if profile is None:
        print("  F1 profile not available in triage result.")
        return None
    n_inf = len(profile.informative_horizons)
    print(
        f"  Peak horizon: {profile.peak_horizon}  |  "
        f"Informative horizons: {profile.informative_horizons[:8]}"
    )
    print(f"  n_informative: {n_inf}  |  is_non_monotone: {profile.is_non_monotone}")
    print(f"  ε-threshold: {profile.epsilon:.4f}")
    print(f"  Summary: {profile.summary}")
    print(f"  Model now: {profile.model_now}")
    return profile


def _plot_f1_profile(profile: ForecastabilityProfile, *, save_path: Path) -> None:
    """Save the forecastability profile curve figure.

    Args:
        profile: Forecastability profile from triage.
        save_path: Destination path for the figure.
    """
    horizons = np.asarray(profile.horizons)
    values = np.asarray(profile.values)
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(horizons, values, lw=1.8, color="tab:blue", label="F(h)")
    ax.axhline(profile.epsilon, color="grey", lw=1.0, ls="--", label=f"ε={profile.epsilon:.3f}")
    for h in profile.informative_horizons:
        ax.axvline(h, color="tab:green", lw=0.6, ls=":", alpha=0.5)
    ax.set_xlabel("Horizon h")
    ax.set_ylabel("Forecastability F(h)")
    ax.set_title(
        f"F1: Forecastability Profile — peak h={profile.peak_horizon}  "
        f"non_monotone={profile.is_non_monotone}",
        fontsize=10,
    )
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → saved {save_path}")


# ---------------------------------------------------------------------------
# F2 — Theoretical Limit Diagnostics
# ---------------------------------------------------------------------------


def _run_f2_limits(triage_result: TriageResult) -> TheoreticalLimitDiagnostics | None:
    """Build theoretical limit diagnostics from the triage AMI curve.

    Args:
        triage_result: Completed triage result providing the raw AMI curve.

    Returns:
        :class:`TheoreticalLimitDiagnostics` or ``None`` on failure.
    """
    _print_section("F2 — Theoretical Limit Diagnostics")
    from forecastability.services.theoretical_limit_diagnostics_service import (
        build_theoretical_limit_diagnostics,
    )

    ar = triage_result.analyze_result
    if ar is None or ar.raw.size == 0:
        print("  F2 unavailable: no AMI curve in triage result.")
        return None
    try:
        limits = build_theoretical_limit_diagnostics(
            ar.raw,
            compression_suspected=False,
            dpi_suspected=False,
        )
    except RuntimeError as exc:
        print(f"  F2 unavailable: {exc}")
        return None
    ceilings = np.asarray(limits.forecastability_ceiling_by_horizon)
    peak_h = int(np.argmax(ceilings)) + 1
    peak_val = float(ceilings[peak_h - 1])
    print(f"  Ceiling peak: h={peak_h}, MI={peak_val:.4f}")
    print(f"  Summary: {limits.ceiling_summary}")
    if limits.compression_warning:
        print(f"  Compression warning: {limits.compression_warning}")
    if limits.dpi_warning:
        print(f"  DPI warning: {limits.dpi_warning}")
    return limits


def _plot_f2_limits(limits: TheoreticalLimitDiagnostics, *, save_path: Path) -> None:
    """Save the theoretical forecastability ceiling bar figure.

    Args:
        limits: Theoretical limit diagnostics result.
        save_path: Destination path for the figure.
    """
    ceilings = np.asarray(limits.forecastability_ceiling_by_horizon)
    horizons = np.arange(1, ceilings.size + 1)
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(horizons, ceilings, color="tab:orange", alpha=0.7, label="MI ceiling")
    ax.set_xlabel("Horizon h")
    ax.set_ylabel("Forecastability ceiling (MI)")
    ax.set_title("F2: Theoretical Forecastability Ceiling", fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → saved {save_path}")


# ---------------------------------------------------------------------------
# F3 — Predictive Info Learning Curve
# ---------------------------------------------------------------------------


def _run_f3_learning_curve(
    ts: np.ndarray,
    *,
    random_state: int,
) -> PredictiveInfoLearningCurve | None:
    """Build predictive information learning curve for the series.

    Args:
        ts: Target time series array.
        random_state: Reproducibility seed.

    Returns:
        :class:`PredictiveInfoLearningCurve` or ``None`` on failure.
    """
    _print_section("F3 — Predictive Info Learning Curve")
    from forecastability.services.predictive_info_learning_curve_service import (
        build_predictive_info_learning_curve,
    )

    try:
        curve = build_predictive_info_learning_curve(ts, max_k=12, random_state=random_state)
    except RuntimeError as exc:
        print(f"  F3 unavailable: {exc}")
        return None
    info_rounded = [round(v, 4) for v in curve.information_values]
    print(
        f"  Plateau detected: {curve.plateau_detected}  |  "
        f"Recommended lookback: k={curve.recommended_lookback}"
    )
    print(f"  Window sizes: {curve.window_sizes}")
    print(f"  Information values: {info_rounded}")
    for warning in curve.reliability_warnings:
        print(f"  Warning: {warning}")
    return curve


def _plot_f3_learning_curve(curve: PredictiveInfoLearningCurve, *, save_path: Path) -> None:
    """Save the predictive information learning curve figure.

    Args:
        curve: Learning curve result.
        save_path: Destination path for the figure.
    """
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(
        curve.window_sizes,
        curve.information_values,
        lw=1.8,
        marker="o",
        ms=5,
        color="tab:purple",
        label="I_pred(k)",
    )
    ax.axvline(
        curve.recommended_lookback,
        color="tab:orange",
        lw=1.2,
        ls="--",
        label=f"recommended k={curve.recommended_lookback}",
    )
    plateau_label = "yes" if curve.plateau_detected else "no"
    ax.set_xlabel("Window size k")
    ax.set_ylabel("Predictive information I(k)")
    ax.set_title(
        f"F3: Predictive Info Learning Curve  (plateau={plateau_label})",
        fontsize=10,
    )
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → saved {save_path}")


# ---------------------------------------------------------------------------
# F4 — Spectral Predictability
# ---------------------------------------------------------------------------


def _run_f4_spectral(ts: np.ndarray) -> SpectralPredictabilityResult | None:
    """Build spectral predictability result for the series.

    Args:
        ts: Target time series array.

    Returns:
        :class:`SpectralPredictabilityResult` or ``None`` on failure.
    """
    _print_section("F4 — Spectral Predictability")
    from forecastability.services.spectral_predictability_service import (
        build_spectral_predictability,
    )

    try:
        spectral = build_spectral_predictability(ts, detrend="constant")
    except RuntimeError as exc:
        print(f"  F4 unavailable: {exc}")
        return None
    print(
        f"  Spectral score Ω: {spectral.score:.4f}  |  "
        f"Normalised entropy: {spectral.normalised_entropy:.4f}"
    )
    print(f"  n_bins: {spectral.n_bins}  |  detrend: {spectral.detrend}")
    print(f"  Interpretation: {spectral.interpretation}")
    return spectral


def _plot_f4_spectral(spectral: SpectralPredictabilityResult, *, save_path: Path) -> None:
    """Save the spectral predictability score figure.

    Args:
        spectral: Spectral predictability result.
        save_path: Destination path for the figure.
    """
    labels = ["Ω (spectral score)", "H_norm (entropy)"]
    values = [spectral.score, spectral.normalised_entropy]
    colors = ["tab:cyan", "tab:pink"]
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.barh(labels, values, color=colors)
    ax.set_xlim(0, 1)
    ax.set_xlabel("Value")
    ax.set_title(
        f"F4: Spectral Predictability  Ω={spectral.score:.4f}\n{spectral.interpretation}",
        fontsize=9,
    )
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → saved {save_path}")


# ---------------------------------------------------------------------------
# F5 — Largest Lyapunov Exponent (EXPERIMENTAL)
# ---------------------------------------------------------------------------


def _run_f5_lle(ts: np.ndarray) -> LargestLyapunovExponentResult | None:
    """Estimate the Largest Lyapunov Exponent (experimental).

    Args:
        ts: Target time series array.

    Returns:
        :class:`LargestLyapunovExponentResult` or ``None`` on failure.
    """
    _print_section("F5 — Largest Lyapunov Exponent (EXPERIMENTAL)")
    from forecastability.services.lyapunov_service import build_largest_lyapunov_exponent

    try:
        lle = build_largest_lyapunov_exponent(ts)
    except RuntimeError as exc:
        print(f"  F5 unavailable: {exc}")
        return None
    lambda_str = f"{lle.lambda_estimate:.4f}" if not np.isnan(lle.lambda_estimate) else "NaN"
    print(
        f"  λ estimate: {lambda_str}  |  embedding_dim: {lle.embedding_dim}  |  delay: {lle.delay}"
    )
    print(f"  n_embedded: {lle.n_embedded_points}  |  evolution_steps: {lle.evolution_steps}")
    print(f"  Interpretation: {lle.interpretation}")
    print(f"  Warning: {lle.reliability_warning}")
    return lle


def _plot_f5_lle(lle: LargestLyapunovExponentResult, *, save_path: Path) -> None:
    """Save the Largest Lyapunov Exponent summary figure.

    Args:
        lle: LLE estimation result.
        save_path: Destination path for the figure.
    """
    lambda_val = lle.lambda_estimate
    is_valid = not np.isnan(lambda_val)
    bar_val = float(lambda_val) if is_valid else 0.0
    color = "tab:red" if (is_valid and lambda_val > 0) else "tab:green"
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.barh(["λ estimate"], [bar_val], color=color)
    ax.axvline(0.0, color="grey", lw=1.0, ls="--")
    lambda_label = f"{lambda_val:.4f}" if is_valid else "NaN"
    ax.set_xlabel("Largest Lyapunov Exponent λ")
    ax.set_title(
        f"F5: LLE (EXPERIMENTAL)  λ={lambda_label}\n{lle.interpretation}",
        fontsize=9,
    )
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → saved {save_path}")


# ---------------------------------------------------------------------------
# F6 — Complexity Band
# ---------------------------------------------------------------------------


def _run_f6_complexity(ts: np.ndarray) -> ComplexityBandResult | None:
    """Build entropy-based complexity band result for the series.

    Args:
        ts: Target time series array.

    Returns:
        :class:`ComplexityBandResult` or ``None`` on failure.
    """
    _print_section("F6 — Complexity Band")
    from forecastability.services.complexity_band_service import build_complexity_band

    try:
        complexity = build_complexity_band(ts)
    except RuntimeError as exc:
        print(f"  F6 unavailable: {exc}")
        return None
    print(
        f"  Permutation entropy: {complexity.permutation_entropy:.4f}  |  "
        f"Spectral entropy: {complexity.spectral_entropy:.4f}"
    )
    print(
        f"  Complexity band: {complexity.complexity_band}  |  "
        f"Embedding order: {complexity.embedding_order}"
    )
    print(f"  Interpretation: {complexity.interpretation}")
    if complexity.pe_reliability_warning:
        print(f"  Warning: {complexity.pe_reliability_warning}")
    return complexity


def _plot_f6_complexity(complexity: ComplexityBandResult, *, save_path: Path) -> None:
    """Save the entropy-based complexity plane figure.

    Args:
        complexity: Complexity band result.
        save_path: Destination path for the figure.
    """
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(
        [complexity.permutation_entropy],
        [complexity.spectral_entropy],
        s=120,
        color="tab:red",
        zorder=3,
        label=f"band: {complexity.complexity_band}",
    )
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Permutation Entropy (PE)")
    ax.set_ylabel("Spectral Entropy (SE)")
    ax.set_title(
        f"F6: Complexity Band — {complexity.complexity_band}\n"
        f"PE={complexity.permutation_entropy:.4f}  SE={complexity.spectral_entropy:.4f}",
        fontsize=9,
    )
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → saved {save_path}")


# ---------------------------------------------------------------------------
# BONUS — holistic agentic interpretation
# ---------------------------------------------------------------------------


def _fmt_m1(triage_result: TriageResult) -> str:
    """Format M1 triage summary line for the holistic agent prompt.

    Args:
        triage_result: Completed triage result.

    Returns:
        One-line summary string.
    """
    interp = triage_result.interpretation
    ar = triage_result.analyze_result
    fc = interp.forecastability_class if interp else "n/a"
    regime = interp.modeling_regime if interp else "n/a"
    n_sig = len(ar.sig_raw_lags) if ar is not None else 0
    return f"M1 run_triage: fc={fc}, regime={regime}, sig_lags={n_sig}"


def _fmt_m2(canonical_result: CanonicalExampleResult) -> str:
    """Format M2 canonical pipeline summary line for the holistic agent prompt.

    Args:
        canonical_result: Canonical pipeline result.

    Returns:
        One-line summary string.
    """
    auc_ami = float(np.trapezoid(canonical_result.ami.values))
    auc_pami = float(np.trapezoid(canonical_result.pami.values))
    sig_arr = canonical_result.ami.significant_lags
    n_sig = int(sig_arr.size) if sig_arr is not None else 0
    return f"M2 Canonical: AUC_ami={auc_ami:.2f}, AUC_pami={auc_pami:.2f}, n_sig_ami={n_sig}"


def _fmt_m3(analyzer_result: AnalyzeResult) -> str:
    """Format M3 analyzer summary line for the holistic agent prompt.

    Args:
        analyzer_result: Analyzer result.

    Returns:
        One-line summary string.
    """
    auc = float(np.trapezoid(analyzer_result.raw))
    rec = analyzer_result.recommendation or "n/a"
    return f"M3 Analyzer: AUC_ami={auc:.2f}, recommendation={rec}"


def _fmt_m4(rolling_result: SeriesEvaluationResult | None) -> str:
    """Format M4 rolling-origin summary line for the holistic agent prompt.

    Args:
        rolling_result: Rolling evaluation result or ``None``.

    Returns:
        One-line summary string.
    """
    if rolling_result is None:
        return "M4 Rolling-origin: skipped"
    parts: list[str] = []
    for fr in rolling_result.forecast_results[:2]:
        smape_h1 = fr.smape_by_horizon.get(1, 0.0)
        parts.append(f"{fr.model_name} h=1={smape_h1:.1f}%")
    return "M4 Rolling-origin: " + (", ".join(parts) if parts else "n/a")


def _fmt_f1(f1_profile: ForecastabilityProfile | None) -> str:
    """Format F1 profile summary line for the holistic agent prompt.

    Args:
        f1_profile: Forecastability profile or ``None``.

    Returns:
        One-line summary string.
    """
    if f1_profile is None:
        return "F1 Profile: unavailable"
    n_inf = len(f1_profile.informative_horizons)
    return (
        f"F1 Profile: peak_h={f1_profile.peak_horizon}, "
        f"n_informative={n_inf}, non_monotone={f1_profile.is_non_monotone}"
    )


def _fmt_f2(f2_limits: TheoreticalLimitDiagnostics | None) -> str:
    """Format F2 ceiling summary line for the holistic agent prompt.

    Args:
        f2_limits: Theoretical limit diagnostics or ``None``.

    Returns:
        One-line summary string.
    """
    if f2_limits is None:
        return "F2 Ceiling: unavailable"
    ceilings = np.asarray(f2_limits.forecastability_ceiling_by_horizon)
    max_val = float(np.max(ceilings)) if ceilings.size > 0 else float("nan")
    return f"F2 Ceiling: max_MI={max_val:.4f}. {f2_limits.ceiling_summary}"


def _fmt_f3(f3_curve: PredictiveInfoLearningCurve | None) -> str:
    """Format F3 learning curve summary line for the holistic agent prompt.

    Args:
        f3_curve: Learning curve result or ``None``.

    Returns:
        One-line summary string.
    """
    if f3_curve is None:
        return "F3 Learning curve: unavailable"
    plateau = "yes" if f3_curve.plateau_detected else "no"
    return f"F3 Learning curve: plateau={plateau}, recommended_k={f3_curve.recommended_lookback}"


def _fmt_f4(f4_spectral: SpectralPredictabilityResult | None) -> str:
    """Format F4 spectral summary line for the holistic agent prompt.

    Args:
        f4_spectral: Spectral predictability result or ``None``.

    Returns:
        One-line summary string.
    """
    if f4_spectral is None:
        return "F4 Spectral: unavailable"
    return (
        f"F4 Spectral: Omega={f4_spectral.score:.4f}, "
        f"H_norm={f4_spectral.normalised_entropy:.4f}. {f4_spectral.interpretation}"
    )


def _fmt_f5(f5_lle: LargestLyapunovExponentResult | None) -> str:
    """Format F5 LLE summary line for the holistic agent prompt.

    Args:
        f5_lle: LLE result or ``None``.

    Returns:
        One-line summary string.
    """
    if f5_lle is None:
        return "F5 LLE: unavailable"
    lam = f"{f5_lle.lambda_estimate:.4f}" if not np.isnan(f5_lle.lambda_estimate) else "NaN"
    return f"F5 LLE (experimental): lambda={lam}. {f5_lle.interpretation}"


def _fmt_f6(f6_complexity: ComplexityBandResult | None) -> str:
    """Format F6 complexity summary line for the holistic agent prompt.

    Args:
        f6_complexity: Complexity band result or ``None``.

    Returns:
        One-line summary string.
    """
    if f6_complexity is None:
        return "F6 Complexity: unavailable"
    return (
        f"F6 Complexity: PE={f6_complexity.permutation_entropy:.4f}, "
        f"SE={f6_complexity.spectral_entropy:.4f}, "
        f"band={f6_complexity.complexity_band}"
    )


def _build_holistic_summary_text(
    *,
    triage_result: TriageResult,
    canonical_result: CanonicalExampleResult,
    analyzer_result: AnalyzeResult,
    rolling_result: SeriesEvaluationResult | None,
    f1_profile: ForecastabilityProfile | None,
    f2_limits: TheoreticalLimitDiagnostics | None,
    f3_curve: PredictiveInfoLearningCurve | None,
    f4_spectral: SpectralPredictabilityResult | None,
    f5_lle: LargestLyapunovExponentResult | None,
    f6_complexity: ComplexityBandResult | None,
) -> str:
    """Build a plain-text structured summary of all 10 diagnostic results.

    Keeps total output under 1 500 characters for LLM context efficiency.

    Args:
        triage_result: M1 result.
        canonical_result: M2 result.
        analyzer_result: M3 result.
        rolling_result: M4 result or ``None``.
        f1_profile: F1 result or ``None``.
        f2_limits: F2 result or ``None``.
        f3_curve: F3 result or ``None``.
        f4_spectral: F4 result or ``None``.
        f5_lle: F5 result or ``None``.
        f6_complexity: F6 result or ``None``.

    Returns:
        Plain-text summary string.
    """
    lines = [
        "Air Passengers (monthly, 144 obs, 1949–1960). Ten forecastability diagnostics:",
        _fmt_m1(triage_result),
        _fmt_m2(canonical_result),
        _fmt_m3(analyzer_result),
        _fmt_m4(rolling_result),
        _fmt_f1(f1_profile),
        _fmt_f2(f2_limits),
        _fmt_f3(f3_curve),
        _fmt_f4(f4_spectral),
        _fmt_f5(f5_lle),
        _fmt_f6(f6_complexity),
    ]
    return "\n".join(lines)


def _run_holistic_agent(
    *,
    ts: np.ndarray,
    triage_result: TriageResult,
    canonical_result: CanonicalExampleResult,
    analyzer_result: AnalyzeResult,
    rolling_result: SeriesEvaluationResult | None,
    f1_profile: ForecastabilityProfile | None,
    f2_limits: TheoreticalLimitDiagnostics | None,
    f3_curve: PredictiveInfoLearningCurve | None,
    f4_spectral: SpectralPredictabilityResult | None,
    f5_lle: LargestLyapunovExponentResult | None,
    f6_complexity: ComplexityBandResult | None,
    random_state: int,
) -> tuple[ShowcaseExplanation | None, object]:
    """Run the holistic LLM agent to interpret all ten diagnostic results.

    Imports are guarded so the script remains runnable without pydantic_ai.
    Uses ``run_sync`` to avoid async boilerplate.

    Args:
        ts: Target time series (unused internally; present for traceability).
        triage_result: M1 result.
        canonical_result: M2 result.
        analyzer_result: M3 result.
        rolling_result: M4 result or ``None``.
        f1_profile: F1 result or ``None``.
        f2_limits: F2 result or ``None``.
        f3_curve: F3 result or ``None``.
        f4_spectral: F4 result or ``None``.
        f5_lle: F5 result or ``None``.
        f6_complexity: F6 result or ``None``.
        random_state: Reproducibility seed (passed for traceability).

    Returns:
        Tuple of (:class:`ShowcaseExplanation` or ``None``, settings object).
    """
    _print_section("BONUS — Holistic AI Interpretation  (all 10 diagnostics)")
    try:
        from pydantic_ai import Agent

        from forecastability.adapters.settings import InfraSettings
    except ImportError as exc:
        _logger.warning("Holistic agent unavailable: %s", exc)
        print(f"  Agent unavailable: {exc}")
        return None, None

    settings = InfraSettings()
    summary_text = _build_holistic_summary_text(
        triage_result=triage_result,
        canonical_result=canonical_result,
        analyzer_result=analyzer_result,
        rolling_result=rolling_result,
        f1_profile=f1_profile,
        f2_limits=f2_limits,
        f3_curve=f3_curve,
        f4_spectral=f4_spectral,
        f5_lle=f5_lle,
        f6_complexity=f6_complexity,
    )
    system_prompt = (
        "You are an expert time-series analyst. Provide an integrated assessment "
        "of the Air Passengers series using the diagnostic summary below. "
        "Never invent numbers — base all statements on the provided data only."
    )
    agent = Agent(
        model=f"openai:{settings.openai_model}",
        output_type=ShowcaseExplanation,
        system_prompt=system_prompt,
    )
    try:
        agent_result = agent.run_sync(user_prompt=summary_text)
    except (RuntimeError, ValueError, OSError) as exc:
        _logger.warning("Agent run failed: %s", exc)
        print(f"  Agent run failed: {exc}")
        return None, settings
    output = agent_result.output
    if not isinstance(output, ShowcaseExplanation):
        _logger.warning("Unexpected agent output type: %s", type(output))
        return None, settings
    return output, settings


def _print_showcase_explanation(explanation: ShowcaseExplanation, settings: object) -> None:
    """Print the holistic showcase explanation in a readable console format.

    Args:
        explanation: Structured LLM output from the holistic agent.
        settings: :class:`InfraSettings` instance (used for model name display).
    """
    model_name = f"openai:{getattr(settings, 'openai_model', 'gpt-4o')}" if settings else "unknown"
    narrative_wrapped = textwrap.fill(explanation.narrative, width=80, subsequent_indent="  ")
    rec_wrapped = textwrap.fill(
        explanation.unified_recommendation, width=80, subsequent_indent="  "
    )
    print(f"  Model: {model_name}")
    print(f"  Overall forecastability: {explanation.overall_forecastability}")
    print(f"\n  Unified recommendation:\n  {rec_wrapped}")
    if explanation.key_findings:
        print("\n  Key findings:")
        for finding in explanation.key_findings:
            print(f"  • {finding}")
    print(f"\n  Narrative:\n  {narrative_wrapped}")
    if explanation.caveats:
        print("\n  Caveats:")
        for caveat in explanation.caveats:
            print(f"  • {caveat}")


# ---------------------------------------------------------------------------
# Merged comparison figure (4×3)
# ---------------------------------------------------------------------------


def _plot_na_panel(ax: plt.Axes, label: str) -> None:
    """Render a greyed-out placeholder panel.

    Args:
        ax: Target axes.
        label: Message to display.
    """
    ax.text(
        0.5,
        0.5,
        label,
        ha="center",
        va="center",
        fontsize=9,
        color="grey",
        transform=ax.transAxes,
    )
    ax.axis("off")


def _build_merged_figure(
    *,
    triage_result: TriageResult,
    canonical_result: CanonicalExampleResult,
    analyzer_result: AnalyzeResult,
    rolling_result: SeriesEvaluationResult | None,
    f1_profile: ForecastabilityProfile | None,
    f2_limits: TheoreticalLimitDiagnostics | None,
    f3_curve: PredictiveInfoLearningCurve | None,
    f4_spectral: SpectralPredictabilityResult | None,
    f5_lle: LargestLyapunovExponentResult | None,
    f6_complexity: ComplexityBandResult | None,
    save_path: Path,
) -> None:
    """Build a 4×3 merged comparison figure for all ten methods.

    Layout::

        Row 0: M1 AMI curve    | F1 profile curve   | F3 learning curve
        Row 1: M2 canonical    | F2 ceiling bar      | F4 spectral score
        Row 2: M3 analyzer     | F5 LLE bar          | F6 PE-SE plane
        Row 3: M4 rolling      | placeholder         | placeholder

    Args:
        triage_result: M1 result.
        canonical_result: M2 result.
        analyzer_result: M3 result.
        rolling_result: M4 result or ``None``.
        f1_profile: F1 result or ``None``.
        f2_limits: F2 result or ``None``.
        f3_curve: F3 result or ``None``.
        f4_spectral: F4 result or ``None``.
        f5_lle: F5 result or ``None``.
        f6_complexity: F6 result or ``None``.
        save_path: Destination path for the merged figure.
    """
    fig, axes = plt.subplots(4, 3, figsize=(18, 20))
    fig.suptitle(
        "Air Passengers — Forecastability Showcase (10 methods)",
        fontsize=14,
        fontweight="bold",
    )

    # Row 0: M1, F1, F3
    _plot_merged_triage(axes[0, 0], triage_result)
    _plot_merged_f1_profile(axes[0, 1], f1_profile)
    _plot_merged_f3_curve(axes[0, 2], f3_curve)

    # Row 1: M2, F2, F4
    _plot_merged_canonical(axes[1, 0], canonical_result)
    _plot_merged_f2_limits(axes[1, 1], f2_limits)
    _plot_merged_f4_spectral(axes[1, 2], f4_spectral)

    # Row 2: M3, F5, F6
    _plot_merged_analyzer(axes[2, 0], analyzer_result)
    _plot_merged_f5_lle(axes[2, 1], f5_lle)
    _plot_merged_f6_complexity(axes[2, 2], f6_complexity)

    # Row 3: M4, placeholders
    _plot_merged_rolling(axes[3, 0], rolling_result)
    _plot_na_panel(axes[3, 1], "col 1 — reserved")
    _plot_na_panel(axes[3, 2], "col 2 — reserved")

    plt.tight_layout()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  → merged figure saved {save_path}")


def _plot_merged_triage(ax: plt.Axes, result: TriageResult) -> None:
    """Populate the triage panel of the merged figure.

    Args:
        ax: Target axes.
        result: Method 1 triage result.
    """
    ar = result.analyze_result
    interp = result.interpretation
    fc = interp.forecastability_class if interp else "n/a"
    dir_class = interp.directness_class if interp else "n/a"
    primary_lags = interp.primary_lags if interp else []

    if ar is not None and ar.raw.size > 0:
        lags = np.arange(1, ar.raw.size + 1)
        ax.plot(lags, ar.raw, lw=1.5, color="tab:blue", label="AMI(h)")
        if ar.partial.size > 0:
            p_lags = np.arange(1, ar.partial.size + 1)
            ax.plot(p_lags, ar.partial, lw=1.2, color="tab:red", ls="--", label="pAMI(h)")
        for i, lag in enumerate(primary_lags[:6]):
            if 1 <= lag <= ar.raw.size:
                label = f"primary {primary_lags[:4]}" if i == 0 else None
                ax.axvline(lag, color="orange", lw=0.9, ls=":", alpha=0.8, label=label)
        ax.set_xlabel("Lag")
        ax.legend(fontsize=7)
        ax.grid(alpha=0.3)
    else:
        _plot_na_panel(ax, "AMI curve unavailable")

    ax.set_title(f"M1: run_triage  (fc: {fc}, dir: {dir_class})", fontsize=10)


def _plot_merged_canonical(ax: plt.Axes, result: CanonicalExampleResult) -> None:
    """Populate the canonical AMI/pAMI panel of the merged figure.

    Args:
        ax: Target axes.
        result: Method 2 canonical result.
    """
    lags = np.arange(1, result.ami.values.size + 1)
    ax.plot(lags, result.ami.values, lw=1.5, label="AMI")
    ax.plot(lags, result.pami.values, lw=1.5, color="tab:red", linestyle="--", label="pAMI")
    if result.ami.upper_band is not None:
        ax.plot(lags, result.ami.upper_band, lw=0.8, ls=":", color="grey", label="95% surr.")
    ax.set_title("M2: Canonical AMI/pAMI", fontsize=10)
    ax.set_xlabel("Lag")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)


def _plot_merged_analyzer(ax: plt.Axes, result: AnalyzeResult) -> None:
    """Populate the analyzer comparison panel of the merged figure.

    Args:
        ax: Target axes.
        result: Method 3 analyzer result.
    """
    lags_raw = np.arange(1, result.raw.size + 1)
    lags_partial = np.arange(1, result.partial.size + 1)
    ax.plot(lags_raw, result.raw, lw=1.5, label="AMI (raw)")
    ax.plot(
        lags_partial,
        result.partial,
        lw=1.5,
        color="tab:red",
        linestyle="--",
        label="pAMI (partial)",
    )
    ax.set_title("M3: ForecastabilityAnalyzer", fontsize=10)
    ax.set_xlabel("Lag")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)


def _plot_merged_rolling(ax: plt.Axes, result: SeriesEvaluationResult | None) -> None:
    """Populate the rolling-origin panel of the merged figure.

    Args:
        ax: Target axes.
        result: Method 4 rolling result, or ``None`` when skipped.
    """
    if result is None:
        _plot_na_panel(ax, "M4: Rolling Origin\nnot run\n(omit --no-rolling to enable)")
        ax.set_title("M4: Rolling Origin (skipped)", fontsize=10)
        return

    horizons = sorted({h for fr in result.forecast_results for h in fr.horizons})
    x = np.arange(len(horizons))
    width = 0.8 / max(len(result.forecast_results), 1)
    for idx, fr in enumerate(result.forecast_results):
        vals = [fr.smape_by_horizon.get(h, 0.0) for h in horizons]
        offset = (idx - len(result.forecast_results) / 2 + 0.5) * width
        ax.bar(x + offset, vals, width, label=fr.model_name)
    ax.set_xticks(x)
    ax.set_xticklabels([f"h={h}" for h in horizons])
    ax.set_ylabel("sMAPE (%)")
    ax.set_title("M4: Rolling Origin sMAPE", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)


def _plot_merged_f1_profile(ax: plt.Axes, profile: ForecastabilityProfile | None) -> None:
    """Populate the F1 forecastability profile panel of the merged figure.

    Args:
        ax: Target axes.
        profile: F1 forecastability profile or ``None``.
    """
    if profile is None:
        _plot_na_panel(ax, "F1: Profile (unavailable)")
        ax.set_title("F1: Forecastability Profile", fontsize=10)
        return
    horizons = np.asarray(profile.horizons)
    values = np.asarray(profile.values)
    ax.plot(horizons, values, lw=1.5, color="tab:blue", label="F(h)")
    ax.axhline(profile.epsilon, color="grey", lw=0.8, ls="--", label=f"ε={profile.epsilon:.3f}")
    ax.set_xlabel("Horizon h")
    ax.set_title(
        f"F1: Profile  peak_h={profile.peak_horizon}  n_inf={len(profile.informative_horizons)}",
        fontsize=10,
    )
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)


def _plot_merged_f2_limits(ax: plt.Axes, limits: TheoreticalLimitDiagnostics | None) -> None:
    """Populate the F2 theoretical ceiling panel of the merged figure.

    Args:
        ax: Target axes.
        limits: F2 theoretical limit diagnostics or ``None``.
    """
    if limits is None:
        _plot_na_panel(ax, "F2: Ceiling (unavailable)")
        ax.set_title("F2: Theoretical Ceiling", fontsize=10)
        return
    ceilings = np.asarray(limits.forecastability_ceiling_by_horizon)
    horizons = np.arange(1, ceilings.size + 1)
    ax.bar(horizons, ceilings, color="tab:orange", alpha=0.7)
    ax.set_xlabel("Horizon h")
    ax.set_ylabel("MI ceiling")
    ax.set_title("F2: Theoretical Ceiling", fontsize=10)
    ax.grid(axis="y", alpha=0.3)


def _plot_merged_f3_curve(ax: plt.Axes, curve: PredictiveInfoLearningCurve | None) -> None:
    """Populate the F3 learning curve panel of the merged figure.

    Args:
        ax: Target axes.
        curve: F3 predictive info learning curve or ``None``.
    """
    if curve is None:
        _plot_na_panel(ax, "F3: Learning Curve (unavailable)")
        ax.set_title("F3: Predictive Info Curve", fontsize=10)
        return
    ax.plot(
        curve.window_sizes,
        curve.information_values,
        lw=1.5,
        marker="o",
        ms=4,
        color="tab:purple",
    )
    ax.axvline(curve.recommended_lookback, color="tab:orange", lw=1.0, ls="--")
    plateau_label = "yes" if curve.plateau_detected else "no"
    ax.set_xlabel("k")
    ax.set_title(
        f"F3: Predictive Info  plateau={plateau_label}  k*={curve.recommended_lookback}",
        fontsize=10,
    )
    ax.grid(alpha=0.3)


def _plot_merged_f4_spectral(ax: plt.Axes, spectral: SpectralPredictabilityResult | None) -> None:
    """Populate the F4 spectral score panel of the merged figure.

    Args:
        ax: Target axes.
        spectral: F4 spectral predictability result or ``None``.
    """
    if spectral is None:
        _plot_na_panel(ax, "F4: Spectral (unavailable)")
        ax.set_title("F4: Spectral Predictability", fontsize=10)
        return
    labels = ["Ω score", "H_norm"]
    values = [spectral.score, spectral.normalised_entropy]
    ax.barh(labels, values, color=["tab:cyan", "tab:pink"])
    ax.set_xlim(0, 1)
    ax.set_title(f"F4: Spectral  Ω={spectral.score:.3f}", fontsize=10)
    ax.grid(axis="x", alpha=0.3)


def _plot_merged_f5_lle(ax: plt.Axes, lle: LargestLyapunovExponentResult | None) -> None:
    """Populate the F5 LLE panel of the merged figure.

    Args:
        ax: Target axes.
        lle: F5 LLE result or ``None``.
    """
    if lle is None:
        _plot_na_panel(ax, "F5: LLE (unavailable)")
        ax.set_title("F5: LLE (EXPERIMENTAL)", fontsize=10)
        return
    lambda_val = lle.lambda_estimate
    is_valid = not np.isnan(lambda_val)
    bar_val = float(lambda_val) if is_valid else 0.0
    color = "tab:red" if (is_valid and lambda_val > 0) else "tab:green"
    ax.barh(["λ"], [bar_val], color=color)
    ax.axvline(0.0, color="grey", lw=0.8, ls="--")
    lambda_label = f"{lambda_val:.4f}" if is_valid else "NaN"
    ax.set_title(f"F5: LLE  λ={lambda_label}", fontsize=10)
    ax.grid(axis="x", alpha=0.3)


def _plot_merged_f6_complexity(ax: plt.Axes, complexity: ComplexityBandResult | None) -> None:
    """Populate the F6 complexity plane panel of the merged figure.

    Args:
        ax: Target axes.
        complexity: F6 complexity band result or ``None``.
    """
    if complexity is None:
        _plot_na_panel(ax, "F6: Complexity (unavailable)")
        ax.set_title("F6: Complexity Band", fontsize=10)
        return
    ax.scatter(
        [complexity.permutation_entropy],
        [complexity.spectral_entropy],
        s=80,
        color="tab:red",
        zorder=3,
    )
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("PE")
    ax.set_ylabel("SE")
    ax.set_title(
        f"F6: band={complexity.complexity_band}  PE={complexity.permutation_entropy:.3f}",
        fontsize=10,
    )
    ax.grid(alpha=0.3)


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------


def _rolling_summary_rows(rolling_result: SeriesEvaluationResult | None) -> str:
    """Build sMAPE horizon summary text for the report table.

    Args:
        rolling_result: Rolling evaluation result or ``None``.

    Returns:
        Human-readable string like ``"h=1: 2.1%, h=12: 4.8%"`` or
        ``"skipped"``.
    """
    if rolling_result is None:
        return "skipped"
    rows: list[str] = []
    for fr in rolling_result.forecast_results[:1]:  # first model only for table
        for h in sorted(fr.horizons):
            rows.append(f"h={h}: {fr.smape_by_horizon.get(h, 0.0):.1f}%")
    return ", ".join(rows) if rows else "n/a"


def _build_report(
    *,
    triage_result: TriageResult,
    canonical_result: CanonicalExampleResult,
    analyzer_result: AnalyzeResult,
    rolling_result: SeriesEvaluationResult | None,
    f1_profile: ForecastabilityProfile | None,
    f2_limits: TheoreticalLimitDiagnostics | None,
    f3_curve: PredictiveInfoLearningCurve | None,
    f4_spectral: SpectralPredictabilityResult | None,
    f5_lle: LargestLyapunovExponentResult | None,
    f6_complexity: ComplexityBandResult | None,
    agent_explanation: ShowcaseExplanation | None,
) -> str:
    """Assemble the showcase Markdown report as a string.

    Args:
        triage_result: M1 result.
        canonical_result: M2 result.
        analyzer_result: M3 result.
        rolling_result: M4 result or ``None``.
        f1_profile: F1 result or ``None``.
        f2_limits: F2 result or ``None``.
        f3_curve: F3 result or ``None``.
        f4_spectral: F4 result or ``None``.
        f5_lle: F5 result or ``None``.
        f6_complexity: F6 result or ``None``.
        agent_explanation: Bonus holistic explanation or ``None``.

    Returns:
        Markdown-formatted report string.
    """
    interp = triage_result.interpretation
    ar = triage_result.analyze_result
    fc_class = interp.forecastability_class if interp else "n/a"
    dir_class = interp.directness_class if interp else "n/a"
    regime = interp.modeling_regime if interp else "n/a"
    primary_lags = interp.primary_lags if interp else []
    sig_ami = ar.sig_raw_lags.tolist() if ar else []
    n_sig_ami = len(sig_ami)
    n_sig_pami = len(ar.sig_partial_lags) if ar else 0
    ami_auc = float(np.trapezoid(canonical_result.ami.values))
    pami_auc = float(np.trapezoid(canonical_result.pami.values))
    rolling_summary = _rolling_summary_rows(rolling_result)

    sections = [
        "# Air Passengers — Forecastability Showcase Report",
        _build_summary_table(
            fc_class=fc_class,
            sig_ami=sig_ami,
            ami_auc=ami_auc,
            pami_auc=pami_auc,
            rolling_summary=rolling_summary,
            f1_profile=f1_profile,
            f2_limits=f2_limits,
            f3_curve=f3_curve,
            f4_spectral=f4_spectral,
            f5_lle=f5_lle,
            f6_complexity=f6_complexity,
        ),
        _build_method1_section(
            fc_class=fc_class,
            dir_class=dir_class,
            regime=regime,
            primary_lags=primary_lags,
            sig_ami=sig_ami,
            n_sig_ami=n_sig_ami,
            n_sig_pami=n_sig_pami,
            recommendation=triage_result.recommendation or "n/a",
        ),
        _build_method2_section(
            canonical_result=canonical_result,
            ami_auc=ami_auc,
            pami_auc=pami_auc,
        ),
        _build_method3_section(analyzer_result=analyzer_result),
        _build_method4_section(rolling_result=rolling_result),
        _build_f1_section(f1_profile=f1_profile),
        _build_f2_section(f2_limits=f2_limits),
        _build_f3_section(f3_curve=f3_curve),
        _build_f4_section(f4_spectral=f4_spectral),
        _build_f5_section(f5_lle=f5_lle),
        _build_f6_section(f6_complexity=f6_complexity),
        _build_bonus_section(agent_explanation=agent_explanation),
    ]
    return "\n\n".join(sections)


def _build_summary_table(
    *,
    fc_class: str,
    sig_ami: list[int],
    ami_auc: float,
    pami_auc: float,
    rolling_summary: str,
    f1_profile: ForecastabilityProfile | None,
    f2_limits: TheoreticalLimitDiagnostics | None,
    f3_curve: PredictiveInfoLearningCurve | None,
    f4_spectral: SpectralPredictabilityResult | None,
    f5_lle: LargestLyapunovExponentResult | None,
    f6_complexity: ComplexityBandResult | None,
) -> str:
    """Build the summary table section of the report.

    Args:
        fc_class: Forecastability class string.
        sig_ami: Significant AMI lag list.
        ami_auc: AMI area under the curve.
        pami_auc: pAMI area under the curve.
        rolling_summary: Rolling origin summary string.
        f1_profile: F1 result or ``None``.
        f2_limits: F2 result or ``None``.
        f3_curve: F3 result or ``None``.
        f4_spectral: F4 result or ``None``.
        f5_lle: F5 result or ``None``.
        f6_complexity: F6 result or ``None``.

    Returns:
        Markdown table string.
    """
    f1_row = _f1_table_row(f1_profile)
    f2_row = _f2_table_row(f2_limits)
    f3_row = _f3_table_row(f3_curve)
    f4_row = _f4_table_row(f4_spectral)
    f5_row = _f5_table_row(f5_lle)
    f6_row = _f6_table_row(f6_complexity)
    return (
        "## Summary\n\n"
        "| Method | Key Finding |\n"
        "|---|---|\n"
        f"| M1: run_triage | Forecastability: {fc_class}, sig. lags: {sig_ami} |\n"
        f"| M2: Canonical AMI/pAMI | AMI AUC: {ami_auc:.2f}, pAMI AUC: {pami_auc:.2f} |\n"
        f"| M3: Analyzer | AMI AUC: {ami_auc:.2f}, pAMI AUC: {pami_auc:.2f} |\n"
        f"| M4: Rolling Origin | {rolling_summary} |\n"
        f"| F1: Profile | {f1_row} |\n"
        f"| F2: Ceiling | {f2_row} |\n"
        f"| F3: Learning Curve | {f3_row} |\n"
        f"| F4: Spectral | {f4_row} |\n"
        f"| F5: LLE (exp.) | {f5_row} |\n"
        f"| F6: Complexity | {f6_row} |"
    )


def _f1_table_row(f1_profile: ForecastabilityProfile | None) -> str:
    """Build the F1 summary table row value.

    Args:
        f1_profile: F1 result or ``None``.

    Returns:
        Table row value string.
    """
    if f1_profile is None:
        return "unavailable"
    n_inf = len(f1_profile.informative_horizons)
    return f"peak_h={f1_profile.peak_horizon}, n_informative={n_inf}"


def _f2_table_row(f2_limits: TheoreticalLimitDiagnostics | None) -> str:
    """Build the F2 summary table row value.

    Args:
        f2_limits: F2 result or ``None``.

    Returns:
        Table row value string.
    """
    if f2_limits is None:
        return "unavailable"
    ceilings = np.asarray(f2_limits.forecastability_ceiling_by_horizon)
    max_val = float(np.max(ceilings)) if ceilings.size > 0 else float("nan")
    return f"max_ceiling={max_val:.4f}"


def _f3_table_row(f3_curve: PredictiveInfoLearningCurve | None) -> str:
    """Build the F3 summary table row value.

    Args:
        f3_curve: F3 result or ``None``.

    Returns:
        Table row value string.
    """
    if f3_curve is None:
        return "unavailable"
    plateau = "yes" if f3_curve.plateau_detected else "no"
    return f"plateau={plateau}, recommended_k={f3_curve.recommended_lookback}"


def _f4_table_row(f4_spectral: SpectralPredictabilityResult | None) -> str:
    """Build the F4 summary table row value.

    Args:
        f4_spectral: F4 result or ``None``.

    Returns:
        Table row value string.
    """
    if f4_spectral is None:
        return "unavailable"
    return f"Ω={f4_spectral.score:.4f}"


def _f5_table_row(f5_lle: LargestLyapunovExponentResult | None) -> str:
    """Build the F5 summary table row value.

    Args:
        f5_lle: F5 result or ``None``.

    Returns:
        Table row value string.
    """
    if f5_lle is None:
        return "unavailable"
    lam = f"{f5_lle.lambda_estimate:.4f}" if not np.isnan(f5_lle.lambda_estimate) else "NaN"
    return f"λ={lam}"


def _f6_table_row(f6_complexity: ComplexityBandResult | None) -> str:
    """Build the F6 summary table row value.

    Args:
        f6_complexity: F6 result or ``None``.

    Returns:
        Table row value string.
    """
    if f6_complexity is None:
        return "unavailable"
    return f"band={f6_complexity.complexity_band}, PE={f6_complexity.permutation_entropy:.4f}"


def _build_method1_section(
    *,
    fc_class: str,
    dir_class: str,
    regime: str,
    primary_lags: list[int],
    sig_ami: list[int],
    n_sig_ami: int,
    n_sig_pami: int,
    recommendation: str,
) -> str:
    """Build the Method 1 section of the report.

    Args:
        fc_class: Forecastability class.
        dir_class: Directness class.
        regime: Modeling regime.
        primary_lags: Primary lag list.
        sig_ami: Significant AMI lags.
        n_sig_ami: Count of significant AMI lags.
        n_sig_pami: Count of significant pAMI lags.
        recommendation: Triage recommendation text.

    Returns:
        Markdown section string.
    """
    return (
        "## M1: run_triage\n\n"
        f"- **Forecastability class**: {fc_class}\n"
        f"- **Directness class**: {dir_class}\n"
        f"- **Modeling regime**: {regime}\n"
        f"- **Primary lags**: {primary_lags}\n"
        f"- **Significant AMI lags**: {sig_ami}\n"
        f"- **n_sig_ami**: {n_sig_ami}  |  **n_sig_pami**: {n_sig_pami}\n"
        f"- **Recommendation**: {recommendation}"
    )


def _build_method2_section(
    *,
    canonical_result: CanonicalExampleResult,
    ami_auc: float,
    pami_auc: float,
) -> str:
    """Build the Method 2 section of the report.

    Args:
        canonical_result: Canonical pipeline result.
        ami_auc: AMI area under the curve.
        pami_auc: pAMI area under the curve.

    Returns:
        Markdown section string.
    """
    ami_sig = canonical_result.ami.significant_lags
    pami_sig = canonical_result.pami.significant_lags
    n_sig_ami = int(ami_sig.size) if ami_sig is not None else 0
    n_sig_pami = int(pami_sig.size) if pami_sig is not None else 0
    peak_ami_lag = int(np.argmax(canonical_result.ami.values)) + 1
    peak_pami_lag = int(np.argmax(canonical_result.pami.values)) + 1

    return (
        "## M2: Canonical AMI/pAMI\n\n"
        f"- **AMI AUC**: {ami_auc:.3f}  |  **pAMI AUC**: {pami_auc:.3f}\n"
        f"- **Significant AMI lags**: {n_sig_ami}  |  **Significant pAMI lags**: {n_sig_pami}\n"
        f"- **Peak AMI lag**: {peak_ami_lag}  |  **Peak pAMI lag**: {peak_pami_lag}"
    )


def _build_method3_section(*, analyzer_result: AnalyzeResult) -> str:
    """Build the Method 3 section of the report.

    Args:
        analyzer_result: ForecastabilityAnalyzer result.

    Returns:
        Markdown section string.
    """
    auc_ami = float(np.trapezoid(analyzer_result.raw))
    auc_pami = float(np.trapezoid(analyzer_result.partial))
    return (
        "## M3: ForecastabilityAnalyzer\n\n"
        f"- **AMI AUC**: {auc_ami:.3f}  |  **pAMI AUC**: {auc_pami:.3f}\n"
        f"- **Recommendation**: {analyzer_result.recommendation}"
    )


def _build_method4_section(*, rolling_result: SeriesEvaluationResult | None) -> str:
    """Build the Method 4 section of the report.

    Args:
        rolling_result: Rolling-origin evaluation result or ``None``.

    Returns:
        Markdown section string.
    """
    if rolling_result is None:
        return "## M4: Rolling Origin\n\n_skipped (omit --no-rolling to enable)_"

    lines = ["## M4: Rolling Origin\n"]
    for fr in rolling_result.forecast_results:
        for h in sorted(fr.horizons):
            smape = fr.smape_by_horizon.get(h, 0.0)
            lines.append(f"- **{fr.model_name} h={h}**: {smape:.2f}%")
    return "\n".join(lines)


def _build_f1_section(*, f1_profile: ForecastabilityProfile | None) -> str:
    """Build the F1 section of the report.

    Args:
        f1_profile: Forecastability profile or ``None``.

    Returns:
        Markdown section string.
    """
    if f1_profile is None:
        return "## F1: Forecastability Profile\n\n_unavailable_"
    n_inf = len(f1_profile.informative_horizons)
    return (
        "## F1: Forecastability Profile\n\n"
        f"- **Peak horizon**: {f1_profile.peak_horizon}\n"
        f"- **n_informative**: {n_inf}  |  **is_non_monotone**: {f1_profile.is_non_monotone}\n"
        f"- **ε-threshold**: {f1_profile.epsilon:.4f}\n"
        f"- **Informative horizons**: {f1_profile.informative_horizons[:10]}\n"
        f"- **Summary**: {f1_profile.summary}\n"
        f"- **Model now**: {f1_profile.model_now}"
    )


def _build_f2_section(*, f2_limits: TheoreticalLimitDiagnostics | None) -> str:
    """Build the F2 section of the report.

    Args:
        f2_limits: Theoretical limit diagnostics or ``None``.

    Returns:
        Markdown section string.
    """
    if f2_limits is None:
        return "## F2: Theoretical Limit Diagnostics\n\n_unavailable_"
    ceilings = np.asarray(f2_limits.forecastability_ceiling_by_horizon)
    max_val = float(np.max(ceilings)) if ceilings.size > 0 else float("nan")
    lines = [
        "## F2: Theoretical Limit Diagnostics\n",
        f"- **Ceiling max (MI)**: {max_val:.4f}",
        f"- **n_horizons**: {ceilings.size}",
        f"- **Summary**: {f2_limits.ceiling_summary}",
    ]
    if f2_limits.compression_warning:
        lines.append(f"- **Compression warning**: {f2_limits.compression_warning}")
    if f2_limits.dpi_warning:
        lines.append(f"- **DPI warning**: {f2_limits.dpi_warning}")
    return "\n".join(lines)


def _build_f3_section(*, f3_curve: PredictiveInfoLearningCurve | None) -> str:
    """Build the F3 section of the report.

    Args:
        f3_curve: Predictive info learning curve or ``None``.

    Returns:
        Markdown section string.
    """
    if f3_curve is None:
        return "## F3: Predictive Info Learning Curve\n\n_unavailable_"
    plateau = "yes" if f3_curve.plateau_detected else "no"
    lines = [
        "## F3: Predictive Info Learning Curve\n",
        f"- **Plateau detected**: {plateau}",
        f"- **Recommended lookback**: k={f3_curve.recommended_lookback}",
        f"- **Window sizes**: {f3_curve.window_sizes}",
    ]
    for w in f3_curve.reliability_warnings:
        lines.append(f"- **Warning**: {w}")
    return "\n".join(lines)


def _build_f4_section(*, f4_spectral: SpectralPredictabilityResult | None) -> str:
    """Build the F4 section of the report.

    Args:
        f4_spectral: Spectral predictability result or ``None``.

    Returns:
        Markdown section string.
    """
    if f4_spectral is None:
        return "## F4: Spectral Predictability\n\n_unavailable_"
    return (
        "## F4: Spectral Predictability\n\n"
        f"- **Spectral score Ω**: {f4_spectral.score:.4f}\n"
        f"- **Normalised entropy H_norm**: {f4_spectral.normalised_entropy:.4f}\n"
        f"- **n_bins**: {f4_spectral.n_bins}  |  **detrend**: {f4_spectral.detrend}\n"
        f"- **Interpretation**: {f4_spectral.interpretation}"
    )


def _build_f5_section(*, f5_lle: LargestLyapunovExponentResult | None) -> str:
    """Build the F5 section of the report.

    Args:
        f5_lle: LLE result or ``None``.

    Returns:
        Markdown section string.
    """
    if f5_lle is None:
        return "## F5: Largest Lyapunov Exponent (EXPERIMENTAL)\n\n_unavailable_"
    lam = f"{f5_lle.lambda_estimate:.4f}" if not np.isnan(f5_lle.lambda_estimate) else "NaN"
    return (
        "## F5: Largest Lyapunov Exponent (EXPERIMENTAL)\n\n"
        f"- **λ estimate**: {lam}\n"
        f"- **embedding_dim**: {f5_lle.embedding_dim}  |  **delay**: {f5_lle.delay}\n"
        f"- **n_embedded**: {f5_lle.n_embedded_points}  |  "
        f"**evolution_steps**: {f5_lle.evolution_steps}\n"
        f"- **Interpretation**: {f5_lle.interpretation}\n"
        f"- **Warning**: {f5_lle.reliability_warning}"
    )


def _build_f6_section(*, f6_complexity: ComplexityBandResult | None) -> str:
    """Build the F6 section of the report.

    Args:
        f6_complexity: Complexity band result or ``None``.

    Returns:
        Markdown section string.
    """
    if f6_complexity is None:
        return "## F6: Complexity Band\n\n_unavailable_"
    lines = [
        "## F6: Complexity Band\n",
        f"- **Permutation entropy (PE)**: {f6_complexity.permutation_entropy:.4f}",
        f"- **Spectral entropy (SE)**: {f6_complexity.spectral_entropy:.4f}",
        f"- **Complexity band**: {f6_complexity.complexity_band}",
        f"- **Embedding order**: {f6_complexity.embedding_order}",
        f"- **Interpretation**: {f6_complexity.interpretation}",
    ]
    if f6_complexity.pe_reliability_warning:
        lines.append(f"- **Warning**: {f6_complexity.pe_reliability_warning}")
    return "\n".join(lines)


def _build_bonus_section(*, agent_explanation: ShowcaseExplanation | None) -> str:
    """Build the Bonus AI section of the report.

    Args:
        agent_explanation: Holistic LLM explanation or ``None``.

    Returns:
        Markdown section string.
    """
    if agent_explanation is None:
        return "## Bonus: Holistic AI Interpretation\n\n_not run (pass --agent to enable)_"

    findings_md = "\n".join(f"- {f}" for f in agent_explanation.key_findings)
    caveats_md = "\n".join(f"- {c}" for c in agent_explanation.caveats)
    return (
        "## Bonus: Holistic AI Interpretation\n\n"
        f"- **Overall forecastability**: {agent_explanation.overall_forecastability}\n\n"
        "### Key Findings\n\n"
        f"{findings_md}\n\n"
        "### Unified Recommendation\n\n"
        f"{agent_explanation.unified_recommendation}\n\n"
        "### Narrative\n\n"
        f"{agent_explanation.narrative}\n\n"
        "### Caveats\n\n"
        f"{caveats_md}"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run all showcase methods and persist artifacts.

    Orchestrates all ten methods (M1–M4, F1–F6), builds the merged 4×3
    figure, and writes the Markdown report to disk.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
    args = _parse_args()
    random_state: int = args.random_state
    output_root = Path(args.output_root)

    figures_dir, reports_dir = _ensure_dirs(output_root=output_root)
    ts = load_air_passengers()

    # Method 1
    triage_result = _run_method1(ts, random_state=random_state)
    _plot_triage_summary(triage_result, save_path=figures_dir / "triage_summary.png")

    # Method 2
    canonical_result = _run_method2(
        ts,
        skip_bands=args.no_bands,
        random_state=random_state,
        figures_dir=figures_dir,
    )

    # Method 3
    analyzer_result = _run_method3(ts, random_state=random_state)
    _plot_analyzer_comparison(analyzer_result, save_path=figures_dir / "analyzer_comparison.png")

    # Method 4 (optional)
    rolling_result: SeriesEvaluationResult | None = None
    if not args.no_rolling:
        rolling_result = _run_method4(ts, random_state=random_state)
        _plot_rolling_errors(rolling_result, save_path=figures_dir / "rolling_origin_errors.png")
    else:
        _print_section("Method 4 — Rolling Origin (SKIPPED via --no-rolling)")
        print("  Pass without --no-rolling to enable.")

    # F1 — Forecastability Profile (from triage_result, no rerun)
    f1_profile = _run_f1_profile(triage_result)
    if f1_profile is not None:
        _plot_f1_profile(f1_profile, save_path=figures_dir / "f1_forecastability_profile.png")

    # F2 — Theoretical Limit Diagnostics
    f2_limits = _run_f2_limits(triage_result)
    if f2_limits is not None:
        _plot_f2_limits(f2_limits, save_path=figures_dir / "f2_theoretical_limits.png")

    # F3 — Predictive Info Learning Curve
    f3_curve = _run_f3_learning_curve(ts, random_state=random_state)
    if f3_curve is not None:
        _plot_f3_learning_curve(f3_curve, save_path=figures_dir / "f3_learning_curve.png")

    # F4 — Spectral Predictability
    f4_spectral = _run_f4_spectral(ts)
    if f4_spectral is not None:
        _plot_f4_spectral(f4_spectral, save_path=figures_dir / "f4_spectral_predictability.png")

    # F5 — Largest Lyapunov Exponent (EXPERIMENTAL)
    f5_lle = _run_f5_lle(ts)
    if f5_lle is not None:
        _plot_f5_lle(f5_lle, save_path=figures_dir / "f5_lle.png")

    # F6 — Complexity Band
    f6_complexity = _run_f6_complexity(ts)
    if f6_complexity is not None:
        _plot_f6_complexity(f6_complexity, save_path=figures_dir / "f6_complexity_band.png")

    # BONUS (optional)
    agent_explanation: ShowcaseExplanation | None = None
    if args.agent:
        agent_explanation, agent_settings = _run_holistic_agent(
            ts=ts,
            triage_result=triage_result,
            canonical_result=canonical_result,
            analyzer_result=analyzer_result,
            rolling_result=rolling_result,
            f1_profile=f1_profile,
            f2_limits=f2_limits,
            f3_curve=f3_curve,
            f4_spectral=f4_spectral,
            f5_lle=f5_lle,
            f6_complexity=f6_complexity,
            random_state=random_state,
        )
        if agent_explanation is not None:
            _print_showcase_explanation(agent_explanation, agent_settings)
    else:
        _print_section("BONUS — Holistic AI Interpretation (SKIPPED)")
        print("  Pass --agent to enable (requires API key in .env).")

    # Merged figure (4×3)
    _print_section("Merged Comparison Figure (4×3)")
    _build_merged_figure(
        triage_result=triage_result,
        canonical_result=canonical_result,
        analyzer_result=analyzer_result,
        rolling_result=rolling_result,
        f1_profile=f1_profile,
        f2_limits=f2_limits,
        f3_curve=f3_curve,
        f4_spectral=f4_spectral,
        f5_lle=f5_lle,
        f6_complexity=f6_complexity,
        save_path=figures_dir / "showcase_merged.png",
    )

    # Report
    report_md = _build_report(
        triage_result=triage_result,
        canonical_result=canonical_result,
        analyzer_result=analyzer_result,
        rolling_result=rolling_result,
        f1_profile=f1_profile,
        f2_limits=f2_limits,
        f3_curve=f3_curve,
        f4_spectral=f4_spectral,
        f5_lle=f5_lle,
        f6_complexity=f6_complexity,
        agent_explanation=agent_explanation,
    )
    report_path = reports_dir / "showcase_report.md"
    report_path.write_text(report_md, encoding="utf-8")
    print(f"  → report saved {report_path}")

    print(f"\n{_SEP}\nShowcase complete.\n{_SEP}\n")


if __name__ == "__main__":
    main()
