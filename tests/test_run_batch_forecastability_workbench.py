"""Tests for the batch forecastability workbench use case and reporting."""

from __future__ import annotations

import pytest

from forecastability.reporting.forecastability_workbench_reporting import (
    build_batch_forecastability_executive_markdown,
    build_batch_forecastability_markdown,
)
from forecastability.triage import BatchSeriesRequest, BatchTriageRequest
from forecastability.use_cases.batch_forecastability_workbench_models import (
    BatchForecastabilityWorkbenchResult,
)
from forecastability.use_cases.run_batch_forecastability_workbench import (
    run_batch_forecastability_workbench,
)
from forecastability.utils.synthetic import (
    generate_ar1_monotonic,
    generate_seasonal_periodic,
    generate_white_noise,
)

_N = 320
_MAX_LAG = 12
_N_SURROGATES = 99


@pytest.fixture(scope="module")
def workbench_result() -> BatchForecastabilityWorkbenchResult:
    """Run the batch workbench on a small deterministic synthetic portfolio."""
    request = BatchTriageRequest(
        items=[
            BatchSeriesRequest(
                series_id="white_noise",
                series=generate_white_noise(n=_N, seed=42).tolist(),
            ),
            BatchSeriesRequest(
                series_id="ar1_monotonic",
                series=generate_ar1_monotonic(n=_N, seed=42).tolist(),
            ),
            BatchSeriesRequest(
                series_id="seasonal_periodic",
                series=generate_seasonal_periodic(n=_N, period=12, seed=42).tolist(),
            ),
            BatchSeriesRequest(
                series_id="too_short",
                series=generate_white_noise(n=24, seed=7).tolist(),
            ),
        ],
        max_lag=_MAX_LAG,
        n_surrogates=_N_SURROGATES,
        random_state=42,
    )
    return run_batch_forecastability_workbench(request, top_n=2)


def test_returns_typed_workbench_result(
    workbench_result: BatchForecastabilityWorkbenchResult,
) -> None:
    """The composite batch workbench should return the typed result model."""
    assert isinstance(workbench_result, BatchForecastabilityWorkbenchResult)
    assert len(workbench_result.items) == 4
    assert workbench_result.summary.n_series == 4


def test_white_noise_downscopes_to_baseline_monitoring(
    workbench_result: BatchForecastabilityWorkbenchResult,
) -> None:
    """White noise should remain on a baseline-first path."""
    white_noise = next(item for item in workbench_result.items if item.series_id == "white_noise")
    assert white_noise.fingerprint_bundle is not None
    assert white_noise.next_step.action == "baseline_monitoring"
    assert "naive" in white_noise.next_step.recommended_model_families


def test_seasonal_series_does_not_downscope_to_baseline(
    workbench_result: BatchForecastabilityWorkbenchResult,
) -> None:
    """The seasonal archetype should remain on an active modeling path."""
    seasonal = next(
        item for item in workbench_result.items if item.series_id == "seasonal_periodic"
    )
    assert seasonal.fingerprint_bundle is not None
    assert seasonal.next_step.action in {
        "seasonal_benchmark",
        "hybrid_review",
        "nonlinear_benchmark",
    }
    assert seasonal.next_step.priority_tier in {"high", "review"}


def test_short_series_requires_remediation(
    workbench_result: BatchForecastabilityWorkbenchResult,
) -> None:
    """Short series should not produce a model-selection bundle."""
    short = next(item for item in workbench_result.items if item.series_id == "too_short")
    assert short.fingerprint_bundle is None
    assert short.next_step.action in {"resolve_readiness", "investigate_failure"}


def test_reports_include_technical_and_executive_surfaces(
    workbench_result: BatchForecastabilityWorkbenchResult,
) -> None:
    """Both markdown renderers should expose the new batch workflow."""
    technical = build_batch_forecastability_markdown(workbench_result)
    executive = build_batch_forecastability_executive_markdown(workbench_result)

    assert "Batch Forecastability Workbench" in technical
    assert "seasonal_periodic" in technical
    assert "next_step_action" in technical

    assert "Forecasting Portfolio Brief" in executive
    assert "Decision Summary" in executive
    assert "white_noise" in executive
