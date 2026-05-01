"""Tests for the batch forecastability workbench use case and reporting."""

from __future__ import annotations

import numpy as np
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


def _build_parity_request() -> BatchTriageRequest:
    """Build a small deterministic request mixing ok and blocked outcomes."""
    return BatchTriageRequest(
        items=[
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


def _assert_results_bit_identical(
    left: BatchForecastabilityWorkbenchResult,
    right: BatchForecastabilityWorkbenchResult,
) -> None:
    """Compare two workbench results structurally, including embedded numpy arrays.

    Some embedded fields (e.g. ``TriageRequest.series`` and the geometry profiles
    inside ``FingerprintBundle``) store ``numpy.ndarray`` values, which break
    Pydantic's element-wise ``__eq__``. ``numpy.testing.assert_equal`` walks
    nested mappings/sequences and applies array-aware comparison.
    """
    assert [item.series_id for item in left.items] == [item.series_id for item in right.items]
    assert left.summary == right.summary
    np.testing.assert_equal(
        [item.model_dump() for item in left.items],
        [item.model_dump() for item in right.items],
    )


def test_n_jobs_default_matches_explicit_serial() -> None:
    """Omitting ``n_jobs`` must match ``n_jobs=1`` exactly."""
    request = _build_parity_request()
    default_result = run_batch_forecastability_workbench(request, top_n=2)
    serial_result = run_batch_forecastability_workbench(request, top_n=2, n_jobs=1)
    _assert_results_bit_identical(default_result, serial_result)


def test_n_jobs_serial_vs_parallel_bit_identical() -> None:
    """Parallel execution must be bit-identical to the serial path under fixed seeds."""
    request = _build_parity_request()
    serial_result = run_batch_forecastability_workbench(request, top_n=2, n_jobs=1)
    parallel_result = run_batch_forecastability_workbench(request, top_n=2, n_jobs=2)
    _assert_results_bit_identical(serial_result, parallel_result)


def test_n_jobs_zero_is_rejected() -> None:
    """``n_jobs=0`` is not a valid joblib value and must raise ``ValueError``."""
    request = _build_parity_request()
    with pytest.raises(ValueError, match="n_jobs"):
        run_batch_forecastability_workbench(request, top_n=2, n_jobs=0)


def test_item_ordering_preserved_across_n_jobs() -> None:
    """Workbench item ordering must follow the upstream execution order regardless of ``n_jobs``."""
    request = _build_parity_request()
    serial_result = run_batch_forecastability_workbench(request, top_n=2, n_jobs=1)
    parallel_result = run_batch_forecastability_workbench(request, top_n=2, n_jobs=2)
    serial_ids = [item.series_id for item in serial_result.items]
    parallel_ids = [item.series_id for item in parallel_result.items]
    assert serial_ids == parallel_ids
    assert set(serial_ids) == {"ar1_monotonic", "seasonal_periodic", "too_short"}
