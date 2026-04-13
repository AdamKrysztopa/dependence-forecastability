"""Tests for the live screening agent adapter extracted from notebook 04."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

pydantic_ai = pytest.importorskip("pydantic_ai", reason="pydantic-ai extra not installed")
from pydantic_ai import models  # noqa: E402

# Block real model requests during tests.
models.ALLOW_MODEL_REQUESTS = False  # type: ignore[assignment]


class TestCreateScreeningAgent:
    """Verify screening agent construction and tool wiring."""

    def test_agent_creation_succeeds(self) -> None:
        from forecastability.adapters.llm.screening_agent import create_screening_agent
        from forecastability.adapters.settings import InfraSettings

        settings = InfraSettings(_env_file=None)  # type: ignore[call-arg]
        agent = create_screening_agent(model="test", settings=settings)
        assert agent is not None

    def test_agent_has_expected_tools(self) -> None:
        from forecastability.adapters.llm.screening_agent import create_screening_agent
        from forecastability.adapters.settings import InfraSettings

        settings = InfraSettings(_env_file=None)  # type: ignore[call-arg]
        agent = create_screening_agent(model="test", settings=settings)
        tool_names = set(agent._function_toolset.tools)
        expected = {"list_candidates", "assess_target", "screen_feature"}
        assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"


class TestScreeningModels:
    """Verify frozen output model contracts."""

    def test_feature_screening_report_is_frozen(self) -> None:
        from forecastability.adapters.llm.screening_agent import (
            FeatureRanking,
            FeatureScreeningReport,
        )

        report = FeatureScreeningReport(
            target_name="cnt",
            target_forecastability="high",
            target_regime="compact_structured_models",
            rankings=[
                FeatureRanking(
                    feature_name="temp",
                    action="include_conditional",
                    peak_cross_ami=0.11,
                    peak_partial_cross_ami=0.09,
                    rationale="Moderate dependence with mostly direct effect.",
                )
            ],
            overall_recommendation="Include temperature with regularisation.",
            caveats=["Short horizon may understate seasonality."],
        )

        with pytest.raises(ValidationError):
            report.target_name = "y"


class TestScreeningResultSummary:
    """Verify deterministic summary extraction used by LLM tools."""

    def test_result_summary_contains_scalar_fields(self) -> None:
        from forecastability.adapters.llm.screening_agent import _result_summary
        from forecastability.triage import TriageRequest, run_triage

        rng = np.random.default_rng(42)
        series = np.zeros(180)
        series[0] = rng.standard_normal()
        for idx in range(1, len(series)):
            series[idx] = 0.8 * series[idx - 1] + rng.standard_normal()

        result = run_triage(TriageRequest(series=series, max_lag=20, random_state=42))
        summary = _result_summary(result)

        assert summary["blocked"] is False
        assert "peak_raw" in summary
        assert "peak_partial" in summary
        assert "recommendation" in summary


class TestAgentWithTestModel:
    """Integration smoke tests using PydanticAI TestModel."""

    @pytest.mark.anyio
    async def test_agent_run_returns_structured_report(self) -> None:
        from pydantic_ai.models.test import TestModel

        from forecastability.adapters.llm.screening_agent import (
            FeatureScreeningReport,
            ScreeningDeps,
            create_screening_agent,
        )
        from forecastability.adapters.settings import InfraSettings

        settings = InfraSettings(_env_file=None)  # type: ignore[call-arg]
        agent = create_screening_agent(model="test", settings=settings)

        rng = np.random.default_rng(7)
        target = rng.standard_normal(220)
        deps = ScreeningDeps(
            target_name="cnt",
            target=target,
            candidates={
                "temp": rng.standard_normal(220),
                "hum": rng.standard_normal(220),
            },
            max_lag=20,
            n_surrogates=99,
            random_state=42,
        )

        with agent.override(model=TestModel()):
            result = await agent.run(
                "Assess target and screen each candidate feature. Return a ranked report.",
                deps=deps,
            )

        assert isinstance(result.output, FeatureScreeningReport)


def test_notebook_04_imports_shared_screening_adapter() -> None:
    """Notebook 04 should consume adapter code, not define runtime agent wiring."""

    notebook_path = Path("notebooks/walkthroughs/04_screening_end_to_end.ipynb")
    source = notebook_path.read_text(encoding="utf-8")

    assert "forecastability.adapters.llm.screening_agent" in source
    assert "pydantic_ai_available" in source
    assert "create_screening_agent(" in source
    assert "def create_screening_agent(" not in source
    assert "_SCREENING_PROMPT =" not in source
    assert "@agent.tool" not in source
    assert "class ScreeningDeps" not in source
    assert "class FeatureScreeningReport" not in source


def test_assemblers_placeholder_package_removed() -> None:
    """C14: empty placeholder package should remain removed."""

    assert not Path("src/forecastability/assemblers").exists()
