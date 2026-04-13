"""Live-LLM screening agent adapter for exogenous feature triage.

This module owns the runtime PydanticAI wiring used by the screening
walkthrough notebook. All deterministic statistics are computed via
``run_triage()`` and exposed to the LLM through tool calls.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from pydantic import BaseModel, ConfigDict

from forecastability.adapters.settings import InfraSettings
from forecastability.triage import AnalysisGoal, TriageRequest, TriageResult, run_triage

try:
    from pydantic_ai import Agent, RunContext

    _PYDANTIC_AI_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PYDANTIC_AI_AVAILABLE = False


@dataclass
class ScreeningDeps:
    """Runtime dependencies required by the screening agent.

    Attributes:
        target_name: Human-readable target series name.
        target: Target time-series values.
        candidates: Candidate exogenous features keyed by feature name.
        max_lag: Maximum lag to evaluate.
        n_surrogates: Surrogate count used in deterministic significance checks.
        random_state: Deterministic seed passed to triage execution.
    """

    target_name: str
    target: np.ndarray
    candidates: dict[str, np.ndarray]
    max_lag: int = 40
    n_surrogates: int = 99
    random_state: int = 42


class FeatureRanking(BaseModel):
    """Ranking entry for a single candidate feature."""

    model_config = ConfigDict(frozen=True)

    feature_name: str
    action: str
    peak_cross_ami: float
    peak_partial_cross_ami: float
    rationale: str


class FeatureScreeningReport(BaseModel):
    """Structured report returned by the screening agent."""

    model_config = ConfigDict(frozen=True)

    target_name: str
    target_forecastability: str
    target_regime: str
    rankings: list[FeatureRanking]
    overall_recommendation: str
    caveats: list[str]


_SCREENING_PROMPT = """\
You are a feature-screening assistant for time-series forecasting.

Your workflow:
1. Call `list_candidates` to see available features.
2. Call `assess_target` to evaluate the target's self-predictability.
3. Call `screen_feature` for EACH candidate — do not skip any.
4. Synthesise all results into a FeatureScreeningReport.

## Interpretation rules

- peak CrossAMI > 0.15 → strong cross-dependence → action = "include"
- peak CrossAMI 0.05–0.15 → moderate → action = "include_conditional"
- peak CrossAMI < 0.05 → weak → action = "drop"
- If pCrossAMI ≈ CrossAMI, the driver's influence is mostly direct.
- If pCrossAMI << CrossAMI, much is mediated through the target's own history.

## Rules

- Every number must come from a tool call. Never invent values.
- Rank features by peak CrossAMI descending.
- Include practical caveats (sample size, stationarity, confounders).
- Be concise in rationales: 1–2 sentences per feature, 3–5 overall.
"""


def pydantic_ai_available() -> bool:
    """Return whether ``pydantic-ai`` is importable in this runtime."""
    return _PYDANTIC_AI_AVAILABLE


def _result_summary(result: TriageResult) -> dict[str, object]:
    """Condense a ``TriageResult`` into scalar fields for LLM consumption."""
    out: dict[str, object] = {"blocked": result.blocked}

    if result.analyze_result is not None:
        out["peak_raw"] = round(float(result.analyze_result.raw.max()), 4)
        if result.analyze_result.partial is not None:
            out["peak_partial"] = round(float(result.analyze_result.partial.max()), 4)

    if result.interpretation is not None:
        out["forecastability"] = result.interpretation.forecastability_class
        out["directness"] = result.interpretation.directness_class
        out["regime"] = result.interpretation.modeling_regime
        out["narrative"] = result.interpretation.narrative

    out["recommendation"] = result.recommendation
    return out


def create_screening_agent(
    model: str | None = None,
    *,
    settings: InfraSettings | None = None,
) -> Agent[ScreeningDeps, FeatureScreeningReport]:
    """Create the live screening agent backed by deterministic triage tools.

    Args:
        model: Optional model identifier (for example ``"openai:gpt-4o"``).
            If omitted, uses ``openai:{settings.openai_model}``.
        settings: Optional infrastructure settings. If omitted, settings are
            loaded from environment defaults.

    Returns:
        Configured ``pydantic_ai.Agent`` for screening workflows.

    Raises:
        ImportError: If ``pydantic-ai`` is not installed.
    """
    if not _PYDANTIC_AI_AVAILABLE:
        raise ImportError(
            "pydantic-ai is required for the screening agent. Install with: uv sync --extra agent"
        )

    if settings is None:
        settings = InfraSettings()

    if model is None:
        model = f"openai:{settings.openai_model}"

    agent: Agent[ScreeningDeps, FeatureScreeningReport] = Agent(  # type: ignore[assignment]
        model,
        deps_type=ScreeningDeps,
        output_type=FeatureScreeningReport,
        system_prompt=_SCREENING_PROMPT,
    )

    @agent.tool
    def list_candidates(ctx: RunContext[ScreeningDeps]) -> dict[str, dict[str, int | float]]:
        """List candidate features with lightweight descriptive statistics."""
        return {
            name: {
                "n": len(arr),
                "mean": round(float(np.mean(arr)), 4),
                "std": round(float(np.std(arr)), 4),
            }
            for name, arr in ctx.deps.candidates.items()
        }

    @agent.tool
    def assess_target(ctx: RunContext[ScreeningDeps]) -> dict[str, object]:
        """Assess target self-predictability via univariate triage."""
        result = run_triage(
            TriageRequest(
                series=ctx.deps.target,
                goal=AnalysisGoal.univariate,
                max_lag=ctx.deps.max_lag,
                n_surrogates=ctx.deps.n_surrogates,
                random_state=ctx.deps.random_state,
            )
        )
        return _result_summary(result)

    @agent.tool
    def screen_feature(ctx: RunContext[ScreeningDeps], feature_name: str) -> dict[str, object]:
        """Assess one candidate feature for cross-predictive value."""
        if feature_name not in ctx.deps.candidates:
            return {
                "error": (
                    f"Unknown feature '{feature_name}'. "
                    f"Available: {list(ctx.deps.candidates.keys())}"
                )
            }

        result = run_triage(
            TriageRequest(
                series=ctx.deps.target,
                exog=ctx.deps.candidates[feature_name],
                goal=AnalysisGoal.exogenous,
                max_lag=ctx.deps.max_lag,
                n_surrogates=ctx.deps.n_surrogates,
                random_state=ctx.deps.random_state,
            )
        )
        return {"feature": feature_name, **_result_summary(result)}

    return agent


__all__ = [
    "FeatureRanking",
    "FeatureScreeningReport",
    "ScreeningDeps",
    "create_screening_agent",
    "pydantic_ai_available",
]
