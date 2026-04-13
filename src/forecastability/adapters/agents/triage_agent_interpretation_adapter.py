"""Deterministic A3 interpretation adapter for triage agent payloads.

Builds concise, explainable narrative fields from A1 payloads and optional A2
serialisation envelopes. This adapter is deterministic and contains no LLM
logic or domain-science computation.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, ValidationError

from forecastability.adapters.agents.triage_agent_payload_models import TriageAgentPayload
from forecastability.adapters.agents.triage_summary_serializer import SerialisedTriageSummary

__all__ = [
    "InterpretationEvidence",
    "TriageAgentInterpretation",
    "interpret_batch",
    "interpret_payload",
]

InterpretationInput: TypeAlias = TriageAgentPayload | SerialisedTriageSummary
SignalBucket: TypeAlias = Literal["blocked", "strong", "mediated", "uncertain", "low"]


class InterpretationEvidence(BaseModel):
    """Deterministic evidence fields used to construct A3 narratives.

    Attributes:
        readiness_status: Readiness status propagated from A1.
        forecastability_class: Forecastability class from A1 interpretation.
        directness_class: Directness class from A1 interpretation.
        modeling_regime: Modeling regime from A1 interpretation.
        informative_horizon_count: Number of informative horizons from F1.
        complexity_band: Complexity band from F6 when available.
        warnings_count: Number of warning strings in A1.
        experimental_notes_count: Number of experimental-note strings in A1.
    """

    model_config = ConfigDict(frozen=True)

    readiness_status: str
    forecastability_class: str | None
    directness_class: str | None
    modeling_regime: str | None
    informative_horizon_count: int
    complexity_band: str | None
    warnings_count: int
    experimental_notes_count: int


class TriageAgentInterpretation(BaseModel):
    """Deterministic A3 interpretation payload for one triage target.

    Attributes:
        schema_version: A3 interpretation schema version.
        source_payload_type: Source payload type; always ``TriageAgentPayload``.
        source_serialised_at: A2 envelope timestamp when source was serialised.
        source_series_id: Series identifier propagated from A1.
        blocked: Whether readiness blocked downstream diagnostics.
        signal_bucket: Deterministic signal bucket from A1 classes.
        deterministic_summary: Concise summary string derived from A1 fields.
        strong_signal_narrative: Narrative for strong high-directness signals.
        cautionary_narrative: Narrative for blocked/mediated/uncertain/low signals.
        warnings: Warning strings propagated from A1.
        reliability_notes: Explicit reliability notes derived from A1 fields.
        experimental_flagged: True when experimental diagnostics are present.
        experimental_notes: Experimental-note strings propagated from A1 and F5.
        experimental_narrative: Explicit caution text for experimental diagnostics.
        evidence: Structured deterministic evidence used by the narrative.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1"
    source_payload_type: str = "TriageAgentPayload"
    source_serialised_at: str | None = None
    source_series_id: str | None
    blocked: bool
    signal_bucket: SignalBucket
    deterministic_summary: str
    strong_signal_narrative: str | None
    cautionary_narrative: str | None
    warnings: list[str]
    reliability_notes: list[str]
    experimental_flagged: bool
    experimental_notes: list[str]
    experimental_narrative: str | None
    evidence: InterpretationEvidence


def _append_unique(values: list[str], note: str) -> None:
    """Append note only if it is not already present.

    Args:
        values: Existing notes.
        note: Candidate note to append.
    """
    if note and note not in values:
        values.append(note)


def _extract_payload(input_payload: InterpretationInput) -> tuple[TriageAgentPayload, str | None]:
    """Resolve A1 payload from direct or A2-envelope input.

    Args:
        input_payload: A1 payload or A2 envelope wrapping an A1 payload.

    Returns:
        Tuple of ``(payload, serialised_at)``.

    Raises:
        ValueError: If envelope payload type is unsupported or payload content
            cannot be validated as ``TriageAgentPayload``.
    """
    if isinstance(input_payload, TriageAgentPayload):
        return input_payload, None

    if input_payload.payload_type != "TriageAgentPayload":
        msg = (
            "A3 interpretation requires SerialisedTriageSummary(payload_type='TriageAgentPayload')."
        )
        raise ValueError(msg)

    try:
        payload = TriageAgentPayload.model_validate(input_payload.payload)
    except ValidationError as exc:
        msg = "Serialised TriageAgentPayload is invalid and cannot be interpreted."
        raise ValueError(msg) from exc

    return payload, input_payload.serialised_at


def _signal_bucket(payload: TriageAgentPayload) -> SignalBucket:
    """Classify deterministic signal bucket from A1 fields.

    Args:
        payload: A1 triage payload.

    Returns:
        One of ``blocked``, ``strong``, ``mediated``, ``uncertain``, or ``low``.
    """
    if payload.blocked:
        return "blocked"

    if payload.forecastability_class == "high" and payload.directness_class in {
        "high",
        "arch_suspected",
    }:
        return "strong"
    if payload.forecastability_class == "high":
        return "mediated"
    if payload.forecastability_class == "medium" or payload.forecastability_class is None:
        return "uncertain"
    return "low"


def _deterministic_summary(payload: TriageAgentPayload, bucket: SignalBucket) -> str:
    """Build concise deterministic summary from A1 evidence.

    Args:
        payload: A1 triage payload.
        bucket: Deterministic signal bucket.

    Returns:
        Short deterministic summary string.
    """
    if bucket == "blocked":
        return (
            "Deterministic triage is blocked at readiness gate "
            f"(status={payload.readiness_status})."
        )

    series_id = payload.series_id or "unnamed"
    forecastability = payload.forecastability_class or "unknown"
    directness = payload.directness_class or "unknown"
    regime = payload.modeling_regime or "unknown"
    return (
        f"Series '{series_id}' was classified as {forecastability} forecastability "
        f"and {directness} directness with regime '{regime}' ({bucket} signal)."
    )


def _strong_signal_narrative(payload: TriageAgentPayload, bucket: SignalBucket) -> str | None:
    """Return strong-signal narrative for high-confidence cases.

    Args:
        payload: A1 triage payload.
        bucket: Deterministic signal bucket.

    Returns:
        Strong-signal narrative or ``None``.
    """
    if bucket != "strong":
        return None

    n_informative = len(payload.f1_profile.informative_horizons) if payload.f1_profile else 0
    return (
        "Strong-signal evidence: high forecastability with high directness indicates "
        "directly exploitable structure. "
        f"Informative horizons detected: {n_informative}."
    )


def _cautionary_narrative(payload: TriageAgentPayload, bucket: SignalBucket) -> str | None:
    """Return cautionary narrative for non-strong or warning-heavy cases.

    Args:
        payload: A1 triage payload.
        bucket: Deterministic signal bucket.

    Returns:
        Cautionary narrative or ``None``.
    """
    message: str | None
    if bucket == "blocked":
        message = (
            "Readiness gate blocked diagnostics; resolve readiness issues before any "
            "model-selection decision."
        )
    elif bucket == "mediated":
        message = (
            "Mediated signal: high forecastability is present, but directness is limited; "
            "prefer compact models and validate long-lag claims."
        )
    elif bucket == "uncertain":
        message = (
            "Uncertain signal: medium or incomplete deterministic evidence; use "
            "conservative model complexity and stronger validation."
        )
    elif bucket == "low":
        message = (
            "Low signal: deterministic evidence is near the noise floor; baseline or "
            "robust designs are usually appropriate."
        )
    else:
        message = None

    if payload.warnings:
        warning_suffix = (
            f" Warnings were emitted ({len(payload.warnings)} total) and must be reviewed."
        )
        if message is None:
            return warning_suffix.strip()
        return f"{message}{warning_suffix}"

    return message


def _reliability_notes(payload: TriageAgentPayload) -> list[str]:
    """Build explicit reliability notes from A1 fields.

    Args:
        payload: A1 triage payload.

    Returns:
        Ordered reliability-note list.
    """
    notes: list[str] = []

    if payload.blocked:
        _append_unique(
            notes,
            "Payload is blocked; downstream diagnostics are intentionally absent.",
        )
    if payload.readiness_status == "warning":
        _append_unique(
            notes,
            "Readiness status is 'warning'; deterministic outputs include caveats.",
        )
    if payload.warnings:
        _append_unique(
            notes,
            f"{len(payload.warnings)} warning(s) propagated from readiness/diagnostic layers.",
        )
    if payload.directness_class == "arch_suspected":
        _append_unique(
            notes,
            "Directness class 'arch_suspected' may indicate ratio inflation "
            "under heteroskedasticity.",
        )
    if payload.f1_profile is None and not payload.blocked:
        _append_unique(notes, "F1 profile is unavailable; horizon-level evidence is limited.")

    if payload.f2_limits is not None and payload.f2_limits.compression_warning is not None:
        _append_unique(notes, payload.f2_limits.compression_warning)
    if payload.f2_limits is not None and payload.f2_limits.dpi_warning is not None:
        _append_unique(notes, payload.f2_limits.dpi_warning)

    return notes


def _experimental_notes(payload: TriageAgentPayload) -> list[str]:
    """Collect explicit experimental notes from A1 fields.

    Args:
        payload: A1 triage payload.

    Returns:
        Ordered list of experimental notes.
    """
    notes: list[str] = list(payload.experimental_notes)

    if payload.f5_lyapunov is not None:
        _append_unique(notes, payload.f5_lyapunov.lyapunov_warning)
        if payload.f5_lyapunov.is_experimental:
            _append_unique(notes, "F5 Lyapunov diagnostic is marked experimental.")

    return notes


def _experimental_narrative(notes: list[str]) -> str | None:
    """Create explicit narrative for experimental diagnostics.

    Args:
        notes: Experimental-note list.

    Returns:
        Experimental caution narrative or ``None``.
    """
    if not notes:
        return None
    return (
        "Experimental diagnostics are present and should be treated as supporting "
        "evidence, not sole decision criteria."
    )


def _evidence(payload: TriageAgentPayload, experimental_notes: list[str]) -> InterpretationEvidence:
    """Build structured evidence object from payload fields.

    Args:
        payload: A1 triage payload.
        experimental_notes: Resolved experimental notes.

    Returns:
        Frozen evidence model.
    """
    informative_count = 0
    if payload.f1_profile is not None:
        informative_count = len(payload.f1_profile.informative_horizons)

    complexity_band = None
    if payload.f6_complexity is not None:
        complexity_band = payload.f6_complexity.complexity_band

    return InterpretationEvidence(
        readiness_status=payload.readiness_status,
        forecastability_class=payload.forecastability_class,
        directness_class=payload.directness_class,
        modeling_regime=payload.modeling_regime,
        informative_horizon_count=informative_count,
        complexity_band=complexity_band,
        warnings_count=len(payload.warnings),
        experimental_notes_count=len(experimental_notes),
    )


def interpret_payload(input_payload: InterpretationInput) -> TriageAgentInterpretation:
    """Interpret one A1 payload (or A2 envelope) into a deterministic A3 payload.

    Args:
        input_payload: ``TriageAgentPayload`` or a ``SerialisedTriageSummary``
            wrapping a ``TriageAgentPayload``.

    Returns:
        Frozen ``TriageAgentInterpretation`` with deterministic narratives,
        explicit warning fields, and explicit experimental handling.
    """
    payload, serialised_at = _extract_payload(input_payload)
    bucket = _signal_bucket(payload)

    experimental_notes = _experimental_notes(payload)
    return TriageAgentInterpretation(
        source_serialised_at=serialised_at,
        source_series_id=payload.series_id,
        blocked=payload.blocked,
        signal_bucket=bucket,
        deterministic_summary=_deterministic_summary(payload, bucket),
        strong_signal_narrative=_strong_signal_narrative(payload, bucket),
        cautionary_narrative=_cautionary_narrative(payload, bucket),
        warnings=list(payload.warnings),
        reliability_notes=_reliability_notes(payload),
        experimental_flagged=bool(experimental_notes),
        experimental_notes=experimental_notes,
        experimental_narrative=_experimental_narrative(experimental_notes),
        evidence=_evidence(payload, experimental_notes),
    )


def interpret_batch(payloads: Sequence[InterpretationInput]) -> list[TriageAgentInterpretation]:
    """Interpret a batch of A1 payloads or A2 envelopes in stable input order.

    Args:
        payloads: Sequence of ``TriageAgentPayload`` or A2 envelopes wrapping
            ``TriageAgentPayload``.

    Returns:
        List of ``TriageAgentInterpretation`` objects preserving input order.
    """
    return [interpret_payload(payload) for payload in payloads]
