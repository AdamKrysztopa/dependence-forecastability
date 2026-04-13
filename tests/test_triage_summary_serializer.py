"""Tests for triage summary serialiser — agent adapter A2."""

from __future__ import annotations

import json
import re

import pytest

from forecastability.adapters.agents.triage_agent_payload_models import (
    F1ProfilePayload,
    F2LimitsPayload,
    F3LearningCurvePayload,
    F4SpectralPayload,
    F5LyapunovPayload,
    F6ComplexityPayload,
    F7BatchRankPayload,
    F8ExogDriverPayload,
    TriageAgentPayload,
)
from forecastability.adapters.agents.triage_summary_serializer import (
    SerialisedTriageSummary,
    serialise_batch,
    serialise_batch_to_json,
    serialise_payload,
    serialise_to_json,
)

# ---------------------------------------------------------------------------
# Fixtures — minimal payload constructors (no domain code, pure Pydantic)
# ---------------------------------------------------------------------------


@pytest.fixture
def f1_payload() -> F1ProfilePayload:
    """Return a minimal F1ProfilePayload for testing."""
    return F1ProfilePayload(
        peak_horizon=1,
        informative_horizons=[1, 2, 3],
        profile_shape_label="monotone_decay",
        profile_summary="Test F1.",
        model_now="Model at horizon 1.",
        review_horizons=[1],
        avoid_horizons=[4, 5],
        epsilon=0.05,
    )


@pytest.fixture
def f2_payload() -> F2LimitsPayload:
    """Return a minimal F2LimitsPayload for testing."""
    return F2LimitsPayload(
        theoretical_ceiling_by_horizon=[0.5, 0.4, 0.3],
        ceiling_summary="Ceiling at horizon 1 is 0.5.",
        compression_warning=None,
        dpi_warning=None,
        exploitation_ratio_supported=False,
    )


@pytest.fixture
def f3_payload() -> F3LearningCurvePayload:
    """Return a minimal F3LearningCurvePayload for testing."""
    return F3LearningCurvePayload(
        recommended_lookback=10,
        plateau_detected=True,
        reliability_warnings=[],
        lookback_summary="Recommended lookback is 10.",
    )


@pytest.fixture
def f4_payload() -> F4SpectralPayload:
    """Return a minimal F4SpectralPayload for testing."""
    return F4SpectralPayload(
        spectral_predictability_score=0.75,
        spectral_summary="High spectral predictability.",
        spectral_reliability_notes="Welch PSD assumptions apply.",
    )


@pytest.fixture
def f5_payload() -> F5LyapunovPayload:
    """Return a minimal F5LyapunovPayload for testing."""
    return F5LyapunovPayload(
        lyapunov_estimate=0.02,
        lyapunov_interpretation="Weakly chaotic.",
        lyapunov_warning="Treat as experimental.",
        experimental_flag_required=True,
        is_experimental=True,
    )


@pytest.fixture
def f6_payload() -> F6ComplexityPayload:
    """Return a minimal F6ComplexityPayload for testing."""
    return F6ComplexityPayload(
        permutation_entropy=0.6,
        spectral_entropy=0.5,
        complexity_band="medium",
        complexity_summary="Moderate complexity.",
    )


@pytest.fixture
def f7_payload() -> F7BatchRankPayload:
    """Return a minimal F7BatchRankPayload for testing."""
    return F7BatchRankPayload(
        series_id="s1",
        batch_rank=1,
        outcome="ok",
        forecastability_class="forecastable",
        directness_class="direct",
        directness_ratio=0.8,
        complexity_band="medium",
        spectral_predictability=0.75,
        diagnostic_vector={"ami": 0.3, "pami": 0.24},
        ranking_summary="Rank 1 of 1.",
    )


@pytest.fixture
def f8_payload() -> F8ExogDriverPayload:
    """Return a minimal F8ExogDriverPayload for testing."""
    return F8ExogDriverPayload(
        driver_name="temperature",
        driver_rank=1,
        recommendation="keep",
        mean_usefulness_score=0.42,
        peak_usefulness_score=0.68,
        driver_scores_summary=[0.42, 0.68],
        redundancy_flag=False,
        driver_recommendation_summary="Keep driver: temperature.",
    )


@pytest.fixture
def composite_payload() -> TriageAgentPayload:
    """Return a minimal TriageAgentPayload with all sub-payloads set to None."""
    return TriageAgentPayload(
        series_id="test",
        blocked=False,
        readiness_status="clear",
        forecastability_class=None,
        directness_class=None,
        modeling_regime=None,
        recommendation=None,
        f1_profile=None,
        f2_limits=None,
        f3_learning_curve=None,
        f4_spectral=None,
        f5_lyapunov=None,
        f6_complexity=None,
        warnings=[],
        experimental_notes=[],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_serialise_payload_returns_serialised_triage_summary(
    f1_payload: F1ProfilePayload,
) -> None:
    """serialise_payload returns a SerialisedTriageSummary instance."""
    result = serialise_payload(f1_payload)
    assert isinstance(result, SerialisedTriageSummary)


def test_serialise_payload_schema_version(f1_payload: F1ProfilePayload) -> None:
    """serialise_payload sets schema_version to '1'."""
    result = serialise_payload(f1_payload)
    assert result.schema_version == "1"


def test_serialise_payload_type_is_class_name(f1_payload: F1ProfilePayload) -> None:
    """payload_type equals the class name of the wrapped payload."""
    result = serialise_payload(f1_payload)
    assert result.payload_type == "F1ProfilePayload"


def test_serialise_payload_serialised_at_is_iso8601_utc(f1_payload: F1ProfilePayload) -> None:
    """serialised_at matches an ISO-8601 UTC timestamp pattern."""
    result = serialise_payload(f1_payload)
    pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.*\+00:00"
    assert re.search(pattern, result.serialised_at) is not None


def test_serialise_payload_payload_contains_no_numpy_types(f1_payload: F1ProfilePayload) -> None:
    """payload dict round-trips through JSON without TypeError."""
    result = serialise_payload(f1_payload)
    dumped = json.dumps(result.payload)
    parsed = json.loads(dumped)
    assert isinstance(parsed, dict)


def test_serialise_payload_payload_dict_has_expected_field(f1_payload: F1ProfilePayload) -> None:
    """payload dict contains the 'peak_horizon' key from F1ProfilePayload."""
    result = serialise_payload(f1_payload)
    assert "peak_horizon" in result.payload


@pytest.mark.parametrize(
    "payload_fixture",
    [
        "f1_payload",
        "f2_payload",
        "f3_payload",
        "f4_payload",
        "f5_payload",
        "f6_payload",
        "f7_payload",
        "f8_payload",
        "composite_payload",
    ],
)
def test_serialise_payload_works_for_all_payload_types(
    payload_fixture: str,
    request: pytest.FixtureRequest,
) -> None:
    """serialise_payload sets payload_type to the class name for all payload types."""
    payload = request.getfixturevalue(payload_fixture)
    result = serialise_payload(payload)
    assert result.payload_type == type(payload).__name__


def test_serialise_batch_returns_list_of_correct_length(
    f1_payload: F1ProfilePayload,
    f2_payload: F2LimitsPayload,
    f6_payload: F6ComplexityPayload,
) -> None:
    """serialise_batch returns a list with the same length as the input sequence."""
    batch = serialise_batch([f1_payload, f2_payload, f6_payload])
    assert len(batch) == 3


def test_serialise_batch_payload_types_match(
    f1_payload: F1ProfilePayload,
    f2_payload: F2LimitsPayload,
) -> None:
    """serialise_batch preserves payload_type order matching the input order."""
    batch = serialise_batch([f1_payload, f2_payload])
    assert [e.payload_type for e in batch] == ["F1ProfilePayload", "F2LimitsPayload"]


def test_serialise_to_json_returns_valid_json_string(f1_payload: F1ProfilePayload) -> None:
    """serialise_to_json returns a string that parses as valid JSON."""
    json_str = serialise_to_json(f1_payload)
    parsed = json.loads(json_str)
    assert isinstance(parsed, dict)


def test_serialise_to_json_envelope_fields(f1_payload: F1ProfilePayload) -> None:
    """serialise_to_json JSON contains all required envelope keys."""
    json_str = serialise_to_json(f1_payload)
    parsed = json.loads(json_str)
    for key in ("schema_version", "payload_type", "serialised_at", "payload"):
        assert key in parsed


def test_serialise_batch_to_json_is_valid_json_array(
    f1_payload: F1ProfilePayload,
    f2_payload: F2LimitsPayload,
) -> None:
    """serialise_batch_to_json returns a JSON array of length 2."""
    json_str = serialise_batch_to_json([f1_payload, f2_payload])
    parsed = json.loads(json_str)
    assert isinstance(parsed, list)
    assert len(parsed) == 2


def test_serialised_triage_summary_is_frozen(f1_payload: F1ProfilePayload) -> None:
    """SerialisedTriageSummary is frozen and raises on attempted attribute mutation."""
    result = serialise_payload(f1_payload)
    with pytest.raises(Exception):  # noqa: B017 — frozen Pydantic raises ValidationError
        result.schema_version = "2"  # type: ignore[misc]


def test_serialise_payload_composite_triage_agent_payload(
    composite_payload: TriageAgentPayload,
) -> None:
    """serialise_payload handles TriageAgentPayload and sets the correct payload_type."""
    result = serialise_payload(composite_payload)
    assert result.payload_type == "TriageAgentPayload"


def test_serialise_batch_empty_input() -> None:
    """serialise_batch returns an empty list for an empty input sequence."""
    assert serialise_batch([]) == []


def test_serialise_batch_to_json_empty_input() -> None:
    """serialise_batch_to_json returns '[]' JSON for an empty input sequence."""
    assert json.loads(serialise_batch_to_json([])) == []
