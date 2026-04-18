"""Minimal forecastability fingerprint example -- V3_1-F02.

Demonstrates ``build_fingerprint`` on four canonical synthetic archetypes
(white noise, AR(1) monotonic, seasonal periodic, nonlinear mixed) using the
generators from ``forecastability.utils.synthetic``.

Two demonstration modes are shown:

**Surrogate-gated mode** -- the full triage pipeline runs AMI + phase-randomised
surrogate significance before calling ``build_fingerprint``.  For linear AR(1)
processes, phase surrogates preserve the autocorrelation structure, so surrogate
AMI bands can match or exceed the original AMI at each lag.  This is statistically
correct: the AR(1) signal is not significantly above what the linear surrogate
expects, and the fingerprint correctly reports ``none`` informative horizons.

**Floor-only mode** -- all horizons whose AMI exceeds the ``ami_floor`` threshold
are treated as significant, bypassing the surrogate gate.  This mode illustrates
what the fingerprint *shape* would look like for each archetype regardless of
whether the surrogate test is applied.

Usage::

    uv run python examples/fingerprint/minimal_fingerprint.py
"""

from __future__ import annotations

import numpy as np

from forecastability import TriageRequest, run_triage
from forecastability.services.fingerprint_service import build_fingerprint
from forecastability.triage import AnalysisGoal
from forecastability.utils.synthetic import (
    generate_ar1_monotonic,
    generate_nonlinear_mixed,
    generate_seasonal_periodic,
    generate_white_noise,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_LAG = 24
N_SURROGATES = 99
N_SAMPLES = 600
RANDOM_STATE = 42
AMI_FLOOR = 0.01


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _print_fingerprint(fp_label: str, fp: object) -> None:
    """Print fingerprint fields in a compact table row."""
    from forecastability.utils.types import ForecastabilityFingerprint  # noqa: PLC0415

    assert isinstance(fp, ForecastabilityFingerprint)
    print(f"  [{fp_label}]")
    print(f"    information_mass      = {fp.information_mass:.4f}")
    print(f"    information_horizon   = {fp.information_horizon}")
    print(f"    information_structure = {fp.information_structure}")
    print(f"    nonlinear_share       = {fp.nonlinear_share:.4f}")
    print(f"    directness_ratio      = {fp.directness_ratio}")
    n_inf = len(fp.informative_horizons)
    preview = fp.informative_horizons[:8]
    suffix = "..." if n_inf > 8 else ""
    print(f"    informative_horizons  = {preview}{suffix}")
    for key, val in fp.metadata.items():
        print(f"    [{key}] {val}")


def _run_archetype(name: str, series: np.ndarray) -> None:
    """Run triage, build fingerprint in both modes, and print results.

    Surrogate-gated mode: uses sig_raw_lags from the triage pipeline.
    Floor-only mode: treats all horizons with AMI >= ami_floor as significant.

    Args:
        name: Human-readable archetype label.
        series: 1-D numeric series for this archetype.
    """
    print(f"\n{'─' * 60}")
    print(f"Archetype : {name}")

    result = run_triage(
        TriageRequest(
            series=series,
            goal=AnalysisGoal.univariate,
            max_lag=MAX_LAG,
            n_surrogates=N_SURROGATES,
            random_state=RANDOM_STATE,
        )
    )

    if result.blocked or result.analyze_result is None:
        print("  [blocked -- no AMI result available]")
        return

    ar = result.analyze_result
    raw_ami: list[float] = ar.raw.tolist()
    horizons: list[int] = list(range(1, len(raw_ami) + 1))

    directness_ratio: float | None = None
    if result.interpretation is not None:
        directness_ratio = result.interpretation.diagnostics.directness_ratio

    # --- Surrogate-gated mode ---
    # sig_raw_lags is 0-based; convert to 1-based horizon indices.
    surrogate_sig_horizons: list[int] = [int(lag) + 1 for lag in ar.sig_raw_lags.tolist()]
    fp_surrogate = build_fingerprint(
        raw_ami,
        horizons=horizons,
        significant_horizons=surrogate_sig_horizons,
        series=series,
        directness_ratio=directness_ratio,
        ami_floor=AMI_FLOOR,
    )
    if not surrogate_sig_horizons:
        print(
            "  Note: phase surrogates found no significant lags -- correct for linear\n"
            "  processes where surrogate AMI bands match the original AMI at each lag."
        )
    _print_fingerprint("surrogate-gated", fp_surrogate)

    # --- Floor-only mode ---
    # Treat all horizons with AMI >= ami_floor as significant (no surrogate gate).
    floor_sig_horizons: list[int] = [
        h for h, ami in zip(horizons, raw_ami, strict=True) if ami >= AMI_FLOOR
    ]
    fp_floor = build_fingerprint(
        raw_ami,
        horizons=horizons,
        significant_horizons=floor_sig_horizons,
        series=series,
        directness_ratio=directness_ratio,
        ami_floor=AMI_FLOOR,
    )
    _print_fingerprint("floor-only (no surrogate gate)", fp_floor)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the canonical four-archetype fingerprint demo."""
    print("=" * 60)
    print("Forecastability Fingerprint -- V3_1-F02 Example")
    print(f"n_samples={N_SAMPLES}, max_lag={MAX_LAG}, n_surrogates={N_SURROGATES}")
    print("=" * 60)

    archetypes: list[tuple[str, np.ndarray]] = [
        ("White Noise", generate_white_noise(N_SAMPLES, seed=RANDOM_STATE)),
        ("AR(1) Monotonic", generate_ar1_monotonic(N_SAMPLES, seed=RANDOM_STATE)),
        ("Seasonal Periodic", generate_seasonal_periodic(N_SAMPLES, seed=RANDOM_STATE)),
        ("Nonlinear Mixed", generate_nonlinear_mixed(N_SAMPLES, seed=RANDOM_STATE)),
    ]

    for name, series in archetypes:
        _run_archetype(name, series)

    print(f"\n{'─' * 60}")
    print("Done.")


if __name__ == "__main__":
    main()
