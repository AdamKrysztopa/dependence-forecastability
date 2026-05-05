"""Lag-aware ForecastPrepContract helpers for sparse covariate selections."""

from __future__ import annotations

from typing import cast

from forecastability.triage.lag_aware_mod_mrmr import (
    LagAwareModMRMRResult,
    SelectedLagAwareFeature,
)
from forecastability.utils.types import (
    CovariateRecommendation,
    ForecastPrepConfidence,
    ForecastPrepContract,
    ForecastPrepContractConfidence,
    ForecastPrepCovariateRole,
    ForecastPrepTargetHistoryContext,
)

_LAG_EXPORTABLE_ROLES: tuple[ForecastPrepCovariateRole, ...] = ("past", "future")


def build_lagged_feature_names(*, driver_name: str, lags: list[int]) -> list[str]:
    """Build deterministic lagged feature names for one driver."""
    safe_name = driver_name.replace(" ", "_").replace("-", "_")
    return [f"x_{safe_name}_lag{lag}" for lag in lags]


def map_lag_aware_covariate_recommendations(
    *,
    lag_aware_result: LagAwareModMRMRResult,
    contract_confidence: ForecastPrepContractConfidence,
) -> tuple[
    list[CovariateRecommendation],
    list[str],
    ForecastPrepTargetHistoryContext,
]:
    """Map Lag-Aware ModMRMR selections into typed ForecastPrep covariate rows."""
    rows: list[CovariateRecommendation] = []
    notes: list[str] = []
    grouped: dict[tuple[str, str], list[SelectedLagAwareFeature]] = {}

    for feature in sorted(
        lag_aware_result.selected,
        key=lambda item: (
            1 if item.is_known_future else 0,
            item.covariate_name,
            item.lag,
            item.feature_name,
        ),
    ):
        role: ForecastPrepCovariateRole = "future" if feature.is_known_future else "past"
        grouped.setdefault((role, feature.covariate_name), []).append(feature)

    row_confidence = _row_confidence(contract_confidence=contract_confidence)
    sorted_group_keys = cast(
        list[tuple[ForecastPrepCovariateRole, str]],
        sorted(grouped, key=lambda item: (item[0], item[1])),
    )
    for role, driver_name in sorted_group_keys:
        features = grouped[(role, driver_name)]
        selected_lags = sorted({feature.lag for feature in features})
        feature_name_by_lag: dict[int, str] = {}
        provenance_values: set[str] = set()
        for feature in features:
            feature_name_by_lag.setdefault(feature.lag, feature.feature_name)
            if feature.known_future_provenance is not None:
                provenance_values.add(feature.known_future_provenance)

        known_future_provenance = _resolve_known_future_provenance(
            role=role,
            driver_name=driver_name,
            provenance_values=provenance_values,
        )
        lagged_feature_names = [
            feature_name_by_lag.get(
                lag,
                build_lagged_feature_names(driver_name=driver_name, lags=[lag])[0],
            )
            for lag in selected_lags
        ]
        rationale = _lag_aware_rationale(
            role=role,
            selected_lags=selected_lags,
            known_future_provenance=known_future_provenance,
        )

        rows.append(
            CovariateRecommendation(
                name=driver_name,
                role=role,
                confidence=row_confidence,
                informative=True,
                future_known_required=role == "future",
                selected_lags=selected_lags,
                lagged_feature_names=lagged_feature_names,
                known_future_provenance=known_future_provenance,
                rationale=rationale,
            )
        )
        notes.append(
            _covariate_note(
                role=role,
                driver_name=driver_name,
                selected_lags=selected_lags,
            )
        )

    return rows, notes, build_target_history_context(lag_aware_result=lag_aware_result)


def build_target_history_context(
    *,
    lag_aware_result: LagAwareModMRMRResult,
) -> ForecastPrepTargetHistoryContext:
    """Build deterministic target-history novelty context for contract export."""
    scorer = lag_aware_result.config.target_history_scorer
    target_lags = list(lag_aware_result.config.target_lags or [])
    penalized_selected_features = sum(
        feature.target_history_redundancy > 0.0 for feature in lag_aware_result.selected
    )
    max_selected_redundancy = (
        max(
            (feature.target_history_redundancy for feature in lag_aware_result.selected),
            default=0.0,
        )
        if lag_aware_result.selected
        else None
    )

    notes: list[str] = []
    if scorer is None:
        notes.append("target-history novelty penalty disabled")
    else:
        notes.append(
            f"target-history novelty scored with {scorer.name} over target lags {target_lags}"
        )
    if penalized_selected_features > 0:
        notes.append(
            f"{penalized_selected_features} selected feature(s) carried "
            "non-zero target-history redundancy"
        )

    return ForecastPrepTargetHistoryContext(
        enabled=scorer is not None,
        target_lags=target_lags,
        scorer_name=None if scorer is None else scorer.name,
        normalization_strategy=None if scorer is None else scorer.normalization,
        penalized_selected_features=penalized_selected_features,
        max_selected_redundancy=max_selected_redundancy,
        notes=notes,
    )


def contract_covariate_lag_rows(contract: ForecastPrepContract) -> list[dict[str, object]]:
    """Explode contract covariate rows into deterministic lag-table rows."""
    exportable_rows = _exportable_covariate_rows(contract=contract)
    if not exportable_rows:
        return _fallback_contract_covariate_lag_rows(contract=contract)

    rows: list[dict[str, object]] = []
    for row in exportable_rows:
        lagged_feature_names = (
            list(row.lagged_feature_names)
            if row.lagged_feature_names
            else build_lagged_feature_names(driver_name=row.name, lags=list(row.selected_lags))
        )
        for lag, feature_name in zip(row.selected_lags, lagged_feature_names, strict=True):
            rows.append(
                {
                    "driver": row.name,
                    "feature_name": feature_name,
                    "axis": row.role,
                    "role": row.role,
                    "lag": lag,
                    "selected_for_handoff": True,
                    "future_known_required": row.future_known_required,
                    "known_future_provenance": row.known_future_provenance,
                    "kind": _covariate_kind(row=row),
                    "rationale": row.rationale,
                }
            )

    rows.sort(
        key=lambda item: (
            0 if item["axis"] == "past" else 1,
            str(item["driver"]),
            int(item["lag"]),
        )
    )
    return rows


def contract_covariate_markdown_table(contract: ForecastPrepContract) -> str:
    """Render a compact markdown table for selected covariate lag rows."""
    exportable_rows = _exportable_covariate_rows(contract=contract)
    if exportable_rows:
        lines = [
            "| axis | kind | driver | selected_lags | feature_names |",
            "| --- | --- | --- | --- | --- |",
        ]
        for row in exportable_rows:
            selected_lags = ", ".join(str(lag) for lag in row.selected_lags) or "-"
            feature_names = ", ".join(
                row.lagged_feature_names
                if row.lagged_feature_names
                else build_lagged_feature_names(driver_name=row.name, lags=list(row.selected_lags))
            )
            lines.append(
                f"| {row.role} | {_covariate_kind(row=row)} | {row.name} | "
                f"{selected_lags} | {feature_names} |"
            )
        return "\n".join(lines)

    fallback_rows = contract_covariate_lag_rows(contract)
    if not fallback_rows:
        return "(none)"

    lines = [
        "| axis | kind | driver | selected_lags | feature_names |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in fallback_rows:
        lines.append(
            f"| {row['axis']} | {row['kind']} | {row['driver']} | {row['lag']} | "
            f"{row['feature_name']} |"
        )
    return "\n".join(lines)


def _exportable_covariate_rows(
    *,
    contract: ForecastPrepContract,
) -> list[CovariateRecommendation]:
    """Return covariate rows that encode lagged hand-off information."""
    return sorted(
        [row for row in contract.covariate_rows if row.role in _LAG_EXPORTABLE_ROLES],
        key=lambda item: (item.role, item.name, list(item.selected_lags)),
    )


def _row_confidence(
    *,
    contract_confidence: ForecastPrepContractConfidence,
) -> ForecastPrepConfidence:
    if contract_confidence == "high":
        return "high"
    if contract_confidence == "medium":
        return "medium"
    return "low"


def _resolve_known_future_provenance(
    *,
    role: str,
    driver_name: str,
    provenance_values: set[str],
) -> str | None:
    if role != "future":
        return None
    if not provenance_values:
        return None
    if len(provenance_values) != 1:
        raise ValueError(
            f"Expected one known-future provenance for {driver_name!r}, "
            f"got {sorted(provenance_values)}"
        )
    return next(iter(provenance_values))


def _lag_aware_rationale(
    *,
    role: str,
    selected_lags: list[int],
    known_future_provenance: str | None,
) -> str:
    if role == "future":
        if known_future_provenance is None:
            return f"lag-aware ModMRMR selected known-future lags: {selected_lags}"
        return (
            "lag-aware ModMRMR selected known-future lags: "
            f"{selected_lags} (provenance={known_future_provenance})"
        )
    return f"lag-aware ModMRMR selected sparse measured lags: {selected_lags}"


def _covariate_note(*, role: str, driver_name: str, selected_lags: list[int]) -> str:
    if role == "future":
        return f"future covariate {driver_name}: lags {selected_lags}"
    return f"past covariate {driver_name}: lags {selected_lags}"


def _covariate_kind(*, row: CovariateRecommendation) -> str:
    if row.role != "future":
        return "measured"
    if row.known_future_provenance is not None:
        return f"known_future:{row.known_future_provenance}"
    return "known_future"


def _fallback_contract_covariate_lag_rows(
    *,
    contract: ForecastPrepContract,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for name in contract.past_covariates:
        rows.append(
            {
                "driver": name,
                "feature_name": build_lagged_feature_names(driver_name=name, lags=[1])[0],
                "axis": "past",
                "role": "past",
                "lag": 1,
                "selected_for_handoff": True,
                "future_known_required": False,
                "known_future_provenance": None,
                "kind": "measured",
                "rationale": "",
            }
        )

    for name in contract.future_covariates:
        rows.append(
            {
                "driver": name,
                "feature_name": build_lagged_feature_names(driver_name=name, lags=[0])[0],
                "axis": "future",
                "role": "future",
                "lag": 0,
                "selected_for_handoff": True,
                "future_known_required": True,
                "known_future_provenance": None,
                "kind": "known_future",
                "rationale": "",
            }
        )

    rows.sort(
        key=lambda item: (
            0 if item["axis"] == "past" else 1,
            str(item["driver"]),
            int(item["lag"]),
        )
    )
    return rows


__all__ = [
    "build_lagged_feature_names",
    "build_target_history_context",
    "contract_covariate_lag_rows",
    "contract_covariate_markdown_table",
    "map_lag_aware_covariate_recommendations",
]
