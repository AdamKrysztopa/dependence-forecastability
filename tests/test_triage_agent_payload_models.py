"""Tests for triage agent adapter payload models (A1)."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.adapters.agents.triage_agent_payload_models import (
    f1_profile_payload,
    f2_limits_payload,
    f3_learning_curve_payload,
    f4_spectral_payload,
    f5_lyapunov_payload,
    f6_complexity_payload,
    f7_batch_rank_payload,
    f8_exog_driver_payload,
    triage_agent_payload,
)
from forecastability.triage.batch_models import BatchTriageItemResult
from forecastability.triage.complexity_band import ComplexityBandResult
from forecastability.triage.forecastability_profile import ForecastabilityProfile
from forecastability.triage.lyapunov import LargestLyapunovExponentResult
from forecastability.triage.predictive_info_learning_curve import PredictiveInfoLearningCurve
from forecastability.triage.spectral_predictability import SpectralPredictabilityResult
from forecastability.triage.theoretical_limit_diagnostics import TheoreticalLimitDiagnostics
from forecastability.types import ExogenousDriverSummary

# ---------------------------------------------------------------------------
# Helpers — minimal domain object constructors
# ---------------------------------------------------------------------------


def _make_fp(
    *, is_non_monotone: bool = False, all_below_epsilon: bool = False
) -> ForecastabilityProfile:
    """Return a minimal ForecastabilityProfile for testing."""
    epsilon = 0.05
    if all_below_epsilon:
        values = np.array([0.01, 0.01, 0.01])
        informative: list[int] = []
    else:
        values = np.array([0.3, 0.2, 0.1])
        informative = [1, 2]
    return ForecastabilityProfile(
        horizons=[1, 2, 3],
        values=values,
        epsilon=epsilon,
        informative_horizons=informative,
        peak_horizon=1,
        is_non_monotone=is_non_monotone,
        summary="Test summary.",
        model_now="Model at horizon 1.",
        review_horizons=[1, 2],
        avoid_horizons=[3],
    )


def _make_diagnostics() -> TheoreticalLimitDiagnostics:
    """Return a minimal TheoreticalLimitDiagnostics for testing."""
    return TheoreticalLimitDiagnostics(
        forecastability_ceiling_by_horizon=np.array([0.5, 0.4, 0.3]),
        ceiling_summary="Ceiling at horizon 1 is 0.5.",
        compression_warning=None,
        dpi_warning=None,
        exploitation_ratio_supported=False,
    )


def _make_learning_curve(*, recommended_lookback: int = 10) -> PredictiveInfoLearningCurve:
    """Return a minimal PredictiveInfoLearningCurve for testing."""
    return PredictiveInfoLearningCurve(
        window_sizes=[5, 10, 20],
        information_values=[0.1, 0.2, 0.21],
        convergence_index=1,
        recommended_lookback=recommended_lookback,
        plateau_detected=True,
        reliability_warnings=[],
    )


def _make_spectral(*, n_bins: int = 64) -> SpectralPredictabilityResult:
    """Return a minimal SpectralPredictabilityResult for testing."""
    return SpectralPredictabilityResult(
        score=0.75,
        normalised_entropy=0.25,
        n_bins=n_bins,
        detrend="constant",
        interpretation="High spectral predictability.",
    )


def _make_lle(*, lambda_estimate: float = 0.02) -> LargestLyapunovExponentResult:
    """Return a minimal LargestLyapunovExponentResult for testing."""
    return LargestLyapunovExponentResult(
        lambda_estimate=lambda_estimate,
        embedding_dim=3,
        delay=1,
        evolution_steps=10,
        n_embedded_points=100,
        interpretation="Weakly chaotic.",
        reliability_warning="Treat as experimental.",
        is_experimental=True,
    )


def _make_complexity() -> ComplexityBandResult:
    """Return a minimal ComplexityBandResult for testing."""
    return ComplexityBandResult(
        permutation_entropy=0.6,
        spectral_entropy=0.5,
        embedding_order=3,
        complexity_band="medium",
        interpretation="Moderate complexity.",
        pe_reliability_warning=None,
    )


def _make_batch_item(
    *,
    rank: int | None = 1,
    outcome: str = "ok",
) -> BatchTriageItemResult:
    """Return a minimal BatchTriageItemResult for testing."""
    return BatchTriageItemResult(
        rank=rank,
        series_id="s1",
        outcome=outcome,  # type: ignore[arg-type]
        blocked=False,
        readiness_status="clear",
        warning_codes=[],
        forecastability_class="forecastable",
        directness_class="direct",
        directness_ratio=0.8,
        exogenous_usefulness="not_applicable",
        recommended_next_action="proceed",
        spectral_predictability=0.75,
        permutation_entropy=0.6,
        complexity_band_label="medium",
    )


def _make_exog_driver_summary(
    *,
    redundancy_score: float | None = None,
) -> ExogenousDriverSummary:
    """Return a minimal ExogenousDriverSummary for testing."""
    return ExogenousDriverSummary(
        overall_rank=1,
        driver_name="temperature",
        recommendation="keep",
        pruned=False,
        prune_reason=None,
        mean_usefulness_score=0.42,
        peak_usefulness_score=0.68,
        top_horizon=3,
        top_horizon_usefulness_score=0.68,
        n_horizons_above_floor=5,
        warning_horizon_count=0,
        bh_significant=True,
        redundancy_score=redundancy_score,
    )


# ---------------------------------------------------------------------------
# F1 tests
# ---------------------------------------------------------------------------


def test_f1_profile_payload_monotone() -> None:
    """Monotone curve (is_non_monotone=False, values > epsilon) → monotone_decay."""
    payload = f1_profile_payload(_make_fp(is_non_monotone=False))
    assert payload.profile_shape_label == "monotone_decay"


def test_f1_profile_payload_non_monotone() -> None:
    """Non-monotone curve → non_monotone label."""
    payload = f1_profile_payload(_make_fp(is_non_monotone=True))
    assert payload.profile_shape_label == "non_monotone"


def test_f1_profile_payload_flat() -> None:
    """All values below epsilon, not non_monotone → flat."""
    payload = f1_profile_payload(_make_fp(is_non_monotone=False, all_below_epsilon=True))
    assert payload.profile_shape_label == "flat"


def test_f1_profile_payload_schema_version() -> None:
    """Schema version defaults to '1'."""
    payload = f1_profile_payload(_make_fp())
    assert payload.schema_version == "1"


# ---------------------------------------------------------------------------
# F2 tests
# ---------------------------------------------------------------------------


def test_f2_limits_payload_roundtrip() -> None:
    """Factory converts ndarray fields to list[float] correctly."""
    diagnostics = _make_diagnostics()
    payload = f2_limits_payload(diagnostics)
    assert payload.ceiling_summary == diagnostics.ceiling_summary
    assert payload.theoretical_ceiling_by_horizon == [0.5, 0.4, 0.3]
    assert not payload.exploitation_ratio_supported
    assert payload.compression_warning is None
    assert payload.dpi_warning is None


def test_f2_limits_payload_with_warnings() -> None:
    """Warnings propagated from domain model."""
    diag = TheoreticalLimitDiagnostics(
        forecastability_ceiling_by_horizon=np.array([0.1]),
        ceiling_summary="Low ceiling.",
        compression_warning="Potential compression detected.",
        dpi_warning="DPI triggered.",
        exploitation_ratio_supported=False,
    )
    payload = f2_limits_payload(diag)
    assert payload.compression_warning == "Potential compression detected."
    assert payload.dpi_warning == "DPI triggered."


# ---------------------------------------------------------------------------
# F3 tests
# ---------------------------------------------------------------------------


def test_f3_learning_curve_payload_lookback_summary() -> None:
    """lookback_summary contains the recommended_lookback value."""
    curve = _make_learning_curve(recommended_lookback=15)
    payload = f3_learning_curve_payload(curve)
    assert "15" in payload.lookback_summary
    assert payload.recommended_lookback == 15


def test_f3_learning_curve_payload_plateau_fields() -> None:
    """plateau_detected and reliability_warnings propagated."""
    curve = _make_learning_curve()
    payload = f3_learning_curve_payload(curve)
    assert payload.plateau_detected is True
    assert payload.reliability_warnings == []


# ---------------------------------------------------------------------------
# F4 tests
# ---------------------------------------------------------------------------


def test_f4_spectral_reliability_note_small_bins() -> None:
    """n_bins < 32 → reliability note mentions fewer than 32 bins."""
    payload = f4_spectral_payload(_make_spectral(n_bins=16))
    assert "fewer than 32 bins" in payload.spectral_reliability_notes


def test_f4_spectral_reliability_note_normal_bins() -> None:
    """n_bins >= 32 → standard note."""
    payload = f4_spectral_payload(_make_spectral(n_bins=64))
    assert "standard parameters" in payload.spectral_reliability_notes


def test_f4_spectral_score_propagated() -> None:
    """Spectral predictability score propagated from domain model."""
    payload = f4_spectral_payload(_make_spectral(n_bins=64))
    assert pytest.approx(payload.spectral_predictability_score) == 0.75


# ---------------------------------------------------------------------------
# F5 tests
# ---------------------------------------------------------------------------


def test_f5_lyapunov_always_experimental() -> None:
    """F5LyapunovPayload.is_experimental must always be True."""
    payload = f5_lyapunov_payload(_make_lle())
    assert payload.is_experimental is True


def test_f5_lyapunov_nan_becomes_none() -> None:
    """NaN lambda_estimate is converted to None."""
    payload = f5_lyapunov_payload(_make_lle(lambda_estimate=float("nan")))
    assert payload.lyapunov_estimate is None


def test_f5_lyapunov_finite_estimate_preserved() -> None:
    """Finite lambda_estimate is preserved in payload."""
    payload = f5_lyapunov_payload(_make_lle(lambda_estimate=0.042))
    assert payload.lyapunov_estimate is not None
    assert pytest.approx(payload.lyapunov_estimate) == 0.042


# ---------------------------------------------------------------------------
# F6 tests
# ---------------------------------------------------------------------------


def test_f6_complexity_payload_fields() -> None:
    """All fields populated from domain ComplexityBandResult."""
    result = _make_complexity()
    payload = f6_complexity_payload(result)
    assert pytest.approx(payload.permutation_entropy) == 0.6
    assert pytest.approx(payload.spectral_entropy) == 0.5
    assert payload.complexity_band == "medium"
    assert payload.complexity_summary == "Moderate complexity."
    assert payload.schema_version == "1"


# ---------------------------------------------------------------------------
# F7 tests
# ---------------------------------------------------------------------------


def test_f7_batch_rank_payload_ranking_summary() -> None:
    """ranking_summary is a non-empty string."""
    item = _make_batch_item(rank=3)
    payload = f7_batch_rank_payload(item)
    assert isinstance(payload.ranking_summary, str)
    assert len(payload.ranking_summary) > 0


def test_f7_batch_rank_payload_diagnostic_vector_keys() -> None:
    """diagnostic_vector contains the expected keys."""
    payload = f7_batch_rank_payload(_make_batch_item())
    assert "spectral_predictability" in payload.diagnostic_vector
    assert "permutation_entropy" in payload.diagnostic_vector
    assert "directness_ratio" in payload.diagnostic_vector


def test_f7_batch_rank_payload_none_rank() -> None:
    """batch_rank is None when item.rank is None."""
    payload = f7_batch_rank_payload(_make_batch_item(rank=None, outcome="blocked"))
    assert payload.batch_rank is None


# ---------------------------------------------------------------------------
# F8 tests
# ---------------------------------------------------------------------------


def test_f8_exog_driver_payload_redundancy_flag_true() -> None:
    """redundancy_score=0.5 → redundancy_flag=True."""
    summary = _make_exog_driver_summary(redundancy_score=0.5)
    payload = f8_exog_driver_payload(summary)
    assert payload.redundancy_flag is True


def test_f8_exog_driver_payload_redundancy_flag_false() -> None:
    """redundancy_score=None → redundancy_flag=False."""
    summary = _make_exog_driver_summary(redundancy_score=None)
    payload = f8_exog_driver_payload(summary)
    assert payload.redundancy_flag is False


def test_f8_exog_driver_payload_redundancy_flag_below_threshold() -> None:
    """redundancy_score <= 0.1 → redundancy_flag=False."""
    summary = _make_exog_driver_summary(redundancy_score=0.05)
    payload = f8_exog_driver_payload(summary)
    assert payload.redundancy_flag is False


def test_f8_exog_driver_recommendation_summary() -> None:
    """driver_recommendation_summary contains driver name and recommendation."""
    summary = _make_exog_driver_summary()
    payload = f8_exog_driver_payload(summary)
    assert "temperature" in payload.driver_recommendation_summary
    assert "keep" in payload.driver_recommendation_summary


# ---------------------------------------------------------------------------
# TriageAgentPayload tests
# ---------------------------------------------------------------------------


def test_triage_agent_payload_from_blocked_result(
    deterministic_blocked_request,  # type: ignore[no-untyped-def]
) -> None:
    """Blocked TriageResult → payload has blocked=True and all diagnostics None."""
    from forecastability.triage.run_triage import run_triage

    result = run_triage(deterministic_blocked_request)
    payload = triage_agent_payload(result, series_id="blocked_series")
    assert payload.blocked is True
    assert payload.f1_profile is None
    assert payload.f2_limits is None
    assert payload.f5_lyapunov is None
    assert payload.f6_complexity is None


def test_triage_agent_payload_schema_version(
    deterministic_triage_result,  # type: ignore[no-untyped-def]
) -> None:
    """All nested payloads that are not None carry schema_version='1'."""
    payload = triage_agent_payload(deterministic_triage_result, series_id="test")
    assert payload.schema_version == "1"
    if payload.f1_profile is not None:
        assert payload.f1_profile.schema_version == "1"
    if payload.f2_limits is not None:
        assert payload.f2_limits.schema_version == "1"
    if payload.f6_complexity is not None:
        assert payload.f6_complexity.schema_version == "1"
    if payload.f5_lyapunov is not None:
        assert payload.f5_lyapunov.schema_version == "1"


def test_payload_json_serializable(
    deterministic_triage_result,  # type: ignore[no-untyped-def]
) -> None:
    """TriageAgentPayload.model_dump() must contain no numpy types."""
    import json

    payload = triage_agent_payload(deterministic_triage_result, series_id="test")
    dumped = payload.model_dump()
    # Raises if any value is not JSON-serialisable (e.g. numpy scalar)
    json.dumps(dumped)


def test_triage_agent_payload_series_id_propagated(
    deterministic_triage_result,  # type: ignore[no-untyped-def]
) -> None:
    """series_id keyword arg is stored in the payload."""
    payload = triage_agent_payload(deterministic_triage_result, series_id="my_series")
    assert payload.series_id == "my_series"


def test_triage_agent_payload_no_series_id(
    deterministic_triage_result,  # type: ignore[no-untyped-def]
) -> None:
    """Omitting series_id yields series_id=None."""
    payload = triage_agent_payload(deterministic_triage_result)
    assert payload.series_id is None
