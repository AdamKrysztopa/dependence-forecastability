"""Live-LLM adapter for covariant interpretation narratives (V3-F09).

This adapter mirrors :mod:`forecastability.adapters.llm.triage_agent`: it
wraps the deterministic :class:`CovariantInterpretationResult` behind a
PydanticAI agent so that a language model can *narrate* the findings without
ever introducing numeric values or fabricating driver names and role tags.

When ``pydantic_ai`` is not installed, when no API key is configured, or when
``strict=True`` is passed, the adapter falls back to a narrative-free
explanation built deterministically from the upstream interpretation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from forecastability.adapters.agents.covariant_agent_payload_models import (
    CovariantAgentExplanation,
    explanation_from_interpretation,
)
from forecastability.adapters.settings import InfraSettings
from forecastability.services.covariant_interpretation_service import (
    verify_narrative_against_bundle,
)
from forecastability.utils.types import (
    CovariantAnalysisBundle,
    CovariantInterpretationResult,
)

try:
    from pydantic_ai import Agent, RunContext

    _PYDANTIC_AI_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised via monkeypatch
    _PYDANTIC_AI_AVAILABLE = False


_logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = """\
You narrate the findings of a deterministic covariant forecastability analysis.

Workflow
--------
1. Call ``get_deterministic_interpretation`` to retrieve the driver roles,
   forecastability class, directness class, and primary drivers.
2. Produce a short explanation (3-5 sentences) grounded *only* in the
   returned deterministic structure.

Hard rules
----------
- Never invent driver names. Only refer to drivers present in the
  ``driver_roles`` list returned by the tool.
- Never invent role tags.  Use only the role tags that appear in the
  returned data.
- Never cite numeric values that are not in the deterministic interpretation.
- Echo the ``conditioning_disclaimer`` verbatim in the ``caveats`` field.
"""


@dataclass
class CovariantAgentDeps:
    """Runtime dependencies injected into the covariant interpretation agent.

    Attributes:
        settings: Infrastructure settings (API keys, model names).
        bundle: Covariant analysis bundle produced upstream.
        interpretation: Deterministic interpretation derived from the bundle.
    """

    settings: InfraSettings
    bundle: CovariantAnalysisBundle
    interpretation: CovariantInterpretationResult


def _strict_fallback(
    interpretation: CovariantInterpretationResult,
    *,
    extra_caveats: list[str] | None = None,
) -> CovariantAgentExplanation:
    caveats: list[str] = ["Narrative disabled (strict/no-network mode)."]
    if extra_caveats:
        caveats.extend(extra_caveats)
    return explanation_from_interpretation(
        interpretation,
        narrative=None,
        caveats=caveats,
    )


def _create_agent(
    *, model: str, settings: InfraSettings
) -> Agent[CovariantAgentDeps, CovariantAgentExplanation]:
    if not _PYDANTIC_AI_AVAILABLE:
        raise ImportError(
            "pydantic-ai is required for the covariant narrative agent. "
            "Install with: uv sync --extra agent"
        )
    del settings  # unused: model string already carries provider prefix
    agent: Agent[CovariantAgentDeps, CovariantAgentExplanation] = Agent(  # type: ignore[assignment]
        model,
        deps_type=CovariantAgentDeps,
        output_type=CovariantAgentExplanation,
        system_prompt=_SYSTEM_PROMPT,
    )

    @agent.tool
    def get_deterministic_interpretation(
        ctx: RunContext[CovariantAgentDeps],
    ) -> dict[str, Any]:
        """Return the full deterministic interpretation as a plain dict."""
        return ctx.deps.interpretation.model_dump()

    return agent


async def run_covariant_interpretation_agent(
    bundle: CovariantAnalysisBundle,
    interpretation: CovariantInterpretationResult,
    *,
    model: str | None = None,
    settings: InfraSettings | None = None,
    strict: bool = False,
) -> CovariantAgentExplanation:
    """Run the covariant interpretation agent and return a verified explanation.

    Args:
        bundle: Covariant analysis bundle (used for context only).
        interpretation: Deterministic interpretation derived from ``bundle``.
        model: Optional provider:model identifier (e.g. ``"openai:gpt-4o"``).
        settings: Optional :class:`InfraSettings`; loaded from ``.env`` when
            ``None``.
        strict: When ``True``, skip the live LLM call entirely and return a
            narrative-free explanation.

    Returns:
        :class:`CovariantAgentExplanation` with a verified narrative or with
        ``narrative=None`` when the strict / no-network fallback is used.
    """
    if settings is None:
        settings = InfraSettings()

    if strict or not _PYDANTIC_AI_AVAILABLE or settings.openai_api_key is None:
        return _strict_fallback(interpretation)

    resolved_model = model if model is not None else f"openai:{settings.openai_model}"
    agent = _create_agent(model=resolved_model, settings=settings)

    deps = CovariantAgentDeps(
        settings=settings,
        bundle=bundle,
        interpretation=interpretation,
    )
    run_result = await agent.run(
        "Summarise the deterministic covariant interpretation for a practitioner.",
        deps=deps,
    )
    explanation: CovariantAgentExplanation = run_result.output

    if explanation.narrative is None:
        return explanation

    violations = verify_narrative_against_bundle(explanation.narrative, interpretation)
    if violations:
        _logger.warning(
            "Dropping covariant agent narrative due to %d hallucination violation(s): %s",
            len(violations),
            violations,
        )
        dropped_caveat = (
            f"Narrative dropped: {len(violations)} hallucination violation(s) detected."
        )
        return explanation_from_interpretation(
            interpretation,
            narrative=None,
            caveats=[dropped_caveat, *violations],
        )
    return explanation


__all__ = [
    "CovariantAgentDeps",
    "run_covariant_interpretation_agent",
]
