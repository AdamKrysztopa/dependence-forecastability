"""Use case that builds a framework-agnostic ForecastPrepContract."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import pandas as pd

from forecastability.services import calendar_feature_service
from forecastability.services.calendar_feature_service import generate_calendar_features
from forecastability.services.forecast_prep_mapper import (
    derive_contract_confidence,
    map_covariate_recommendations,
    map_family_recommendations,
    map_target_lag_recommendations,
    validate_covariate_recommendations,
)
from forecastability.utils.types import (
    CovariateRecommendation,
    FingerprintBundle,
    ForecastPrepContract,
    LaggedExogBundle,
    RoutingRecommendation,
)

if TYPE_CHECKING:
    from forecastability.triage.models import TriageResult


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    """Return de-duplicated list while preserving insertion order."""
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _resolve_known_future_driver_names(
    *,
    known_future_drivers: dict[str, bool] | None,
    lagged_exog_bundle: LaggedExogBundle | None,
) -> set[str]:
    """Resolve known-future drivers from user and lagged-exog metadata."""
    known_future: set[str] = set(
        lagged_exog_bundle.known_future_drivers if lagged_exog_bundle else []
    )
    if known_future_drivers is None:
        return known_future

    for name, is_known_future in known_future_drivers.items():
        if not isinstance(is_known_future, bool):
            raise ValueError(
                f"known_future_drivers values must be bool entries, got {name}={is_known_future!r}"
            )
        if is_known_future:
            known_future.add(name)
    return known_future


def _resolve_source_goal(
    *,
    triage_result: TriageResult,
    lagged_exog_bundle: LaggedExogBundle | None,
) -> Literal["univariate", "covariant", "lagged_exogenous"]:
    """Resolve source-goal label for ForecastPrepContract."""
    if lagged_exog_bundle is not None:
        return "lagged_exogenous"
    goal_value = str(getattr(triage_result.request.goal, "value", triage_result.request.goal))
    if goal_value == "exogenous":
        return "covariant"
    return "univariate"


def _resolve_routing_recommendation(
    *,
    routing_recommendation: RoutingRecommendation | None,
    fingerprint_bundle: FingerprintBundle | None,
) -> RoutingRecommendation | None:
    """Resolve explicit or fingerprint-derived routing recommendation."""
    if routing_recommendation is not None:
        return routing_recommendation
    if fingerprint_bundle is None:
        return None
    return fingerprint_bundle.recommendation


def _calendar_covariate_rows(
    *,
    add_calendar_features: bool,
    datetime_index: pd.DatetimeIndex | None,
    calendar_locale: str | None,
) -> tuple[list[CovariateRecommendation], list[str], list[str]]:
    """Build deterministic calendar covariate rows and caution flags."""
    if not add_calendar_features:
        return [], [], []
    if datetime_index is None:
        raise ValueError(
            "add_calendar_features=True requires datetime_index. "
            "Pass datetime_index=<pd.DatetimeIndex> or set add_calendar_features=False."
        )

    calendar_frame = generate_calendar_features(datetime_index, locale=calendar_locale)
    feature_names = [str(name) for name in calendar_frame.columns]
    rows = [
        CovariateRecommendation(
            name=feature_name,
            role="future",
            confidence="high",
            informative=True,
            future_known_required=True,
            selected_lags=[0],
            rationale="deterministic calendar feature",
        )
        for feature_name in feature_names
    ]

    caution_flags: list[str] = []
    if (
        calendar_locale is not None
        and calendar_locale.strip()
        and not calendar_feature_service._HOLIDAYS_AVAILABLE
    ):
        caution_flags.append("calendar_locale_set_but_holidays_unavailable")

    return rows, feature_names, caution_flags


def build_forecast_prep_contract(
    triage_result: TriageResult,
    *,
    horizon: int | None = None,
    target_frequency: str | None = None,
    lagged_exog_bundle: LaggedExogBundle | None = None,
    fingerprint_bundle: FingerprintBundle | None = None,
    routing_recommendation: RoutingRecommendation | None = None,
    known_future_drivers: dict[str, bool] | None = None,
    add_calendar_features: bool = True,
    calendar_locale: str | None = None,
    datetime_index: pd.DatetimeIndex | None = None,
) -> ForecastPrepContract:
    """Build a ForecastPrepContract from deterministic triage outputs.

    Args:
        triage_result: Output of ``run_triage()``. Determines blocked state and
            primary lags.
        horizon: Forecast horizon in samples.
        target_frequency: Pandas-compatible target frequency string.
        lagged_exog_bundle: Optional output of ``run_lagged_exogenous_triage()``.
        fingerprint_bundle: Optional output of ``run_forecastability_fingerprint()``.
        routing_recommendation: Optional explicit routing recommendation.
        known_future_drivers: Optional mapping ``{column_name: bool}``.
        add_calendar_features: Inject deterministic calendar future covariates.
        calendar_locale: Locale used by the optional holidays integration.
        datetime_index: Datetime index aligned with the target series.

    Returns:
        Frozen ForecastPrepContract.
    """
    if horizon is not None and horizon < 1:
        raise ValueError(f"horizon must be >= 1 when provided, got {horizon}")

    resolved_routing = _resolve_routing_recommendation(
        routing_recommendation=routing_recommendation,
        fingerprint_bundle=fingerprint_bundle,
    )
    contract_confidence = derive_contract_confidence(
        blocked=triage_result.blocked,
        routing_recommendation=resolved_routing,
    )
    known_future_driver_names = _resolve_known_future_driver_names(
        known_future_drivers=known_future_drivers,
        lagged_exog_bundle=lagged_exog_bundle,
    )

    caution_flags: list[str] = []
    if triage_result.blocked:
        caution_flags.append("blocked_readiness_status")
    if resolved_routing is not None:
        caution_flags.extend(str(flag) for flag in resolved_routing.caution_flags)

    if triage_result.blocked:
        lag_rows = []
        candidate_periods: list[int] = []
        lag_rationale: list[str] = []
        covariate_rows: list[CovariateRecommendation] = []
        covariate_notes: list[str] = []
        calendar_rows: list[CovariateRecommendation] = []
        calendar_features: list[str] = []
        calendar_cautions: list[str] = []
    else:
        primary_lags = (
            list(triage_result.interpretation.primary_lags)
            if triage_result.interpretation is not None
            else []
        )
        lag_rows, candidate_periods, _recommended_seasonal_lags, lag_rationale = (
            map_target_lag_recommendations(
                primary_lags=primary_lags,
                fingerprint_bundle=fingerprint_bundle,
                contract_confidence=contract_confidence,
            )
        )
        covariate_rows, covariate_notes = map_covariate_recommendations(
            lagged_exog_bundle=lagged_exog_bundle,
            known_future_driver_names=known_future_driver_names,
            contract_confidence=contract_confidence,
        )
        calendar_rows, calendar_features, calendar_cautions = _calendar_covariate_rows(
            add_calendar_features=add_calendar_features,
            datetime_index=datetime_index,
            calendar_locale=calendar_locale,
        )
        covariate_rows.extend(calendar_rows)
        allowed_zero_future_names = set(calendar_features) | known_future_driver_names
        validate_covariate_recommendations(
            covariate_rows=covariate_rows,
            allowed_zero_future_names=allowed_zero_future_names,
        )

    family_rows, recommended_families, baseline_families = map_family_recommendations(
        routing_recommendation=resolved_routing,
        contract_confidence=contract_confidence,
    )
    caution_flags.extend(calendar_cautions if not triage_result.blocked else [])

    recommended_target_lags = sorted(
        {
            row.lag
            for row in lag_rows
            if row.selected_for_handoff and row.role in {"direct", "secondary"}
        }
    )
    recommended_seasonal_lags = sorted(
        {row.lag for row in lag_rows if row.selected_for_handoff and row.role == "seasonal"}
    )
    excluded_target_lags = sorted({row.lag for row in lag_rows if row.role == "excluded"})

    past_covariates = sorted({row.name for row in covariate_rows if row.role == "past"})
    future_covariates = sorted({row.name for row in covariate_rows if row.role == "future"})
    static_features = sorted({row.name for row in covariate_rows if row.role == "static"})
    rejected_covariates = sorted({row.name for row in covariate_rows if row.role == "rejected"})

    if contract_confidence == "abstain":
        recommended_families = []

    return ForecastPrepContract(
        source_goal=_resolve_source_goal(
            triage_result=triage_result,
            lagged_exog_bundle=lagged_exog_bundle,
        ),
        blocked=triage_result.blocked,
        readiness_status=triage_result.readiness.status.value,
        forecastability_class=(
            triage_result.interpretation.forecastability_class
            if triage_result.interpretation is not None
            else None
        ),
        confidence_label=contract_confidence,
        target_frequency=target_frequency,
        horizon=horizon,
        recommended_target_lags=recommended_target_lags,
        recommended_seasonal_lags=recommended_seasonal_lags,
        excluded_target_lags=excluded_target_lags,
        lag_rationale=lag_rationale,
        candidate_seasonal_periods=candidate_periods,
        recommended_families=recommended_families,
        baseline_families=baseline_families,
        past_covariates=past_covariates,
        future_covariates=future_covariates,
        static_features=static_features,
        rejected_covariates=rejected_covariates,
        covariate_notes=covariate_notes,
        caution_flags=_dedupe_preserve_order(caution_flags),
        downstream_notes=(resolved_routing.rationale if resolved_routing is not None else []),
        calendar_features=sorted(calendar_features if not triage_result.blocked else []),
        calendar_locale=calendar_locale,
        metadata={
            "lag_rows": len(lag_rows),
            "covariate_rows": len(covariate_rows),
            "family_rows": len(family_rows),
        },
    )


__all__ = ["build_forecast_prep_contract"]
