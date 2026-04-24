"""Pure mapping helpers for building forecast-prep contracts."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import cast

from forecastability.utils.types import (
    CovariateRecommendation,
    FamilyRecommendation,
    FingerprintBundle,
    ForecastPrepConfidence,
    ForecastPrepContractConfidence,
    LaggedExogBundle,
    LagRecommendation,
    RoutingRecommendation,
)

_BASELINE_FAMILIES: tuple[str, ...] = ("naive", "seasonal_naive")


def _unique_sorted(values: Iterable[int]) -> list[int]:
    """Return stable sorted unique integer values."""
    return sorted(set(values))


def _confidence_for_rows(
    *,
    contract_confidence: ForecastPrepContractConfidence,
) -> ForecastPrepConfidence:
    """Map contract confidence into row-level confidence labels."""
    if contract_confidence == "high":
        return "high"
    if contract_confidence == "medium":
        return "medium"
    return "low"


def derive_contract_confidence(
    *,
    blocked: bool,
    routing_recommendation: RoutingRecommendation | None,
) -> ForecastPrepContractConfidence:
    """Resolve contract confidence from blocked state and routing output."""
    if blocked:
        return "abstain"
    if routing_recommendation is None:
        return "medium"
    return routing_recommendation.confidence_label


def extract_candidate_seasonal_periods(
    *,
    fingerprint_bundle: FingerprintBundle | None,
) -> list[int]:
    """Extract candidate seasonal periods from informative-horizon spacing."""
    if fingerprint_bundle is None:
        return []
    horizons = sorted(set(fingerprint_bundle.geometry.informative_horizons))
    if len(horizons) < 2:
        return []

    spacings = [horizons[index] - horizons[index - 1] for index in range(1, len(horizons))]
    spacing_counter = Counter(spacing for spacing in spacings if spacing >= 2)
    if not spacing_counter:
        return []

    return [
        period
        for period, _count in sorted(
            spacing_counter.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]


def recommended_seasonal_lags(
    *,
    primary_lags: list[int],
    candidate_periods: list[int],
    fingerprint_bundle: FingerprintBundle | None,
    contract_confidence: ForecastPrepContractConfidence,
) -> list[int]:
    """Resolve conservative seasonal lag recommendations."""
    if fingerprint_bundle is None:
        return []
    if fingerprint_bundle.geometry.information_structure != "periodic":
        return []
    if contract_confidence not in {"high", "medium"}:
        return []

    candidate_set = set(candidate_periods)
    return _unique_sorted(lag for lag in primary_lags if lag in candidate_set)


def map_target_lag_recommendations(
    *,
    primary_lags: list[int],
    fingerprint_bundle: FingerprintBundle | None,
    contract_confidence: ForecastPrepContractConfidence,
) -> tuple[list[LagRecommendation], list[int], list[int], list[str]]:
    """Map univariate primary lags into typed lag recommendations."""
    filtered_primary_lags = _unique_sorted(lag for lag in primary_lags if lag >= 1)
    candidate_periods = extract_candidate_seasonal_periods(fingerprint_bundle=fingerprint_bundle)
    seasonal_lags = recommended_seasonal_lags(
        primary_lags=filtered_primary_lags,
        candidate_periods=candidate_periods,
        fingerprint_bundle=fingerprint_bundle,
        contract_confidence=contract_confidence,
    )
    seasonal_set = set(seasonal_lags)

    strongest_nonseasonal = next(
        (lag for lag in filtered_primary_lags if lag not in seasonal_set),
        None,
    )
    row_confidence = _confidence_for_rows(contract_confidence=contract_confidence)
    include_secondary = contract_confidence == "high"

    rows: list[LagRecommendation] = []
    rationale: list[str] = []
    for lag in filtered_primary_lags:
        if lag in seasonal_set:
            role = "seasonal"
            selected = True
            reason = f"lag {lag} aligns with seasonal period candidates"
        elif strongest_nonseasonal is not None and lag == strongest_nonseasonal:
            role = "direct"
            selected = True
            reason = f"lag {lag} is the strongest non-seasonal lag"
        else:
            role = "secondary"
            selected = include_secondary
            reason = f"lag {lag} is secondary under current confidence"

        rows.append(
            LagRecommendation(
                lag=lag,
                role=role,
                confidence=row_confidence,
                selected_for_handoff=selected,
                rationale=reason,
            )
        )
        rationale.append(reason)

    return rows, candidate_periods, seasonal_lags, rationale


def map_covariate_recommendations(
    *,
    lagged_exog_bundle: LaggedExogBundle | None,
    known_future_driver_names: set[str],
    contract_confidence: ForecastPrepContractConfidence,
) -> tuple[list[CovariateRecommendation], list[str]]:
    """Map lagged-exogenous rows and known-future drivers into covariate rows."""
    row_confidence = _confidence_for_rows(contract_confidence=contract_confidence)
    past_by_driver: dict[str, set[int]] = {}
    rows: list[CovariateRecommendation] = []
    notes: list[str] = []

    if lagged_exog_bundle is not None:
        for row in lagged_exog_bundle.selected_lags:
            if not row.selected_for_tensor:
                continue
            if row.driver in known_future_driver_names:
                continue
            if row.lag < 1:
                raise ValueError(
                    "Lagged exogenous selections for past covariates must use lag >= 1"
                )
            past_by_driver.setdefault(row.driver, set()).add(row.lag)

    for driver in sorted(past_by_driver):
        selected_lags = _unique_sorted(past_by_driver[driver])
        rows.append(
            CovariateRecommendation(
                name=driver,
                role="past",
                confidence=row_confidence,
                informative=True,
                future_known_required=False,
                selected_lags=selected_lags,
                rationale=f"selected sparse lag set for past covariate: {selected_lags}",
            )
        )
        notes.append(f"past covariate {driver}: lags {selected_lags}")

    for driver in sorted(known_future_driver_names):
        rows.append(
            CovariateRecommendation(
                name=driver,
                role="future",
                confidence=row_confidence,
                informative=True,
                future_known_required=True,
                selected_lags=[0],
                rationale="declared as known-future by user contract",
            )
        )
        notes.append(f"future covariate {driver}: lag [0]")

    return rows, notes


def validate_covariate_recommendations(
    *,
    covariate_rows: Iterable[CovariateRecommendation],
    allowed_zero_future_names: set[str],
) -> None:
    """Validate covariate role, lag, and disjointness invariants."""
    past_names: set[str] = set()
    future_names: set[str] = set()

    for row in covariate_rows:
        if row.role == "past":
            if any(lag < 1 for lag in row.selected_lags):
                raise ValueError("Past covariate lags must all be >= 1")
            if any(lag == 0 for lag in row.selected_lags):
                raise ValueError("Lag 0 is reserved for future covariates only")
            past_names.add(row.name)
            continue

        if row.role == "future":
            for lag in row.selected_lags:
                if lag < 0:
                    raise ValueError("Future covariate lags must be >= 0")
                if lag == 0 and row.name not in allowed_zero_future_names:
                    raise ValueError(
                        "Future lag 0 is only allowed for known-future or calendar covariates"
                    )
            future_names.add(row.name)
            continue

        if any(lag == 0 for lag in row.selected_lags):
            raise ValueError("Lag 0 is reserved for future covariates only")

    overlap = sorted(past_names & future_names)
    if overlap:
        raise ValueError(
            f"Drivers cannot appear in both past_covariates and future_covariates: {overlap}"
        )


def map_family_recommendations(
    *,
    routing_recommendation: RoutingRecommendation | None,
    contract_confidence: ForecastPrepContractConfidence,
) -> tuple[list[FamilyRecommendation], list[str], list[str]]:
    """Map routing recommendation into recommended and baseline families."""
    baseline_families = list(_BASELINE_FAMILIES)
    rows: list[FamilyRecommendation] = [
        FamilyRecommendation(
            family=family,
            tier="baseline",
            rationale="baseline family retained for conservative benchmarking",
        )
        for family in baseline_families
    ]

    if routing_recommendation is None:
        return rows, [], baseline_families

    primary_families: list[str] = [
        cast(str, family) for family in routing_recommendation.primary_families
    ]
    recommended_families: list[str]
    if contract_confidence == "abstain":
        recommended_families = []
    elif contract_confidence == "low":
        recommended_families = primary_families[:1]
    else:
        recommended_families = primary_families

    for family in recommended_families:
        rows.append(
            FamilyRecommendation(
                family=family,
                tier="preferred",
                rationale="preferred family from deterministic routing recommendation",
            )
        )

    for family in routing_recommendation.secondary_families:
        family_name = str(family)
        if family_name in recommended_families or family_name in baseline_families:
            continue
        rows.append(
            FamilyRecommendation(
                family=family_name,
                tier="fallback",
                rationale="fallback family from deterministic routing recommendation",
            )
        )

    return rows, recommended_families, baseline_families


__all__ = [
    "derive_contract_confidence",
    "extract_candidate_seasonal_periods",
    "map_covariate_recommendations",
    "map_family_recommendations",
    "map_target_lag_recommendations",
    "recommended_seasonal_lags",
    "validate_covariate_recommendations",
]
