"""Optional live-LLM adapter for routing-validation narration (plan v0.3.3 V3_4-F09).

This adapter is downstream of the deterministic routing-validation workflow. It
accepts an already-computed :class:`RoutingValidationBundle`, builds the
deterministic payload once, and optionally asks an LLM to narrate that payload.
No audit, confidence, or routing fields are recomputed here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

from forecastability.adapters.agents.routing_validation_agent_payload_models import (
    RoutingValidationAgentPayload,
    routing_validation_agent_payload,
)
from forecastability.adapters.settings import InfraSettings
from forecastability.utils.types import (
    RoutingPolicyAudit,
    RoutingValidationBundle,
    RoutingValidationCase,
)

try:
    from pydantic_ai import Agent, RunContext

    _PYDANTIC_AI_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised via monkeypatch
    _PYDANTIC_AI_AVAILABLE = False


_logger = logging.getLogger(__name__)

pydantic_ai_available: bool = _PYDANTIC_AI_AVAILABLE
"""``True`` when ``pydantic-ai`` is installed; ``False`` otherwise."""

_SYSTEM_PROMPT = """\
You narrate the findings of a deterministic routing-validation review.

Workflow
--------
1. Call ``get_routing_validation_payload``.
2. Summarise the audit counts, the most important flagged cases, and the review
   meaning of downgrade / abstain / low-confidence outcomes.

Hard rules
----------
- Use only values returned by the tool.
- Do not compute, estimate, or infer new numeric values.
- Do not change audit counts, case outcomes, confidence labels, or family lists.
- Repeat every caveat string from the payload verbatim in the final narrative.
"""


@dataclass
class RoutingValidationDeps:
    """Runtime dependencies injected into the routing-validation agent.

    Attributes:
        settings: Infrastructure settings for API keys and model defaults.
        payload: Deterministic routing-validation payload.
    """

    settings: InfraSettings
    payload: RoutingValidationAgentPayload


class RoutingValidationNarrative(BaseModel):
    """Structured live-agent output containing narration only.

    Attributes:
        narrative: Narrative grounded in the deterministic payload.
    """

    model_config = ConfigDict(frozen=True)

    narrative: str


class RoutingValidationExplanation(BaseModel):
    """Deterministic routing-validation payload plus optional narrative.

    Attributes:
        bundle_audit: Aggregate pass / fail / downgrade / abstain counts.
        case_summaries: Per-case deterministic audit rows.
        headline_findings: Deterministic headline findings.
        caveats: Hard caveats carried through any narration.
        narrative: Optional live LLM narration; ``None`` in strict mode.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    bundle_audit: RoutingPolicyAudit
    case_summaries: list[RoutingValidationCase]
    headline_findings: list[str]
    caveats: list[str]
    narrative: str | None


def _explanation_from_payload(
    payload: RoutingValidationAgentPayload,
    *,
    narrative: str | None,
) -> RoutingValidationExplanation:
    """Build the outward explanation object from a deterministic payload.

    Args:
        payload: Deterministic routing-validation payload.
        narrative: Optional narrative text.

    Returns:
        Frozen explanation object.
    """
    return RoutingValidationExplanation(
        bundle_audit=payload.bundle_audit,
        case_summaries=list(payload.case_summaries),
        headline_findings=list(payload.headline_findings),
        caveats=list(payload.caveats),
        narrative=narrative,
    )


def _ensure_caveats_in_narrative(
    *,
    narrative: str,
    caveats: list[str],
) -> str:
    """Ensure every caveat string appears verbatim in the returned narrative.

    Args:
        narrative: Raw narrative from the live agent.
        caveats: Mandatory caveat strings.

    Returns:
        Narrative with any missing caveats appended verbatim.
    """
    cleaned = narrative.strip()
    missing = [caveat for caveat in caveats if caveat not in cleaned]
    if not missing:
        return cleaned
    suffix = " ".join(missing)
    if not cleaned:
        return suffix
    return f"{cleaned} {suffix}"


def _selected_provider(*, model: str | None) -> str:
    """Return the provider prefix for a provider:model identifier."""
    if model is None or ":" not in model:
        return "openai"
    provider, _, _ = model.partition(":")
    return provider.strip().lower() or "openai"


def _has_provider_credentials(*, model: str | None, settings: InfraSettings) -> bool:
    """Return whether the selected provider has a configured API key."""
    provider = _selected_provider(model=model)
    if provider == "openai":
        return settings.openai_api_key is not None
    if provider == "anthropic":
        return settings.anthropic_api_key is not None
    if provider == "xai":
        return settings.xai_api_key is not None
    return True


def create_routing_validation_agent(
    *,
    model: str | None = None,
    settings: InfraSettings | None = None,
) -> Agent[RoutingValidationDeps, RoutingValidationNarrative]:
    """Create the optional routing-validation narration agent.

    Args:
        model: Optional provider:model identifier.
        settings: Optional infrastructure settings; loaded from environment when
            omitted.

    Returns:
        Configured PydanticAI agent.

    Raises:
        ImportError: If ``pydantic-ai`` is not installed.
    """
    if not _PYDANTIC_AI_AVAILABLE:
        raise ImportError(
            "pydantic-ai is required for the live routing-validation adapter. "
            "Install with: uv sync --extra agent"
        )
    if settings is None:
        settings = InfraSettings()
    resolved_model = model if model is not None else f"openai:{settings.openai_model}"

    agent: Agent[RoutingValidationDeps, RoutingValidationNarrative] = Agent(  # type: ignore[assignment]
        resolved_model,
        deps_type=RoutingValidationDeps,
        output_type=RoutingValidationNarrative,
        system_prompt=_SYSTEM_PROMPT,
    )

    @agent.tool
    def get_routing_validation_payload(
        ctx: RunContext[RoutingValidationDeps],
    ) -> dict[str, object]:
        """Return the deterministic payload as a plain dict for narration.

        Args:
            ctx: PydanticAI run context.

        Returns:
            JSON-safe payload dict.
        """
        return ctx.deps.payload.model_dump(mode="json")

    return agent


async def run_routing_validation_agent(
    bundle: RoutingValidationBundle,
    *,
    model: str | None = None,
    settings: InfraSettings | None = None,
    strict: bool = True,
    prompt: str = "Summarise the routing-validation bundle for release review.",
) -> RoutingValidationExplanation:
    """Run the optional routing-validation narration agent.

    Args:
        bundle: Deterministic routing-validation bundle produced upstream.
        model: Optional provider:model identifier for the live path.
        settings: Optional infrastructure settings; loaded from environment when
            omitted.
        strict: When ``True``, skip the live LLM path and return deterministic
            payload plus ``narrative=None``.
        prompt: User prompt for the live agent.

    Returns:
        Deterministic explanation with optional narrative.
    """
    payload = routing_validation_agent_payload(bundle)
    if settings is None:
        settings = InfraSettings()

    if (
        strict
        or not _PYDANTIC_AI_AVAILABLE
        or not _has_provider_credentials(
            model=model,
            settings=settings,
        )
    ):
        return _explanation_from_payload(payload, narrative=None)

    try:
        agent = create_routing_validation_agent(model=model, settings=settings)
        deps = RoutingValidationDeps(settings=settings, payload=payload)
        run_result = await agent.run(prompt, deps=deps)
        narrative = _ensure_caveats_in_narrative(
            narrative=run_result.output.narrative,
            caveats=list(payload.caveats),
        )
        return _explanation_from_payload(payload, narrative=narrative)
    except Exception:
        _logger.exception(
            "Live routing-validation agent failed; falling back to deterministic payload."
        )
        return _explanation_from_payload(payload, narrative=None)


__all__ = [
    "RoutingValidationDeps",
    "RoutingValidationExplanation",
    "RoutingValidationNarrative",
    "create_routing_validation_agent",
    "pydantic_ai_available",
    "run_routing_validation_agent",
]
