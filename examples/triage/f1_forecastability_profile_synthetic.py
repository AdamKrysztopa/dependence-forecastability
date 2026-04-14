"""F1 synthetic example: forecastability profiles on synthetic signals.

This script demonstrates F1 with two deterministic synthetic series:
1) A seasonal non-monotone signal.
2) A smoother AR(1) process.

It prints horizons, profile values, informative horizons, and recommendations,
and saves profile plots.

Usage:
    uv run python examples/triage/f1_forecastability_profile_synthetic.py
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt

from forecastability.triage.forecastability_profile import ForecastabilityProfile
from forecastability.triage.models import TriageRequest
from forecastability.use_cases.run_triage import run_triage
from forecastability.utils.datasets import generate_ar1


def _generate_non_monotone_seasonal(*, random_state: int, n_samples: int = 720) -> np.ndarray:
    """Generate a deterministic non-monotone seasonal signal.

    Args:
        random_state: Integer seed for deterministic noise generation.
        n_samples: Number of observations.

    Returns:
        A 1-D numpy array containing a seasonal process with harmonic structure.
    """
    rng = np.random.default_rng(random_state)
    time_index = np.arange(n_samples, dtype=float)

    primary = np.sin(2.0 * np.pi * time_index / 12.0)
    secondary = 0.55 * np.sin(2.0 * np.pi * time_index / 6.0 + 0.45)
    envelope = 1.0 + 0.20 * np.sin(2.0 * np.pi * time_index / 72.0)
    noise = rng.normal(0.0, 0.20, size=n_samples)

    return envelope * (primary + secondary) + noise


def _run_profile(
    *,
    series: np.ndarray,
    max_lag: int,
    random_state: int,
    n_surrogates: int = 99,
) -> ForecastabilityProfile:
    """Run triage and extract the F1 forecastability profile.

    Args:
        series: Input univariate series.
        max_lag: Maximum lag used by triage.
        random_state: Deterministic random state passed to triage.
        n_surrogates: Number of surrogates used for significance testing.

    Returns:
        Forecastability profile produced by the triage pipeline.

    Raises:
        RuntimeError: If triage is blocked or profile generation is unavailable.
    """
    request = TriageRequest(
        series=series,
        max_lag=max_lag,
        n_surrogates=n_surrogates,
        random_state=random_state,
    )
    result = run_triage(request)
    profile = result.forecastability_profile
    if result.blocked or profile is None:
        raise RuntimeError("Triage did not return a forecastability profile.")
    return profile


def _print_profile_summary(*, label: str, profile: ForecastabilityProfile) -> None:
    """Print key F1 outputs for one profile.

    Args:
        label: Human-readable series label.
        profile: Forecastability profile to summarize.
    """
    rounded_values = np.round(profile.values, 4)
    values_text = np.array2string(rounded_values, separator=", ", max_line_width=120)

    print(f"\n=== {label} ===")
    print(f"horizons: {profile.horizons}")
    print(f"profile values: {values_text}")
    print(f"informative horizons: {profile.informative_horizons}")
    print(f"peak horizon: {profile.peak_horizon}")
    print(f"is non-monotone: {profile.is_non_monotone}")
    print(f"summary: {profile.summary}")
    print(f"model_now: {profile.model_now}")
    print(f"review_horizons: {profile.review_horizons}")
    print(f"avoid_horizons: {profile.avoid_horizons}")


def _plot_profiles(
    *,
    profiles: dict[str, ForecastabilityProfile],
    save_path: Path,
) -> None:
    """Plot AMI-derived forecastability profiles and informative horizons.

    Args:
        profiles: Mapping from label to forecastability profile.
        save_path: Output PNG path.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.5), sharey=True)

    for axis, (label, profile) in zip(axes, profiles.items(), strict=True):
        horizons = np.asarray(profile.horizons, dtype=int)
        values = profile.values
        informative = set(profile.informative_horizons)

        axis.plot(horizons, values, marker="o", lw=1.8, color="tab:blue", label="F(h)")
        axis.axhline(profile.epsilon, ls="--", lw=1.2, color="tab:orange", label="epsilon")

        if informative:
            mask = np.array([h in informative for h in horizons])
            axis.scatter(
                horizons[mask],
                values[mask],
                color="tab:red",
                s=45,
                zorder=3,
                label="informative horizon",
            )

        axis.set_title(label)
        axis.set_xlabel("Horizon")
        axis.grid(alpha=0.3)
        axis.legend(fontsize=8)

    axes[0].set_ylabel("Forecastability profile value (AMI)")
    fig.suptitle("F1 Synthetic Forecastability Profiles", fontsize=12, fontweight="bold")
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(save_path, dpi=160)
    plt.close(fig)


def _plot_series(*, series_map: dict[str, np.ndarray], save_path: Path) -> None:
    """Plot representative windows of the synthetic series.

    Args:
        series_map: Mapping from label to generated series.
        save_path: Output PNG path.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 4), sharex=False)

    for axis, (label, series) in zip(axes, series_map.items(), strict=True):
        window = min(240, series.size)
        axis.plot(np.arange(window), series[:window], lw=1.2, color="tab:gray")
        axis.set_title(label)
        axis.set_xlabel("Time index")
        axis.grid(alpha=0.3)

    axes[0].set_ylabel("Value")
    fig.suptitle("Synthetic Signals Used in F1 Example", fontsize=12, fontweight="bold")
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(save_path, dpi=160)
    plt.close(fig)


def main() -> None:
    """Run the F1 synthetic profile example and persist artifacts."""
    random_state = 42
    max_lag = 36

    seasonal = _generate_non_monotone_seasonal(random_state=random_state, n_samples=720)
    ar_smoother = generate_ar1(n_samples=720, phi=0.88, random_state=17)

    series_map = {
        "Seasonal non-monotone": seasonal,
        "Smoother AR(1)": ar_smoother,
    }

    profiles = {
        label: _run_profile(series=series, max_lag=max_lag, random_state=random_state)
        for label, series in series_map.items()
    }

    for label, profile in profiles.items():
        _print_profile_summary(label=label, profile=profile)

    output_dir = Path("outputs/figures/examples/triage")
    profile_path = output_dir / "f1_forecastability_profile_synthetic_profiles.png"
    signal_path = output_dir / "f1_forecastability_profile_synthetic_signals.png"

    _plot_profiles(profiles=profiles, save_path=profile_path)
    _plot_series(series_map=series_map, save_path=signal_path)

    print("\nSaved figures:")
    print(f"- {profile_path}")
    print(f"- {signal_path}")


if __name__ == "__main__":
    main()
