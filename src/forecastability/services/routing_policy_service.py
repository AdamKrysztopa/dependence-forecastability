"""Deterministic routing policy for geometry-backed forecastability fingerprints."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field

from forecastability.services.fingerprint_service import FingerprintThresholdConfig
from forecastability.utils.types import (
    ForecastabilityFingerprint,
    ModelFamilyLabel,
    RoutingConfidenceLabel,
    RoutingRecommendation,
)

_LINEAR_FAMILIES: frozenset[str] = frozenset(
    {"arima", "ets", "linear_state_space", "dynamic_regression"}
)
_NONLINEAR_FAMILIES: frozenset[str] = frozenset(
    {"tree_on_lags", "tcn", "nbeats", "nhits", "nonlinear_tabular"}
)


class RoutingPolicyConfig(BaseModel):
    """Versioned thresholds for model-family routing."""

    model_config = ConfigDict(frozen=True)

    low_mass_max: float = Field(default=0.03, ge=0.0)
    high_mass_min: float = Field(default=0.10, ge=0.0)
    short_horizon_max: int = Field(default=3, ge=1)
    high_nonlinear_share_min: float = Field(default=0.30, ge=0.0, le=1.0)
    high_directness_min: float = Field(default=0.60, ge=0.0, le=1.0)
    near_threshold_margin: float = Field(default=0.01, ge=0.0)
    policy_version: str = "v0.3.1"


RoutingThresholdConfig = RoutingPolicyConfig


def _validate_directness_ratio(directness_ratio: float | None) -> None:
    """Validate optional directness ratio at the routing seam."""
    if directness_ratio is None:
        return
    if not math.isfinite(directness_ratio) or not (0.0 <= directness_ratio <= 1.0):
        raise ValueError("directness_ratio must be finite and within [0.0, 1.0]")


def _metadata_flag(value: str | int | float | None) -> bool:
    """Parse heterogeneous metadata flags into a robust boolean."""
    if value is None:
        return False
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "t", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "f", "no", "n", "off", ""}:
            return False
        return False
    return bool(value)


def _threshold_margin_penalty(
    fingerprint: ForecastabilityFingerprint,
    *,
    config: RoutingPolicyConfig,
) -> int:
    """Flag borderline scalar decisions around versioned thresholds."""
    threshold_pairs = [
        (fingerprint.information_mass, config.low_mass_max),
        (fingerprint.information_mass, config.high_mass_min),
        (fingerprint.nonlinear_share, config.high_nonlinear_share_min),
    ]
    if fingerprint.directness_ratio is not None:
        threshold_pairs.append((fingerprint.directness_ratio, config.high_directness_min))
    for value, threshold in threshold_pairs:
        if abs(value - threshold) <= config.near_threshold_margin:
            return 1
    return 0


def _classifier_used_tiebreak(fingerprint: ForecastabilityFingerprint) -> bool:
    """Return True when the upstream classifier recorded a deterministic tie-break."""
    return _metadata_flag(fingerprint.metadata.get("classifier_used_tiebreak"))


def _select_route(
    fingerprint: ForecastabilityFingerprint,
    *,
    config: RoutingPolicyConfig,
) -> tuple[list[ModelFamilyLabel], list[ModelFamilyLabel], list[str]]:
    """Select primary families, secondary families, and rationale."""
    if (
        fingerprint.information_structure == "none"
        or fingerprint.information_mass <= config.low_mass_max
    ):
        return (
            ["naive", "seasonal_naive", "downscope"],
            [],
            ["Low information mass or no informative structure detected."],
        )

    if (
        fingerprint.information_structure == "periodic"
        and fingerprint.nonlinear_share < config.high_nonlinear_share_min
    ):
        return (
            ["seasonal_naive", "harmonic_regression", "tbats"],
            ["seasonal_state_space"],
            ["Stable repeated informative peaks indicate seasonal structure."],
        )

    if (
        fingerprint.information_structure == "monotonic"
        and fingerprint.nonlinear_share < config.high_nonlinear_share_min
        and (
            fingerprint.directness_ratio is None
            or fingerprint.directness_ratio >= config.high_directness_min
        )
    ):
        return (
            ["arima", "ets", "linear_state_space"],
            ["dynamic_regression"],
            ["Mostly linear monotonic decay with strong direct lag structure."],
        )

    if (
        fingerprint.information_structure == "monotonic"
        and fingerprint.nonlinear_share < config.high_nonlinear_share_min
    ):
        return (
            ["arima", "ets"],
            ["linear_state_space", "dynamic_regression"],
            [
                "Monotonic dependence is present, but weaker directness suggests richer "
                "state review."
            ],
        )

    return (
        ["tree_on_lags", "tcn", "nbeats", "nhits"],
        ["nonlinear_tabular"],
        ["Mixed structure or nonlinear excess suggests richer nonlinear families."],
    )


def _signal_conflict_penalty(
    fingerprint: ForecastabilityFingerprint,
    *,
    primary_families: list[ModelFamilyLabel],
    config: RoutingPolicyConfig,
) -> int:
    """Detect contradictions between the selected route and supporting signals."""
    linear_route = any(item in _LINEAR_FAMILIES for item in primary_families) and not any(
        item in _NONLINEAR_FAMILIES for item in primary_families
    )
    nonlinear_route = any(item in _NONLINEAR_FAMILIES for item in primary_families) and not any(
        item in _LINEAR_FAMILIES for item in primary_families
    )

    if (
        linear_route
        and fingerprint.nonlinear_share >= config.high_nonlinear_share_min
        and fingerprint.information_mass >= config.high_mass_min
    ):
        return 1
    if (
        nonlinear_route
        and fingerprint.information_structure == "periodic"
        and fingerprint.nonlinear_share < config.high_nonlinear_share_min
    ):
        return 1
    if (
        fingerprint.information_structure == "periodic"
        and 0 < fingerprint.information_horizon < 2 * config.short_horizon_max
    ):
        return 1
    return 0


def _low_signal_quality_penalty(
    fingerprint: ForecastabilityFingerprint,
    *,
    fingerprint_config: FingerprintThresholdConfig,
) -> int:
    """Down-rank confidence when the corrected-profile margin above tau is weak."""
    if fingerprint.information_structure == "none":
        return 0
    return int(
        fingerprint.signal_to_noise < fingerprint_config.low_signal_to_noise_confidence_threshold
    )


def _taxonomy_uncertainty_penalty(
    fingerprint: ForecastabilityFingerprint,
    *,
    fingerprint_config: FingerprintThresholdConfig,
) -> int:
    """Penalize mixed/tie-break/low-support cases."""
    too_few_horizons = (
        fingerprint.information_structure != "none"
        and len(fingerprint.informative_horizons) < fingerprint_config.min_confident_horizons
    )
    return int(
        fingerprint.information_structure == "mixed"
        or _classifier_used_tiebreak(fingerprint)
        or too_few_horizons
    )


def _confidence_from_penalties(penalty_sum: int) -> RoutingConfidenceLabel:
    """Map the deterministic penalty sum to a confidence label."""
    if penalty_sum == 0:
        return "high"
    if penalty_sum == 1:
        return "medium"
    return "low"


def _build_caution_flags(
    fingerprint: ForecastabilityFingerprint,
    *,
    config: RoutingPolicyConfig,
    fingerprint_config: FingerprintThresholdConfig,
    threshold_margin_penalty: int,
    signal_conflict_penalty: int,
) -> list[str]:
    """Build the caution-flag surface from fingerprint and penalty state."""
    caution_flags: list[str] = []

    if threshold_margin_penalty:
        caution_flags.append("near_threshold")
    if fingerprint.information_structure == "mixed":
        caution_flags.append("mixed_structure")
    if (
        fingerprint.directness_ratio is not None
        and fingerprint.directness_ratio < config.high_directness_min
    ):
        caution_flags.append("low_directness")
    if fingerprint.nonlinear_share >= config.high_nonlinear_share_min:
        caution_flags.append("high_nonlinear_share")
    if 0 < fingerprint.information_horizon <= config.short_horizon_max:
        caution_flags.append("short_information_horizon")
    if (
        fingerprint.information_structure != "none"
        and len(fingerprint.informative_horizons) < fingerprint_config.min_confident_horizons
    ):
        caution_flags.append("weak_informative_support")
    if signal_conflict_penalty:
        caution_flags.append("signal_conflict")
    if fingerprint.information_structure != "none" and (
        fingerprint.signal_to_noise < fingerprint_config.low_signal_to_noise_confidence_threshold
    ):
        caution_flags.append("low_signal_to_noise")
    if _metadata_flag(fingerprint.metadata.get("geometry_threshold_borderline")):
        caution_flags.append("geometry_threshold_borderline")

    return sorted(set(caution_flags))


def route_fingerprint(
    fingerprint: ForecastabilityFingerprint,
    *,
    config: RoutingPolicyConfig | None = None,
    fingerprint_config: FingerprintThresholdConfig | None = None,
) -> RoutingRecommendation:
    """Map a geometry-backed fingerprint to deterministic model-family guidance."""
    _validate_directness_ratio(fingerprint.directness_ratio)
    resolved_config = config if config is not None else RoutingPolicyConfig()
    resolved_fingerprint_config = (
        fingerprint_config if fingerprint_config is not None else FingerprintThresholdConfig()
    )
    primary_families, secondary_families, rationale = _select_route(
        fingerprint,
        config=resolved_config,
    )

    threshold_margin_penalty = _threshold_margin_penalty(
        fingerprint,
        config=resolved_config,
    )
    taxonomy_uncertainty_penalty = _taxonomy_uncertainty_penalty(
        fingerprint,
        fingerprint_config=resolved_fingerprint_config,
    )
    signal_conflict_penalty = _signal_conflict_penalty(
        fingerprint,
        primary_families=primary_families,
        config=resolved_config,
    )
    low_signal_quality_penalty = _low_signal_quality_penalty(
        fingerprint,
        fingerprint_config=resolved_fingerprint_config,
    )
    penalty_sum = (
        threshold_margin_penalty
        + taxonomy_uncertainty_penalty
        + signal_conflict_penalty
        + low_signal_quality_penalty
    )
    confidence_label = _confidence_from_penalties(penalty_sum)
    caution_flags = _build_caution_flags(
        fingerprint,
        config=resolved_config,
        fingerprint_config=resolved_fingerprint_config,
        threshold_margin_penalty=threshold_margin_penalty,
        signal_conflict_penalty=signal_conflict_penalty,
    )

    return RoutingRecommendation(
        primary_families=primary_families,
        secondary_families=secondary_families,
        rationale=rationale,
        caution_flags=caution_flags,  # type: ignore[arg-type]
        confidence_label=confidence_label,
        metadata={
            "policy_version": resolved_config.policy_version,
            "threshold_margin_penalty": threshold_margin_penalty,
            "taxonomy_uncertainty_penalty": taxonomy_uncertainty_penalty,
            "signal_conflict_penalty": signal_conflict_penalty,
            "low_signal_quality_penalty": low_signal_quality_penalty,
        },
    )


def build_routing_recommendation(
    fingerprint: ForecastabilityFingerprint,
    *,
    config: RoutingPolicyConfig | None = None,
    fingerprint_config: FingerprintThresholdConfig | None = None,
) -> RoutingRecommendation:
    """Compatibility alias for the geometry-aware routing policy."""
    return route_fingerprint(
        fingerprint,
        config=config,
        fingerprint_config=fingerprint_config,
    )


recommend_model_families = build_routing_recommendation


__all__ = [
    "RoutingPolicyConfig",
    "RoutingThresholdConfig",
    "build_routing_recommendation",
    "recommend_model_families",
    "route_fingerprint",
]
