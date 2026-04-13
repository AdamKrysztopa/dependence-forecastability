"""PydanticAI adapter wrapping the deterministic triage pipeline (AGT-008a).

This adapter exposes ``run_triage()`` and its sub-steps as PydanticAI tools,
letting an LLM orchestrate and *explain* the deterministic results — without
ever generating numeric values itself.

All scientific computation is delegated to existing library functions; the
agent only selects the execution path and narrates the outcome.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict

from forecastability.adapters.settings import InfraSettings
from forecastability.triage.models import (
    AnalysisGoal,
    MethodPlan,
    ReadinessReport,
    ReadinessStatus,
    TriageRequest,
    TriageResult,
)
from forecastability.triage.readiness import assess_readiness
from forecastability.triage.router import plan_method
from forecastability.triage.run_triage import run_triage

try:
    from pydantic_ai import Agent, RunContext

    _PYDANTIC_AI_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PYDANTIC_AI_AVAILABLE = False


# ---------------------------------------------------------------------------
# Dependency container
# ---------------------------------------------------------------------------


@dataclass
class TriageDeps:
    """Runtime dependencies injected into the PydanticAI agent.

    Attributes:
        settings: Infrastructure settings (API keys, model names).
        series: Target time-series array.
        exog: Optional exogenous series.
        goal: Analysis goal.
        max_lag: Maximum lag to evaluate.
        n_surrogates: Number of surrogates for significance estimation.
        random_state: Seed for deterministic execution.
    """

    settings: InfraSettings
    series: np.ndarray
    exog: np.ndarray | None = None
    goal: AnalysisGoal = AnalysisGoal.univariate
    max_lag: int = 40
    n_surrogates: int = 99
    random_state: int = 42


# ---------------------------------------------------------------------------
# Structured output
# ---------------------------------------------------------------------------


class TriageExplanation(BaseModel):
    """Structured output returned by the triage agent.

    Attributes:
        forecastability_class: ``"high"``, ``"medium"``, or ``"low"``.
        directness_class: ``"high"``, ``"medium"``, ``"low"``, or ``"arch_suspected"``.
        modeling_regime: Recommended modeling strategy identifier.
        primary_lags: Most important lags for forecasting.
        recommendation: Deterministic triage recommendation string.
        narrative: LLM-generated explanation of the results.
        caveats: List of caveats and limitations the user should know about.
    """

    model_config = ConfigDict(frozen=True)

    forecastability_class: str
    directness_class: str
    modeling_regime: str
    primary_lags: list[int]
    recommendation: str
    narrative: str
    caveats: list[str]


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a forecastability triage assistant for time-series analysis.

Your job is to run deterministic analysis tools and then explain the results
in plain language. You must NEVER invent or hallucinate numeric values. All
numbers must come from tool outputs.

## Workflow

1. Call ``validate_series`` to check if the series is ready for analysis.
2. If validation passes, call ``plan_analysis`` to select the compute path.
3. Call ``run_full_triage`` to execute the complete pipeline.
4. Use the deterministic results to produce a clear, structured explanation.

## Interpretation patterns

- **Pattern A** (high forecastability, high directness): Rich structured models
  justified — deep AR, nonlinear, LSTM.
- **Pattern B** (high forecastability, low directness): Compact lag or
  state-space/seasonal designs preferred — much long-lag structure is mediated.
- **Pattern C** (medium forecastability): Seasonal models or regularised AR; if
  a seasonal peak exists in pAMI, seasonal decomposition is preferred.
- **Pattern D** (low forecastability, low directness): Near noise floor —
  baseline methods (mean, drift, naive) are likely sufficient.
- **Pattern D′** (low forecastability, high directness at short lags): Compact
  AR(1)–AR(3) may capture the residual structure.
- **Pattern E** (exploitability mismatch): High dependence but high error
  indicates nonstationarity, model-class limitations, or insufficient sample.

## Rules

- Every number you cite must come from a tool call. Do not compute or guess.
- Include relevant caveats from the readiness report and interpretation.
- If the series is blocked, explain why and suggest remediation.
- Be concise — aim for 3-5 sentences of narrative.
"""


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------


def _build_request(deps: TriageDeps) -> TriageRequest:
    """Construct a ``TriageRequest`` from the dependency container."""
    return TriageRequest(
        series=deps.series,
        exog=deps.exog,
        goal=deps.goal,
        max_lag=deps.max_lag,
        n_surrogates=deps.n_surrogates,
        random_state=deps.random_state,
    )


def _readiness_to_dict(report: ReadinessReport) -> dict[str, Any]:
    """Serialise a ReadinessReport to a plain dict for the LLM."""
    return {
        "status": report.status.value,
        "warnings": [{"code": w.code, "message": w.message} for w in report.warnings],
    }


def _method_plan_to_dict(plan: MethodPlan) -> dict[str, Any]:
    """Serialise a MethodPlan to a plain dict for the LLM."""
    return {
        "route": plan.route,
        "compute_surrogates": plan.compute_surrogates,
        "assumptions": plan.assumptions,
        "rationale": plan.rationale,
    }


def _triage_result_to_dict(result: TriageResult) -> dict[str, Any]:
    """Serialise a TriageResult to a plain dict for the LLM.

    Avoids passing large numpy arrays; instead provides summary statistics.
    """
    out: dict[str, Any] = {
        "blocked": result.blocked,
        "readiness": _readiness_to_dict(result.readiness),
    }

    if result.method_plan is not None:
        out["method_plan"] = _method_plan_to_dict(result.method_plan)

    if result.analyze_result is not None:
        ar = result.analyze_result
        out["analyze_summary"] = {
            "method": ar.method,
            "recommendation": ar.recommendation,
            "raw_curve_mean": float(np.mean(ar.raw[:20]) if ar.raw.size >= 20 else np.mean(ar.raw)),
            "partial_curve_mean": float(
                np.mean(ar.partial[:20]) if ar.partial.size >= 20 else np.mean(ar.partial)
            ),
            "n_sig_raw_lags": (int(ar.sig_raw_lags.size) if ar.sig_raw_lags is not None else 0),
            "n_sig_partial_lags": (
                int(ar.sig_partial_lags.size) if ar.sig_partial_lags is not None else 0
            ),
            "raw_curve_max": float(np.max(ar.raw)),
            "partial_curve_max": float(np.max(ar.partial)),
        }

    if result.interpretation is not None:
        interp = result.interpretation
        out["interpretation"] = {
            "forecastability_class": interp.forecastability_class,
            "directness_class": interp.directness_class,
            "primary_lags": interp.primary_lags,
            "modeling_regime": interp.modeling_regime,
            "narrative": interp.narrative,
            "diagnostics": {
                "peak_ami_first_5": interp.diagnostics.peak_ami_first_5,
                "directness_ratio": interp.diagnostics.directness_ratio,
                "n_sig_ami": interp.diagnostics.n_sig_ami,
                "n_sig_pami": interp.diagnostics.n_sig_pami,
            },
        }

    if result.recommendation is not None:
        out["recommendation"] = result.recommendation

    return out


def create_triage_agent(
    *,
    model: str | None = None,
    settings: InfraSettings | None = None,
) -> Agent[TriageDeps, TriageExplanation]:
    """Create a PydanticAI triage agent backed by deterministic tools.

    Args:
        model: Model identifier string (e.g. ``"openai:gpt-4o"``,
            ``"anthropic:claude-sonnet-4-5"``).  When ``None``, reads from
            *settings* defaulting to ``openai:{settings.openai_model}``.
        settings: Infrastructure settings.  When ``None``, loads from ``.env``.

    Returns:
        Configured :class:`pydantic_ai.Agent` instance.

    Raises:
        ImportError: When ``pydantic-ai`` is not installed.
    """
    if not _PYDANTIC_AI_AVAILABLE:
        raise ImportError(
            "pydantic-ai is required for the agent adapter. Install with: uv sync --extra agent"
        )

    if settings is None:
        settings = InfraSettings()

    if model is None:
        model = f"openai:{settings.openai_model}"

    agent: Agent[TriageDeps, TriageExplanation] = Agent(  # type: ignore[assignment]
        model,
        deps_type=TriageDeps,
        output_type=TriageExplanation,
        system_prompt=_SYSTEM_PROMPT,
    )

    # ------------------------------------------------------------------
    # Tool: validate_series
    # ------------------------------------------------------------------

    @agent.tool
    def validate_series(ctx: RunContext[TriageDeps]) -> dict[str, Any]:
        """Validate the time series and assess readiness for analysis.

        Returns a readiness report with status and any warnings.
        """
        request = _build_request(ctx.deps)
        report = assess_readiness(request)
        return _readiness_to_dict(report)

    # ------------------------------------------------------------------
    # Tool: plan_analysis
    # ------------------------------------------------------------------

    @agent.tool
    def plan_analysis(ctx: RunContext[TriageDeps]) -> dict[str, Any]:
        """Select the compute path for the analysis.

        Returns the method plan including route, assumptions, and rationale.
        Requires that validation has passed (not blocked).
        """
        request = _build_request(ctx.deps)
        readiness = assess_readiness(request)
        if readiness.status == ReadinessStatus.blocked:
            return {
                "error": "Series is blocked by readiness gate",
                "readiness": _readiness_to_dict(readiness),
            }
        plan = plan_method(request, readiness)
        return _method_plan_to_dict(plan)

    # ------------------------------------------------------------------
    # Tool: run_full_triage
    # ------------------------------------------------------------------

    @agent.tool
    def run_full_triage(ctx: RunContext[TriageDeps]) -> dict[str, Any]:
        """Run the complete triage pipeline: validate → route → compute → interpret.

        Returns a structured summary of all results including forecastability
        class, directness, primary lags, modeling regime, and recommendation.
        """
        from forecastability.adapters.event_emitter import LoggingEventEmitter

        request = _build_request(ctx.deps)
        result = run_triage(request, event_emitter=LoggingEventEmitter())
        out = _triage_result_to_dict(result)
        if result.timing:
            out["timing_ms"] = result.timing
        return out

    # ------------------------------------------------------------------
    # Tool: list_available_scorers
    # ------------------------------------------------------------------

    @agent.tool
    def list_available_scorers(ctx: RunContext[TriageDeps]) -> list[dict[str, str]]:
        """List all registered dependence scorers.

        Returns scorer names, families, and descriptions.
        """
        from forecastability.scorers import default_registry

        registry = default_registry()
        return [
            {
                "name": info.name,
                "family": info.family,
                "description": info.description,
            }
            for info in registry.list_scorers()
        ]

    return agent


# ---------------------------------------------------------------------------
# Convenience runner
# ---------------------------------------------------------------------------


async def run_triage_agent(
    series: np.ndarray,
    *,
    prompt: str = "Analyze this time series and explain the forecastability results.",
    exog: np.ndarray | None = None,
    goal: AnalysisGoal = AnalysisGoal.univariate,
    max_lag: int = 40,
    n_surrogates: int = 99,
    random_state: int = 42,
    model: str | None = None,
    settings: InfraSettings | None = None,
) -> TriageExplanation:
    """Run the triage agent and return a structured explanation.

    This is the primary public entry point for agent-assisted triage. It
    creates the agent, injects the series as a dependency, runs the LLM
    orchestration loop, and returns the structured explanation.

    Args:
        series: Target time-series array.
        prompt: User prompt for the agent.
        exog: Optional exogenous series.
        goal: Analysis goal.
        max_lag: Maximum lag to evaluate.
        n_surrogates: Number of surrogates for significance estimation.
        random_state: Seed for deterministic execution.
        model: Model identifier string.  ``None`` → reads from settings.
        settings: Infrastructure settings.  ``None`` → loads from ``.env``.

    Returns:
        :class:`TriageExplanation` with deterministic results and LLM narrative.
    """
    if settings is None:
        settings = InfraSettings()

    agent = create_triage_agent(model=model, settings=settings)

    deps = TriageDeps(
        settings=settings,
        series=series,
        exog=exog,
        goal=goal,
        max_lag=max_lag,
        n_surrogates=n_surrogates,
        random_state=random_state,
    )

    result = await agent.run(prompt, deps=deps)
    return result.output
