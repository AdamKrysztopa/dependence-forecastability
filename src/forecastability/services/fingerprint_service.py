"""Forecastability fingerprint construction from geometry and baseline outputs."""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from forecastability.services.linear_information_service import (
    LinearInformationCurve,
    compute_linear_information_curve,
)
from forecastability.utils.types import (
    AmiGeometryCurvePoint,
    AmiInformationGeometry,
    ForecastabilityFingerprint,
)

_CLASSIFIER_TIEBREAK_METADATA = "classifier_used_tiebreak"
_GEOMETRY_BORDERLINE_METADATA = "geometry_threshold_borderline"


class FingerprintThresholdConfig(BaseModel):
    """Downstream fingerprint and routing thresholds layered on geometry outputs."""

    model_config = ConfigDict(frozen=True)

    min_confident_horizons: int = Field(default=3, ge=1)
    low_signal_to_noise_confidence_threshold: float = Field(default=0.10, ge=0.0, le=1.0)
    epsilon: float = Field(default=1e-12, gt=0.0)


def _accepted_curve_points(geometry: AmiInformationGeometry) -> list[AmiGeometryCurvePoint]:
    """Return the accepted corrected-profile points from the geometry output."""
    return [
        point
        for point in geometry.curve
        if point.valid and point.accepted and point.ami_corrected is not None
    ]


def _valid_horizon_count(geometry: AmiInformationGeometry) -> int:
    """Return the count of valid evaluated horizons."""
    return sum(1 for point in geometry.curve if point.valid)


def _compute_information_mass(
    accepted_points: list[AmiGeometryCurvePoint],
    *,
    denominator: int,
) -> float:
    """Compute normalized information mass over the accepted corrected profile."""
    if not accepted_points or denominator <= 0:
        return 0.0
    accepted_sum = sum(
        float(point.ami_corrected) for point in accepted_points if point.ami_corrected
    )
    return accepted_sum / denominator


def _compute_nonlinear_share(
    accepted_points: list[AmiGeometryCurvePoint],
    *,
    baseline: LinearInformationCurve | None,
    epsilon: float,
) -> tuple[float, list[str]]:
    """Compute nonlinear share above the Gaussian-information baseline."""
    notes: list[str] = []
    if not accepted_points:
        return 0.0, notes
    if baseline is None or not baseline.points:
        notes.append("nonlinear_share=0.0: linear-information baseline not provided")
        return 0.0, notes

    baseline_map = {point.horizon: point for point in baseline.points}
    corrected_total = 0.0
    excess_total = 0.0
    for point in accepted_points:
        baseline_point = baseline_map.get(point.horizon)
        corrected = float(point.ami_corrected or 0.0)
        if (
            baseline_point is None
            or not baseline_point.valid
            or baseline_point.gaussian_information is None
        ):
            notes.append(f"nonlinear_share: excluded h={point.horizon} (invalid I_G)")
            continue
        corrected_total += corrected
        excess_total += max(corrected - baseline_point.gaussian_information, 0.0)

    if corrected_total <= epsilon:
        return 0.0, notes
    return excess_total / corrected_total, notes


def build_forecastability_fingerprint(
    *,
    geometry: AmiInformationGeometry,
    baseline: LinearInformationCurve | None = None,
    directness_ratio: float | None = None,
    config: FingerprintThresholdConfig | None = None,
) -> ForecastabilityFingerprint:
    """Build the geometry-backed forecastability fingerprint."""
    resolved_config = config if config is not None else FingerprintThresholdConfig()
    accepted_points = _accepted_curve_points(geometry)
    valid_horizon_count = _valid_horizon_count(geometry)
    informative_horizons = [point.horizon for point in accepted_points]
    information_mass = _compute_information_mass(
        accepted_points,
        denominator=max(1, valid_horizon_count),
    )
    nonlinear_share, notes = _compute_nonlinear_share(
        accepted_points,
        baseline=baseline,
        epsilon=resolved_config.epsilon,
    )

    metadata: dict[str, str | int | float] = {
        "geometry_method": geometry.method,
        _CLASSIFIER_TIEBREAK_METADATA: int(geometry.metadata.get(_CLASSIFIER_TIEBREAK_METADATA, 0)),
        _GEOMETRY_BORDERLINE_METADATA: int(geometry.metadata.get(_GEOMETRY_BORDERLINE_METADATA, 0)),
        "valid_horizon_count": int(valid_horizon_count),
        "accepted_horizon_count": int(len(informative_horizons)),
    }
    for idx, note in enumerate(notes):
        metadata[f"note_{idx}"] = note

    return ForecastabilityFingerprint(
        information_mass=information_mass,
        information_horizon=geometry.information_horizon,
        information_structure=(
            "monotonic"
            if geometry.information_structure == "monotone"
            else geometry.information_structure
        ),
        nonlinear_share=nonlinear_share,
        signal_to_noise=geometry.signal_to_noise,
        directness_ratio=directness_ratio,
        informative_horizons=informative_horizons,
        metadata=metadata,
    )


def _build_legacy_informative_horizons(
    ami_values: list[float],
    horizons: list[int],
    significant_horizons: list[int],
    *,
    ami_floor: float,
) -> list[int]:
    """Build the legacy informative set from raw AMI and significance input."""
    significant = set(significant_horizons)
    return [
        horizon
        for horizon, ami_value in zip(horizons, ami_values, strict=True)
        if horizon in significant and ami_value >= ami_floor
    ]


def _legacy_structure(
    ami_values: list[float],
    horizons: list[int],
    informative_horizons: list[int],
    *,
    peak_prominence_abs: float,
    spacing_tolerance: int,
    min_horizons_for_periodic: int,
) -> str:
    """Classify the legacy raw-AMI profile for compatibility callers."""
    if not informative_horizons:
        return "none"

    h_to_ami = dict(zip(horizons, ami_values, strict=True))
    informative_values = [h_to_ami[horizon] for horizon in informative_horizons]
    candidates: list[int] = []
    if (
        len(informative_values) >= 2
        and informative_values[0] > informative_values[1]
        and informative_values[0] - informative_values[1] >= peak_prominence_abs
    ):
        candidates.append(0)

    for idx in range(1, len(informative_values) - 1):
        left = informative_values[idx - 1]
        center = informative_values[idx]
        right = informative_values[idx + 1]
        if center > left and center > right and center - max(left, right) >= peak_prominence_abs:
            candidates.append(idx)

    if len(candidates) >= min_horizons_for_periodic:
        spacings = [right - left for left, right in zip(candidates, candidates[1:], strict=True)]
        if spacings and all(
            abs(spacing - spacings[0]) <= spacing_tolerance for spacing in spacings
        ):
            return "periodic"
    if len(candidates) <= 1:
        return "monotonic"
    return "mixed"


def build_fingerprint(
    ami_values: list[float],
    *,
    horizons: list[int],
    significant_horizons: list[int],
    series: np.ndarray | None = None,
    directness_ratio: float | None = None,
    ami_floor: float = 0.01,
    peak_prominence_abs: float = 0.01,
    peak_prominence_rel: float = 0.1,  # noqa: ARG001 - preserved for compatibility.
    spacing_tolerance: int = 2,  # noqa: ARG001 - preserved for compatibility.
    monotonicity_tolerance: float = 0.05,  # noqa: ARG001 - preserved for compatibility.
    min_horizons_for_periodic: int = 4,
    nonlinear_epsilon: float = 1e-12,
) -> ForecastabilityFingerprint:
    """Legacy compatibility wrapper for the pre-geometry fingerprint builder.

    The geometry-first path for v0.3.1 is :func:`build_forecastability_fingerprint`.
    This wrapper is kept only to avoid breaking external imports while the repo
    migrates from raw-AMI semantics to geometry-backed semantics.
    """
    if len(ami_values) != len(horizons):
        raise ValueError(
            f"ami_values length ({len(ami_values)}) must equal horizons length ({len(horizons)})"
        )

    informative_horizons = _build_legacy_informative_horizons(
        ami_values,
        horizons,
        significant_horizons,
        ami_floor=ami_floor,
    )
    structure = _legacy_structure(
        ami_values,
        horizons,
        informative_horizons,
        peak_prominence_abs=peak_prominence_abs,
        spacing_tolerance=spacing_tolerance,
        min_horizons_for_periodic=min_horizons_for_periodic,
    )
    informative_horizon_set = set(informative_horizons)
    geometry = AmiInformationGeometry(
        signal_to_noise=1.0 if informative_horizons else 0.0,
        information_horizon=max(informative_horizons, default=0),
        information_structure=structure,  # type: ignore[arg-type]
        informative_horizons=informative_horizons,
        curve=[
            AmiGeometryCurvePoint(
                horizon=horizon,
                ami_raw=float(ami_value),
                ami_bias=0.0,
                ami_corrected=max(float(ami_value), 0.0),
                tau=0.0,
                accepted=horizon in informative_horizon_set,
                valid=True,
            )
            for horizon, ami_value in zip(horizons, ami_values, strict=True)
        ],
        metadata={
            "compatibility_mode": 1,
            "peak_prominence_abs": peak_prominence_abs,
            "ami_floor": ami_floor,
        },
    )
    baseline = (
        None
        if series is None
        else compute_linear_information_curve(
            np.asarray(series, dtype=float),
            horizons=horizons,
            epsilon=nonlinear_epsilon,
        )
    )
    return build_forecastability_fingerprint(
        geometry=geometry,
        baseline=baseline,
        directness_ratio=directness_ratio,
        config=FingerprintThresholdConfig(epsilon=nonlinear_epsilon),
    )


__all__ = [
    "FingerprintThresholdConfig",
    "build_fingerprint",
    "build_forecastability_fingerprint",
]
