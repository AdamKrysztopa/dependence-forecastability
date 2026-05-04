"""Deterministic routing for extended forecastability fingerprints."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from forecastability.services.forecastability_profile_service import build_forecastability_profile
from forecastability.triage.extended_forecastability import (
    ExtendedForecastabilityFingerprint,
    ExtendedForecastabilityProfile,
    NoiseRiskLabel,
    PredictabilitySourceLabel,
    RoutingMetadataValue,
    SignalStrengthLabel,
)
from forecastability.triage.forecastability_profile import ForecastabilityProfile
from forecastability.utils.types import AmiInformationGeometry

_NONLINEAR_AVOID_FAMILIES: tuple[str, ...] = (
    "tree_on_lags",
    "tcn",
    "nbeats",
    "nhits",
    "nonlinear_tabular",
)
_SEASONAL_FAMILIES: tuple[str, ...] = (
    "seasonal_naive",
    "harmonic_regression",
    "tbats",
    "seasonal_state_space",
)
_LAG_FAMILIES: tuple[str, ...] = (
    "arima",
    "ets",
    "linear_state_space",
)
_TREND_FAMILIES: tuple[str, ...] = (
    "differenced_arima",
    "linear_state_space",
    "local_linear_trend",
)
_ORDINAL_FAMILIES: tuple[str, ...] = (
    "tree_on_lags",
    "nonlinear_tabular",
    "tcn",
)
_LONG_MEMORY_FAMILIES: tuple[str, ...] = (
    "long_window_ar",
    "fractional_differencing_candidate",
)


class ExtendedForecastabilityRoutingConfig(BaseModel):
    """Versioned thresholds for the extended forecastability router."""

    model_config = ConfigDict(frozen=True)

    lag_signal_to_noise_min: float = Field(default=0.25, ge=0.0, le=1.0)
    lag_information_horizon_min: int = Field(default=3, ge=1)
    spectral_predictability_min: float = Field(default=0.45, ge=0.0, le=1.0)
    spectral_concentration_min: float = Field(default=0.45, ge=0.0, le=1.0)
    seasonality_strength_min: float = Field(default=0.45, ge=0.0, le=1.0)
    trend_strength_min: float = Field(default=0.55, ge=0.0, le=1.0)
    ordinal_redundancy_min: float = Field(default=0.20, ge=0.0, le=1.0)
    long_memory_alpha_min: float = Field(default=0.60, ge=0.0)
    low_spectral_predictability_max: float = Field(default=0.25, ge=0.0, le=1.0)
    low_trend_strength_max: float = Field(default=0.20, ge=0.0, le=1.0)
    low_seasonality_strength_max: float = Field(default=0.20, ge=0.0, le=1.0)
    low_acf1_abs_max: float = Field(default=0.20, ge=0.0, le=1.0)
    policy_version: str = "v0.4.2"


class ExtendedForecastabilityRoutingDecision(BaseModel):
    """Composite routing output used by the extended analysis use case."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    profile: ExtendedForecastabilityProfile
    metadata: dict[str, RoutingMetadataValue] = Field(default_factory=dict)


def _coerce_raw_curve(geometry: AmiInformationGeometry) -> np.ndarray:
    """Return a conservative raw AMI curve from the geometry payload."""
    values = [0.0 if point.ami_raw is None else float(point.ami_raw) for point in geometry.curve]
    return np.asarray(values, dtype=float)


def _base_profile_from_fingerprint(
    fingerprint: ExtendedForecastabilityFingerprint,
) -> ForecastabilityProfile:
    """Build the parent AMI-first profile from geometry when available."""
    geometry = fingerprint.information_geometry
    if geometry is None or len(geometry.curve) == 0:
        return build_forecastability_profile(np.asarray([], dtype=float))

    sig_raw_lags = np.asarray(geometry.informative_horizons, dtype=int) - 1
    return build_forecastability_profile(
        _coerce_raw_curve(geometry),
        sig_raw_lags=sig_raw_lags,
    )


def _lag_dependence_source(
    fingerprint: ExtendedForecastabilityFingerprint,
    *,
    config: ExtendedForecastabilityRoutingConfig,
) -> bool:
    """Return whether AMI geometry supports a lag-dependence source."""
    geometry = fingerprint.information_geometry
    if geometry is None:
        return False
    return (
        geometry.information_horizon >= config.lag_information_horizon_min
        and geometry.signal_to_noise >= config.lag_signal_to_noise_min
        and len(geometry.informative_horizons) > 0
    )


def _spectral_concentration_source(
    fingerprint: ExtendedForecastabilityFingerprint,
    *,
    config: ExtendedForecastabilityRoutingConfig,
) -> bool:
    """Return whether the spectral block shows concentrated periodic structure."""
    spectral = fingerprint.spectral
    if spectral is None:
        return False
    return (
        spectral.spectral_predictability >= config.spectral_predictability_min
        and spectral.spectral_concentration >= config.spectral_concentration_min
        and spectral.periodicity_hint in {"moderate", "strong"}
    )


def _seasonality_source(
    fingerprint: ExtendedForecastabilityFingerprint,
    *,
    config: ExtendedForecastabilityRoutingConfig,
) -> bool:
    """Return whether the classical block supports a seasonality source."""
    classical = fingerprint.classical
    if classical is None or classical.seasonal_strength is None:
        return False
    return classical.seasonal_strength >= config.seasonality_strength_min


def _trend_source(
    fingerprint: ExtendedForecastabilityFingerprint,
    *,
    config: ExtendedForecastabilityRoutingConfig,
) -> bool:
    """Return whether the classical block shows trend-dominated structure."""
    classical = fingerprint.classical
    if classical is None or classical.trend_strength is None:
        return False
    return (
        classical.trend_strength >= config.trend_strength_min
        and classical.stationarity_hint == "trend_nonstationary"
    )


def _ordinal_source(
    fingerprint: ExtendedForecastabilityFingerprint,
    *,
    config: ExtendedForecastabilityRoutingConfig,
) -> bool:
    """Return whether the ordinal block indicates redundant nonlinear structure."""
    ordinal = fingerprint.ordinal
    if ordinal is None:
        return False
    return (
        ordinal.ordinal_redundancy >= config.ordinal_redundancy_min
        and ordinal.complexity_class in {"structured_nonlinear", "complex_but_redundant"}
    )


def _memory_notes_are_unstable(fingerprint: ExtendedForecastabilityFingerprint) -> bool:
    """Return whether the memory block surfaced an unstable-fit caveat."""
    memory = fingerprint.memory
    if memory is None:
        return False
    return any("unstable" in note.lower() for note in memory.notes)


def _long_memory_source(
    fingerprint: ExtendedForecastabilityFingerprint,
    *,
    config: ExtendedForecastabilityRoutingConfig,
) -> bool:
    """Return whether the memory block indicates persistent dependence across scales."""
    memory = fingerprint.memory
    if memory is None or memory.dfa_alpha is None:
        return False
    if _memory_notes_are_unstable(fingerprint):
        return False
    if _seasonality_source(fingerprint, config=config):
        return False
    if _spectral_concentration_source(fingerprint, config=config):
        return False
    return memory.dfa_alpha >= config.long_memory_alpha_min and memory.memory_type in {
        "persistent",
        "long_memory_candidate",
    }


def _predictability_sources(
    fingerprint: ExtendedForecastabilityFingerprint,
    *,
    config: ExtendedForecastabilityRoutingConfig,
) -> tuple[PredictabilitySourceLabel, ...]:
    """Collect predictability sources in the public contract order."""
    ordered_checks: tuple[tuple[PredictabilitySourceLabel, bool], ...] = (
        ("lag_dependence", _lag_dependence_source(fingerprint, config=config)),
        (
            "spectral_concentration",
            _spectral_concentration_source(fingerprint, config=config),
        ),
        ("seasonality", _seasonality_source(fingerprint, config=config)),
        ("trend", _trend_source(fingerprint, config=config)),
        ("ordinal_redundancy", _ordinal_source(fingerprint, config=config)),
        ("long_memory", _long_memory_source(fingerprint, config=config)),
    )
    return tuple(label for label, fired in ordered_checks if fired)


def _all_notes(fingerprint: ExtendedForecastabilityFingerprint) -> list[str]:
    """Collect notes across enabled diagnostic blocks for conservative routing."""
    note_groups = (
        fingerprint.spectral.notes if fingerprint.spectral is not None else [],
        fingerprint.ordinal.notes if fingerprint.ordinal is not None else [],
        fingerprint.classical.notes if fingerprint.classical is not None else [],
        fingerprint.memory.notes if fingerprint.memory is not None else [],
    )
    out: list[str] = []
    for group in note_groups:
        out.extend(group)
    return out


def _all_notes_point_to_instability(fingerprint: ExtendedForecastabilityFingerprint) -> bool:
    """Return whether all surfaced notes indicate low-information instability."""
    notes = _all_notes(fingerprint)
    if not notes:
        return False
    lowered = [note.lower() for note in notes]
    return all(
        "too short" in note or "constant series" in note or "unstable" in note for note in lowered
    )


def _signal_strength(
    fingerprint: ExtendedForecastabilityFingerprint,
    *,
    sources: tuple[PredictabilitySourceLabel, ...],
) -> SignalStrengthLabel:
    """Classify top-level signal strength conservatively."""
    if len(sources) == 0:
        return "unclear" if _all_notes_point_to_instability(fingerprint) else "low"

    geometry = fingerprint.information_geometry
    strong_ami = geometry is not None and (
        geometry.signal_to_noise >= 0.55 or geometry.information_horizon >= 6
    )
    spectral = fingerprint.spectral
    strong_spectral = spectral is not None and spectral.periodicity_hint == "strong"
    if strong_ami or len(sources) >= 3 or (len(sources) >= 2 and strong_spectral):
        return "high"
    return "medium"


def _noise_vote_count(
    fingerprint: ExtendedForecastabilityFingerprint,
    *,
    config: ExtendedForecastabilityRoutingConfig,
) -> int:
    """Count conservative noise-like signals across the enabled blocks."""
    votes = 0
    spectral = fingerprint.spectral
    if spectral is not None and (
        spectral.spectral_predictability <= config.low_spectral_predictability_max
        and spectral.periodicity_hint == "none"
    ):
        votes += 1

    ordinal = fingerprint.ordinal
    if ordinal is not None and ordinal.complexity_class == "noise_like":
        votes += 1

    classical = fingerprint.classical
    if classical is not None:
        acf1_abs = abs(classical.acf1) if classical.acf1 is not None else 0.0
        trend_strength = classical.trend_strength or 0.0
        seasonal_strength = classical.seasonal_strength or 0.0
        if (
            acf1_abs <= config.low_acf1_abs_max
            and trend_strength <= config.low_trend_strength_max
            and seasonal_strength <= config.low_seasonality_strength_max
        ):
            votes += 1

    memory = fingerprint.memory
    if memory is not None and memory.memory_type in {"short_memory", "unclear"}:
        votes += 1

    return votes


def _noise_risk(
    fingerprint: ExtendedForecastabilityFingerprint,
    *,
    config: ExtendedForecastabilityRoutingConfig,
    sources: tuple[PredictabilitySourceLabel, ...],
) -> NoiseRiskLabel:
    """Classify noise risk from weak or contradictory structure evidence."""
    if len(sources) == 0 and _all_notes_point_to_instability(fingerprint):
        return "unclear"

    noise_votes = _noise_vote_count(fingerprint, config=config)
    if len(sources) == 0:
        return "high" if noise_votes >= 2 else "medium"
    if noise_votes == 0:
        return "low"
    return "medium"


def _supports_nonlinear_followup(
    *,
    sources: tuple[PredictabilitySourceLabel, ...],
) -> bool:
    """Return whether nonlinear families have sufficient AMI/lag support."""
    return "lag_dependence" in sources and "ordinal_redundancy" in sources


def _descriptive_only_summary() -> str:
    """Return the profile summary used when AMI geometry is intentionally disabled."""
    return "AMI geometry was intentionally disabled; extended diagnostics are descriptive-only."


def _descriptive_only_summary_for_reason(*, ami_geometry_requested: bool) -> str:
    """Return the descriptive-only summary for disabled versus unavailable geometry."""
    if not ami_geometry_requested:
        return _descriptive_only_summary()
    return (
        "AMI geometry was unavailable for this series; extended diagnostics are descriptive-only."
    )


def _descriptive_only_model_now() -> str:
    """Return the model_now message used for diagnostics-only routing."""
    return (
        "DIAGNOSTIC ONLY — AMI geometry was intentionally disabled; no model-family "
        "routing emitted."
    )


def _descriptive_only_model_now_for_reason(*, ami_geometry_requested: bool) -> str:
    """Return the diagnostics-only model_now message for the geometry reason."""
    if not ami_geometry_requested:
        return _descriptive_only_model_now()
    return (
        "DIAGNOSTIC ONLY — AMI geometry was unavailable for this series; no "
        "model-family routing emitted."
    )


def _extend_unique(items: list[str], candidates: Iterable[str]) -> None:
    """Append candidate items while preserving order and uniqueness."""
    for candidate in candidates:
        if candidate not in items:
            items.append(candidate)


def _recommended_model_families(
    *,
    sources: tuple[PredictabilitySourceLabel, ...],
    diagnostics_only: bool,
) -> list[str]:
    """Build a deterministic recommended-family shortlist from fired sources."""
    if diagnostics_only:
        return []
    if len(sources) == 0:
        return ["naive", "seasonal_naive", "downscope"]

    recommended: list[str] = []
    for source in sources:
        if source == "lag_dependence":
            _extend_unique(recommended, _LAG_FAMILIES)
        elif source == "spectral_concentration":
            _extend_unique(recommended, ("harmonic_regression", "tbats"))
        elif source == "seasonality":
            _extend_unique(recommended, _SEASONAL_FAMILIES)
        elif source == "trend":
            _extend_unique(recommended, _TREND_FAMILIES)
        elif source == "ordinal_redundancy" and _supports_nonlinear_followup(sources=sources):
            _extend_unique(recommended, _ORDINAL_FAMILIES)
        elif source == "long_memory":
            _extend_unique(recommended, _LONG_MEMORY_FAMILIES)
    return recommended


def _avoid_model_families(
    *,
    sources: tuple[PredictabilitySourceLabel, ...],
    noise_risk: str,
    diagnostics_only: bool,
) -> list[str]:
    """Build a conservative avoid-list when evidence argues against a family search."""
    if diagnostics_only:
        return []

    nonlinear_followup = _supports_nonlinear_followup(sources=sources)
    avoid: list[str] = []
    if len(sources) == 0 or noise_risk == "high":
        _extend_unique(avoid, _NONLINEAR_AVOID_FAMILIES)
        _extend_unique(avoid, ("tbats",))
        return avoid

    if not nonlinear_followup:
        _extend_unique(avoid, _NONLINEAR_AVOID_FAMILIES)
    if "seasonality" not in sources and "spectral_concentration" not in sources:
        _extend_unique(avoid, ("tbats",))
    return avoid


def _spectral_period_text(fingerprint: ExtendedForecastabilityFingerprint) -> str:
    """Render dominant periods deterministically for explanation text."""
    spectral = fingerprint.spectral
    if spectral is None or len(spectral.dominant_periods) == 0:
        return ""
    periods = ", ".join(str(period) for period in spectral.dominant_periods[:3])
    return f" near period(s) {periods}"


def _explanation(
    fingerprint: ExtendedForecastabilityFingerprint,
    *,
    sources: tuple[PredictabilitySourceLabel, ...],
    ami_geometry_requested: bool,
) -> list[str]:
    """Build deterministic explanation strings for each fired rule."""
    lines: list[str] = []
    geometry = fingerprint.information_geometry
    diagnostics_only = not ami_geometry_requested or geometry is None
    nonlinear_followup = _supports_nonlinear_followup(sources=sources)

    if not ami_geometry_requested:
        lines.append(
            "AMI-first view: lag geometry was intentionally disabled, so this fingerprint "
            "is descriptive-only and emits no model-family routing."
        )
    elif geometry is None:
        lines.append(
            "AMI-first view: lag geometry was unavailable for this series, likely because "
            "it was too short or degenerate, so this fingerprint is descriptive-only and "
            "emits no model-family routing."
        )
    elif "lag_dependence" in sources:
        lines.append(
            "AMI-first view: informative lag structure extends to horizon "
            f"{geometry.information_horizon} with signal-to-noise {geometry.signal_to_noise:.2f}."
        )
    else:
        lines.append("AMI-first view: no stable informative lag structure was detected.")

    if "spectral_concentration" in sources and fingerprint.spectral is not None:
        spectral = fingerprint.spectral
        lines.append(
            "Spectral predictability is "
            f"{spectral.spectral_predictability:.2f} with concentrated frequency power"
            f"{_spectral_period_text(fingerprint)}."
        )

    if "seasonality" in sources and fingerprint.classical is not None:
        seasonal_strength = fingerprint.classical.seasonal_strength
        assert seasonal_strength is not None
        if diagnostics_only:
            lines.append(
                f"Seasonality strength is {seasonal_strength:.2f}; classical seasonal "
                "structure is visible in the diagnostic blocks."
            )
        else:
            lines.append(
                f"Seasonality strength is {seasonal_strength:.2f}; validate seasonal "
                "baselines before richer search."
            )

    if "trend" in sources and fingerprint.classical is not None:
        trend_strength = fingerprint.classical.trend_strength
        assert trend_strength is not None
        if diagnostics_only:
            lines.append(
                f"Trend strength is {trend_strength:.2f} with trend-nonstationary "
                "classical cues in the diagnostic blocks."
            )
        else:
            lines.append(
                f"Trend strength is {trend_strength:.2f}; review differencing or "
                "trend-aware state-space baselines first."
            )

    if "ordinal_redundancy" in sources and fingerprint.ordinal is not None:
        ordinal = fingerprint.ordinal
        if diagnostics_only or not nonlinear_followup:
            lines.append(
                "Ordinal redundancy is "
                f"{ordinal.ordinal_redundancy:.2f} with complexity class "
                f"'{ordinal.complexity_class}', but without sufficient "
                "AMI/lag support it remains descriptive rather than a "
                "nonlinear recommendation."
            )
        else:
            lines.append(
                "Ordinal redundancy is "
                f"{ordinal.ordinal_redundancy:.2f} with complexity class "
                f"'{ordinal.complexity_class}', so nonlinear lag models are "
                "worth a targeted follow-up only after simpler baselines."
            )

    if "long_memory" in sources and fingerprint.memory is not None:
        memory = fingerprint.memory
        assert memory.dfa_alpha is not None
        if diagnostics_only:
            lines.append(
                f"DFA alpha is {memory.dfa_alpha:.2f} with memory type '{memory.memory_type}'; "
                "treat this as descriptive because AMI-first routing is unavailable."
            )
        else:
            lines.append(
                f"DFA alpha is {memory.dfa_alpha:.2f} with memory type '{memory.memory_type}', "
                "which justifies conservative long-window review."
            )

    if len(sources) == 0:
        if diagnostics_only:
            geometry_status = (
                "intentionally disabled" if not ami_geometry_requested else "unavailable"
            )
            lines.append(
                f"With AMI geometry {geometry_status} and no strong secondary signatures, "
                "keep this fingerprint descriptive-only."
            )
        else:
            lines.append(
                "All enabled diagnostics are weak or noise-like; start with naive baselines "
                "and avoid expensive black-box search."
            )
    return lines


def build_extended_forecastability_profile(
    fingerprint: ExtendedForecastabilityFingerprint,
    *,
    config: ExtendedForecastabilityRoutingConfig | None = None,
    ami_geometry_requested: bool = True,
) -> ExtendedForecastabilityRoutingDecision:
    """Build an AMI-first extended routing profile from the composite fingerprint.

    Args:
        fingerprint: Composite extended fingerprint produced by the Phase 1 diagnostics.
        config: Optional routing-threshold configuration.
        ami_geometry_requested: Whether the caller intentionally enabled the
            AMI geometry block. When ``False``, routing becomes descriptive-only.

    Returns:
        Routing decision with the additive extended profile and JSON-safe metadata.
    """
    resolved_config = config if config is not None else ExtendedForecastabilityRoutingConfig()
    diagnostics_only = not ami_geometry_requested or fingerprint.information_geometry is None
    parent_profile = _base_profile_from_fingerprint(fingerprint)
    sources = _predictability_sources(fingerprint, config=resolved_config)
    signal_strength = _signal_strength(fingerprint, sources=sources)
    noise_risk = _noise_risk(fingerprint, config=resolved_config, sources=sources)
    recommended_model_families = _recommended_model_families(
        sources=sources,
        diagnostics_only=diagnostics_only,
    )
    avoid_model_families = _avoid_model_families(
        sources=sources,
        noise_risk=noise_risk,
        diagnostics_only=diagnostics_only,
    )
    explanation = _explanation(
        fingerprint,
        sources=sources,
        ami_geometry_requested=ami_geometry_requested,
    )

    profile = ExtendedForecastabilityProfile(
        horizons=parent_profile.horizons,
        values=parent_profile.values,
        epsilon=parent_profile.epsilon,
        informative_horizons=parent_profile.informative_horizons,
        peak_horizon=parent_profile.peak_horizon,
        is_non_monotone=parent_profile.is_non_monotone,
        summary=(
            _descriptive_only_summary_for_reason(
                ami_geometry_requested=ami_geometry_requested,
            )
            if diagnostics_only
            else parent_profile.summary
        ),
        model_now=(
            _descriptive_only_model_now_for_reason(
                ami_geometry_requested=ami_geometry_requested,
            )
            if diagnostics_only
            else parent_profile.model_now
        ),
        review_horizons=parent_profile.review_horizons,
        avoid_horizons=parent_profile.avoid_horizons,
        signal_strength=signal_strength,
        predictability_sources=sources,
        noise_risk=noise_risk,
        recommended_model_families=recommended_model_families,
        avoid_model_families=avoid_model_families,
        explanation=explanation,
    )
    return ExtendedForecastabilityRoutingDecision(
        profile=profile,
        metadata={
            "policy_version": resolved_config.policy_version,
            "ami_geometry_requested": ami_geometry_requested,
            "ami_geometry_available": fingerprint.information_geometry is not None,
            "descriptive_only": diagnostics_only,
            "predictability_source_count": len(sources),
            "has_nonlinear_followup": (
                _supports_nonlinear_followup(sources=sources) and not diagnostics_only
            ),
            "signal_strength": signal_strength,
            "noise_risk": noise_risk,
        },
    )


__all__ = [
    "ExtendedForecastabilityRoutingConfig",
    "ExtendedForecastabilityRoutingDecision",
    "build_extended_forecastability_profile",
]
