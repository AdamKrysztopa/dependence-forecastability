"""Deterministic A3 interpretation adapter for fingerprint agent payloads (V3_1-F05.1).

Builds concise, explainable narrative fields from A1 :class:`FingerprintAgentPayload`
or A2 :class:`SerialisedFingerprintSummary` inputs without performing any domain
computation.  All numeric values and categorical fields are propagated verbatim.

Ownership rules (SOLID / hexagonal):
* This module owns A3 deterministic prose compression and caveat framing only.
* It must NOT invent metrics, routes, probabilities, or caution language.
* It must NOT override ``information_structure``, ``confidence_label``, or
  routing families from the source payload.
* No pydantic-ai, provider SDK, or scientific formula belongs here.
"""

from __future__ import annotations

from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict

from forecastability.adapters.agents.fingerprint_agent_payload_models import (
    FingerprintAgentPayload,
)
from forecastability.adapters.agents.fingerprint_summary_serializer import (
    SerialisedFingerprintSummary,
)

__all__ = [
    "FingerprintInterpretationEvidence",
    "FingerprintAgentInterpretation",
    "interpret_fingerprint_payload",
    "interpret_fingerprint_batch",
]

FingerprintInterpretationInput: TypeAlias = (
    FingerprintAgentPayload | SerialisedFingerprintSummary
)
StructureBucket: TypeAlias = Literal["none", "monotonic", "periodic", "mixed"]


class FingerprintInterpretationEvidence(BaseModel):
    """Deterministic evidence fields used to construct A3 fingerprint narratives.

    Attributes:
        information_structure: Structure label from A1.
        confidence_label: Routing confidence label from A1.
        information_horizon: Latest informative horizon from A1.
        informative_horizon_count: Number of informative horizons from A1.
        information_mass_bucket: Coarse bucket derived from mass value.
        nonlinear_share_bucket: Coarse bucket derived from nonlinear share.
        signal_to_noise_bucket: Coarse bucket derived from signal_to_noise.
        has_directness_ratio: Whether directness ratio was computed.
        caution_count: Number of caution flags in A1.
    """

    model_config = ConfigDict(frozen=True)

    information_structure: str
    confidence_label: str
    information_horizon: int
    informative_horizon_count: int
    information_mass_bucket: Literal["low", "medium", "high"]
    nonlinear_share_bucket: Literal["low", "medium", "high"]
    signal_to_noise_bucket: Literal["low", "medium", "high"]
    has_directness_ratio: bool
    caution_count: int


class FingerprintAgentInterpretation(BaseModel):
    """Deterministic A3 interpretation payload for one fingerprint bundle.

    Attributes:
        schema_version: A3 interpretation schema version.
        source_payload_type: Source payload type; always ``FingerprintAgentPayload``.
        source_serialised_at: A2 envelope timestamp when source was serialised.
        source_target_name: Target series name propagated from A1.
        structure_bucket: Deterministic structure category from A1.
        confidence_label: Routing confidence label propagated unchanged from A1.
        primary_families: Primary routing families propagated from A1.
        secondary_families: Secondary routing families propagated from A1.
        deterministic_summary: Concise summary string derived from A1 fields.
        rich_signal_narrative: Narrative for high-mass / well-structured signals.
        cautionary_narrative: Narrative for none-structure, low-mass, or flagged signals.
        caution_flags: Caution flags propagated from A1.
        rationale: Routing rationale propagated from A1.
        evidence: Structured deterministic evidence used by the narrative.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1"
    source_payload_type: str = "FingerprintAgentPayload"
    source_serialised_at: str | None = None
    source_target_name: str
    structure_bucket: str
    confidence_label: str
    primary_families: list[str]
    secondary_families: list[str]
    deterministic_summary: str
    rich_signal_narrative: str | None
    cautionary_narrative: str | None
    caution_flags: list[str]
    rationale: list[str]
    evidence: FingerprintInterpretationEvidence


def _mass_bucket(mass: float) -> Literal["low", "medium", "high"]:
    """Map a raw information_mass value to a coarse bucket label.

    Args:
        mass: Normalised information mass scalar.

    Returns:
        ``"low"``, ``"medium"``, or ``"high"``.
    """
    if mass < 0.05:
        return "low"
    if mass < 0.15:
        return "medium"
    return "high"


def _nonlinear_bucket(share: float) -> Literal["low", "medium", "high"]:
    """Map a nonlinear_share value to a coarse bucket label.

    Args:
        share: Nonlinear share scalar in [0, 1].

    Returns:
        ``"low"``, ``"medium"``, or ``"high"``.
    """
    if share < 0.25:
        return "low"
    if share < 0.55:
        return "medium"
    return "high"


def _signal_to_noise_bucket(value: float) -> Literal["low", "medium", "high"]:
    """Map signal_to_noise to a coarse quality bucket."""
    if value < 0.10:
        return "low"
    if value < 0.35:
        return "medium"
    return "high"


def _extract_payload(
    source: FingerprintInterpretationInput,
) -> tuple[FingerprintAgentPayload, str | None]:
    """Extract a :class:`FingerprintAgentPayload` and optional timestamp.

    Args:
        source: Either an A1 payload or an A2 serialised summary.

    Returns:
        Tuple of (payload, serialised_at).

    Raises:
        TypeError: If source is neither a payload nor a serialised summary.
        ValueError: If the serialised summary does not contain a valid payload.
    """
    if isinstance(source, FingerprintAgentPayload):
        return source, None
    if isinstance(source, SerialisedFingerprintSummary):
        raw = source.payload
        try:
            payload = FingerprintAgentPayload.model_validate(raw)
        except Exception as exc:
            msg = f"Cannot reconstruct FingerprintAgentPayload from serialised summary: {exc}"
            raise ValueError(msg) from exc
        return payload, source.serialised_at
    msg = f"Expected FingerprintAgentPayload or SerialisedFingerprintSummary, got {type(source)}"
    raise TypeError(msg)


def _build_deterministic_summary(
    payload: FingerprintAgentPayload,
    mass_bkt: Literal["low", "medium", "high"],
    nl_bkt: Literal["low", "medium", "high"],
    snr_bkt: Literal["low", "medium", "high"],
) -> str:
    """Build a one-line deterministic summary from payload fields.

    Args:
        payload: A1 payload.
        mass_bkt: Coarse information mass bucket.
        nl_bkt: Coarse nonlinear share bucket.

    Returns:
        A concise summary string.
    """
    structure = payload.information_structure
    horizon = payload.information_horizon
    families = ", ".join(payload.primary_families) if payload.primary_families else "none"
    return (
        f"[{payload.target_name}] structure={structure}, mass={mass_bkt}, "
        f"nonlinear={nl_bkt}, signal={snr_bkt}, horizon={horizon}, "
        f"confidence={payload.confidence_label}, route=[{families}]"
    )


def _build_rich_signal_narrative(
    payload: FingerprintAgentPayload,
    mass_bkt: Literal["low", "medium", "high"],
) -> str | None:
    """Build a narrative for signals with exploitable structure.

    Returns ``None`` for ``none`` structure or ``low`` mass to avoid misleading text.

    Args:
        payload: A1 payload.
        mass_bkt: Coarse information mass bucket.

    Returns:
        Narrative string or ``None``.
    """
    if payload.information_structure == "none" or mass_bkt == "low":
        return None
    structure = payload.information_structure
    families = ", ".join(payload.primary_families) if payload.primary_families else "none"
    horizon = payload.information_horizon
    confidence = payload.confidence_label
    nl_text = (
        "Nonlinear excess is present; nonlinear model families are indicated."
        if payload.nonlinear_share > 0.25
        else "Dependence is primarily linear in character."
    )
    return (
        f"The '{payload.target_name}' series shows {structure} forecastability structure "
        f"with information persisting to horizon {horizon}. "
        f"Recommended families: {families} (confidence: {confidence}). "
        f"{nl_text}"
    )


def _build_cautionary_narrative(
    payload: FingerprintAgentPayload,
    mass_bkt: Literal["low", "medium", "high"],
) -> str | None:
    """Build a cautionary narrative for weak, blocked, or flagged signals.

    Returns ``None`` for rich, unflagged signals to avoid redundancy.

    Args:
        payload: A1 payload.
        mass_bkt: Coarse information mass bucket.

    Returns:
        Cautionary string or ``None``.
    """
    if payload.information_structure == "none":
        return (
            f"No informative horizons found for '{payload.target_name}'. "
            "Naïve or seasonal-naïve baselines are appropriate; "
            "complex model investment is unlikely to pay off."
        )
    if mass_bkt == "low":
        families = ", ".join(payload.primary_families) if payload.primary_families else "none"
        return (
            f"Information mass is low for '{payload.target_name}'. "
            f"Routing suggests {families}, but marginal forecastability means "
            "modest model complexity is preferred over deep architectures."
        )
    if payload.caution_flags:
        flag_text = ", ".join(payload.caution_flags)
        return (
            f"Routing confidence is {payload.confidence_label} for "
            f"'{payload.target_name}' due to: {flag_text}. "
            "Review the rationale and caution flags before committing to a model family."
        )
    if payload.signal_to_noise < 0.10:
        return (
            f"Corrected AMI exists for '{payload.target_name}', but the margin above the "
            "surrogate threshold is weak. Treat the suggested families as cautious starting "
            "points rather than a strong routing verdict."
        )
    return None


def interpret_fingerprint_payload(
    source: FingerprintInterpretationInput,
) -> FingerprintAgentInterpretation:
    """Build a deterministic A3 interpretation from an A1 or A2 source.

    No domain science is computed here. All values are propagated from the
    source payload or derived by simple deterministic bucketing.

    Args:
        source: A :class:`FingerprintAgentPayload` (A1) or a
            :class:`SerialisedFingerprintSummary` (A2).

    Returns:
        Immutable :class:`FingerprintAgentInterpretation`.

    Raises:
        TypeError: If ``source`` is neither supported type.
        ValueError: If the A2 payload field cannot be reconstructed.
    """
    payload, serialised_at = _extract_payload(source)

    mass_bkt = _mass_bucket(payload.information_mass)
    nl_bkt = _nonlinear_bucket(payload.nonlinear_share)
    snr_bkt = _signal_to_noise_bucket(payload.signal_to_noise)

    evidence = FingerprintInterpretationEvidence(
        information_structure=payload.information_structure,
        confidence_label=payload.confidence_label,
        information_horizon=payload.information_horizon,
        informative_horizon_count=len(payload.informative_horizons),
        information_mass_bucket=mass_bkt,
        nonlinear_share_bucket=nl_bkt,
        signal_to_noise_bucket=snr_bkt,
        has_directness_ratio=payload.directness_ratio is not None,
        caution_count=len(payload.caution_flags),
    )

    deterministic_summary = _build_deterministic_summary(payload, mass_bkt, nl_bkt, snr_bkt)
    rich_signal_narrative = _build_rich_signal_narrative(payload, mass_bkt)
    cautionary_narrative = _build_cautionary_narrative(payload, mass_bkt)

    return FingerprintAgentInterpretation(
        source_serialised_at=serialised_at,
        source_target_name=payload.target_name,
        structure_bucket=payload.information_structure,
        confidence_label=payload.confidence_label,
        primary_families=list(payload.primary_families),
        secondary_families=list(payload.secondary_families),
        deterministic_summary=deterministic_summary,
        rich_signal_narrative=rich_signal_narrative,
        cautionary_narrative=cautionary_narrative,
        caution_flags=list(payload.caution_flags),
        rationale=list(payload.rationale),
        evidence=evidence,
    )


def interpret_fingerprint_batch(
    sources: list[FingerprintInterpretationInput],
) -> list[FingerprintAgentInterpretation]:
    """Interpret a batch of A1 or A2 sources.

    Args:
        sources: List of :class:`FingerprintAgentPayload` or
            :class:`SerialisedFingerprintSummary` instances.

    Returns:
        List of :class:`FingerprintAgentInterpretation` objects in the same order.
    """
    return [interpret_fingerprint_payload(s) for s in sources]
