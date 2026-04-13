"""Tests for F7 batch multi-signal ranking with new scorer columns."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.triage.batch_models import (
    SUMMARY_TABLE_COLUMNS,
    BatchSeriesRequest,
    BatchTriageItemResult,
    BatchTriageRequest,
)
from forecastability.triage.complexity_band import ComplexityBandResult
from forecastability.triage.models import (
    ReadinessReport,
    ReadinessStatus,
    TriageRequest,
    TriageResult,
)
from forecastability.use_cases.run_batch_triage import run_batch_triage_with_details


def _stub_triage_runner(request: TriageRequest) -> TriageResult:
    band = ComplexityBandResult(
        permutation_entropy=0.6,
        spectral_entropy=0.4,
        embedding_order=3,
        complexity_band="medium",
        interpretation="Medium complexity",
        pe_reliability_warning=None,
    )
    return TriageResult(
        request=request,
        readiness=ReadinessReport(status=ReadinessStatus.clear, warnings=[]),
        blocked=False,
        complexity_band=band,
    )


def test_batch_summary_row_includes_new_scorer_columns() -> None:
    assert "spectral_predictability" in SUMMARY_TABLE_COLUMNS
    assert "permutation_entropy" in SUMMARY_TABLE_COLUMNS
    assert "complexity_band_label" in SUMMARY_TABLE_COLUMNS


def test_batch_item_result_new_fields_none_when_complexity_band_absent() -> None:
    item = BatchTriageItemResult(
        series_id="no-band",
        outcome="ok",
        blocked=False,
        readiness_status="clear",
        recommended_next_action="prioritize_structured_models",
    )
    assert item.spectral_predictability is None
    assert item.permutation_entropy is None
    assert item.complexity_band_label is None


def test_build_item_result_populates_new_scorer_columns_from_complexity_band() -> None:
    request = BatchTriageRequest(
        items=[
            BatchSeriesRequest(
                series_id="stub-series",
                series=list(np.linspace(0.0, 1.0, 30).tolist()),
                max_lag=5,
            )
        ],
        max_lag=5,
        random_state=42,
    )
    execution = run_batch_triage_with_details(request, triage_runner=_stub_triage_runner)
    item = execution.response.items[0]

    assert item.spectral_predictability == pytest.approx(1.0 - 0.4, abs=1e-5)
    assert item.permutation_entropy == pytest.approx(0.6, abs=1e-12)
    assert item.complexity_band_label == "medium"


def test_summary_row_new_columns_match_item_result() -> None:
    request = BatchTriageRequest(
        items=[
            BatchSeriesRequest(
                series_id="stub-series",
                series=list(np.linspace(0.0, 1.0, 30).tolist()),
                max_lag=5,
            )
        ],
        max_lag=5,
        random_state=42,
    )
    execution = run_batch_triage_with_details(request, triage_runner=_stub_triage_runner)
    item = execution.response.items[0]
    row = execution.response.summary_table[0]

    assert row.spectral_predictability == item.spectral_predictability
    assert row.permutation_entropy == item.permutation_entropy
    assert row.complexity_band_label == item.complexity_band_label
