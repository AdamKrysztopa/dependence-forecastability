"""Minimal geometry-backed forecastability fingerprint example.

Runs the public ``run_forecastability_fingerprint()`` use case on the shared
synthetic archetypes and prints the deterministic geometry, fingerprint, and
routing outputs. This is the smallest example that still reflects the v0.3.1
release semantics.

Usage::

    uv run python examples/fingerprint/minimal_fingerprint.py
"""

from __future__ import annotations

import numpy as np

from forecastability import run_forecastability_fingerprint
from forecastability.utils.synthetic import generate_fingerprint_archetypes

N_SAMPLES = 600
MAX_LAG = 24
N_SURROGATES = 99
RANDOM_STATE = 42


def _print_bundle(name: str, series: np.ndarray) -> None:
    """Run the fingerprint use case for one archetype and print key fields."""
    bundle = run_forecastability_fingerprint(
        series=series,
        target_name=name,
        max_lag=MAX_LAG,
        n_surrogates=N_SURROGATES,
        random_state=RANDOM_STATE,
    )
    geometry = bundle.geometry
    fingerprint = bundle.fingerprint
    recommendation = bundle.recommendation

    print(f"\n{'=' * 60}")
    print(f"Archetype: {name}")
    print(f"{'=' * 60}")
    print("Geometry")
    print(f"  method                = {geometry.method}")
    print(f"  signal_to_noise       = {geometry.signal_to_noise:.4f}")
    print(f"  information_horizon   = {geometry.information_horizon}")
    print(f"  information_structure = {geometry.information_structure}")
    print(f"  informative_horizons  = {geometry.informative_horizons}")
    print("Fingerprint")
    print(f"  information_mass      = {fingerprint.information_mass:.4f}")
    print(f"  information_horizon   = {fingerprint.information_horizon}")
    print(f"  information_structure = {fingerprint.information_structure}")
    print(f"  nonlinear_share       = {fingerprint.nonlinear_share:.4f}")
    print(f"  directness_ratio      = {fingerprint.directness_ratio}")
    print("Routing")
    print(f"  primary_families      = {recommendation.primary_families}")
    print(f"  confidence_label      = {recommendation.confidence_label}")
    print(f"  caution_flags         = {recommendation.caution_flags}")


def main() -> None:
    """Run the minimal example on the shared synthetic archetypes."""
    print("=" * 60)
    print("Forecastability Fingerprint — Minimal Geometry Example")
    print(f"n_samples={N_SAMPLES}, max_lag={MAX_LAG}, n_surrogates={N_SURROGATES}")
    print("=" * 60)

    for name, series in generate_fingerprint_archetypes(
        n=N_SAMPLES,
        seed=RANDOM_STATE,
    ).items():
        _print_bundle(name, series)

    print(f"\n{'=' * 60}")
    print("Done.")


if __name__ == "__main__":
    main()
