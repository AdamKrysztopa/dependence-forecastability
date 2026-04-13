"""A3 deterministic triage interpretation adapter demo.

Runs deterministic triage on three distinct signal types, converts results to A1
payloads, derives A3 interpretations (including A2 envelope support), and saves
JSON and figure artifacts for review.

Usage:
    uv run python examples/triage/a3_triage_interpretation_adapter_demo.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt

from forecastability.adapters.agents.triage_agent_interpretation_adapter import (
    TriageAgentInterpretation,
    interpret_batch,
)
from forecastability.adapters.agents.triage_agent_payload_models import (
    TriageAgentPayload,
    triage_agent_payload,
)
from forecastability.adapters.agents.triage_summary_serializer import serialise_batch
from forecastability.triage.models import TriageRequest, TriageResult
from forecastability.use_cases.run_triage import run_triage

_FIG_DIR = Path("outputs/figures/agent")
_JSON_DIR = Path("outputs/json")


def _make_ar_series(phi: float, n: int, seed: int) -> np.ndarray:
    """Generate deterministic AR(1) series.

    Args:
        phi: Autoregressive coefficient.
        n: Number of observations.
        seed: Random seed for deterministic behavior.

    Returns:
        1-D float64 array.
    """
    rng = np.random.default_rng(seed)
    series = np.zeros(n, dtype=float)
    series[0] = rng.standard_normal()
    for idx in range(1, n):
        series[idx] = phi * series[idx - 1] + rng.standard_normal()
    return series


def _make_seasonal_series(period: int, n: int, seed: int) -> np.ndarray:
    """Generate deterministic seasonal series with additive noise.

    Args:
        period: Main seasonal period.
        n: Number of observations.
        seed: Random seed.

    Returns:
        1-D float64 array.
    """
    rng = np.random.default_rng(seed)
    t = np.arange(n, dtype=float)
    return (
        np.sin(2.0 * np.pi * t / period)
        + 0.6 * np.sin(2.0 * np.pi * t / (period / 2.0))
        + 0.2 * rng.standard_normal(n)
    )


def _make_white_noise(n: int, seed: int) -> np.ndarray:
    """Generate deterministic Gaussian white noise.

    Args:
        n: Number of observations.
        seed: Random seed.

    Returns:
        1-D float64 array.
    """
    return np.random.default_rng(seed).standard_normal(n)


def _run_triage(series_id: str, series: np.ndarray) -> tuple[TriageResult, TriageAgentPayload]:
    """Run deterministic triage and build corresponding A1 payload.

    Args:
        series_id: Stable signal identifier.
        series: Input time series.

    Returns:
        Tuple of ``(TriageResult, TriageAgentPayload)``.
    """
    request = TriageRequest(series=series, max_lag=20, n_surrogates=99, random_state=42)
    result = run_triage(request)
    payload = triage_agent_payload(result, series_id=series_id)
    return result, payload


def _truncate(text: str, *, width: int) -> str:
    """Truncate text to a fixed width for table output."""
    if len(text) <= width:
        return text
    return f"{text[: width - 3]}..."


def _print_evidence_table(interpretations: list[TriageAgentInterpretation]) -> None:
    """Print deterministic evidence versus A3 narrative summary table.

    Args:
        interpretations: Ordered A3 interpretations.
    """
    print("\n=== A3 evidence vs narrative table ===")
    header = (
        f"{'Series':<16} | {'F-Class':<8} | {'D-Class':<12} | {'Bucket':<10} | "
        f"{'Warn':<4} | {'Exp':<3} | Summary"
    )
    print(header)
    print("-" * len(header))

    for item in interpretations:
        summary = _truncate(item.deterministic_summary, width=84)
        print(
            f"{str(item.source_series_id):<16} | "
            f"{str(item.evidence.forecastability_class or '-'):<8} | "
            f"{str(item.evidence.directness_class or '-'):<12} | "
            f"{item.signal_bucket:<10} | "
            f"{item.evidence.warnings_count:<4} | "
            f"{item.evidence.experimental_notes_count:<3} | "
            f"{summary}"
        )


def _print_narrative_table(interpretations: list[TriageAgentInterpretation]) -> None:
    """Print table focused on A3 narrative fields.

    Args:
        interpretations: Ordered A3 interpretations.
    """
    print("\n=== A3 narrative fields ===")
    header = f"{'Series':<16} | {'Strong narrative':<60} | Caution / experimental"
    print(header)
    print("-" * len(header))

    for item in interpretations:
        strong = _truncate(item.strong_signal_narrative or "-", width=60)
        caution_parts = [item.cautionary_narrative or "-"]
        if item.experimental_narrative is not None:
            caution_parts.append(item.experimental_narrative)
        caution = _truncate(" ".join(caution_parts), width=82)
        print(f"{str(item.source_series_id):<16} | {strong:<60} | {caution}")


def _save_json_artifacts(
    payloads: list[TriageAgentPayload],
    interpretations: list[TriageAgentInterpretation],
) -> tuple[Path, Path]:
    """Persist A1 and A3 artifacts as JSON files.

    Args:
        payloads: A1 payload list.
        interpretations: A3 interpretation list.

    Returns:
        Tuple of output paths ``(a1_path, a3_path)``.
    """
    _JSON_DIR.mkdir(parents=True, exist_ok=True)
    a1_path = _JSON_DIR / "a3_demo_a1_payloads.json"
    a3_path = _JSON_DIR / "a3_demo_interpretations.json"

    a1_path.write_text(
        json.dumps([payload.model_dump(mode="json") for payload in payloads], indent=2),
        encoding="utf-8",
    )
    a3_path.write_text(
        json.dumps([item.model_dump(mode="json") for item in interpretations], indent=2),
        encoding="utf-8",
    )
    return a1_path, a3_path


def _save_comparison_figure(interpretations: list[TriageAgentInterpretation]) -> Path:
    """Create and save A3 comparison figure across signal types.

    Args:
        interpretations: Ordered A3 interpretations.

    Returns:
        Output figure path.
    """
    labels = [item.source_series_id or "unnamed" for item in interpretations]
    bucket_order = {"blocked": -1.0, "low": 0.0, "uncertain": 1.0, "mediated": 2.0, "strong": 3.0}
    bucket_values = [bucket_order[item.signal_bucket] for item in interpretations]
    warning_counts = [item.evidence.warnings_count for item in interpretations]
    experimental_counts = [item.evidence.experimental_notes_count for item in interpretations]

    bar_colors = [
        {
            "strong": "#1f77b4",
            "mediated": "#2ca02c",
            "uncertain": "#ff7f0e",
            "low": "#d62728",
            "blocked": "#7f7f7f",
        }[item.signal_bucket]
        for item in interpretations
    ]

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    axes[0].bar(labels, bucket_values, color=bar_colors, alpha=0.85)
    axes[0].set_title("A3 signal bucket strength")
    axes[0].set_ylabel("bucket score")
    axes[0].set_xlabel("signal")
    axes[0].set_ylim(-1.2, 3.4)
    for idx, item in enumerate(interpretations):
        axes[0].text(
            idx,
            bucket_values[idx] + 0.08,
            item.signal_bucket,
            ha="center",
            va="bottom",
            fontsize=8,
        )

    axes[1].bar(labels, warning_counts, label="warnings", color="#e67e22", alpha=0.85)
    axes[1].bar(
        labels,
        experimental_counts,
        bottom=warning_counts,
        label="experimental notes",
        color="#16a085",
        alpha=0.85,
    )
    axes[1].set_title("A3 explicit caution fields")
    axes[1].set_ylabel("count")
    axes[1].set_xlabel("signal")
    axes[1].legend(fontsize=8)

    fig.suptitle("A3 triage interpretation adapter: deterministic comparison", fontsize=12)
    fig.tight_layout()

    _FIG_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _FIG_DIR / "a3_triage_interpretation_adapter_demo.png"
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out_path


def main() -> None:
    """Run A3 deterministic interpretation adapter demo end to end."""
    print("=== A3 triage interpretation adapter demo ===")

    series_map: dict[str, np.ndarray] = {
        "persistent_ar": _make_ar_series(phi=0.93, n=520, seed=11),
        "seasonal": _make_seasonal_series(period=12, n=600, seed=22),
        "white_noise": _make_white_noise(n=520, seed=33),
    }

    payloads: list[TriageAgentPayload] = []
    for series_id, series in series_map.items():
        result, payload = _run_triage(series_id, series)
        payloads.append(payload)
        fc = result.interpretation.forecastability_class if result.interpretation else "none"
        dc = result.interpretation.directness_class if result.interpretation else "none"
        print(
            f"  {series_id:<13} readiness={result.readiness.status.value:<8} "
            f"fc={fc:<7} dc={dc:<14} blocked={result.blocked}"
        )

    # Demonstrate A2-envelope support: interpret from serialised payload envelopes.
    envelopes = serialise_batch(payloads)
    interpretations = interpret_batch(envelopes)

    _print_evidence_table(interpretations)
    _print_narrative_table(interpretations)

    a1_path, a3_path = _save_json_artifacts(payloads, interpretations)
    fig_path = _save_comparison_figure(interpretations)

    print("\nArtifacts")
    print(f"  A1 payloads      : {a1_path}")
    print(f"  A3 interpretations: {a3_path}")
    print(f"  Figure           : {fig_path}")
    print("\nDemo complete.")


if __name__ == "__main__":
    main()
