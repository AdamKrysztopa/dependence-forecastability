"""Unit tests for the covariant agent payload models (V3-F09)."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from forecastability.adapters.agents.covariant_agent_payload_models import (
    CovariantAgentExplanation,
    explanation_from_interpretation,
)
from forecastability.utils.types import (
    CovariantDriverRole,
    CovariantInterpretationResult,
    CovariantMethodConditioning,
)


def _make_interpretation() -> CovariantInterpretationResult:
    conditioning = CovariantMethodConditioning(cross_ami="none")
    return CovariantInterpretationResult(
        target="target",
        driver_roles=[
            CovariantDriverRole(
                driver="driver_direct",
                role="direct_driver",
                best_lag=2,
                evidence=["max_cross_ami=0.25"],
                methods_supporting=["cross_ami", "pcmci"],
                methods_missing=["gcmi"],
                conditioning=conditioning,
                warnings=["driver-local caveat"],
            ),
            CovariantDriverRole(
                driver="driver_noise",
                role="noise_or_weak",
                best_lag=None,
                evidence=["max_cross_ami=0.0010"],
                methods_supporting=[],
                methods_missing=["cross_ami"],
                conditioning=conditioning,
            ),
        ],
        forecastability_class="high",
        directness_class="high",
        primary_drivers=["driver_direct"],
        modeling_regime="high+high -> deep structured exogenous models",
        conditioning_disclaimer="Bundle conditioning scope: ...",
        warnings=["top-level caveat"],
    )


def test_explanation_from_interpretation_echoes_roles() -> None:
    interpretation = _make_interpretation()

    explanation = explanation_from_interpretation(interpretation, narrative="brief narrative.")

    assert explanation.target == "target"
    assert explanation.driver_role_echo == {
        "driver_direct": "direct_driver",
        "driver_noise": "noise_or_weak",
    }
    assert explanation.primary_drivers == ["driver_direct"]
    assert explanation.narrative == "brief narrative."
    assert "top-level caveat" in explanation.caveats
    assert "driver-local caveat" in explanation.caveats


def test_explanation_merges_additional_caveats_without_duplicates() -> None:
    interpretation = _make_interpretation()

    explanation = explanation_from_interpretation(
        interpretation,
        narrative=None,
        caveats=["top-level caveat", "extra caveat"],
    )

    # Deduplicated: "top-level caveat" appears once.
    assert explanation.caveats.count("top-level caveat") == 1
    assert "extra caveat" in explanation.caveats


def test_explanation_roundtrips_through_json() -> None:
    interpretation = _make_interpretation()

    explanation = explanation_from_interpretation(interpretation, narrative="ok.")
    payload = explanation.model_dump(mode="json")
    roundtripped = CovariantAgentExplanation.model_validate(json.loads(json.dumps(payload)))

    assert roundtripped == explanation


def test_explanation_rejects_extra_fields() -> None:
    interpretation = _make_interpretation()
    explanation = explanation_from_interpretation(interpretation, narrative=None)
    payload = explanation.model_dump()
    payload["unexpected"] = "oops"

    with pytest.raises(ValidationError):
        CovariantAgentExplanation.model_validate(payload)


def test_explanation_schema_version_is_frozen_default() -> None:
    interpretation = _make_interpretation()

    explanation = explanation_from_interpretation(interpretation, narrative=None)

    assert explanation.schema_version == "1"
