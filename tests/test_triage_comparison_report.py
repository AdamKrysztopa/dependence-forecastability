"""Focused tests for multi-series comparison report generation (backlog item #15)."""

from __future__ import annotations

import numpy as np

from forecastability.pipeline.analyzer import AnalyzeResult
from forecastability.triage.batch_models import BatchSeriesRequest, BatchTriageRequest
from forecastability.triage.comparison_report import (
    HORIZON_DROPOFF_TABLE_COLUMNS,
    RECOMMENDATION_TABLE_COLUMNS,
    SERIES_COMPARISON_TABLE_COLUMNS,
    build_multi_series_comparison_report,
)
from forecastability.triage.models import (
    MethodPlan,
    ReadinessReport,
    ReadinessStatus,
    TriageRequest,
    TriageResult,
)
from forecastability.utils.types import Diagnostics, InterpretationResult


def _make_stub_triage_result(
    *,
    marker: float,
    raw: list[float],
    partial: list[float],
    sig_raw: list[int],
    sig_partial: list[int],
    forecastability_class: str,
    directness_class: str,
    modeling_regime: str,
) -> TriageResult:
    """Build a deterministic ``TriageResult`` for test injection."""
    raw_arr = np.asarray(raw, dtype=np.float64)
    partial_arr = np.asarray(partial, dtype=np.float64)
    sig_raw_arr = np.asarray(sig_raw, dtype=int)
    sig_partial_arr = np.asarray(sig_partial, dtype=int)

    ami_auc = float(np.trapezoid(raw_arr))
    pami_auc = float(np.trapezoid(partial_arr))
    directness_ratio = float(pami_auc / max(ami_auc, 1e-12))

    request = TriageRequest(
        series=np.asarray([marker, 0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float64),
        max_lag=max(len(raw), len(partial)),
        n_surrogates=99,
        random_state=42,
    )

    readiness = ReadinessReport(status=ReadinessStatus.clear, warnings=[])
    method_plan = MethodPlan(
        route="univariate_with_significance",
        compute_surrogates=True,
        assumptions=["test"],
        rationale="stub",
    )
    analyze = AnalyzeResult(
        raw=raw_arr,
        partial=partial_arr,
        sig_raw_lags=sig_raw_arr,
        sig_partial_lags=sig_partial_arr,
        recommendation="stub recommendation",
        method="mi",
    )
    interpretation = InterpretationResult(
        forecastability_class=forecastability_class,
        directness_class=directness_class,
        primary_lags=sig_partial,
        modeling_regime=modeling_regime,
        narrative="stub narrative",
        diagnostics=Diagnostics(
            peak_ami_first_5=float(np.max(raw_arr[: min(5, raw_arr.size)])),
            directness_ratio=directness_ratio,
            n_sig_ami=int(sig_raw_arr.size),
            n_sig_pami=int(sig_partial_arr.size),
            exploitability_mismatch=0,
            best_smape=-1.0,
        ),
    )

    return TriageResult(
        request=request,
        readiness=readiness,
        method_plan=method_plan,
        analyze_result=analyze,
        interpretation=interpretation,
        recommendation="stub recommendation",
        blocked=False,
    )


def test_comparison_report_tables_have_expected_standardized_columns() -> None:
    """Comparison report tables must expose stable, standardized column schemas."""
    alpha = _make_stub_triage_result(
        marker=1.0,
        raw=[0.9, 0.8, 0.7, 0.6, 0.5, 0.4],
        partial=[0.7, 0.6, 0.5, 0.4, 0.35, 0.3],
        sig_raw=[1, 2, 3],
        sig_partial=[1, 2],
        forecastability_class="high",
        directness_class="high",
        modeling_regime="rich_models_with_structured_memory",
    )
    beta = _make_stub_triage_result(
        marker=2.0,
        raw=[0.5, 0.4, 0.3, 0.25, 0.2, 0.18],
        partial=[0.2, 0.15, 0.1, 0.08, 0.06, 0.05],
        sig_raw=[1, 2],
        sig_partial=[1],
        forecastability_class="medium",
        directness_class="medium",
        modeling_regime="seasonal_or_regularized_models",
    )

    def stub_runner(request: TriageRequest) -> TriageResult:
        marker = float(request.series[0])
        if marker == -1.0:
            raise ValueError("synthetic per-series failure")
        if marker == 1.0:
            return alpha
        if marker == 2.0:
            return beta
        raise ValueError("unknown marker")

    request = BatchTriageRequest(
        items=[
            BatchSeriesRequest(series_id="alpha", series=[1.0, 0.2, 0.3, 0.4, 0.5, 0.6]),
            BatchSeriesRequest(series_id="beta", series=[2.0, 0.2, 0.3, 0.4, 0.5, 0.6]),
            BatchSeriesRequest(series_id="failed", series=[-1.0, 0.2, 0.3, 0.4, 0.5, 0.6]),
        ],
        max_lag=6,
        n_surrogates=99,
        random_state=42,
    )

    report = build_multi_series_comparison_report(request, triage_runner=stub_runner, top_n=2)

    assert list(report.series_table_frame().columns) == list(SERIES_COMPARISON_TABLE_COLUMNS)
    assert list(report.horizon_dropoff_frame().columns) == list(HORIZON_DROPOFF_TABLE_COLUMNS)
    assert list(report.recommendation_frame().columns) == list(RECOMMENDATION_TABLE_COLUMNS)


def test_recommendation_summary_prioritizes_deeper_modeling_candidates() -> None:
    """Summary must recommend top deeper-modeling candidates and exclude weak profiles."""
    alpha = _make_stub_triage_result(
        marker=10.0,
        raw=[0.9, 0.82, 0.74, 0.66, 0.58, 0.52],
        partial=[0.74, 0.66, 0.6, 0.54, 0.5, 0.46],
        sig_raw=[1, 2, 3, 4],
        sig_partial=[1, 2, 3],
        forecastability_class="high",
        directness_class="high",
        modeling_regime="rich_models_with_structured_memory",
    )
    beta = _make_stub_triage_result(
        marker=20.0,
        raw=[0.45, 0.35, 0.28, 0.2, 0.14, 0.1],
        partial=[0.03, 0.015, 0.01, 0.008, 0.006, 0.005],
        sig_raw=[1, 2],
        sig_partial=[1],
        forecastability_class="medium",
        directness_class="low",
        modeling_regime="seasonal_or_regularized_models",
    )
    delta = _make_stub_triage_result(
        marker=30.0,
        raw=[0.75, 0.58, 0.4, 0.24, 0.14, 0.08],
        partial=[0.41, 0.22, 0.08, 0.03, 0.015, 0.008],
        sig_raw=[1, 2, 3],
        sig_partial=[1, 2],
        forecastability_class="high",
        directness_class="medium",
        modeling_regime="compact_structured_models",
    )

    def stub_runner(request: TriageRequest) -> TriageResult:
        marker = float(request.series[0])
        if marker == 10.0:
            return alpha
        if marker == 20.0:
            return beta
        if marker == 30.0:
            return delta
        raise ValueError("unknown marker")

    request = BatchTriageRequest(
        items=[
            BatchSeriesRequest(series_id="alpha", series=[10.0, 0.2, 0.3, 0.4, 0.5, 0.6]),
            BatchSeriesRequest(series_id="beta", series=[20.0, 0.2, 0.3, 0.4, 0.5, 0.6]),
            BatchSeriesRequest(series_id="delta", series=[30.0, 0.2, 0.3, 0.4, 0.5, 0.6]),
        ],
        max_lag=6,
        n_surrogates=99,
        random_state=42,
    )

    report = build_multi_series_comparison_report(request, triage_runner=stub_runner, top_n=1)

    assert report.summary.recommended_series_ids == ["alpha"]
    assert report.summary.n_series_recommended == 1
    assert "alpha" in report.summary.summary_markdown

    recommendation_df = report.recommendation_frame()
    winner = recommendation_df[recommendation_df["series_id"] == "alpha"].iloc[0]
    beta_row = recommendation_df[recommendation_df["series_id"] == "beta"].iloc[0]

    assert bool(winner["deserves_deeper_modeling"]) is True
    assert bool(beta_row["deserves_deeper_modeling"]) is False
