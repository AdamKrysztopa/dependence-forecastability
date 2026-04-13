"""Tests for the PydanticAI triage agent adapter (AGT-008a, AGT-008b)."""

from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError
from pydantic_ai import models

# Block real model requests during tests — any accidental real call will fail.
models.ALLOW_MODEL_REQUESTS = False  # type: ignore[assignment]


class TestCreateTriageAgent:
    """Verify agent construction and tool registration."""

    def test_agent_creation_succeeds(self) -> None:
        from forecastability.adapters.pydantic_ai_agent import (
            InfraSettings,
            create_triage_agent,
        )

        settings = InfraSettings(_env_file=None)  # type: ignore[call-arg]
        agent = create_triage_agent(model="test", settings=settings)
        assert agent is not None

    def test_agent_has_expected_tools(self) -> None:
        from forecastability.adapters.pydantic_ai_agent import (
            InfraSettings,
            create_triage_agent,
        )

        settings = InfraSettings(_env_file=None)  # type: ignore[call-arg]
        agent = create_triage_agent(model="test", settings=settings)
        tool_names = set(agent._function_toolset.tools)
        expected = {
            "validate_series",
            "plan_analysis",
            "run_full_triage",
            "list_available_scorers",
        }
        assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"


class TestTriageExplanationModel:
    """Verify the structured output model."""

    def test_model_validates(self) -> None:
        from forecastability.adapters.pydantic_ai_agent import TriageExplanation

        explanation = TriageExplanation(
            forecastability_class="high",
            directness_class="high",
            modeling_regime="rich_models_with_structured_memory",
            primary_lags=[1, 2, 3],
            recommendation="HIGH -> Complex global models",
            narrative="Strong total dependence remains direct after conditioning.",
            caveats=["Series length is below 200."],
        )
        assert explanation.forecastability_class == "high"
        assert len(explanation.caveats) == 1

    def test_model_is_frozen(self) -> None:
        from forecastability.adapters.pydantic_ai_agent import TriageExplanation

        explanation = TriageExplanation(
            forecastability_class="low",
            directness_class="low",
            modeling_regime="baseline_or_robust_decision_design",
            primary_lags=[],
            recommendation="LOW -> Naive or seasonal naive only",
            narrative="Both total and direct dependence are weak.",
            caveats=[],
        )
        with pytest.raises(ValidationError):
            explanation.forecastability_class = "high"  # type: ignore[misc]


class TestToolSerialisation:
    """Verify that tool helpers serialise results correctly."""

    def test_readiness_to_dict(self) -> None:
        from forecastability.adapters.pydantic_ai_agent import _readiness_to_dict
        from forecastability.triage.models import (
            ReadinessReport,
            ReadinessStatus,
            ReadinessWarning,
        )

        report = ReadinessReport(
            status=ReadinessStatus.warning,
            warnings=[ReadinessWarning(code="SIGNIFICANCE_FEASIBILITY", message="Short series")],
        )
        d = _readiness_to_dict(report)
        assert d["status"] == "warning"
        assert len(d["warnings"]) == 1
        assert d["warnings"][0]["code"] == "SIGNIFICANCE_FEASIBILITY"

    def test_method_plan_to_dict(self) -> None:
        from forecastability.adapters.pydantic_ai_agent import _method_plan_to_dict
        from forecastability.triage.models import MethodPlan

        plan = MethodPlan(
            route="univariate_with_significance",
            compute_surrogates=True,
            assumptions=["Long enough"],
            rationale="Standard path",
        )
        d = _method_plan_to_dict(plan)
        assert d["route"] == "univariate_with_significance"
        assert d["compute_surrogates"] is True

    def test_triage_result_to_dict_blocked(self) -> None:
        from forecastability.adapters.pydantic_ai_agent import _triage_result_to_dict
        from forecastability.triage.models import (
            ReadinessReport,
            ReadinessStatus,
            TriageRequest,
            TriageResult,
        )

        rng = np.random.default_rng(0)
        req = TriageRequest(series=rng.standard_normal(30), max_lag=40)
        result = TriageResult(
            request=req,
            readiness=ReadinessReport(status=ReadinessStatus.blocked, warnings=[]),
            blocked=True,
        )
        d = _triage_result_to_dict(result)
        assert d["blocked"] is True
        assert "analyze_summary" not in d

    def test_triage_result_to_dict_complete(self) -> None:
        from forecastability.adapters.pydantic_ai_agent import _triage_result_to_dict
        from forecastability.triage.models import TriageRequest
        from forecastability.triage.run_triage import run_triage

        rng = np.random.default_rng(42)
        n = 150
        ts = np.zeros(n)
        ts[0] = rng.standard_normal()
        for i in range(1, n):
            ts[i] = 0.85 * ts[i - 1] + rng.standard_normal()

        req = TriageRequest(series=ts, max_lag=20, random_state=42)
        result = run_triage(req)
        d = _triage_result_to_dict(result)

        assert d["blocked"] is False
        assert "analyze_summary" in d
        assert "interpretation" in d
        assert d["interpretation"]["forecastability_class"] == "high"


class TestAgentWithTestModel:
    """Integration tests using PydanticAI TestModel (mocked LLM)."""

    @pytest.mark.anyio
    async def test_agent_dispatches_tools_with_test_model(self) -> None:
        from pydantic_ai.models.test import TestModel

        from forecastability.adapters.pydantic_ai_agent import (
            AnalysisGoal,
            InfraSettings,
            TriageDeps,
            TriageExplanation,
            create_triage_agent,
        )

        settings = InfraSettings(_env_file=None)  # type: ignore[call-arg]
        agent = create_triage_agent(model="test", settings=settings)

        rng = np.random.default_rng(42)
        n = 150
        ts = np.zeros(n)
        ts[0] = rng.standard_normal()
        for i in range(1, n):
            ts[i] = 0.85 * ts[i - 1] + rng.standard_normal()

        deps = TriageDeps(
            settings=settings,
            series=ts,
            goal=AnalysisGoal.univariate,
            max_lag=20,
            random_state=42,
        )

        m = TestModel()
        with agent.override(model=m):
            result = await agent.run(
                "Analyze this time series and explain the results.",
                deps=deps,
            )

        assert isinstance(result.output, TriageExplanation)

    @pytest.mark.anyio
    async def test_agent_tools_are_callable(self) -> None:
        """Verify that each tool can be called directly without LLM."""

        from forecastability.adapters.pydantic_ai_agent import (
            InfraSettings,
            TriageDeps,
            _build_request,
            _readiness_to_dict,
            _triage_result_to_dict,
        )
        from forecastability.triage.readiness import assess_readiness
        from forecastability.triage.run_triage import run_triage

        settings = InfraSettings(_env_file=None)  # type: ignore[call-arg]
        rng = np.random.default_rng(42)
        ts = rng.standard_normal(200)

        deps = TriageDeps(settings=settings, series=ts, max_lag=20, random_state=42)
        request = _build_request(deps)

        # validate_series
        readiness = assess_readiness(request)
        rd = _readiness_to_dict(readiness)
        assert "status" in rd

        # run_full_triage
        result = run_triage(request)
        td = _triage_result_to_dict(result)
        assert "blocked" in td


class TestTriageResultNarrativeField:
    """AGT-008b: narrative field on TriageResult."""

    def test_narrative_default_is_none(self) -> None:
        from forecastability.triage.models import (
            ReadinessReport,
            ReadinessStatus,
            TriageRequest,
            TriageResult,
        )

        rng = np.random.default_rng(0)
        req = TriageRequest(series=rng.standard_normal(30), max_lag=40)
        result = TriageResult(
            request=req,
            readiness=ReadinessReport(status=ReadinessStatus.blocked, warnings=[]),
            blocked=True,
        )
        assert result.narrative is None

    def test_narrative_can_be_set(self) -> None:
        from forecastability.triage.models import (
            ReadinessReport,
            ReadinessStatus,
            TriageRequest,
            TriageResult,
        )

        rng = np.random.default_rng(0)
        req = TriageRequest(series=rng.standard_normal(200), max_lag=20)
        result = TriageResult(
            request=req,
            readiness=ReadinessReport(status=ReadinessStatus.clear, warnings=[]),
            blocked=False,
            narrative="Strong dependence with direct memory structure.",
        )
        assert result.narrative == "Strong dependence with direct memory structure."

    def test_existing_run_triage_returns_none_narrative(self) -> None:
        """Deterministic run_triage returns None narrative (no LLM)."""
        from forecastability.triage.models import TriageRequest
        from forecastability.triage.run_triage import run_triage

        rng = np.random.default_rng(42)
        ts = rng.standard_normal(150)
        req = TriageRequest(series=ts, max_lag=20, random_state=42)
        result = run_triage(req)
        assert result.narrative is None


class TestBoundaryEnforcement:
    """Verify that pydantic_ai imports are confined to adapters/."""

    def test_triage_modules_do_not_import_pydantic_ai(self) -> None:
        import ast
        from pathlib import Path

        triage_dir = Path(__file__).parent.parent / "src" / "forecastability" / "triage"
        for py_file in sorted(triage_dir.glob("*.py")):
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not alias.name.startswith("pydantic_ai"), (
                            f"{py_file.name} imports pydantic_ai"
                        )
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        assert not node.module.startswith("pydantic_ai"), (
                            f"{py_file.name} imports from pydantic_ai"
                        )

    def test_domain_modules_do_not_import_pydantic_ai(self) -> None:
        import ast
        from pathlib import Path

        root = Path(__file__).parent.parent
        domain_files = [
            "src/forecastability/metrics.py",
            "src/forecastability/validation.py",
            "src/forecastability/interpretation.py",
            "src/forecastability/types.py",
            "src/forecastability/scorers.py",
        ]
        for rel in domain_files:
            path = root / rel
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not alias.name.startswith("pydantic_ai"), (
                            f"{rel} imports pydantic_ai"
                        )
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        assert not node.module.startswith("pydantic_ai"), (
                            f"{rel} imports from pydantic_ai"
                        )


class TestAGT027AgentQuickstart:
    """AGT-027: Smoke tests for the canonical agent entry point documented in README."""

    def test_create_triage_agent_returns_agent_instance(self) -> None:
        """create_triage_agent() is importable and returns an Agent instance."""
        from pydantic_ai import Agent

        from forecastability.adapters.pydantic_ai_agent import (
            InfraSettings,
            create_triage_agent,
        )

        settings = InfraSettings(_env_file=None)  # type: ignore[call-arg]
        agent = create_triage_agent(model="test", settings=settings)
        assert isinstance(agent, Agent)

    def test_agent_tool_count_matches_readme(self) -> None:
        """All four tools described in README are registered on the agent."""
        from forecastability.adapters.pydantic_ai_agent import (
            InfraSettings,
            create_triage_agent,
        )

        settings = InfraSettings(_env_file=None)  # type: ignore[call-arg]
        agent = create_triage_agent(model="test", settings=settings)
        tool_names = set(agent._function_toolset.tools)
        # These four tools are described in the README agent quickstart.
        expected_tools = (
            "validate_series",
            "plan_analysis",
            "run_full_triage",
            "list_available_scorers",
        )
        for expected in expected_tools:
            assert expected in tool_names, f"Tool '{expected}' missing from agent"

    def test_agent_result_is_deterministic_tool_output(self) -> None:
        """TriageExplanation narrative is set by LLM; run_triage always returns None."""
        # The docstring above was shortened to satisfy the line-length limit.
        from forecastability.triage.models import TriageRequest
        from forecastability.triage.run_triage import run_triage

        # Deterministic path — no agent involved
        rng = np.random.default_rng(42)
        ts = np.array([0.85**i + rng.standard_normal() * 0.1 for i in range(200)])
        req = TriageRequest(series=ts, max_lag=20, random_state=42)
        result = run_triage(req)
        # Narrative ownership: deterministic run_triage never sets narrative
        assert result.narrative is None
