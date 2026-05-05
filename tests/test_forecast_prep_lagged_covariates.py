"""Focused tests for lag-aware ForecastPrepContract covariate export."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.services.forecast_prep_export import (
    forecast_prep_contract_to_lag_table,
    forecast_prep_contract_to_markdown,
)
from forecastability.triage.lag_aware_mod_mrmr import (
    LagAwareModMRMRConfig,
    LagAwareModMRMRResult,
    PairwiseScorerSpec,
    SelectedLagAwareFeature,
)
from forecastability.triage.models import (
    AnalysisGoal,
    InterpretationResult,
    ReadinessReport,
    ReadinessStatus,
    TriageRequest,
    TriageResult,
)
from forecastability.use_cases.build_forecast_prep_contract import build_forecast_prep_contract
from forecastability.utils.types import (
    Diagnostics,
    LaggedExogBundle,
    LaggedExogSelectionRow,
    RoutingRecommendation,
)


def _triage_result() -> TriageResult:
    return TriageResult(
        request=TriageRequest(
            series=np.linspace(0.0, 1.0, 120),
            goal=AnalysisGoal.univariate,
            max_lag=24,
            n_surrogates=99,
            random_state=42,
        ),
        readiness=ReadinessReport(status=ReadinessStatus.clear, warnings=[]),
        blocked=False,
        interpretation=InterpretationResult(
            forecastability_class="high",
            directness_class="medium",
            primary_lags=[1, 4],
            modeling_regime="deterministic triage",
            narrative="lag-aware forecast-prep test",
            diagnostics=Diagnostics(
                peak_ami_first_5=0.3,
                directness_ratio=0.4,
                n_sig_ami=4,
                n_sig_pami=2,
                exploitability_mismatch=0,
                best_smape=0.1,
            ),
        ),
    )


def _routing() -> RoutingRecommendation:
    return RoutingRecommendation(
        primary_families=["arima"],
        secondary_families=["linear_state_space"],
        rationale=["deterministic lag-aware route"],
        caution_flags=[],
        confidence_label="high",
    )


def _scorer_spec() -> PairwiseScorerSpec:
    return PairwiseScorerSpec(
        name="spearman_abs",
        backend="scipy",
        normalization="rank_percentile",
        significance_method="none",
    )


def _lag_aware_result() -> LagAwareModMRMRResult:
    spec = _scorer_spec()
    config = LagAwareModMRMRConfig(
        forecast_horizon=2,
        availability_margin=0,
        candidate_lags=[1, 2, 4, 6],
        relevance_scorer=spec,
        redundancy_scorer=spec,
        target_lags=[2, 4],
        target_history_scorer=spec,
    )
    selected = [
        SelectedLagAwareFeature(
            covariate_name="sensor_a",
            lag=4,
            legality_reason="legal",
            feature_name="x_sensor_a_lag4",
            relevance=0.9,
            max_redundancy=0.1,
            target_history_redundancy=0.3,
            final_score=0.567,
            selection_rank=1,
            relevance_scorer_name="spearman_abs",
            redundancy_scorer_name="spearman_abs",
            target_history_scorer_name="spearman_abs",
            normalization_strategy="rank_percentile",
        ),
        SelectedLagAwareFeature(
            covariate_name="sensor_a",
            lag=6,
            legality_reason="legal",
            feature_name="x_sensor_a_lag6",
            relevance=0.8,
            max_redundancy=0.2,
            target_history_redundancy=0.1,
            final_score=0.576,
            selection_rank=2,
            relevance_scorer_name="spearman_abs",
            redundancy_scorer_name="spearman_abs",
            target_history_scorer_name="spearman_abs",
            normalization_strategy="rank_percentile",
        ),
        SelectedLagAwareFeature(
            covariate_name="calendar_flag",
            lag=1,
            is_known_future=True,
            known_future_provenance="calendar",
            legality_reason="legal_known_future",
            feature_name="x_calendar_flag_lag1",
            relevance=0.7,
            max_redundancy=0.0,
            target_history_redundancy=0.0,
            final_score=0.7,
            selection_rank=3,
            relevance_scorer_name="spearman_abs",
            redundancy_scorer_name="spearman_abs",
            target_history_scorer_name="spearman_abs",
            normalization_strategy="rank_percentile",
        ),
    ]
    return LagAwareModMRMRResult(
        config=config,
        selected=selected,
        rejected=[],
        blocked=[],
        n_candidates_evaluated=len(selected),
        n_candidates_blocked=0,
        relevance_scorer_spec=spec,
        redundancy_scorer_spec=spec,
        target_history_scorer_spec=spec,
        notes=["lag-aware regression fixture"],
    )


def _lagged_exog_bundle() -> LaggedExogBundle:
    return LaggedExogBundle(
        target_name="target",
        driver_names=["sensor_bundle"],
        max_lag=8,
        profile_rows=[],
        selected_lags=[
            LaggedExogSelectionRow(
                target="target",
                driver="sensor_bundle",
                lag=4,
                selected_for_tensor=True,
                selector_name="xami_sparse",
                tensor_role="predictive",
            )
        ],
        known_future_drivers=[],
    )


def test_contract_preserves_lag_aware_covariate_rows() -> None:
    contract = build_forecast_prep_contract(
        _triage_result(),
        lag_aware_result=_lag_aware_result(),
        routing_recommendation=_routing(),
        add_calendar_features=False,
    )

    assert contract.past_covariates == ["sensor_a"]
    assert contract.future_covariates == ["calendar_flag"]
    assert len(contract.covariate_rows) == 2

    past_row = next(row for row in contract.covariate_rows if row.role == "past")
    future_row = next(row for row in contract.covariate_rows if row.role == "future")

    assert past_row.selected_lags == [4, 6]
    assert past_row.lagged_feature_names == ["x_sensor_a_lag4", "x_sensor_a_lag6"]
    assert future_row.selected_lags == [1]
    assert future_row.known_future_provenance == "calendar"
    assert future_row.lagged_feature_names == ["x_calendar_flag_lag1"]


def test_contract_exposes_target_history_context_for_lag_aware_result() -> None:
    contract = build_forecast_prep_contract(
        _triage_result(),
        lag_aware_result=_lag_aware_result(),
        routing_recommendation=_routing(),
        add_calendar_features=False,
    )

    assert contract.target_history_context is not None
    assert contract.target_history_context.enabled is True
    assert contract.target_history_context.target_lags == [2, 4]
    assert contract.target_history_context.scorer_name == "spearman_abs"
    assert contract.target_history_context.penalized_selected_features == 2
    assert contract.target_history_context.max_selected_redundancy == 0.3


def test_lag_table_uses_real_lag_aware_lags_instead_of_default_lag_one() -> None:
    contract = build_forecast_prep_contract(
        _triage_result(),
        lag_aware_result=_lag_aware_result(),
        routing_recommendation=_routing(),
        add_calendar_features=False,
    )

    rows = forecast_prep_contract_to_lag_table(contract)
    past_rows = [row for row in rows if row["axis"] == "past"]
    future_rows = [row for row in rows if row["axis"] == "future"]

    assert [row["lag"] for row in past_rows] == [4, 6]
    assert [row["feature_name"] for row in past_rows] == [
        "x_sensor_a_lag4",
        "x_sensor_a_lag6",
    ]
    assert [row["lag"] for row in future_rows] == [1]
    assert future_rows[0]["feature_name"] == "x_calendar_flag_lag1"


def test_markdown_includes_compact_selected_lag_table() -> None:
    contract = build_forecast_prep_contract(
        _triage_result(),
        lag_aware_result=_lag_aware_result(),
        routing_recommendation=_routing(),
        add_calendar_features=False,
    )

    markdown = forecast_prep_contract_to_markdown(contract)

    assert "**selected_covariate_lags:**" in markdown
    assert "| axis | kind | driver | selected_lags | feature_names |" in markdown
    assert "x_sensor_a_lag4, x_sensor_a_lag6" in markdown
    assert "known_future:calendar" in markdown


def test_contract_rejects_ambiguous_lagged_exog_and_lag_aware_sources() -> None:
    with pytest.raises(ValueError, match="Provide at most one covariate source"):
        build_forecast_prep_contract(
            _triage_result(),
            lagged_exog_bundle=_lagged_exog_bundle(),
            lag_aware_result=_lag_aware_result(),
            routing_recommendation=_routing(),
            add_calendar_features=False,
        )
