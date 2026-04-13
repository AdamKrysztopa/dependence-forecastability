"""A2 triage summary serialiser demo: converting triage results to versioned JSON envelopes.

Demonstrates how the A2 serialiser layer (triage_summary_serializer) wraps
deterministic triage payloads in versioned JSON-safe envelopes suitable for
agent consumers, APIs, and cross-system transport.

This example covers:
* serialise_payload()  — single payload → SerialisedTriageSummary
* serialise_batch()    — list of payloads → list[SerialisedTriageSummary]
* serialise_to_json()  — single payload → pretty JSON string
* serialise_batch_to_json() — batch → JSON array string
* Schema-version envelope inspection
* Batch contrast: AR(0.9), seasonal, white noise — F1/F2/F6 payload fields vs series type
* Matplotlib figure: 3-panel comparison of payloads across signal types

Usage:
    uv run python examples/triage/a2_triage_summary_serializer_demo.py
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import cast

import numpy as np

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt

from forecastability.adapters.agents.triage_agent_payload_models import (
    triage_agent_payload,
)
from forecastability.adapters.agents.triage_summary_serializer import (
    SerialisedTriageSummary,
    serialise_batch,
    serialise_batch_to_json,
    serialise_payload,
    serialise_to_json,
)
from forecastability.triage.models import TriageRequest, TriageResult
from forecastability.use_cases.run_triage import run_triage

_FIG_DIR = Path("outputs/figures/agent")
_JSON_DIR = Path("outputs/json")


# ---------------------------------------------------------------------------
# Signal generators
# ---------------------------------------------------------------------------


def _make_ar_series(phi: float, n: int, seed: int) -> np.ndarray:
    """Generate an AR(1) series with a fixed random seed.

    Args:
        phi: Autoregressive coefficient.
        n: Number of observations.
        seed: Random seed for reproducibility.

    Returns:
        1-D numpy float64 array of length n.
    """
    rng = np.random.default_rng(seed)
    series = np.zeros(n, dtype=float)
    series[0] = rng.standard_normal()
    for i in range(1, n):
        series[i] = phi * series[i - 1] + rng.standard_normal()
    return series


def _make_seasonal_series(period: int, n: int, seed: int) -> np.ndarray:
    """Generate a two-harmonic seasonal series with additive noise.

    Args:
        period: Dominant seasonal period.
        n: Number of observations.
        seed: Random seed for reproducibility.

    Returns:
        1-D numpy float64 array of length n.
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
        1-D numpy float64 array of length n.
    """
    return np.random.default_rng(seed).standard_normal(n)


# ---------------------------------------------------------------------------
# Triage helpers
# ---------------------------------------------------------------------------


def _run_triage(series: np.ndarray, series_id: str) -> TriageResult:
    """Run deterministic triage on a univariate series.

    Args:
        series: Univariate time series.
        series_id: Human-readable label (used in progress messages).

    Returns:
        Full domain TriageResult.
    """
    request = TriageRequest(series=series, random_state=42)
    result = run_triage(request)
    blocked_str = " [BLOCKED]" if result.blocked else ""
    print(f"  {series_id:>12}: readiness={result.readiness.status.value}{blocked_str}")
    return result


# ---------------------------------------------------------------------------
# Figure helpers
# ---------------------------------------------------------------------------


def _get_ami_values(result: TriageResult, n_horizons: int) -> np.ndarray:
    """Extract AMI profile values from a domain triage result.

    Returns zeros when the series was blocked or the profile is absent.

    Args:
        result: Domain triage result.
        n_horizons: Desired array length.

    Returns:
        1-D float64 array of length n_horizons.
    """
    if result.forecastability_profile is None:
        return np.zeros(n_horizons)
    vals: np.ndarray = result.forecastability_profile.values
    if len(vals) >= n_horizons:
        return vals[:n_horizons]
    return np.pad(vals, (0, n_horizons - len(vals)))


def _f1_fields(serialised: SerialisedTriageSummary) -> tuple[list[int], float]:
    """Extract informative_horizons and epsilon from a serialised TriageAgentPayload.

    Args:
        serialised: Versioned serialisation envelope wrapping a TriageAgentPayload.

    Returns:
        Tuple of (informative_horizons, epsilon); defaults to ([], 0.0) when absent.
    """
    f1 = serialised.payload.get("f1_profile")
    if not isinstance(f1, dict):
        return [], 0.0
    f1_typed = cast("dict[str, object]", f1)
    horizons_raw = f1_typed.get("informative_horizons")
    epsilon_raw = f1_typed.get("epsilon")
    horizons: list[int] = (
        [int(h) for h in horizons_raw if isinstance(h, (int, float))]
        if isinstance(horizons_raw, list)
        else []
    )
    epsilon: float = float(epsilon_raw) if isinstance(epsilon_raw, (int, float)) else 0.0
    return horizons, epsilon


def _plot_bar_panel(
    ax: plt.Axes,
    ami_values: np.ndarray,
    informative_horizons: list[int],
    epsilon: float,
    *,
    blocked: bool,
) -> None:
    """Render AMI bar chart onto an Axes for one signal panel.

    Informative horizons are coloured green; non-informative ones grey.
    A horizontal dashed red line marks epsilon when it is positive.

    Args:
        ax: Target Axes for the bar chart.
        ami_values: AMI values per horizon.
        informative_horizons: Horizons with AMI ≥ epsilon.
        epsilon: Significance threshold.
        blocked: When True, overlay a "BLOCKED" annotation.
    """
    horizons = list(range(1, len(ami_values) + 1))
    colors = ["green" if h in informative_horizons else "grey" for h in horizons]
    ax.bar(horizons, ami_values, color=colors, alpha=0.75, edgecolor="white", linewidth=0.5)
    if epsilon > 0:
        ax.axhline(epsilon, color="red", linestyle="--", linewidth=1.2, label=f"ε = {epsilon:.3f}")
        ax.legend(fontsize=8)
    if blocked:
        ax.text(
            0.5,
            0.5,
            "BLOCKED" if blocked else "NO PROFILE",
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=14,
            color="crimson",
            alpha=0.65,
            fontweight="bold",
        )
    ax.set_xlabel("Horizon h", fontsize=9)
    ax.set_ylabel("AMI", fontsize=9)
    ax.tick_params(labelsize=8)


def _plot_annotation_row(
    ax: plt.Axes,
    serialised: SerialisedTriageSummary,
) -> None:
    """Render schema-envelope summary text onto an Axes.

    Args:
        ax: Target Axes (axis turned off; text only).
        serialised: Serialised triage summary envelope.
    """
    payload = serialised.payload
    fc_class = payload.get("forecastability_class") or "N/A"
    complexity_band: object = "N/A"
    f6 = payload.get("f6_complexity")
    if isinstance(f6, dict):
        f6_typed = cast("dict[str, object]", f6)
        complexity_band = f6_typed.get("complexity_band") or "N/A"
    lines = [
        f"fc_class: {fc_class}",
        f"complexity: {complexity_band}",
        f"schema_v: {serialised.schema_version} | type: {serialised.payload_type}",
    ]
    ax.axis("off")
    ax.text(
        0.5,
        0.5,
        "\n".join(lines),
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=8,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "#f3f3f3", "edgecolor": "#bbbbbb"},
    )


def _make_figure(
    signal_names: list[str],
    results: list[TriageResult],
    serialised_list: list[SerialisedTriageSummary],
) -> None:
    """Create and save the 3-panel A2 serialiser comparison figure.

    Each panel shows:
    * Upper: AMI profile bar chart coloured by informative-horizon membership.
    * Lower: Schema-envelope annotation (fc_class, complexity_band, schema_version).

    Args:
        signal_names: Display label for each panel.
        results: Domain triage results aligned with signal_names.
        serialised_list: Serialised envelopes aligned with signal_names.
    """
    n = len(signal_names)
    fig, axes = plt.subplots(
        2,
        n,
        figsize=(5.2 * n, 5.5),
        gridspec_kw={"height_ratios": [4, 1]},
    )
    fig.subplots_adjust(hspace=0.08, wspace=0.35)

    for i, (name, result, serialised) in enumerate(
        zip(signal_names, results, serialised_list, strict=True)
    ):
        inf_horizons, epsilon = _f1_fields(serialised)
        blocked = bool(serialised.payload.get("blocked", False))
        n_horizons = (
            len(result.forecastability_profile.values)
            if result.forecastability_profile is not None
            else 12
        )
        ami_values = _get_ami_values(result, n_horizons)

        ax_bar: plt.Axes = axes[0, i]
        _plot_bar_panel(ax_bar, ami_values, inf_horizons, epsilon, blocked=blocked)
        ax_bar.set_title(name, fontsize=10, fontweight="bold")

        ax_ann: plt.Axes = axes[1, i]
        _plot_annotation_row(ax_ann, serialised)

    fig.suptitle(
        "A2 Serialiser Demo — Payload Comparison Across Signal Types",
        fontsize=12,
        fontweight="bold",
        y=1.01,
    )
    _FIG_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _FIG_DIR / "a2_serialiser_demo.png"
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  [Figure] Saved → {out_path}")


# ---------------------------------------------------------------------------
# Demo sections
# ---------------------------------------------------------------------------


def _section1(result: TriageResult) -> None:
    """Section 1: Single payload serialisation with serialise_payload / serialise_to_json.

    Args:
        result: Domain triage result for the AR(0.9) series.
    """
    print("\n" + "=" * 62)
    print("SECTION 1 — Single payload serialisation  (ar09, AR φ=0.9)")
    print("=" * 62)

    payload = triage_agent_payload(result, series_id="ar09")
    serialised = serialise_payload(payload)

    print(f"  schema_version        : {serialised.schema_version}")
    print(f"  payload_type          : {serialised.payload_type}")
    print(f"  serialised_at         : {serialised.serialised_at}")
    print(f"  forecastability_class : {serialised.payload.get('forecastability_class')}")
    print(f"  blocked               : {serialised.payload.get('blocked')}")
    print(f"  readiness_status      : {serialised.payload.get('readiness_status')}")

    json_str = serialise_to_json(payload)
    _JSON_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _JSON_DIR / "a2_serialised_ar09.json"
    out_path.write_text(json_str, encoding="utf-8")
    print(f"\n  [JSON] serialise_to_json → {out_path}")


def _section2(
    names: list[str],
    results: list[TriageResult],
) -> list[SerialisedTriageSummary]:
    """Section 2: Batch serialisation with serialise_batch / serialise_batch_to_json.

    Args:
        names: Signal labels aligned with results.
        results: Domain triage results for all three signals.

    Returns:
        List of SerialisedTriageSummary for downstream figure use.
    """
    print("\n" + "=" * 62)
    print("SECTION 2 — Batch serialisation  (all 3 signals)")
    print("=" * 62)

    payloads = [triage_agent_payload(r, series_id=n) for n, r in zip(names, results, strict=True)]
    batch: list[SerialisedTriageSummary] = serialise_batch(payloads)
    batch_json = serialise_batch_to_json(payloads)

    _JSON_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _JSON_DIR / "a2_serialised_batch.json"
    out_path.write_text(batch_json, encoding="utf-8")
    print(f"  [JSON] serialise_batch_to_json → {out_path}\n")

    hdr = f"  {'Series':<14} | {'Blocked':<7} | {'FC Class':<22} | {'Schema':<8} | Payload Type"
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for name, s in zip(names, batch, strict=True):
        blocked = str(s.payload.get("blocked"))
        fc = str(s.payload.get("forecastability_class") or "—")
        print(f"  {name:<14} | {blocked:<7} | {fc:<22} | {s.schema_version:<8} | {s.payload_type}")

    return batch


def _section3(
    names: list[str],
    results: list[TriageResult],
) -> None:
    """Section 3: F1ProfilePayload serialised individually from triage_agent_payload.

    Extracts and serialises the F1 sub-payload for each signal that produced a
    forecastability profile, demonstrating that serialise_payload works on any
    A1 payload type, not just the top-level TriageAgentPayload.

    Args:
        names: Signal labels aligned with results.
        results: Domain triage results.
    """
    print("\n" + "=" * 62)
    print("SECTION 3 — F1ProfilePayload individual serialisation")
    print("=" * 62)

    for name, result in zip(names, results, strict=True):
        payload = triage_agent_payload(result, series_id=name)
        if payload.f1_profile is None:
            print(f"\n  [{name}] No F1 profile — skipped (series may be blocked).")
            continue
        serialised = serialise_payload(payload.f1_profile)
        print(f"\n  [{name}]")
        print(f"    informative_horizons : {serialised.payload.get('informative_horizons')}")
        print(f"    profile_shape_label  : {serialised.payload.get('profile_shape_label')}")
        print(f"    schema_version       : {serialised.schema_version}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the full A2 triage summary serialiser demonstration."""
    print("=== A2 Triage Summary Serialiser Demo ===\n")

    ar09 = _make_ar_series(phi=0.9, n=500, seed=42)
    seasonal = _make_seasonal_series(period=12, n=600, seed=7)
    white_noise = _make_white_noise(n=400, seed=99)

    names: list[str] = ["ar09", "seasonal", "white_noise"]
    series_list: list[np.ndarray] = [ar09, seasonal, white_noise]

    print("Running triage (3 signals, n_surrogates=99)…")
    results: list[TriageResult] = [
        _run_triage(s, n) for n, s in zip(names, series_list, strict=True)
    ]

    _section1(results[0])
    batch = _section2(names, results)
    _section3(names, results)

    print("\n" + "=" * 62)
    print("SECTION 4 — Figure")
    print("=" * 62)
    _make_figure(names, results, batch)

    print("\n=== Demo complete ===")


if __name__ == "__main__":
    main()
