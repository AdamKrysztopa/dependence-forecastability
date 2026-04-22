"""Fingerprint agent payload demo: FingerprintBundle → agent-ready payloads.

Demonstrates the V3_1-F05.1 agent adapter layer:

* A1: :func:`fingerprint_agent_payload` — builds a strict JSON-safe payload
* A2: :func:`serialise_fingerprint_payload` / :func:`serialise_fingerprint_to_json`
  — wraps the payload in a versioned transport envelope
* A3: :func:`interpret_fingerprint_payload` — builds a deterministic human-readable
  interpretation without any LLM narration

Four synthetic archetypes from :mod:`forecastability.utils.synthetic` are used
as inputs so that each stage of the adapter pipeline is observable on series with
distinct forecastability profiles.

Outputs:
* Console tables for each archetype: fingerprint fields, routing, payload, A3 narrative
* JSON files under ``outputs/json/examples/univariate/agents/``
* Matplotlib 2×2 bar chart saved to
  ``outputs/figures/examples/univariate/agents/fingerprint_agent_payload_demo.png``

Usage:
    uv run python examples/univariate/agents/fingerprint_agent_payload_demo.py
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt

from forecastability.adapters.agents.fingerprint_agent_interpretation_adapter import (
    FingerprintAgentInterpretation,
    interpret_fingerprint_payload,
)
from forecastability.adapters.agents.fingerprint_agent_payload_models import (
    FingerprintAgentPayload,
    fingerprint_agent_payload,
)
from forecastability.adapters.agents.fingerprint_summary_serializer import (
    serialise_fingerprint_to_json,
)
from forecastability.use_cases.run_forecastability_fingerprint import (
    run_forecastability_fingerprint,
)
from forecastability.utils.synthetic import generate_fingerprint_archetypes
from forecastability.utils.types import FingerprintBundle

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_N: int = 600
_SEED: int = 42
_MAX_LAG: int = 24
_N_SURROGATES: int = 99

_FIG_DIR = Path("outputs/figures/examples/univariate/agents")
_JSON_DIR = Path("outputs/json/examples/univariate/agents")

_ARCHETYPES: dict[str, str] = {
    "white_noise": "Expected: low mass + fallback routing; avoid over-asserting structure",
    "ar1_monotonic": "Expected: none/monotonic structure with route-family consistency",
    "seasonal_periodic": "Expected: periodic structure, seasonal families",
    "nonlinear_mixed": "Expected: non-trivial signal; fail transparently if power is weak",
}

_LINEAR_FAMILIES: frozenset[str] = frozenset(
    {"arima", "ets", "linear_state_space", "dynamic_regression"}
)
_SEASONAL_FAMILIES: frozenset[str] = frozenset(
    {"tbats", "seasonal_state_space", "harmonic_regression", "seasonal_naive"}
)
_NONLINEAR_FAMILIES: frozenset[str] = frozenset(
    {"tree_on_lags", "tcn", "nbeats", "nhits", "nonlinear_tabular"}
)
_FALLBACK_FAMILIES: frozenset[str] = frozenset({"naive", "seasonal_naive", "downscope"})


@dataclass(frozen=True)
class _GeometryDiagnostics:
    """Deterministic geometry diagnostics mirrored into the agent payload."""

    method: str
    signal_to_noise: float
    information_horizon: int
    information_structure: str
    informative_horizons: list[int]
    threshold_borderline: bool


@dataclass(frozen=True)
class _ArchetypeRun:
    """Aggregated deterministic outputs for one archetype run."""

    bundle: FingerprintBundle
    payload: FingerprintAgentPayload
    interpretation: FingerprintAgentInterpretation
    geometry: _GeometryDiagnostics


@dataclass(frozen=True)
class _VerificationIssue:
    """Typed issue emitted by demo verification."""

    category: Literal["power_shortfall", "behavioral_contradiction"]
    message: str


# ---------------------------------------------------------------------------
# Series generators
# ---------------------------------------------------------------------------


def _build_series_map(*, n: int, seed: int) -> dict[str, np.ndarray]:
    """Generate the four canonical fingerprint archetype series.

    Args:
        n: Number of time steps per series.
        seed: Integer random seed for reproducibility.

    Returns:
        Ordered mapping from archetype name to 1-D numpy array.
    """
    return generate_fingerprint_archetypes(n=n, seed=seed)


# ---------------------------------------------------------------------------
# Payload pipeline
# ---------------------------------------------------------------------------


def _run_pipeline(
    name: str,
    series: np.ndarray,
) -> _ArchetypeRun:
    """Run the full A1 → A2 → A3 adapter pipeline for one archetype.

    Args:
        name: Archetype label.
        series: 1-D time series array.

    Returns:
        Aggregated deterministic run outputs.
    """
    bundle = run_forecastability_fingerprint(
        series,
        target_name=name,
        max_lag=_MAX_LAG,
        n_surrogates=_N_SURROGATES,
        random_state=_SEED,
    )
    payload = fingerprint_agent_payload(bundle, narrative=None)  # strict mode
    interpretation = interpret_fingerprint_payload(payload)
    geometry = _compute_geometry_diagnostics(bundle=bundle)
    return _ArchetypeRun(
        bundle=bundle,
        payload=payload,
        interpretation=interpretation,
        geometry=geometry,
    )


def _compute_geometry_diagnostics(
    *,
    bundle: FingerprintBundle,
) -> _GeometryDiagnostics:
    """Collect the canonical geometry outputs for transparent diagnostics.

    Args:
        bundle: Deterministic fingerprint bundle.

    Returns:
        Geometry diagnostics derived directly from the bundle contract.
    """
    geometry = bundle.geometry
    return _GeometryDiagnostics(
        method=str(geometry.method),
        signal_to_noise=geometry.signal_to_noise,
        information_horizon=geometry.information_horizon,
        information_structure=str(geometry.information_structure),
        informative_horizons=list(geometry.informative_horizons),
        threshold_borderline=bool(geometry.metadata.get("geometry_threshold_borderline", 0)),
    )


def _contains_any(families: list[str], allowed: frozenset[str]) -> bool:
    """Return True when at least one family label belongs to allowed set."""
    return any(f in allowed for f in families)


# ---------------------------------------------------------------------------
# Console reporting
# ---------------------------------------------------------------------------


def _print_archetype_report(
    name: str,
    run: _ArchetypeRun,
) -> None:
    """Print a formatted report for one archetype.

    Args:
        name: Archetype label.
        run: Aggregated deterministic run outputs.
    """
    payload = run.payload
    interpretation = run.interpretation
    geometry = run.geometry

    separator = "─" * 68
    print(f"\n{separator}")
    print(f"  ARCHETYPE: {name.upper()}")
    print(f"  Hint: {_ARCHETYPES[name]}")
    print(separator)

    print("\n  ── Geometry (deterministic) ──────────────────────────────")
    print(f"  geometry_method       : {payload.geometry_method}")
    print(f"  signal_to_noise       : {payload.signal_to_noise:.6f}")
    print(f"  geometry_horizon      : {payload.geometry_information_horizon}")
    print(f"  geometry_structure    : {payload.geometry_information_structure}")
    print(f"  informative_horizons  : {geometry.informative_horizons}")
    print(f"  threshold_borderline  : {geometry.threshold_borderline}")

    print("\n  ── Fingerprint (A1) ──────────────────────────────────────")
    print(f"  information_mass      : {payload.information_mass:.6f}")
    print(f"  information_horizon   : {payload.information_horizon}")
    print(f"  information_structure : {payload.information_structure}")
    print(f"  nonlinear_share       : {payload.nonlinear_share:.6f}")
    print(f"  directness_ratio      : {payload.directness_ratio}")
    print(f"  informative_horizons  : {payload.informative_horizons}")

    print("\n  ── Routing (A1) ──────────────────────────────────────────")
    print(f"  primary_families      : {payload.primary_families}")
    print(f"  secondary_families    : {payload.secondary_families}")
    print(f"  confidence_label      : {payload.confidence_label}")
    print(f"  caution_flags         : {payload.caution_flags}")
    for r in payload.rationale:
        print(f"    • {r}")

    print("\n  ── Deterministic Summary (A3) ────────────────────────────")
    print(f"  {interpretation.deterministic_summary}")
    if interpretation.rich_signal_narrative:
        print(f"\n  Rich signal:\n    {interpretation.rich_signal_narrative}")
    if interpretation.cautionary_narrative:
        print(f"\n  Cautionary:\n    {interpretation.cautionary_narrative}")


def _print_cross_archetype_summary(
    results: dict[str, _ArchetypeRun],
) -> None:
    """Print a cross-archetype comparison table.

    Args:
        results: Mapping from archetype name to (payload, interpretation) tuple.
    """
    print("\n" + "═" * 80)
    print("  CROSS-ARCHETYPE SUMMARY")
    print("═" * 80)
    header = (
        f"  {'Archetype':<22} {'Geom':<12} {'S/N':>7} {'Mass':>8}"
        f" {'NL Share':>9} {'Confidence':<12} {'Route'}"
    )
    print(header)
    print("  " + "─" * 76)
    for name, run in results.items():
        payload = run.payload
        families = ", ".join(payload.primary_families[:2]) if payload.primary_families else "none"
        print(
            f"  {name:<22} {payload.geometry_information_structure:<12} "
            f"{payload.signal_to_noise:>7.4f} {payload.information_mass:>8.4f} "
            f"{payload.nonlinear_share:>9.4f} "
            f"{payload.confidence_label:<12} {families}"
        )


# ---------------------------------------------------------------------------
# JSON artifacts
# ---------------------------------------------------------------------------


def _save_json_artifacts(
    results: dict[str, _ArchetypeRun],
    *,
    json_dir: Path,
) -> None:
    """Save A2 serialised envelopes and A3 interpretations to JSON files.

    Args:
        results: Mapping from archetype name to (payload, interpretation) pair.
        json_dir: Output directory for JSON files.
    """
    json_dir.mkdir(parents=True, exist_ok=True)

    for name, run in results.items():
        payload = run.payload
        interpretation = run.interpretation
        # A2 envelope
        a2_path = json_dir / f"fingerprint_{name}_a2_serialised.json"
        a2_path.write_text(serialise_fingerprint_to_json(payload), encoding="utf-8")

        # A3 interpretation
        a3_path = json_dir / f"fingerprint_{name}_a3_interpretation.json"
        a3_path.write_text(json.dumps(interpretation.model_dump(), indent=2), encoding="utf-8")

    print(f"\n  JSON artifacts saved to: {json_dir.resolve()}")


# ---------------------------------------------------------------------------
# Matplotlib figure
# ---------------------------------------------------------------------------


def _save_figure(
    results: dict[str, _ArchetypeRun],
    *,
    fig_dir: Path,
) -> None:
    """Save a 2×2 bar chart comparing fingerprint metrics across archetypes.

    Args:
        results: Mapping from archetype name to (payload, interpretation) pair.
        fig_dir: Output directory for the figure.
    """
    fig_dir.mkdir(parents=True, exist_ok=True)

    names = list(results.keys())
    payloads = [results[n].payload for n in names]

    mass_vals = [p.information_mass for p in payloads]
    horizon_vals = [float(p.geometry_information_horizon) for p in payloads]
    nl_vals = [p.nonlinear_share for p in payloads]
    signal_vals = [p.signal_to_noise for p in payloads]

    colors = ["#4C72B0", "#DD8452", "#55A868", "#C44E52"]
    x = np.arange(len(names))
    width = 0.6

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle("Fingerprint Agent Payload — Cross-Archetype Comparison", fontsize=14, y=1.01)

    panels = [
        (axes[0, 0], mass_vals, "information_mass", "Normalised masked AMI area"),
        (axes[0, 1], horizon_vals, "geometry_horizon", "Latest geometry horizon"),
        (axes[1, 0], nl_vals, "nonlinear_share", "Fraction of AMI above linear baseline"),
        (axes[1, 1], signal_vals, "signal_to_noise", "Corrected AMI above surrogate noise"),
    ]

    for ax, vals, title, ylabel in panels:
        bars = ax.bar(x, vals, width=width, color=colors)
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.set_xticks(x)
        ax.set_xticklabels([n.replace("_", "\n") for n in names], fontsize=9)
        ax.bar_label(bars, fmt="%.3f", padding=3, fontsize=8)
        ax.set_ylim(bottom=0)
        ax.grid(axis="y", linestyle="--", alpha=0.4)

    fig.tight_layout()
    out_path = fig_dir / "fingerprint_agent_payload_demo.png"
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  Figure saved to: {out_path.resolve()}")


# ---------------------------------------------------------------------------
# Verification against expected routing
# ---------------------------------------------------------------------------


def _verify_routing(
    results: dict[str, _ArchetypeRun],
) -> None:
    """Print payload parity and routing verification against expected behaviour.

    Args:
        results: Mapping from archetype name to (payload, interpretation) pair.
    """
    print("\n  ── Payload Verification ──────────────────────────────────")
    all_passed = True

    for name, run in results.items():
        issues = _verify_payload_parity(run=run)
        issues.extend(_verify_archetype(name=name, run=run))
        if issues:
            all_passed = False
            for issue in issues:
                tag = "POWER" if issue.category == "power_shortfall" else "CONTRADICTION"
                print(f"  [MISMATCH][{tag}] {name}: {issue.message}")
        else:
            print(f"  [OK]       {name}: routing consistent with expected behaviour")

    if all_passed:
        print("\n  ✓ All routing checks passed.")
    else:
        print("\n  ⚠ Some routing checks produced mismatches — review above.")


def _verify_payload_parity(*, run: _ArchetypeRun) -> list[_VerificationIssue]:
    """Verify that the A1 payload mirrors the deterministic bundle exactly."""
    payload = run.payload
    bundle = run.bundle
    geometry = bundle.geometry
    fingerprint = bundle.fingerprint
    recommendation = bundle.recommendation
    issues: list[_VerificationIssue] = []

    numeric_pairs = [
        ("signal_to_noise", payload.signal_to_noise, geometry.signal_to_noise),
        ("information_mass", payload.information_mass, fingerprint.information_mass),
        ("nonlinear_share", payload.nonlinear_share, fingerprint.nonlinear_share),
    ]
    for label, actual, expected in numeric_pairs:
        if not math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9):
            issues.append(
                _VerificationIssue(
                    category="behavioral_contradiction",
                    message=f"payload {label} mismatch: expected {expected}, got {actual}",
                )
            )

    exact_pairs = [
        ("geometry_method", payload.geometry_method, str(geometry.method)),
        (
            "geometry_information_horizon",
            payload.geometry_information_horizon,
            geometry.information_horizon,
        ),
        (
            "geometry_information_structure",
            payload.geometry_information_structure,
            str(geometry.information_structure),
        ),
        ("information_horizon", payload.information_horizon, fingerprint.information_horizon),
        (
            "information_structure",
            payload.information_structure,
            str(fingerprint.information_structure),
        ),
        ("primary_families", payload.primary_families, list(recommendation.primary_families)),
        ("secondary_families", payload.secondary_families, list(recommendation.secondary_families)),
        ("caution_flags", payload.caution_flags, list(recommendation.caution_flags)),
        ("confidence_label", payload.confidence_label, str(recommendation.confidence_label)),
    ]
    for label, actual, expected in exact_pairs:
        if actual != expected:
            issues.append(
                _VerificationIssue(
                    category="behavioral_contradiction",
                    message=f"payload {label} mismatch: expected {expected}, got {actual}",
                )
            )

    return issues


def _verify_archetype(*, name: str, run: _ArchetypeRun) -> list[_VerificationIssue]:
    """Return verification issues for one archetype.

    Args:
        name: Archetype label.
        run: Aggregated deterministic run outputs.

    Returns:
        Categorised mismatch list.
    """
    payload = run.payload
    all_families = payload.primary_families + payload.secondary_families
    issues: list[_VerificationIssue] = []

    if name == "white_noise":
        if payload.information_mass > 0.08:
            issues.append(
                _VerificationIssue(
                    category="behavioral_contradiction",
                    message=(
                        "expected low information_mass for white noise "
                        f"(<= 0.08), got {payload.information_mass:.4f}"
                    ),
                )
            )
        if not _contains_any(all_families, _FALLBACK_FAMILIES):
            issues.append(
                _VerificationIssue(
                    category="behavioral_contradiction",
                    message=(
                        f"expected fallback routing families for white noise, got {all_families}"
                    ),
                )
            )
        if payload.information_mass > 0.03 and payload.information_structure in {
            "monotonic",
            "periodic",
        }:
            issues.append(
                _VerificationIssue(
                    category="behavioral_contradiction",
                    message=(
                        "structure_not violated for white noise: expected not in "
                        f"['monotonic', 'periodic'], got {payload.information_structure!r}"
                    ),
                )
            )

    if name == "ar1_monotonic":
        if payload.information_structure not in {"none", "monotonic", "mixed"}:
            issues.append(
                _VerificationIssue(
                    category="behavioral_contradiction",
                    message=(
                        "expected structure in ['none', 'monotonic', 'mixed'] for AR(1), "
                        f"got {payload.information_structure!r}"
                    ),
                )
            )
        if payload.information_structure in {"monotonic", "mixed"} and not _contains_any(
            all_families, _LINEAR_FAMILIES
        ):
            issues.append(
                _VerificationIssue(
                    category="behavioral_contradiction",
                    message=(
                        "AR(1) structure implies linear families should be routed, "
                        f"got {all_families}"
                    ),
                )
            )
        if payload.information_structure == "none" and payload.information_mass <= 0.02:
            issues.append(
                _VerificationIssue(
                    category="power_shortfall",
                    message=(
                        "AR(1) collapsed to none with near-zero mass; likely statistical "
                        "power shortfall rather than routing contradiction"
                    ),
                )
            )

    if name == "seasonal_periodic":
        if payload.information_structure not in {"periodic", "mixed", "monotonic"}:
            issues.append(
                _VerificationIssue(
                    category="behavioral_contradiction",
                    message=(
                        "expected seasonal structure in ['periodic', 'mixed', 'monotonic'], "
                        f"got {payload.information_structure!r}"
                    ),
                )
            )
        if not _contains_any(all_families, _SEASONAL_FAMILIES):
            issues.append(
                _VerificationIssue(
                    category="behavioral_contradiction",
                    message=(
                        "expected at least one seasonal family for seasonal archetype, "
                        f"got {all_families}"
                    ),
                )
            )

    if name == "nonlinear_mixed":
        informative_count = len(run.geometry.informative_horizons)
        if payload.information_mass < 0.02 or informative_count < 2:
            issues.append(
                _VerificationIssue(
                    category="power_shortfall",
                    message=(
                        "nonlinear archetype has weak informative support "
                        "(mass="
                        f"{payload.information_mass:.4f}, "
                        f"informative_count={informative_count})"
                    ),
                )
            )
        elif payload.nonlinear_share < 0.08 and not _contains_any(
            all_families, _NONLINEAR_FAMILIES
        ):
            issues.append(
                _VerificationIssue(
                    category="behavioral_contradiction",
                    message=(
                        "nonlinear archetype lacks nonlinear evidence and nonlinear routing "
                        f"(nonlinear_share={payload.nonlinear_share:.4f}, families={all_families})"
                    ),
                )
            )

    return issues


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the full fingerprint agent payload demo."""
    print("=" * 68)
    print("  FINGERPRINT AGENT PAYLOAD DEMO  (V3_1-F05.1)")
    print("  Strict deterministic mode — no LLM required")
    print("=" * 68)

    series_map = _build_series_map(n=_N, seed=_SEED)

    results: dict[str, _ArchetypeRun] = {}
    for name, series in series_map.items():
        print(f"\n  Computing fingerprint for: {name} …")
        results[name] = _run_pipeline(name, series)

    for name, run in results.items():
        _print_archetype_report(name, run)

    _print_cross_archetype_summary(results)
    _verify_routing(results)
    _save_json_artifacts(results, json_dir=_JSON_DIR)
    _save_figure(results, fig_dir=_FIG_DIR)

    print("\n" + "=" * 68)
    print("  Demo complete.")
    print("=" * 68)


if __name__ == "__main__":
    main()
