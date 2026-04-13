"""Tests for deterministic A3 triage interpretation adapter."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from forecastability.adapters.agents.triage_agent_interpretation_adapter import (
    TriageAgentInterpretation,
    interpret_batch,
    interpret_payload,
)
from forecastability.adapters.agents.triage_agent_payload_models import (
    F1ProfilePayload,
    F2LimitsPayload,
    F5LyapunovPayload,
    F6ComplexityPayload,
    TriageAgentPayload,
)
from forecastability.adapters.agents.triage_summary_serializer import (
    SerialisedTriageSummary,
    serialise_payload,
)


def _f1_payload() -> F1ProfilePayload:
    """Return deterministic F1 payload for interpretation tests."""
    return F1ProfilePayload(
        peak_horizon=1,
        informative_horizons=[1, 2, 3],
        profile_shape_label="monotone_decay",
        profile_summary="Stable direct profile.",
        model_now="Use short-lag model.",
        review_horizons=[1, 2],
        avoid_horizons=[4, 5],
        epsilon=0.05,
    )


def _f2_payload() -> F2LimitsPayload:
    """Return deterministic F2 payload with reliability warnings."""
    return F2LimitsPayload(
        theoretical_ceiling_by_horizon=[0.4, 0.3, 0.2],
        ceiling_summary="Theoretical ceiling declines with horizon.",
        compression_warning="Compression may hide weak long-lag dependence.",
        dpi_warning="DPI warning: transformed signal may lose information.",
        exploitation_ratio_supported=False,
    )


def _f5_payload() -> F5LyapunovPayload:
    """Return deterministic experimental F5 payload."""
    return F5LyapunovPayload(
        lyapunov_estimate=0.03,
        lyapunov_interpretation="Weakly chaotic.",
        lyapunov_warning="Treat LLE as experimental.",
        experimental_flag_required=True,
        is_experimental=True,
    )


def _f6_payload() -> F6ComplexityPayload:
    """Return deterministic F6 payload."""
    return F6ComplexityPayload(
        permutation_entropy=0.58,
        spectral_entropy=0.47,
        complexity_band="medium",
        complexity_summary="Moderate complexity.",
    )


def _payload(
    *,
    series_id: str,
    blocked: bool,
    readiness_status: str,
    forecastability_class: str | None,
    directness_class: str | None,
    modeling_regime: str | None,
    warnings: list[str] | None = None,
    experimental_notes: list[str] | None = None,
    include_f1: bool = True,
    include_f2: bool = False,
    include_f5: bool = False,
    include_f6: bool = True,
) -> TriageAgentPayload:
    """Build a minimal deterministic TriageAgentPayload for tests."""
    return TriageAgentPayload(
        series_id=series_id,
        blocked=blocked,
        readiness_status=readiness_status,
        forecastability_class=forecastability_class,
        directness_class=directness_class,
        modeling_regime=modeling_regime,
        recommendation=None,
        f1_profile=_f1_payload() if include_f1 else None,
        f2_limits=_f2_payload() if include_f2 else None,
        f3_learning_curve=None,
        f4_spectral=None,
        f5_lyapunov=_f5_payload() if include_f5 else None,
        f6_complexity=_f6_payload() if include_f6 else None,
        warnings=list(warnings or []),
        experimental_notes=list(experimental_notes or []),
    )


def test_interpret_payload_blocked_payload_handling() -> None:
    """Blocked payloads should produce blocked deterministic interpretation."""
    payload = _payload(
        series_id="blocked_case",
        blocked=True,
        readiness_status="blocked",
        forecastability_class=None,
        directness_class=None,
        modeling_regime=None,
        warnings=["max_lag too large for sample size"],
        include_f1=False,
        include_f6=False,
    )

    interpreted = interpret_payload(payload)

    assert interpreted.signal_bucket == "blocked"
    assert interpreted.strong_signal_narrative is None
    assert "blocked at readiness gate" in interpreted.deterministic_summary.lower()
    assert interpreted.cautionary_narrative is not None
    assert "readiness gate blocked diagnostics" in interpreted.cautionary_narrative.lower()
    assert interpreted.warnings == ["max_lag too large for sample size"]


def test_interpret_payload_strong_high_signal_handling() -> None:
    """High forecastability plus high directness should map to strong signal path."""
    payload = _payload(
        series_id="strong_case",
        blocked=False,
        readiness_status="clear",
        forecastability_class="high",
        directness_class="high",
        modeling_regime="rich_models_with_structured_memory",
    )

    interpreted = interpret_payload(payload)

    assert interpreted.signal_bucket == "strong"
    assert interpreted.strong_signal_narrative is not None
    assert "Strong-signal evidence" in interpreted.strong_signal_narrative
    assert "Informative horizons detected: 3" in interpreted.strong_signal_narrative
    assert interpreted.cautionary_narrative is None


@pytest.mark.parametrize(
    ("forecastability_class", "directness_class", "expected_bucket", "expected_phrase"),
    [
        ("high", "medium", "mediated", "Mediated signal"),
        ("medium", "medium", "uncertain", "Uncertain signal"),
        ("low", "low", "low", "Low signal"),
    ],
)
def test_interpret_payload_mediated_low_uncertain_handling(
    forecastability_class: str,
    directness_class: str,
    expected_bucket: str,
    expected_phrase: str,
) -> None:
    """Mediated/uncertain/low payloads should route to cautionary narrative."""
    payload = _payload(
        series_id="caution_case",
        blocked=False,
        readiness_status="clear",
        forecastability_class=forecastability_class,
        directness_class=directness_class,
        modeling_regime="compact_models",
    )

    interpreted = interpret_payload(payload)

    assert interpreted.signal_bucket == expected_bucket
    assert interpreted.strong_signal_narrative is None
    assert interpreted.cautionary_narrative is not None
    assert expected_phrase in interpreted.cautionary_narrative


def test_interpret_payload_warnings_propagation() -> None:
    """Warnings should be propagated and explicitly reflected in reliability fields."""
    payload = _payload(
        series_id="warning_case",
        blocked=False,
        readiness_status="warning",
        forecastability_class="high",
        directness_class="medium",
        modeling_regime="compact_structured_models",
        warnings=["Surrogate bands unstable.", "Near-constant variance."],
    )

    interpreted = interpret_payload(payload)

    assert interpreted.warnings == ["Surrogate bands unstable.", "Near-constant variance."]
    assert interpreted.cautionary_narrative is not None
    assert "Warnings were emitted (2 total)" in interpreted.cautionary_narrative
    assert any("2 warning(s)" in note for note in interpreted.reliability_notes)
    assert any("Readiness status is 'warning'" in note for note in interpreted.reliability_notes)


def test_interpret_payload_experimental_flags_propagation() -> None:
    """Experimental notes and F5 flags should be explicit in A3 output fields."""
    payload = _payload(
        series_id="experimental_case",
        blocked=False,
        readiness_status="clear",
        forecastability_class="medium",
        directness_class="medium",
        modeling_regime="seasonal_or_regularized_models",
        experimental_notes=["Adapter-level experimental note."],
        include_f5=True,
    )

    interpreted = interpret_payload(payload)

    assert interpreted.experimental_flagged is True
    assert interpreted.experimental_narrative is not None
    assert "experimental diagnostics are present" in interpreted.experimental_narrative.lower()
    assert "Adapter-level experimental note." in interpreted.experimental_notes
    assert "Treat LLE as experimental." in interpreted.experimental_notes
    assert "F5 Lyapunov diagnostic is marked experimental." in interpreted.experimental_notes


def test_interpret_payload_serialised_envelope_input_behavior() -> None:
    """A2 envelope input should resolve to the same deterministic A3 interpretation."""
    payload = _payload(
        series_id="envelope_case",
        blocked=False,
        readiness_status="clear",
        forecastability_class="high",
        directness_class="high",
        modeling_regime="rich_models_with_structured_memory",
    )
    envelope = serialise_payload(payload)

    interpreted_from_payload = interpret_payload(payload)
    interpreted_from_envelope = interpret_payload(envelope)

    assert interpreted_from_envelope.source_serialised_at == envelope.serialised_at
    assert interpreted_from_envelope.source_series_id == payload.series_id
    assert (
        interpreted_from_envelope.deterministic_summary
        == interpreted_from_payload.deterministic_summary
    )


def test_interpret_payload_rejects_non_triage_envelope_payload_type() -> None:
    """A2 envelope payload_type must be TriageAgentPayload for A3 interpretation."""
    envelope = SerialisedTriageSummary(
        payload_type="F1ProfilePayload",
        serialised_at="2026-04-13T12:00:00+00:00",
        payload={"peak_horizon": 1},
    )

    with pytest.raises(ValueError, match="requires SerialisedTriageSummary"):
        interpret_payload(envelope)


def test_interpret_batch_preserves_input_order() -> None:
    """Batch interpretation should preserve payload order, including A2 envelopes."""
    first = _payload(
        series_id="first",
        blocked=False,
        readiness_status="clear",
        forecastability_class="high",
        directness_class="high",
        modeling_regime="rich_models_with_structured_memory",
    )
    second = _payload(
        series_id="second",
        blocked=False,
        readiness_status="clear",
        forecastability_class="medium",
        directness_class="medium",
        modeling_regime="seasonal_or_regularized_models",
    )
    third = _payload(
        series_id="third",
        blocked=False,
        readiness_status="clear",
        forecastability_class="low",
        directness_class="low",
        modeling_regime="baseline_or_robust_decision_design",
    )

    interpreted = interpret_batch([first, serialise_payload(second), third])

    assert [item.source_series_id for item in interpreted] == ["first", "second", "third"]


def test_triage_agent_interpretation_model_is_frozen() -> None:
    """A3 output model should be frozen for transport-layer safety."""
    payload = _payload(
        series_id="frozen_case",
        blocked=False,
        readiness_status="clear",
        forecastability_class="high",
        directness_class="high",
        modeling_regime="rich_models_with_structured_memory",
    )
    interpreted = interpret_payload(payload)

    with pytest.raises(ValidationError):
        interpreted.signal_bucket = "low"


def test_interpret_payload_deterministic_output_strings_and_fields() -> None:
    """Repeated interpretation of same payload should produce identical deterministic text."""
    payload = _payload(
        series_id="deterministic_case",
        blocked=False,
        readiness_status="clear",
        forecastability_class="high",
        directness_class="high",
        modeling_regime="rich_models_with_structured_memory",
        include_f2=True,
    )

    first: TriageAgentInterpretation = interpret_payload(payload)
    second: TriageAgentInterpretation = interpret_payload(payload)

    assert first.model_dump() == second.model_dump()
    assert "Series 'deterministic_case'" in first.deterministic_summary
    assert "strong signal" in first.deterministic_summary
    assert first.evidence.forecastability_class == "high"
    assert first.evidence.informative_horizon_count == 3
    assert "Compression may hide weak long-lag dependence." in first.reliability_notes
    assert "DPI warning: transformed signal may lose information." in first.reliability_notes
