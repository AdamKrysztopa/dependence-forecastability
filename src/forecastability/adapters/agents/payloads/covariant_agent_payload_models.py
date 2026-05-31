"""Agent payload models for the covariant interpretation surface (V3-F09).

These Pydantic models are the serialisation boundary between the deterministic
:class:`CovariantInterpretationResult` and agent / LLM consumers.  The
canonical constructor, :func:`explanation_from_interpretation`, is used by
both the strict path (narrative disabled) and the live path (narrative
verified against the deterministic interpretation).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from forecastability.utils.types import CovariantInterpretationResult


class CovariantAgentExplanation(BaseModel):
    """Agent-serialisable explanation built from a deterministic interpretation.

    Attributes:
        target: Target variable name.
        forecastability_class: Bundle-level forecastability class label.
        directness_class: Bundle-level directness class label.
        primary_drivers: Ordered list of drivers judged as primary.
        driver_role_echo: Mapping driver name → deterministic role tag.
        conditioning_disclaimer: Verbatim bundle-level conditioning disclaimer.
        narrative: Optional free-form LLM narrative; ``None`` in strict mode.
        caveats: Caveats and mandatory warnings surfaced to the consumer.
        schema_version: Payload schema version string.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    target: str
    forecastability_class: str
    directness_class: str
    primary_drivers: list[str]
    driver_role_echo: dict[str, str]
    conditioning_disclaimer: str
    narrative: str | None
    caveats: list[str]
    schema_version: str = "1"


def explanation_from_interpretation(
    interpretation: CovariantInterpretationResult,
    *,
    narrative: str | None,
    caveats: list[str] | None = None,
) -> CovariantAgentExplanation:
    """Build a :class:`CovariantAgentExplanation` from a deterministic result.

    Args:
        interpretation: Deterministic bundle-level interpretation.
        narrative: Optional free-form narrative; pass ``None`` to disable.
        caveats: Additional caveats to merge with the deterministic warnings.

    Returns:
        Immutable payload ready for serialisation to JSON.
    """
    role_echo: dict[str, str] = {
        entry.driver: str(entry.role) for entry in interpretation.driver_roles
    }
    merged_caveats = list(interpretation.warnings)
    for entry in interpretation.driver_roles:
        merged_caveats.extend(entry.warnings)
    if caveats:
        merged_caveats.extend(caveats)
    # Deduplicate while preserving order.
    seen: set[str] = set()
    unique_caveats: list[str] = []
    for item in merged_caveats:
        if item not in seen:
            seen.add(item)
            unique_caveats.append(item)
    return CovariantAgentExplanation(
        target=interpretation.target,
        forecastability_class=interpretation.forecastability_class,
        directness_class=interpretation.directness_class,
        primary_drivers=list(interpretation.primary_drivers),
        driver_role_echo=role_echo,
        conditioning_disclaimer=interpretation.conditioning_disclaimer,
        narrative=narrative,
        caveats=unique_caveats,
    )
