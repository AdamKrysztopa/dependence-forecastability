"""Unified showcase runner: all forecastability surfaces on Air Passengers.

Demonstrates every public API surface on the Air Passengers dataset:

  1. run_triage       — deterministic fast triage
  2. run_canonical_example — full AMI/pAMI pipeline with significance bands
  3. ForecastabilityAnalyzer — multi-scorer comparison
  4. run_rolling_origin_evaluation — rolling-origin benchmark (skippable)
  5. run_triage_agent — LLM agentic interpretation (opt-in BONUS)

Usage::

    uv run scripts/run_showcase.py
    uv run scripts/run_showcase.py --no-rolling
    uv run scripts/run_showcase.py --no-rolling --agent

Artifacts are written to outputs/figures/showcase/ and
outputs/reports/showcase/.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

# Set non-interactive backend before any matplotlib import.
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np

from forecastability.pipeline import run_canonical_example, run_rolling_origin_evaluation
from forecastability.pipeline.analyzer import AnalyzeResult, ForecastabilityAnalyzer
from forecastability.triage.models import AnalysisGoal, TriageRequest, TriageResult
from forecastability.use_cases.run_triage import run_triage
from forecastability.utils.datasets import load_air_passengers
from forecastability.utils.plots import plot_canonical_result, save_all_canonical_plots
from forecastability.utils.types import CanonicalExampleResult, SeriesEvaluationResult

if TYPE_CHECKING:
    from forecastability.adapters.llm.triage_agent import TriageExplanation

_logger = logging.getLogger(__name__)

_SEP = "═" * 50
_SERIES_NAME = "air_passengers"


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
# BONUS — agentic interpretation
# ---------------------------------------------------------------------------


def _run_agent(
    ts: np.ndarray,
    *,
    random_state: int,
) -> tuple[TriageExplanation | None, object]:
    """Run the LLM triage agent and return the explanation.

    Imports are guarded so the script remains runnable without pydantic_ai.

    Args:
        ts: Target time series array.
        random_state: Reproducibility seed.

    Returns:
        Tuple of (:class:`TriageExplanation` or ``None``, :class:`InfraSettings`).
    """
    _print_section("BONUS — AI Agentic Interpretation  (run_triage_agent)")

    try:
        from forecastability.adapters.llm.triage_agent import run_triage_agent
        from forecastability.adapters.settings import InfraSettings

        settings = InfraSettings()
        explanation = asyncio.run(
            run_triage_agent(
                ts,
                max_lag=40,
                n_surrogates=99,
                random_state=random_state,
                settings=settings,
            )
        )
        return explanation, settings
    except Exception as exc:
        _logger.warning("Agent interpretation unavailable: %s", exc)
        print(f"  Agent unavailable: {exc}")
        return None, None


def _print_agent_result(explanation: TriageExplanation, settings: object) -> None:
    """Print the LLM triage explanation in the canonical console format.

    Args:
        explanation: Structured output from the triage agent.
        settings: :class:`InfraSettings` instance (used for model name).
    """
    # Resolve actual model: default path in create_triage_agent uses openai:<openai_model>
    if settings is not None:
        model_name = f"openai:{getattr(settings, 'openai_model', 'gpt-4o')}"
    else:
        model_name = "unknown"
    narrative_wrapped = textwrap.fill(explanation.narrative, width=80, subsequent_indent="  ")

    print(f"  Model: {model_name}")
    print(
        f"  Forecastability: {explanation.forecastability_class}"
        f"  |  Directness: {explanation.directness_class}"
    )
    print(f"  Primary lags: {explanation.primary_lags}")
    print(f"  Regime: {explanation.modeling_regime}")
    print(f"\n  Narrative:\n  {narrative_wrapped}")
    if explanation.caveats:
        print("\n  Caveats:")
        for caveat in explanation.caveats:
            print(f"  • {caveat}")


# ---------------------------------------------------------------------------
# Merged comparison figure (2×2)
# ---------------------------------------------------------------------------


def _build_merged_figure(
    *,
    triage_result: TriageResult,
    canonical_result: CanonicalExampleResult,
    analyzer_result: AnalyzeResult,
    rolling_result: SeriesEvaluationResult | None,
    save_path: Path,
) -> None:
    """Build a 2×2 merged comparison figure for all methods.

    Args:
        triage_result: Method 1 result.
        canonical_result: Method 2 result.
        analyzer_result: Method 3 result.
        rolling_result: Method 4 result; ``None`` when rolling was skipped.
        save_path: Destination path for the merged figure.
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Air Passengers — Forecastability Showcase", fontsize=14, fontweight="bold")

    _plot_merged_triage(axes[0, 0], triage_result)
    _plot_merged_canonical(axes[0, 1], canonical_result)
    _plot_merged_analyzer(axes[1, 0], analyzer_result)
    _plot_merged_rolling(axes[1, 1], rolling_result)

    plt.tight_layout()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  → merged figure saved {save_path}")


def _plot_merged_triage(ax: plt.Axes, result: TriageResult) -> None:
    """Populate the triage panel of the merged figure.

    Shows the AMI curve from run_triage with primary lags marked as vertical
    dashed lines and classification fields in the title.

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
        ax.text(0.5, 0.5, "n/a", ha="center", va="center", transform=ax.transAxes)
        ax.axis("off")

    ax.set_title(f"1. run_triage  (fc: {fc}, dir: {dir_class})", fontsize=10)


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
    ax.set_title("2. Canonical AMI/pAMI", fontsize=10)
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
    ax.set_title("3. ForecastabilityAnalyzer", fontsize=10)
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
        ax.text(
            0.5,
            0.5,
            "not run\n(omit --no-rolling to enable)",
            ha="center",
            va="center",
            fontsize=11,
            color="grey",
            transform=ax.transAxes,
        )
        ax.set_title("4. Rolling Origin (skipped)", fontsize=10)
        ax.axis("off")
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
    ax.set_title("4. Rolling Origin sMAPE", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)


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
    agent_explanation: TriageExplanation | None,
) -> str:
    """Assemble the showcase Markdown report as a string.

    Args:
        triage_result: Method 1 result.
        canonical_result: Method 2 result.
        analyzer_result: Method 3 result.
        rolling_result: Method 4 result or ``None``.
        agent_explanation: Bonus LLM explanation or ``None``.

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
) -> str:
    """Build the summary table section of the report.

    Args:
        fc_class: Forecastability class string.
        sig_ami: Significant AMI lag list.
        ami_auc: AMI area under the curve.
        pami_auc: pAMI area under the curve.
        rolling_summary: Rolling origin summary string.

    Returns:
        Markdown table string.
    """
    return (
        "## Summary\n\n"
        "| Method | Key Finding |\n"
        "|---|---|\n"
        f"| run_triage | Forecastability: {fc_class}, sig. lags: {sig_ami} |\n"
        f"| Canonical AMI/pAMI | AMI AUC: {ami_auc:.2f}, pAMI AUC: {pami_auc:.2f} |\n"
        f"| Analyzer | AMI AUC: {ami_auc:.2f}, pAMI AUC: {pami_auc:.2f} |\n"
        f"| Rolling Origin | {rolling_summary} |"
    )


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
        "## Method 1: run_triage\n\n"
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
        "## Method 2: Canonical AMI/pAMI\n\n"
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
        "## Method 3: ForecastabilityAnalyzer\n\n"
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
        return "## Method 4: Rolling Origin\n\n_skipped (omit --no-rolling to enable)_"

    lines = ["## Method 4: Rolling Origin\n"]
    for fr in rolling_result.forecast_results:
        for h in sorted(fr.horizons):
            smape = fr.smape_by_horizon.get(h, 0.0)
            lines.append(f"- **{fr.model_name} h={h}**: {smape:.2f}%")
    return "\n".join(lines)


def _build_bonus_section(*, agent_explanation: TriageExplanation | None) -> str:
    """Build the Bonus AI section of the report.

    Args:
        agent_explanation: LLM triage explanation or ``None``.

    Returns:
        Markdown section string.
    """
    if agent_explanation is None:
        return "## Bonus: AI Agentic Interpretation\n\n_not run (pass --agent to enable)_"

    caveats_md = "\n".join(f"- {c}" for c in agent_explanation.caveats)
    return (
        "## Bonus: AI Agentic Interpretation\n\n"
        f"- **Forecastability**: {agent_explanation.forecastability_class}\n"
        f"- **Directness**: {agent_explanation.directness_class}\n"
        f"- **Regime**: {agent_explanation.modeling_regime}\n"
        f"- **Primary lags**: {agent_explanation.primary_lags}\n\n"
        f"### Narrative\n\n{agent_explanation.narrative}\n\n"
        f"### Caveats\n\n{caveats_md}"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run all showcase methods and persist artifacts.

    Orchestrates all five methods, builds the merged figure, and writes
    the Markdown report to disk.
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

    # BONUS (optional)
    agent_explanation: TriageExplanation | None = None
    if args.agent:
        agent_explanation, agent_settings = _run_agent(ts, random_state=random_state)
        if agent_explanation is not None:
            _print_agent_result(agent_explanation, agent_settings)
    else:
        _print_section("BONUS — AI Agentic Interpretation (SKIPPED)")
        print("  Pass --agent to enable (requires API key in .env).")

    # Merged figure
    _print_section("Merged Comparison Figure")
    _build_merged_figure(
        triage_result=triage_result,
        canonical_result=canonical_result,
        analyzer_result=analyzer_result,
        rolling_result=rolling_result,
        save_path=figures_dir / "showcase_merged.png",
    )

    # Report
    report_md = _build_report(
        triage_result=triage_result,
        canonical_result=canonical_result,
        analyzer_result=analyzer_result,
        rolling_result=rolling_result,
        agent_explanation=agent_explanation,
    )
    report_path = reports_dir / "showcase_report.md"
    report_path.write_text(report_md, encoding="utf-8")
    print(f"  → report saved {report_path}")

    print(f"\n{_SEP}\nShowcase complete.\n{_SEP}\n")


if __name__ == "__main__":
    main()
