"""Public use case for the geometry-backed forecastability fingerprint workflow."""

from __future__ import annotations

import numpy as np

from forecastability.services.ami_information_geometry_service import (
    AmiInformationGeometryConfig,
    compute_ami_information_geometry,
)
from forecastability.services.fingerprint_service import (
    FingerprintThresholdConfig,
    build_forecastability_fingerprint,
)
from forecastability.services.linear_information_service import compute_linear_information_curve
from forecastability.services.routing_policy_service import (
    RoutingPolicyConfig,
    route_fingerprint,
)
from forecastability.utils.types import FingerprintBundle
from forecastability.utils.validation import validate_time_series


def _validate_directness_ratio(directness_ratio: float | None) -> None:
    """Validate optional directness ratio at the use-case seam."""
    if directness_ratio is None:
        return
    if not np.isfinite(directness_ratio) or not (0.0 <= directness_ratio <= 1.0):
        raise ValueError("directness_ratio must be finite and within [0.0, 1.0]")


def _resolve_geometry_config(
    *,
    max_lag: int,
    n_surrogates: int,
    base_config: AmiInformationGeometryConfig | None,
) -> AmiInformationGeometryConfig:
    """Resolve the geometry config while preserving the public max_lag interface."""
    if base_config is None:
        return AmiInformationGeometryConfig(
            n_surrogates=n_surrogates,
            max_lag_frac=1.0,
            max_horizon=max_lag,
        )
    return AmiInformationGeometryConfig.model_validate(
        {
            **base_config.model_dump(),
            "n_surrogates": n_surrogates,
            "max_lag_frac": 1.0,
            "max_horizon": max_lag,
        }
    )


def run_forecastability_fingerprint(
    series: np.ndarray,
    *,
    target_name: str = "series",
    max_lag: int = 24,
    n_surrogates: int = 99,
    random_state: int = 42,
    ami_floor: float = 0.01,
    directness_ratio: float | None = None,
    geometry_config: AmiInformationGeometryConfig | None = None,
    fingerprint_config: FingerprintThresholdConfig | None = None,
    routing_config: RoutingPolicyConfig | None = None,
) -> FingerprintBundle:
    """Compute geometry, fingerprint, and routing guidance for one series.

    The ``ami_floor`` parameter is retained for backward-compatible call sites,
    but the v0.3.1 geometry-backed workflow does not use local AMI-floor gating.

    For rolling-origin evaluation, callers must pass each origin's training
    window only. This use case intentionally does not perform split logic.
    """
    _validate_directness_ratio(directness_ratio)
    resolved_geometry_config = _resolve_geometry_config(
        max_lag=max_lag,
        n_surrogates=n_surrogates,
        base_config=geometry_config,
    )
    validated = validate_time_series(
        series,
        min_length=max(max_lag + 1, resolved_geometry_config.min_n),
    )
    geometry = compute_ami_information_geometry(
        validated,
        config=resolved_geometry_config,
        random_state=random_state,
    )
    baseline = compute_linear_information_curve(
        validated,
        horizons=[point.horizon for point in geometry.curve if point.valid],
    )
    resolved_fingerprint_config = (
        fingerprint_config if fingerprint_config is not None else FingerprintThresholdConfig()
    )
    fingerprint = build_forecastability_fingerprint(
        geometry=geometry,
        baseline=baseline,
        directness_ratio=directness_ratio,
        config=resolved_fingerprint_config,
    )
    recommendation = route_fingerprint(
        fingerprint,
        config=routing_config,
        fingerprint_config=resolved_fingerprint_config,
    )

    profile_summary: dict[str, str | int | float] = {
        "max_lag": max_lag,
        "evaluated_max_horizon": len(geometry.curve),
        "n_surrogates": n_surrogates,
        "geometry_method": geometry.method,
        "signal_to_noise": geometry.signal_to_noise,
        "geometry_information_horizon": geometry.information_horizon,
        "geometry_information_structure": geometry.information_structure,
        "accepted_horizon_count": len(geometry.informative_horizons),
        "informative_horizons": ",".join(str(item) for item in geometry.informative_horizons),
        "confidence": recommendation.confidence_label,
        "input_window_contract": "train_window_only_for_rolling_origin",
    }

    metadata: dict[str, str | int | float] = {
        "release": "0.3.1",
        "input_window_contract": "train_window_only_for_rolling_origin",
    }
    if ami_floor != 0.01:
        metadata["legacy_ami_floor_ignored"] = ami_floor

    return FingerprintBundle(
        target_name=target_name,
        geometry=geometry,
        fingerprint=fingerprint,
        recommendation=recommendation,
        profile_summary=profile_summary,
        metadata=metadata,
    )
