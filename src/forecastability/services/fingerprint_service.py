"""Fingerprint builder service for V3_1-F02.

Builds a ForecastabilityFingerprint from AMI profile outputs. This is a pure
domain service — no routing, plotting, dashboard, pipeline, or adapter imports.

Core semantics:
        - Informative horizons H_info require both AMI >= floor and surrogate significance.
        - Structure classification precedence is: none > periodic > monotonic > mixed.
        - nonlinear_share aggregates only horizons with valid Gaussian baseline I_G(h);
            invalid baseline horizons are excluded from both numerator and denominator.
"""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel
from scipy.signal import find_peaks

from forecastability.services.linear_information_service import (
    compute_linear_information_curve,
)
from forecastability.utils.types import FingerprintStructure, ForecastabilityFingerprint

# ---------------------------------------------------------------------------
# Input model
# ---------------------------------------------------------------------------


class FingerprintInput(BaseModel, frozen=True):
    """Input to the fingerprint builder service.

    Attributes:
        ami_values: AMI(h) values, indexed 0 = lag 1.
        horizons: 1-based horizon indices, e.g. [1, 2, 3, ..., H].
        significant_horizons: Horizons where p_sur(h) <= alpha (1-based).
        series: Raw series, needed for nonlinear_share via autocorrelation.
        directness_ratio: Passed through as-is.
        ami_floor: tau_AMI — minimum AMI value to count as informative.
        peak_prominence_abs: Absolute prominence floor for periodic peak detection.
        peak_prominence_rel: Relative prominence factor (fraction of max informative AMI).
        spacing_tolerance: Max allowed deviation in inter-peak spacing for periodic label.
        monotonicity_tolerance: Max fractional reversal for monotonic label.
        min_horizons_for_periodic: Minimum informative horizons before inferring periodic.
        nonlinear_epsilon: Numerical floor for nonlinear_share denominator.
    """

    model_config = {"arbitrary_types_allowed": True}

    ami_values: list[float]
    horizons: list[int]
    significant_horizons: list[int]
    series: np.ndarray | None = None
    directness_ratio: float | None = None
    ami_floor: float = 0.01
    peak_prominence_abs: float = 0.01
    peak_prominence_rel: float = 0.1
    spacing_tolerance: int = 2
    monotonicity_tolerance: float = 0.05
    min_horizons_for_periodic: int = 4
    nonlinear_epsilon: float = 1e-12


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_informative_horizons(
    ami_values: list[float],
    horizons: list[int],
    significant_horizons: list[int],
    *,
    ami_floor: float,
) -> list[int]:
    """Return sorted informative horizon set H_info.

    A horizon is informative when AMI(h) >= ami_floor AND h is significant.

    Args:
        ami_values: AMI(h) values aligned to horizons list.
        horizons: 1-based horizon indices.
        significant_horizons: Horizons passing significance threshold.
        ami_floor: Minimum AMI for inclusion.

    Returns:
        Sorted list of informative horizon indices.
    """
    sig_set = set(significant_horizons)
    h_info = [
        h for h, ami in zip(horizons, ami_values, strict=True) if ami >= ami_floor and h in sig_set
    ]
    return sorted(h_info)


def _compute_information_mass(
    ami_values: list[float],
    horizons: list[int],
    h_info: list[int],
) -> float:
    """Compute normalised information mass over informative horizons.

    M = (1 / H) * sum(AMI(h) for h in H_info), where H = max(1, len(horizons)).

    Args:
        ami_values: AMI(h) values aligned to horizons.
        horizons: Full horizon list.
        h_info: Informative horizon subset.

    Returns:
        Non-negative mass value.
    """
    if not h_info:
        return 0.0
    h_total = max(1, len(horizons))
    h_info_set = set(h_info)
    ami_sum = sum(ami for h, ami in zip(horizons, ami_values, strict=True) if h in h_info_set)
    return ami_sum / h_total


def _has_stable_spacing(peak_positions: np.ndarray, *, spacing_tolerance: int) -> bool:
    """Check whether inter-peak spacings are within tolerance of their median.

    Args:
        peak_positions: Indices of detected peaks (1-D, at least 2 elements).
        spacing_tolerance: Maximum absolute deviation from median spacing.

    Returns:
        True when all spacings are within spacing_tolerance of the median.
    """
    spacings = np.diff(peak_positions)
    median_spacing = float(np.median(spacings))
    return bool(np.all(np.abs(spacings - median_spacing) <= spacing_tolerance))


def _classify_structure(
    ami_values: list[float],
    horizons: list[int],
    h_info: list[int],
    *,
    peak_prominence_abs: float,
    peak_prominence_rel: float,
    spacing_tolerance: int,
    monotonicity_tolerance: float,
    min_horizons_for_periodic: int,
) -> FingerprintStructure:
    """Classify the information structure shape.

    Priority order: none > periodic > monotonic > mixed.

    Args:
        ami_values: AMI(h) values aligned to horizons.
        horizons: Full horizon list.
        h_info: Informative horizon subset (sorted ascending).
        peak_prominence_abs: Absolute prominence floor.
        peak_prominence_rel: Relative prominence factor.
        spacing_tolerance: Tolerance on inter-peak spacing.
        monotonicity_tolerance: Fractional reversal tolerance for monotonic.
        min_horizons_for_periodic: Minimum informative horizons for periodic.

    Returns:
        One of "none", "periodic", "monotonic", "mixed".
    """
    if not h_info:
        return "none"

    h_to_ami: dict[int, float] = dict(zip(horizons, ami_values, strict=True))
    info_ami = [h_to_ami[h] for h in h_info]
    max_info_ami = max(info_ami)

    # --- periodic check ---
    if len(h_info) >= min_horizons_for_periodic:
        arr = np.array(info_ami)
        prominence_threshold = max(
            peak_prominence_abs,
            peak_prominence_rel * max_info_ami,
        )
        peak_indices, _ = find_peaks(arr, prominence=prominence_threshold)
        if len(peak_indices) >= 2 and _has_stable_spacing(
            peak_indices, spacing_tolerance=spacing_tolerance
        ):
            return "periodic"

    # --- monotonic check ---
    if _is_monotonic_decreasing(info_ami, max_ami=max_info_ami, tolerance=monotonicity_tolerance):
        return "monotonic"

    return "mixed"


def _is_monotonic_decreasing(values: list[float], *, max_ami: float, tolerance: float) -> bool:
    """Check whether values are approximately non-increasing within tolerance.

    Args:
        values: Sequence of AMI values at informative horizons.
        max_ami: Maximum AMI value (denominator for relative reversal).
        tolerance: Maximum fractional increase allowed (relative to max_ami).

    Returns:
        True when all forward differences are <= tolerance * max_ami.
    """
    if len(values) <= 1:
        return True
    threshold = tolerance * max_ami
    arr = np.array(values)
    reversals = np.diff(arr)
    return bool(np.all(reversals <= threshold))


def _compute_nonlinear_share(
    ami_values: list[float],
    horizons: list[int],
    h_info: list[int],
    series: np.ndarray | None,
    *,
    epsilon: float,
) -> tuple[float, list[str]]:
    """Compute nonlinear AMI share above the Gaussian-information baseline.

    The ratio is computed only across informative horizons with valid I_G(h).
    Informative horizons whose I_G(h) is invalid are excluded from both
    numerator and denominator and logged as metadata notes.

    Args:
        ami_values: AMI(h) values aligned to horizons.
        horizons: Full horizon list.
        h_info: Informative horizon subset.
        series: Raw time series, or None.
        epsilon: Numerical floor for denominator.

    Returns:
        Tuple of (nonlinear_share, metadata_notes).
    """
    notes: list[str] = []
    if not h_info:
        return 0.0, notes

    h_to_ami: dict[int, float] = dict(zip(horizons, ami_values, strict=True))

    if series is None:
        notes.append("nonlinear_share=0.0: series not provided")
        return 0.0, notes

    curve = compute_linear_information_curve(series, horizons=h_info, epsilon=epsilon)
    ig_map: dict[int, float] = dict(curve.valid_gaussian_values())

    ami_total = 0.0
    excess_total = 0.0
    for h in h_info:
        ami_h = h_to_ami[h]
        if h in ig_map:
            ami_total += ami_h
            excess_total += max(ami_h - ig_map[h], 0.0)
        else:
            notes.append(f"nonlinear_share: excluded h={h} (invalid I_G)")

    if ami_total <= epsilon:
        return 0.0, notes

    return excess_total / ami_total, notes


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_fingerprint(
    ami_values: list[float],
    *,
    horizons: list[int],
    significant_horizons: list[int],
    series: np.ndarray | None = None,
    directness_ratio: float | None = None,
    ami_floor: float = 0.01,
    peak_prominence_abs: float = 0.01,
    peak_prominence_rel: float = 0.1,
    spacing_tolerance: int = 2,
    monotonicity_tolerance: float = 0.05,
    min_horizons_for_periodic: int = 4,
    nonlinear_epsilon: float = 1e-12,
) -> ForecastabilityFingerprint:
    """Build a ForecastabilityFingerprint from AMI profile outputs.

    All parameters after ami_values are keyword-only. This function is a
    pure domain computation — it performs no I/O, routing, or plotting.

    Algorithm summary:
        1. Compute H_info — informative horizons (AMI >= floor AND significant).
        2. Compute information_mass — normalised masked AMI sum.
        3. Compute information_horizon — latest informative horizon.
        4. Classify information_structure — none/periodic/monotonic/mixed.
        5. Compute nonlinear_share — excess AMI over Gaussian-information baseline,
           restricted to informative horizons with valid I_G(h).

    Args:
        ami_values: AMI(h) values, indexed 0 = lag 1, aligned with horizons.
        horizons: 1-based horizon indices, e.g. [1, 2, ..., H].
        significant_horizons: Horizons where p_sur(h) <= alpha (1-based).
        series: Raw time series; required for nonlinear_share computation.
            If None, nonlinear_share is set to 0.0.
        directness_ratio: Direct vs. mediated lag structure ratio. Passed through
            as-is; not used internally for fingerprint computation.
        ami_floor: Minimum AMI(h) to include h in H_info. Defaults to 0.01.
        peak_prominence_abs: Absolute prominence floor for periodic peak detection.
        peak_prominence_rel: Relative prominence factor (fraction of max informative AMI).
        spacing_tolerance: Max allowed absolute deviation in inter-peak spacing.
        monotonicity_tolerance: Fractional tolerance for monotone-decreasing check.
        min_horizons_for_periodic: Minimum informative horizons before inferring periodic.
        nonlinear_epsilon: Numerical floor for nonlinear_share denominator.

    Returns:
        ForecastabilityFingerprint: Frozen fingerprint model.

    Raises:
        ValueError: If ami_values and horizons have different lengths.
    """
    if len(ami_values) != len(horizons):
        raise ValueError(
            f"ami_values length ({len(ami_values)}) must equal horizons length ({len(horizons)})"
        )

    h_info = _build_informative_horizons(
        ami_values, horizons, significant_horizons, ami_floor=ami_floor
    )
    mass = _compute_information_mass(ami_values, horizons, h_info)
    h_max = max(h_info) if h_info else 0
    structure = _classify_structure(
        ami_values,
        horizons,
        h_info,
        peak_prominence_abs=peak_prominence_abs,
        peak_prominence_rel=peak_prominence_rel,
        spacing_tolerance=spacing_tolerance,
        monotonicity_tolerance=monotonicity_tolerance,
        min_horizons_for_periodic=min_horizons_for_periodic,
    )
    nl_share, notes = _compute_nonlinear_share(
        ami_values, horizons, h_info, series, epsilon=nonlinear_epsilon
    )

    metadata: dict[str, str | int | float] = {}
    for i, note in enumerate(notes):
        metadata[f"note_{i}"] = note

    return ForecastabilityFingerprint(
        information_mass=mass,
        information_horizon=h_max,
        information_structure=structure,
        nonlinear_share=nl_share,
        directness_ratio=directness_ratio,
        informative_horizons=h_info,
        metadata=metadata,
    )
