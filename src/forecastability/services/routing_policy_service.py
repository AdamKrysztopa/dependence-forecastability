"""Routing policy service for V3_1-F03.

Maps a ForecastabilityFingerprint to a RoutingRecommendation using deterministic
bucket rules and a penalty-based confidence system.

NON-GOAL: Routing is heuristic product guidance. It is NOT empirical model
selection, a ranking guarantee, or a performance promise.
"""

from __future__ import annotations

from dataclasses import dataclass

from forecastability.utils.types import (
    ForecastabilityFingerprint,
    ModelFamilyLabel,
    RoutingCautionFlag,
    RoutingConfidenceLabel,
    RoutingRecommendation,
)

# ---------------------------------------------------------------------------
# Versioned configuration
# ---------------------------------------------------------------------------

_LINEAR_FAMILIES: frozenset[str] = frozenset(
    {
        "arima",
        "ets",
        "linear_state_space",
        "dynamic_regression",
        "seasonal_naive",
        "tbats",
        "seasonal_state_space",
        "harmonic_regression",
    }
)

_NONLINEAR_FAMILIES: frozenset[str] = frozenset(
    {"tree_on_lags", "tcn", "nbeats", "nhits", "nonlinear_tabular"}
)


@dataclass(frozen=True, slots=True)
class RoutingPolicyConfig:
    """Versioned threshold configuration for routing policy.

    Attributes:
        mass_high_threshold: Minimum information_mass to classify as high mass.
        nonlinear_share_high_threshold: Minimum nonlinear_share for high-nl routing.
        directness_ratio_low_threshold: directness_ratio below this → low directness.
        margin_band: Fractional margin around each threshold for near_threshold detection.
        min_confident_horizons: Minimum informative horizons for full confidence.
        min_information_horizon: Minimum horizon for non-short classification.
        policy_version: Semantic version tag for this policy configuration.
    """

    mass_high_threshold: float = 0.05
    nonlinear_share_high_threshold: float = 0.3
    directness_ratio_low_threshold: float = 0.4
    margin_band: float = 0.1
    min_confident_horizons: int = 3
    min_information_horizon: int = 3
    policy_version: str = "v0.3.1"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _RoutingFlags:
    """Derived boolean flags from fingerprint + config thresholds.

    Attributes:
        is_high_mass: True when information_mass >= mass_high_threshold.
        is_high_nl: True when nonlinear_share >= nonlinear_share_high_threshold.
        is_high_directness: True when directness_ratio >= directness_ratio_low_threshold.
            Always False when directness_ratio is None.
    """

    is_high_mass: bool
    is_high_nl: bool
    is_high_directness: bool


def _derive_flags(
    fingerprint: ForecastabilityFingerprint,
    *,
    config: RoutingPolicyConfig,
) -> _RoutingFlags:
    """Derive boolean routing flags from fingerprint scalars.

    Args:
        fingerprint: Forecastability fingerprint to evaluate.
        config: Routing policy thresholds.

    Returns:
        Frozen set of derived boolean flags.
    """
    is_high_mass = fingerprint.information_mass >= config.mass_high_threshold
    is_high_nl = fingerprint.nonlinear_share >= config.nonlinear_share_high_threshold
    dr = fingerprint.directness_ratio
    is_high_directness = dr is not None and dr >= config.directness_ratio_low_threshold
    return _RoutingFlags(
        is_high_mass=is_high_mass,
        is_high_nl=is_high_nl,
        is_high_directness=is_high_directness,
    )


def _select_monotonic_families(
    *,
    flags: _RoutingFlags,
) -> tuple[list[ModelFamilyLabel], list[ModelFamilyLabel]]:
    """Select primary and secondary families for monotonic high-mass fingerprints.

    Args:
        flags: Derived routing flags.

    Returns:
        Tuple of (primary_families, secondary_families).
    """
    if flags.is_high_nl:
        return ["tree_on_lags", "nbeats", "nhits"], ["arima"]
    if flags.is_high_directness:
        return ["arima", "ets", "linear_state_space"], ["dynamic_regression"]
    return ["arima", "ets"], ["linear_state_space", "dynamic_regression"]


def _select_families(
    fingerprint: ForecastabilityFingerprint,
    *,
    flags: _RoutingFlags,
) -> tuple[list[ModelFamilyLabel], list[ModelFamilyLabel]]:
    """Select primary and secondary model families based on routing bucket.

    Args:
        fingerprint: Forecastability fingerprint providing structure and mass.
        flags: Derived boolean flags from thresholds.

    Returns:
        Tuple of (primary_families, secondary_families).
    """
    structure = fingerprint.information_structure

    if structure == "none":
        return ["naive", "seasonal_naive", "downscope"], []

    if structure == "periodic":
        return ["seasonal_naive", "tbats", "seasonal_state_space"], ["harmonic_regression"]

    if structure == "monotonic" and flags.is_high_mass:
        return _select_monotonic_families(flags=flags)

    if structure == "mixed" or flags.is_high_nl:
        return ["tree_on_lags", "tcn", "nbeats", "nhits", "nonlinear_tabular"], []

    # low mass, not "none"
    return ["naive", "seasonal_naive"], []


def _is_near_threshold(
    value: float,
    *,
    threshold: float,
    margin_band: float,
) -> bool:
    """Check if a scalar is within the fractional margin of a threshold.

    Args:
        value: Scalar to check.
        threshold: Decision boundary value.
        margin_band: Fractional margin (e.g. 0.1 = 10% of threshold value).

    Returns:
        True if abs(value - threshold) / threshold < margin_band.
    """
    if threshold == 0.0:
        return False
    return abs(value - threshold) / threshold < margin_band


def _compute_threshold_penalty(
    fingerprint: ForecastabilityFingerprint,
    *,
    config: RoutingPolicyConfig,
) -> int:
    """Compute the threshold margin penalty (0 or 1).

    Args:
        fingerprint: Fingerprint to evaluate.
        config: Routing policy configuration.

    Returns:
        1 if any routing-defining scalar is near its threshold, else 0.
    """
    near_mass = _is_near_threshold(
        fingerprint.information_mass,
        threshold=config.mass_high_threshold,
        margin_band=config.margin_band,
    )
    near_nl = _is_near_threshold(
        fingerprint.nonlinear_share,
        threshold=config.nonlinear_share_high_threshold,
        margin_band=config.margin_band,
    )
    dr = fingerprint.directness_ratio
    near_dr = dr is not None and _is_near_threshold(
        dr,
        threshold=config.directness_ratio_low_threshold,
        margin_band=config.margin_band,
    )
    return 1 if (near_mass or near_nl or near_dr) else 0


def _compute_taxonomy_penalty(
    fingerprint: ForecastabilityFingerprint,
    *,
    config: RoutingPolicyConfig,
) -> int:
    """Compute the taxonomy uncertainty penalty (0 or 1).

    Args:
        fingerprint: Fingerprint to evaluate.
        config: Routing policy configuration.

    Returns:
        1 if structure is mixed or too few informative horizons, else 0.
    """
    is_mixed = fingerprint.information_structure == "mixed"
    # "none" is a definitive verdict (zero informative horizons is unambiguous);
    # exempt it from the too_few check to avoid spurious medium confidence.
    too_few = (
        fingerprint.information_structure != "none"
        and len(fingerprint.informative_horizons) < config.min_confident_horizons
    )
    return 1 if (is_mixed or too_few) else 0


def _compute_signal_conflict_penalty(
    fingerprint: ForecastabilityFingerprint,
    *,
    primary_families: list[ModelFamilyLabel],
    config: RoutingPolicyConfig,
) -> int:
    """Compute the signal conflict penalty (0 or 1).

    Args:
        fingerprint: Fingerprint to evaluate.
        primary_families: Selected primary model families.
        config: Routing policy configuration.

    Returns:
        1 if the primary route conflicts with nonlinear share signal, else 0.
    """
    has_linear = any(f in _LINEAR_FAMILIES for f in primary_families)
    has_nonlinear = any(f in _NONLINEAR_FAMILIES for f in primary_families)
    is_linear_route = has_linear and not has_nonlinear
    is_nonlinear_route = has_nonlinear and not has_linear
    is_high_nl = fingerprint.nonlinear_share >= config.nonlinear_share_high_threshold

    linear_but_nl = is_linear_route and is_high_nl
    nonlinear_but_linear_signal = (
        is_nonlinear_route and not is_high_nl and fingerprint.information_structure != "mixed"
    )
    return 1 if (linear_but_nl or nonlinear_but_linear_signal) else 0


def _compute_caution_flags(
    fingerprint: ForecastabilityFingerprint,
    *,
    config: RoutingPolicyConfig,
    threshold_penalty: int,
    signal_penalty: int,
) -> list[RoutingCautionFlag]:
    """Build the list of caution flags for a recommendation.

    Args:
        fingerprint: Fingerprint to evaluate.
        config: Routing policy configuration.
        threshold_penalty: Precomputed threshold margin penalty (0 or 1).
        signal_penalty: Precomputed signal conflict penalty (0 or 1).

    Returns:
        List of applicable caution flags (may be empty).
    """
    flags: list[RoutingCautionFlag] = []

    if threshold_penalty == 1:
        flags.append("near_threshold")

    if fingerprint.information_structure == "mixed":
        flags.append("mixed_structure")

    dr = fingerprint.directness_ratio
    if dr is not None and dr < config.directness_ratio_low_threshold:
        flags.append("low_directness")

    if fingerprint.nonlinear_share >= config.nonlinear_share_high_threshold:
        flags.append("high_nonlinear_share")

    horizon = fingerprint.information_horizon
    if 0 < horizon < config.min_information_horizon:
        flags.append("short_information_horizon")

    if (
        len(fingerprint.informative_horizons) < config.min_confident_horizons
        and fingerprint.information_structure != "none"
    ):
        flags.append("weak_informative_support")

    if signal_penalty == 1:
        flags.append("signal_conflict")

    return flags


def _confidence_from_penalties(penalty_count: int) -> RoutingConfidenceLabel:
    """Map total penalty count to a confidence label.

    Args:
        penalty_count: Total number of triggered penalties (0–3).

    Returns:
        "high" for 0, "medium" for 1, "low" for 2 or 3.
    """
    if penalty_count == 0:
        return "high"
    if penalty_count == 1:
        return "medium"
    return "low"


def _build_rationale(
    fingerprint: ForecastabilityFingerprint,
    *,
    flags: _RoutingFlags,
    primary_families: list[ModelFamilyLabel],
) -> list[str]:
    """Build a non-empty list of human-readable rationale strings.

    Args:
        fingerprint: Fingerprint driving the routing decision.
        flags: Derived boolean flags.
        primary_families: Selected primary families.

    Returns:
        Non-empty list of rationale strings.
    """
    parts: list[str] = []
    structure = fingerprint.information_structure
    parts.append(f"Information structure: {structure!r}.")
    mass_label = "high" if flags.is_high_mass else "low"
    parts.append(
        f"Information mass {fingerprint.information_mass:.4f} ({mass_label} relative to threshold)."
    )
    nl_label = "high" if flags.is_high_nl else "low"
    parts.append(
        f"Nonlinear share {fingerprint.nonlinear_share:.4f} ({nl_label} relative to threshold)."
    )
    parts.append(f"Primary families selected: {primary_families}.")
    return parts


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def route_fingerprint(
    fingerprint: ForecastabilityFingerprint,
    *,
    config: RoutingPolicyConfig | None = None,
) -> RoutingRecommendation:
    """Map a ForecastabilityFingerprint to a RoutingRecommendation.

    NON-GOAL: This function produces heuristic product guidance only.
    It is NOT empirical model selection, a ranking guarantee, or a performance promise.

    Args:
        fingerprint: Compact forecastability profile to route.
        config: Optional routing policy configuration. Defaults to
            ``RoutingPolicyConfig()`` when not provided.

    Returns:
        A frozen RoutingRecommendation with primary/secondary families,
        rationale strings, caution flags, and a confidence label.
    """
    resolved_config = config if config is not None else RoutingPolicyConfig()
    flags = _derive_flags(fingerprint, config=resolved_config)
    primary, secondary = _select_families(fingerprint, flags=flags)

    threshold_penalty = _compute_threshold_penalty(fingerprint, config=resolved_config)
    taxonomy_penalty = _compute_taxonomy_penalty(fingerprint, config=resolved_config)
    signal_penalty = _compute_signal_conflict_penalty(
        fingerprint,
        primary_families=primary,
        config=resolved_config,
    )
    total_penalties = threshold_penalty + taxonomy_penalty + signal_penalty
    confidence = _confidence_from_penalties(total_penalties)
    caution_flags = _compute_caution_flags(
        fingerprint,
        config=resolved_config,
        threshold_penalty=threshold_penalty,
        signal_penalty=signal_penalty,
    )
    rationale = _build_rationale(fingerprint, flags=flags, primary_families=primary)

    return RoutingRecommendation(
        primary_families=primary,
        secondary_families=secondary,
        rationale=rationale,
        caution_flags=caution_flags,
        confidence_label=confidence,
        metadata={"policy_version": resolved_config.policy_version},
    )
