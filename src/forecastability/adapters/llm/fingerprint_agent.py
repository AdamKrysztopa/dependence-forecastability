"""Optional live-LLM adapter for forecastability fingerprint narration (V3_1-F05.2).

This adapter is the fingerprint counterpart of
:mod:`forecastability.adapters.llm.triage_agent`.  It wraps the deterministic
:class:`FingerprintBundle` behind a PydanticAI agent so that a language model
can *narrate* the fingerprint and routing findings without introducing numeric
values, inventing model recommendations, or overriding deterministic outputs.

When ``pydantic_ai`` is not installed, when no API key is configured, or when
``strict=True`` is passed to :func:`run_fingerprint_agent`, the adapter falls
back to a deterministic explanation built from the A3 interpretation adapter,
with ``narrative`` set to ``None``.

Ownership rules (SOLID / hexagonal):
* This module owns live-agent prompt / tool orchestration and strict fallback only.
* All scientific computation stays in ``use_cases/run_forecastability_fingerprint.py``
  and the domain services it composes.
* No AMI formulas, routing thresholds, or fingerprint recomputation belong here.
* The live path calls the use case or reads the A1/A2 payload; it does NOT recompute.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict

from forecastability.adapters.agents.fingerprint_agent_interpretation_adapter import (
    FingerprintAgentInterpretation,
    interpret_fingerprint_payload,
)
from forecastability.adapters.agents.fingerprint_agent_payload_models import (
    fingerprint_agent_payload,
)
from forecastability.adapters.settings import InfraSettings
from forecastability.use_cases.run_forecastability_fingerprint import (
    run_forecastability_fingerprint,
)
from forecastability.utils.types import FingerprintBundle, RoutingConfidenceLabel

try:
    from pydantic_ai import Agent, RunContext

    _PYDANTIC_AI_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised via monkeypatch
    _PYDANTIC_AI_AVAILABLE = False


_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public availability flag
# ---------------------------------------------------------------------------

pydantic_ai_available: bool = _PYDANTIC_AI_AVAILABLE
"""``True`` when ``pydantic-ai`` is installed; ``False`` otherwise."""


# ---------------------------------------------------------------------------
# Dependency container
# ---------------------------------------------------------------------------


@dataclass
class FingerprintDeps:
    """Runtime dependencies injected into the fingerprint PydanticAI agent.

    Attributes:
        settings: Infrastructure settings (API keys, model identifiers).
        series: Target time-series array.
        target_name: Human-readable label for the series.
        max_lag: Maximum horizon H to analyse.
        n_surrogates: Number of surrogates for significance estimation.
        random_state: Seed for deterministic execution.
        ami_floor: Legacy compatibility argument retained for older callers.
    """

    settings: InfraSettings
    series: np.ndarray
    target_name: str = "series"
    max_lag: int = 24
    n_surrogates: int = 99
    random_state: int = 42
    ami_floor: float = 0.01
    # Internal cache — populated by the ``run_fingerprint`` tool on first call.
    _bundle: FingerprintBundle | None = field(default=None, repr=False)


# ---------------------------------------------------------------------------
# Structured output
# ---------------------------------------------------------------------------


class FingerprintExplanation(BaseModel):
    """Structured output returned by the live fingerprint agent.

    Attributes:
        target_name: Series label propagated from the deterministic bundle.
        geometry_method: Deterministic geometry engine identifier.
        signal_to_noise: Geometry signal-quality statistic.
        geometry_information_horizon: Geometry-derived latest informative horizon.
        geometry_information_structure: Geometry-derived structure label.
        information_mass: Normalised masked AMI area over informative horizons.
        information_horizon: Latest informative horizon index (0 when none).
        information_structure: Shape label for the AMI profile.
        nonlinear_share: Fraction of AMI in excess of the linear baseline.
        primary_families: Primary model-family routing recommendations.
        confidence_label: Deterministic routing confidence.
        narrative: LLM-generated narration grounded in deterministic results.
        caveats: Caution flags and rationale propagated from the deterministic layer.
    """

    model_config = ConfigDict(frozen=True)

    target_name: str
    geometry_method: str
    signal_to_noise: float
    geometry_information_horizon: int
    geometry_information_structure: str
    information_mass: float
    information_horizon: int
    information_structure: str
    nonlinear_share: float
    primary_families: list[str]
    confidence_label: RoutingConfidenceLabel
    narrative: str
    caveats: list[str]


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a forecastability fingerprint assistant for time-series analysis.

Your job is to run the deterministic fingerprint computation via tools and then
explain the results in clear, precise language.  You MUST NEVER invent or
hallucinate numeric values. Every number you cite must come from a tool output.

## Workflow

1. Call ``run_fingerprint`` to compute the forecastability fingerprint.
2. Call ``get_interpretation`` to retrieve the deterministic interpretation.
3. Produce a structured explanation grounded only in the tool outputs.

## Fingerprint metric semantics

- **signal_to_noise**: Share of corrected AMI that sits above the surrogate
  threshold profile. Low → weak margin above surrogate noise; high → clearer
  usable signal.
- **information_mass**: Normalised area under the informative AMI profile.
  Low → weak forecastability; high → rich predictive information.
- **information_horizon**: Latest horizon where AMI remains informative (0 = none).
  Short → information decays quickly; long → information persists farther.
- **information_structure**: Shape of the AMI profile.
  ``none`` → no signal; ``monotonic`` → decaying; ``periodic`` → repeating peaks;
  ``mixed`` → complex combination.
- **nonlinear_share**: Fraction of AMI in excess of a Gaussian-information linear
  baseline. Low → mostly linear; high → substantial nonlinear structure.
  NOTE: nonlinear_share is NOT related to directness_ratio.

## Routing semantics

Primary model families are heuristic product guidance — NOT a ranking guarantee
or a performance promise. Always include the routing confidence level and any
caution flags in your explanation.

## Rules

- Cite only numeric values that appear in tool outputs.
- Do NOT invent model names, metric values, or caution flags.
- Do NOT override primary_families, confidence_label, or information_structure.
- Mention caution flags whenever confidence is medium or low.
- Be concise: aim for 4-6 sentences of narrative.
"""


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------


def create_fingerprint_agent(
    *,
    model: str | None = None,
    settings: InfraSettings | None = None,
) -> Agent[FingerprintDeps, FingerprintExplanation]:
    """Create a PydanticAI forecastability fingerprint agent.

    The agent uses two tools:

    * ``run_fingerprint`` — calls :func:`run_forecastability_fingerprint` and
      caches the bundle in :attr:`FingerprintDeps._bundle`.
    * ``get_interpretation`` — retrieves the deterministic A3 interpretation from
      the cached bundle.

    Args:
        model: PydanticAI model identifier, e.g. ``"openai:gpt-4o"`` or
            ``"anthropic:claude-sonnet-4-5"``.  Defaults to
            ``openai:<settings.openai_model>`` when ``None``.
        settings: Infrastructure settings; loaded from environment when ``None``.

    Returns:
        Configured :class:`pydantic_ai.Agent` instance.

    Raises:
        ImportError: When ``pydantic-ai`` is not installed.
    """
    if not _PYDANTIC_AI_AVAILABLE:
        raise ImportError(
            "pydantic-ai is required for the live fingerprint adapter. "
            "Install with: uv sync --extra agent"
        )

    if settings is None:
        settings = InfraSettings()

    if model is None:
        model = f"openai:{settings.openai_model}"

    agent: Agent[FingerprintDeps, FingerprintExplanation] = Agent(  # type: ignore[assignment]
        model,
        deps_type=FingerprintDeps,
        output_type=FingerprintExplanation,
        system_prompt=_SYSTEM_PROMPT,
    )

    # ------------------------------------------------------------------
    # Tool: run_fingerprint
    # ------------------------------------------------------------------

    @agent.tool
    def run_fingerprint(ctx: RunContext[FingerprintDeps]) -> dict[str, Any]:
        """Compute the forecastability fingerprint for the target series.

        Returns a dict with geometry, fingerprint, and routing fields,
        including information_mass, information_horizon,
        information_structure, nonlinear_share, directness_ratio,
        informative_horizons, primary_families, secondary_families,
        confidence_label, caution_flags, and rationale.
        """
        deps = ctx.deps
        bundle = run_forecastability_fingerprint(
            deps.series,
            target_name=deps.target_name,
            max_lag=deps.max_lag,
            n_surrogates=deps.n_surrogates,
            random_state=deps.random_state,
            ami_floor=deps.ami_floor,
        )
        # Cache the bundle for subsequent tool calls.
        object.__setattr__(deps, "_bundle", bundle)
        geometry = bundle.geometry
        fp = bundle.fingerprint
        rec = bundle.recommendation
        return {
            "target_name": bundle.target_name,
            "geometry_method": geometry.method,
            "signal_to_noise": geometry.signal_to_noise,
            "geometry_information_horizon": geometry.information_horizon,
            "geometry_information_structure": geometry.information_structure,
            "information_mass": fp.information_mass,
            "information_horizon": fp.information_horizon,
            "information_structure": fp.information_structure,
            "nonlinear_share": fp.nonlinear_share,
            "directness_ratio": fp.directness_ratio,
            "informative_horizons": fp.informative_horizons,
            "primary_families": list(rec.primary_families),
            "secondary_families": list(rec.secondary_families),
            "confidence_label": rec.confidence_label,
            "caution_flags": list(rec.caution_flags),
            "rationale": list(rec.rationale),
            "profile_summary": bundle.profile_summary,
        }

    # ------------------------------------------------------------------
    # Tool: get_interpretation
    # ------------------------------------------------------------------

    @agent.tool
    def get_interpretation(ctx: RunContext[FingerprintDeps]) -> dict[str, Any]:
        """Retrieve the deterministic A3 interpretation for the cached fingerprint.

        Returns a dict with structure_bucket, confidence_label, deterministic_summary,
        rich_signal_narrative, cautionary_narrative, and evidence.
        Requires that ``run_fingerprint`` has been called first.
        """
        deps = ctx.deps
        if deps._bundle is None:
            return {"error": "Fingerprint not yet computed. Call run_fingerprint first."}
        payload = fingerprint_agent_payload(deps._bundle, narrative=None)
        interpretation: FingerprintAgentInterpretation = interpret_fingerprint_payload(payload)
        return {
            "structure_bucket": interpretation.structure_bucket,
            "confidence_label": interpretation.confidence_label,
            "deterministic_summary": interpretation.deterministic_summary,
            "rich_signal_narrative": interpretation.rich_signal_narrative,
            "cautionary_narrative": interpretation.cautionary_narrative,
            "caution_flags": interpretation.caution_flags,
            "rationale": interpretation.rationale,
            "evidence": interpretation.evidence.model_dump(),
        }

    return agent


# ---------------------------------------------------------------------------
# Strict deterministic fallback
# ---------------------------------------------------------------------------


def _strict_explanation(bundle: FingerprintBundle) -> FingerprintExplanation:
    """Build a strict :class:`FingerprintExplanation` without any LLM narration.

    Args:
        bundle: Deterministic :class:`FingerprintBundle`.

    Returns:
        :class:`FingerprintExplanation` with ``narrative`` derived deterministically.
    """
    payload = fingerprint_agent_payload(bundle, narrative=None)
    interpretation = interpret_fingerprint_payload(payload)

    # Build narrative from deterministic fragments.
    fragments: list[str] = []
    if interpretation.rich_signal_narrative:
        fragments.append(interpretation.rich_signal_narrative)
    if interpretation.cautionary_narrative:
        fragments.append(interpretation.cautionary_narrative)
    if not fragments:
        fragments.append(interpretation.deterministic_summary)

    narrative = " ".join(fragments)
    caveats = list(payload.caution_flags) + list(payload.rationale)

    fp = bundle.fingerprint
    geometry = bundle.geometry
    rec = bundle.recommendation
    return FingerprintExplanation(
        target_name=bundle.target_name,
        geometry_method=str(geometry.method),
        signal_to_noise=geometry.signal_to_noise,
        geometry_information_horizon=geometry.information_horizon,
        geometry_information_structure=str(geometry.information_structure),
        information_mass=fp.information_mass,
        information_horizon=fp.information_horizon,
        information_structure=str(fp.information_structure),
        nonlinear_share=fp.nonlinear_share,
        primary_families=[str(f) for f in rec.primary_families],
        confidence_label=rec.confidence_label,
        narrative=narrative,
        caveats=caveats,
    )


# ---------------------------------------------------------------------------
# Convenience runner
# ---------------------------------------------------------------------------


async def run_fingerprint_agent(
    series: np.ndarray,
    *,
    target_name: str = "series",
    max_lag: int = 24,
    n_surrogates: int = 99,
    random_state: int = 42,
    ami_floor: float = 0.01,
    strict: bool = False,
    model: str | None = None,
    settings: InfraSettings | None = None,
    prompt: str = "Analyze this time series and explain the forecastability fingerprint.",
) -> FingerprintExplanation:
    """Run the forecastability fingerprint agent and return a structured explanation.

    When ``strict=True`` or when ``pydantic-ai`` is unavailable, the function
    returns a deterministic explanation without any LLM narration.

    Args:
        series: Target time-series array.
        target_name: Human-readable label for the series.
        max_lag: Maximum horizon H to analyse.
        n_surrogates: Number of surrogates for significance estimation.
        random_state: Seed for deterministic execution.
        ami_floor: Legacy compatibility argument retained for older callers.
            The geometry-backed v0.3.1 path ignores it semantically.
        strict: When ``True``, skip the live agent and return the deterministic
            fallback only.
        model: PydanticAI model identifier.  Defaults to ``openai:<settings.openai_model>``.
        settings: Infrastructure settings; loaded from environment when ``None``.
        prompt: User prompt passed to the agent.

    Returns:
        :class:`FingerprintExplanation` with either a live narrative or a
        deterministic fallback narrative.
    """
    if settings is None:
        settings = InfraSettings()

    # Compute the deterministic bundle first — required for strict mode and as
    # the basis for the live agent's cached bundle.
    bundle = run_forecastability_fingerprint(
        series,
        target_name=target_name,
        max_lag=max_lag,
        n_surrogates=n_surrogates,
        random_state=random_state,
        ami_floor=ami_floor,
    )

    if strict or not _PYDANTIC_AI_AVAILABLE:
        return _strict_explanation(bundle)

    deps = FingerprintDeps(
        settings=settings,
        series=series,
        target_name=target_name,
        max_lag=max_lag,
        n_surrogates=n_surrogates,
        random_state=random_state,
        ami_floor=ami_floor,
        _bundle=bundle,
    )

    try:
        agent = create_fingerprint_agent(model=model, settings=settings)
        result = await agent.run(prompt, deps=deps)
        return result.output
    except Exception:
        _logger.exception(
            "Live fingerprint agent failed; falling back to deterministic explanation."
        )
        return _strict_explanation(bundle)
