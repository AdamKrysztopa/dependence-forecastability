"""Unit tests for the covariant interpretation LLM adapter (V3-F09)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from forecastability.adapters.agents.covariant_agent_payload_models import (
    CovariantAgentExplanation,
    explanation_from_interpretation,
)
from forecastability.adapters.llm import covariant_interpretation_agent as agent_module
from forecastability.adapters.llm.covariant_interpretation_agent import (
    run_covariant_interpretation_agent,
)
from forecastability.adapters.settings import InfraSettings
from forecastability.utils.types import (
    CovariantAnalysisBundle,
    CovariantDriverRole,
    CovariantInterpretationResult,
    CovariantMethodConditioning,
    CovariantSummaryRow,
)


def _bundle() -> CovariantAnalysisBundle:
    row = CovariantSummaryRow(
        target="target",
        driver="driver_direct",
        lag=1,
        cross_ami=0.3,
        cross_pami=0.25,
        significance="above_band",
        lagged_exog_conditioning=CovariantMethodConditioning(cross_ami="none"),
    )
    return CovariantAnalysisBundle(
        summary_table=[row],
        target_name="target",
        driver_names=["driver_direct"],
        horizons=[1],
    )


def _interpretation() -> CovariantInterpretationResult:
    return CovariantInterpretationResult(
        target="target",
        driver_roles=[
            CovariantDriverRole(
                driver="driver_direct",
                role="direct_driver",
                best_lag=1,
                evidence=["max_cross_ami=0.3000"],
                methods_supporting=["cross_ami"],
                methods_missing=[],
                conditioning=CovariantMethodConditioning(cross_ami="none"),
            )
        ],
        forecastability_class="high",
        directness_class="high",
        primary_drivers=["driver_direct"],
        modeling_regime="high+high -> deep structured exogenous models",
        conditioning_disclaimer="Bundle conditioning scope: ...",
    )


def _settings_without_key() -> InfraSettings:
    # Explicitly pass openai_api_key=None so env-var OPENAI_API_KEY (if set in
    # the test environment) does not bypass the no-key fallback guard.
    return InfraSettings(_env_file=None, openai_api_key=None)  # type: ignore[call-arg]


def test_strict_mode_returns_narrative_none() -> None:
    explanation = asyncio.run(
        run_covariant_interpretation_agent(
            _bundle(),
            _interpretation(),
            settings=_settings_without_key(),
            strict=True,
        )
    )

    assert explanation.narrative is None
    assert any("strict" in c.lower() for c in explanation.caveats)


def test_no_api_key_returns_strict_fallback() -> None:
    explanation = asyncio.run(
        run_covariant_interpretation_agent(
            _bundle(),
            _interpretation(),
            settings=_settings_without_key(),
            strict=False,
        )
    )

    assert explanation.narrative is None


def test_missing_pydantic_ai_returns_strict_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_module, "_PYDANTIC_AI_AVAILABLE", False)

    settings = InfraSettings(_env_file=None, openai_api_key="pretend")  # type: ignore[call-arg]
    explanation = asyncio.run(
        run_covariant_interpretation_agent(
            _bundle(),
            _interpretation(),
            settings=settings,
            strict=False,
        )
    )

    assert explanation.narrative is None


def test_hallucinated_narrative_is_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    interpretation = _interpretation()

    @dataclass
    class _FakeRunResult:
        output: CovariantAgentExplanation

    class _FakeAgent:
        async def run(self, prompt: str, deps: object) -> _FakeRunResult:
            del prompt, deps
            fabricated = explanation_from_interpretation(
                interpretation,
                narrative="driver_phantom drives the series at 0.987654.",
            )
            return _FakeRunResult(output=fabricated)

    def _fake_create_agent(*, model: str, settings: InfraSettings) -> _FakeAgent:
        del model, settings
        return _FakeAgent()

    monkeypatch.setattr(agent_module, "_PYDANTIC_AI_AVAILABLE", True)
    monkeypatch.setattr(agent_module, "_create_agent", _fake_create_agent)

    settings = InfraSettings(_env_file=None, openai_api_key="pretend")  # type: ignore[call-arg]
    explanation = asyncio.run(
        run_covariant_interpretation_agent(
            _bundle(),
            interpretation,
            settings=settings,
            strict=False,
        )
    )

    assert explanation.narrative is None
    assert any("dropped" in c.lower() for c in explanation.caveats)
    assert any("driver_phantom" in c for c in explanation.caveats)


def test_consistent_narrative_is_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    interpretation = _interpretation()

    @dataclass
    class _FakeRunResult:
        output: CovariantAgentExplanation

    class _FakeAgent:
        async def run(self, prompt: str, deps: object) -> _FakeRunResult:
            del prompt, deps
            clean = explanation_from_interpretation(
                interpretation,
                narrative="driver_direct acts as a direct_driver for the target.",
            )
            return _FakeRunResult(output=clean)

    def _fake_create_agent(*, model: str, settings: InfraSettings) -> _FakeAgent:
        del model, settings
        return _FakeAgent()

    monkeypatch.setattr(agent_module, "_PYDANTIC_AI_AVAILABLE", True)
    monkeypatch.setattr(agent_module, "_create_agent", _fake_create_agent)

    settings = InfraSettings(_env_file=None, openai_api_key="pretend")  # type: ignore[call-arg]
    explanation = asyncio.run(
        run_covariant_interpretation_agent(
            _bundle(),
            interpretation,
            settings=settings,
            strict=False,
        )
    )

    assert explanation.narrative is not None
    assert "driver_direct" in explanation.narrative
