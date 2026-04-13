"""Focused tests for batch triage screening mode (backlog item #14)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest

from forecastability.adapters.cli import build_parser, cmd_triage_batch
from forecastability.triage.batch_models import (
    FAILURE_TABLE_COLUMNS,
    SUMMARY_TABLE_COLUMNS,
    BatchSeriesRequest,
    BatchTriageItemResult,
    BatchTriageRequest,
)
from forecastability.triage.models import TriageRequest, TriageResult
from forecastability.use_cases.run_batch_triage import rank_batch_items, run_batch_triage
from forecastability.use_cases.run_triage import run_triage


def _make_ar1(n: int = 150, *, phi: float = 0.85, seed: int = 42) -> list[float]:
    """Generate an AR(1) series for deterministic tests."""
    rng = np.random.default_rng(seed)
    ts = np.zeros(n)
    ts[0] = rng.standard_normal()
    for idx in range(1, n):
        ts[idx] = phi * ts[idx - 1] + rng.standard_normal()
    return ts.tolist()


def test_batch_mixed_good_and_failed_series_is_isolated() -> None:
    """One failing series must not prevent other series from being processed."""

    def injected_runner(request: TriageRequest) -> TriageResult:
        if float(request.series[0]) < -900.0:
            raise RuntimeError("synthetic per-series failure")
        return run_triage(request)

    good = BatchSeriesRequest(series_id="good-ar1", series=_make_ar1(), max_lag=20)
    bad_series = [-999.0, *_make_ar1()[1:]]
    bad = BatchSeriesRequest(series_id="bad-series", series=bad_series, max_lag=20)
    batch = BatchTriageRequest(items=[good, bad], max_lag=20, random_state=42)

    response = run_batch_triage(batch, triage_runner=injected_runner)
    outcomes = {item.series_id: item.outcome for item in response.items}

    assert outcomes["good-ar1"] == "ok"
    assert outcomes["bad-series"] == "failed"


def test_rank_batch_items_uses_all_priority_dimensions() -> None:
    """Ranking must follow readiness, profile, directness, exogenous value, and action."""
    items = [
        BatchTriageItemResult(
            series_id="a-clear-high-direct",
            outcome="ok",
            blocked=False,
            readiness_status="clear",
            forecastability_profile="high:high:rich",
            forecastability_class="high",
            directness_class="high",
            directness_ratio=0.90,
            exogenous_usefulness="not_applicable",
            recommended_next_action="prioritize_structured_models",
        ),
        BatchTriageItemResult(
            series_id="b-clear-high-exog-high",
            outcome="ok",
            blocked=False,
            readiness_status="clear",
            forecastability_profile="high:high:include_exogenous_multivariate",
            forecastability_class="high",
            directness_class="high",
            directness_ratio=0.50,
            exogenous_usefulness="high",
            recommended_next_action="prioritize_exogenous_inclusion",
        ),
        BatchTriageItemResult(
            series_id="c-clear-high-exog-low-action-a",
            outcome="ok",
            blocked=False,
            readiness_status="clear",
            forecastability_profile="high:medium:drop_exogenous",
            forecastability_class="high",
            directness_class="medium",
            directness_ratio=0.50,
            exogenous_usefulness="low",
            recommended_next_action="drop_or_retest_exogenous",
        ),
        BatchTriageItemResult(
            series_id="d-clear-high-exog-low-action-b",
            outcome="ok",
            blocked=False,
            readiness_status="clear",
            forecastability_profile="high:medium:drop_exogenous",
            forecastability_class="high",
            directness_class="medium",
            directness_ratio=0.50,
            exogenous_usefulness="low",
            recommended_next_action="use_baseline_models",
        ),
        BatchTriageItemResult(
            series_id="e-clear-medium-direct",
            outcome="ok",
            blocked=False,
            readiness_status="clear",
            forecastability_profile="medium:high:compact",
            forecastability_class="medium",
            directness_class="high",
            directness_ratio=0.95,
            exogenous_usefulness="not_applicable",
            recommended_next_action="validate_compact_models",
        ),
        BatchTriageItemResult(
            series_id="f-warning-high",
            outcome="ok",
            blocked=False,
            readiness_status="warning",
            forecastability_profile="high:high:rich",
            forecastability_class="high",
            directness_class="high",
            directness_ratio=0.99,
            exogenous_usefulness="not_applicable",
            recommended_next_action="prioritize_structured_models",
        ),
        BatchTriageItemResult(
            series_id="g-failed",
            outcome="failed",
            blocked=True,
            readiness_status="failed",
            exogenous_usefulness="not_applicable",
            recommended_next_action="inspect_failure",
            error_code="RuntimeError",
            error_message="failed",
        ),
    ]

    ranked = rank_batch_items(items)
    ordered_ids = [item.series_id for item in ranked]

    assert ordered_ids == [
        "a-clear-high-direct",
        "b-clear-high-exog-high",
        "c-clear-high-exog-low-action-a",
        "d-clear-high-exog-low-action-b",
        "e-clear-medium-direct",
        "f-warning-high",
        "g-failed",
    ]


def test_triage_batch_cli_exports_expected_table_columns(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI export tables must match the stable summary/failure table schema."""
    payload = {
        "max_lag": 20,
        "n_surrogates": 99,
        "random_state": 42,
        "items": [
            {"series_id": "ar1", "series": _make_ar1(n=150), "max_lag": 20},
            {"series_id": "short", "series": [1.0, 2.0, 3.0], "max_lag": 20},
        ],
    }
    batch_json_path = tmp_path / "batch_payload.json"
    batch_json_path.write_text(json.dumps(payload), encoding="utf-8")

    summary_csv_path = tmp_path / "summary.csv"
    failures_csv_path = tmp_path / "failures.csv"

    parser = build_parser()
    args = parser.parse_args(
        [
            "triage-batch",
            "--batch-json",
            str(batch_json_path),
            "--export-summary-csv",
            str(summary_csv_path),
            "--export-failures-csv",
            str(failures_csv_path),
            "--format",
            "json",
        ]
    )

    exit_code = cmd_triage_batch(args)
    assert exit_code == 0

    captured = capsys.readouterr()
    payload_out = json.loads(captured.out)
    assert "summary_table" in payload_out

    with summary_csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(SUMMARY_TABLE_COLUMNS)
        rows = list(reader)
        assert len(rows) == 2

    with failures_csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(FAILURE_TABLE_COLUMNS)
