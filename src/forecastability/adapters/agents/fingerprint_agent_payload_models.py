"""Agent payload models for the forecastability fingerprint surface (V3_1-F05.1).

These Pydantic models are the A1 serialisation boundary between the deterministic
:class:`FingerprintBundle` and agent / LLM consumers.  The canonical constructor,
:func:`fingerprint_agent_payload`, maps a bundle to a JSON-safe, frozen payload
without performing any scientific computation.

Ownership rules (SOLID / hexagonal):
* This module owns A1 payload schemas and bundle-to-payload mapping only.
* No domain services, scientific formulas, or routing logic belong here.
* No pydantic-ai, provider SDK, or prompt text belongs here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from forecastability.utils.types import FingerprintBundle


__all__ = [
    "FingerprintAgentPayload",
    "fingerprint_agent_payload",
]


class FingerprintAgentPayload(BaseModel):
    """Agent-serialisable payload built from a deterministic :class:`FingerprintBundle`.

    All four Peter Catt fingerprint metrics, routing families, confidence label,
    and caution flags are present as plain Python types with no numpy dtypes.

    Attributes:
        schema_version: Payload schema version string.
        target_name: Name of the series being fingerprinted.
        information_mass: Normalised masked area under the informative AMI profile.
        information_horizon: Latest informative horizon index (0 when none).
        information_structure: Shape label for the AMI profile.
            One of: ``none``, ``monotonic``, ``periodic``, ``mixed``.
        nonlinear_share: Fraction of informative AMI in excess of a linear
            Gaussian-information baseline.
        directness_ratio: Direct vs. mediated lag structure ratio; ``None`` if
            not computed.
        informative_horizons: List of horizon indices in the informative set.
        primary_families: Primary model-family routing recommendations.
        secondary_families: Secondary / fallback model families.
        confidence_label: Deterministic routing confidence.
            One of: ``low``, ``medium``, ``high``.
        caution_flags: Caution flags raised during routing.
        rationale: Human-readable routing rationale strings.
        profile_summary: Scalar summary of the underlying AMI profile.
        narrative: Optional free-form LLM narrative; ``None`` in strict mode.
        metadata: Optional annotations for provenance.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1"
    target_name: str
    # Four fingerprint fields (Peter Catt metrics)
    information_mass: float
    information_horizon: int
    information_structure: str
    nonlinear_share: float
    # Additional fingerprint fields
    directness_ratio: float | None
    informative_horizons: list[int]
    # Routing fields
    primary_families: list[str]
    secondary_families: list[str]
    confidence_label: str
    caution_flags: list[str]
    rationale: list[str]
    # Profile context
    profile_summary: dict[str, str | int | float]
    # Narrative (set by live agent, None in strict mode)
    narrative: str | None
    # Provenance
    metadata: dict[str, str | int | float]


def fingerprint_agent_payload(
    bundle: FingerprintBundle,
    *,
    narrative: str | None = None,
) -> FingerprintAgentPayload:
    """Build a :class:`FingerprintAgentPayload` from a deterministic bundle.

    This is a pure mapping function: it copies typed fields without recomputing
    any science. The optional ``narrative`` field is populated only by a live
    agent; pass ``None`` for the strict deterministic path.

    Args:
        bundle: Deterministic :class:`FingerprintBundle` from the use case.
        narrative: Optional free-form narrative text from a live LLM agent.
            Pass ``None`` to produce a strict, deterministic-only payload.

    Returns:
        Immutable :class:`FingerprintAgentPayload` ready for A2 serialisation.
    """
    fp = bundle.fingerprint
    rec = bundle.recommendation
    return FingerprintAgentPayload(
        target_name=bundle.target_name,
        information_mass=fp.information_mass,
        information_horizon=fp.information_horizon,
        information_structure=str(fp.information_structure),
        nonlinear_share=fp.nonlinear_share,
        directness_ratio=fp.directness_ratio,
        informative_horizons=list(fp.informative_horizons),
        primary_families=[str(f) for f in rec.primary_families],
        secondary_families=[str(f) for f in rec.secondary_families],
        confidence_label=str(rec.confidence_label),
        caution_flags=[str(flag) for flag in rec.caution_flags],
        rationale=list(rec.rationale),
        profile_summary=dict(bundle.profile_summary),
        narrative=narrative,
        metadata=dict(bundle.metadata),
    )
