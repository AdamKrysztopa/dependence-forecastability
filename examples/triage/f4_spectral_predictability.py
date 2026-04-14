"""F4 example: spectral predictability on deterministic synthetic signals.

This example contrasts white-noise-like, periodic, and structured signals,
reports PSD-based score summaries, and prints preprocessing assumptions.

Usage:
    uv run python examples/triage/f4_spectral_predictability.py
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt

from forecastability.diagnostics.spectral_utils import compute_normalised_psd
from forecastability.services.spectral_predictability_service import build_spectral_predictability
from forecastability.triage.spectral_predictability import SpectralPredictabilityResult


def _make_white_noise(*, n_samples: int, random_state: int) -> np.ndarray:
    """Generate deterministic white noise.

    Args:
        n_samples: Number of observations.
        random_state: Integer seed.

    Returns:
        White-noise series.
    """
    rng = np.random.default_rng(random_state)
    return rng.standard_normal(n_samples)


def _make_periodic(*, n_samples: int) -> np.ndarray:
    """Generate a deterministic periodic signal.

    Args:
        n_samples: Number of observations.

    Returns:
        A sine-wave series.
    """
    time_index = np.linspace(0.0, 16.0 * np.pi, n_samples)
    return np.sin(time_index)


def _make_structured_irregular(*, n_samples: int, random_state: int) -> np.ndarray:
    """Generate a deterministic structured-irregular signal.

    Args:
        n_samples: Number of observations.
        random_state: Integer seed.

    Returns:
        A seasonal plus autoregressive-noise signal.
    """
    rng = np.random.default_rng(random_state)
    time_index = np.arange(n_samples, dtype=float)
    seasonal = np.sin(2.0 * np.pi * time_index / 24.0) + 0.35 * np.sin(
        2.0 * np.pi * time_index / 6.0
    )
    ar_noise = np.zeros(n_samples, dtype=float)
    ar_noise[0] = rng.standard_normal()
    for index in range(1, n_samples):
        ar_noise[index] = 0.55 * ar_noise[index - 1] + 0.45 * rng.standard_normal()
    return seasonal + ar_noise


def _score_guidance(*, score: float) -> str:
    """Translate spectral score to practical model guidance.

    Args:
        score: Spectral predictability score in [0, 1].

    Returns:
        Practical recommendation string.
    """
    if score >= 0.70:
        return "Strong frequency concentration: prioritize seasonal and lag-structured models."
    if score >= 0.40:
        return "Mixed spectrum: compare simple structured models with robust baselines."
    return "Near-flat spectrum: start with conservative baselines and short-memory models."


def build_example_results() -> list[tuple[str, np.ndarray, SpectralPredictabilityResult]]:
    """Run F4 example scenarios.

    Returns:
        List of tuples with signal label, series, and F4 result.
    """
    signal_specs: list[tuple[str, np.ndarray]] = [
        ("White-noise-like signal", _make_white_noise(n_samples=512, random_state=31)),
        ("Periodic sine signal", _make_periodic(n_samples=512)),
        (
            "Structured irregular signal",
            _make_structured_irregular(n_samples=512, random_state=32),
        ),
    ]

    return [
        (label, series, build_spectral_predictability(series, detrend="constant"))
        for label, series in signal_specs
    ]


def _print_results(*, results: list[tuple[str, np.ndarray, SpectralPredictabilityResult]]) -> None:
    """Print numeric and practical outputs.

    Args:
        results: Outputs from :func:`build_example_results`.
    """
    reliability_notes = [
        "Welch PSD assumes approximately stable dynamics over the analyzed window.",
        "Strong trends or level shifts should be detrended before interpreting score levels.",
        (
            "Sampling cadence affects frequency interpretation; compare only at "
            "consistent sampling rates."
        ),
    ]

    print("\n=== F4 Spectral Predictability ===")
    for label, _series, result in results:
        print(f"\nSignal: {label}")
        print(f"spectral_predictability_score: {result.score:.4f}")
        print(f"spectral_entropy_normalized: {result.normalised_entropy:.4f}")
        print(f"spectral_summary: {result.interpretation}")
        print(f"model_guidance: {_score_guidance(score=result.score)}")

    print("\nspectral_reliability_notes:")
    for note in reliability_notes:
        print(f"- {note}")


def _plot_results(
    *,
    results: list[tuple[str, np.ndarray, SpectralPredictabilityResult]],
    save_path: Path,
) -> None:
    """Plot signal traces and PSD summaries.

    Args:
        results: Outputs from :func:`build_example_results`.
        save_path: PNG output path.
    """
    fig, axes = plt.subplots(len(results), 2, figsize=(12, 3.4 * len(results)))
    if len(results) == 1:
        axes = np.array([axes])

    for row, (label, series, result) in enumerate(results):
        axis_series = axes[row, 0]
        axis_psd = axes[row, 1]

        axis_series.plot(series[:220], lw=1.0, color="tab:gray")
        axis_series.set_title(label)
        axis_series.set_xlabel("time index")
        axis_series.set_ylabel("value")
        axis_series.grid(alpha=0.3)

        freqs, weights = compute_normalised_psd(series)
        axis_psd.plot(freqs, weights, lw=1.2, color="tab:blue")
        axis_psd.fill_between(freqs, weights, color="tab:blue", alpha=0.25)
        axis_psd.set_xlabel("normalized frequency")
        axis_psd.set_ylabel("normalized power")
        axis_psd.set_title(f"score={result.score:.3f}")
        axis_psd.grid(alpha=0.3)

    fig.suptitle("F4 Spectral Predictability: signal and PSD views", fontsize=12, fontweight="bold")
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(save_path, dpi=160)
    plt.close(fig)


def main() -> None:
    """Run the F4 example and save artifacts."""
    results = build_example_results()
    _print_results(results=results)

    figure_path = Path("outputs/figures/examples/triage/f4_spectral_predictability.png")
    _plot_results(results=results, save_path=figure_path)

    print("\nSaved figure:")
    print(f"- {figure_path}")


if __name__ == "__main__":
    main()
