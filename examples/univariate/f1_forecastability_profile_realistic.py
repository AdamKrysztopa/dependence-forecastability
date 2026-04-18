"""F1 realistic example: forecastability profile on a loader-backed dataset.

This script uses the AirPassengers series from project loaders and reports the
same F1 outputs as the synthetic script: horizons, profile values, informative
horizons, and recommendations.

Usage:
    uv run python examples/univariate/f1_forecastability_profile_realistic.py
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
from forecastability.utils.datasets import load_air_passengers


def _compute_realistic_profile(
    *,
    series: np.ndarray,
    max_lag: int,
    random_state: int,
    n_surrogates: int = 99,
) -> ForecastabilityProfile:
    """Run triage and return the realistic-series F1 profile.

    Args:
        series: Realistic input series loaded from repository dataset utilities.
        max_lag: Maximum lag used for triage.
        random_state: Deterministic random state for triage execution.
        n_surrogates: Number of surrogates used for significance bands.

    Returns:
        Forecastability profile from triage.

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
        raise RuntimeError("Triage did not return a realistic forecastability profile.")
    return profile


def _print_profile_summary(*, profile: ForecastabilityProfile) -> None:
    """Print key profile outputs for the realistic dataset.

    Args:
        profile: Forecastability profile object.
    """
    rounded_values = np.round(profile.values, 4)
    values_text = np.array2string(rounded_values, separator=", ", max_line_width=120)

    print("\n=== AirPassengers (realistic loader dataset) ===")
    print(f"horizons: {profile.horizons}")
    print(f"profile values: {values_text}")
    print(f"informative horizons: {profile.informative_horizons}")
    print(f"peak horizon: {profile.peak_horizon}")
    print(f"is non-monotone: {profile.is_non_monotone}")
    print(f"summary: {profile.summary}")
    print(f"model_now: {profile.model_now}")
    print(f"review_horizons: {profile.review_horizons}")
    print(f"avoid_horizons: {profile.avoid_horizons}")


def _plot_realistic_profile(
    *,
    series: np.ndarray,
    profile: ForecastabilityProfile,
    save_path: Path,
) -> None:
    """Save a two-panel realistic profile figure.

    Args:
        series: Input realistic series.
        profile: Computed F1 forecastability profile.
        save_path: Output PNG path.
    """
    fig, (axis_series, axis_profile) = plt.subplots(2, 1, figsize=(11, 7), sharex=False)

    axis_series.plot(series, lw=1.3, color="tab:blue")
    axis_series.set_title("AirPassengers series")
    axis_series.set_xlabel("Time index")
    axis_series.set_ylabel("Passengers")
    axis_series.grid(alpha=0.3)

    horizons = np.asarray(profile.horizons, dtype=int)
    values = profile.values
    informative = set(profile.informative_horizons)

    axis_profile.plot(horizons, values, marker="o", lw=1.8, color="tab:green", label="F(h)")
    axis_profile.axhline(
        profile.epsilon,
        ls="--",
        lw=1.2,
        color="tab:orange",
        label="epsilon",
    )

    if informative:
        mask = np.array([h in informative for h in horizons])
        axis_profile.scatter(
            horizons[mask],
            values[mask],
            color="tab:red",
            s=45,
            zorder=3,
            label="informative horizon",
        )

    axis_profile.set_title("F1 Forecastability Profile (realistic)")
    axis_profile.set_xlabel("Horizon")
    axis_profile.set_ylabel("Forecastability profile value (AMI)")
    axis_profile.grid(alpha=0.3)
    axis_profile.legend(fontsize=9)

    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(save_path, dpi=160)
    plt.close(fig)


def main() -> None:
    """Run the realistic F1 example and persist artifacts."""
    random_state = 42
    max_lag = 24

    series = load_air_passengers()
    profile = _compute_realistic_profile(
        series=series,
        max_lag=max_lag,
        random_state=random_state,
    )

    _print_profile_summary(profile=profile)

    output_path = Path("outputs/figures/examples/univariate") / (
        "f1_forecastability_profile_realistic_air_passengers.png"
    )
    _plot_realistic_profile(series=series, profile=profile, save_path=output_path)

    print("\nSaved figure:")
    print(f"- {output_path}")


if __name__ == "__main__":
    main()
