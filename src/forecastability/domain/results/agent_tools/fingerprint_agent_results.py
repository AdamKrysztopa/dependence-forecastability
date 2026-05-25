"""Frozen Pydantic result models for fingerprint agent tool returns.

Each model maps 1-to-1 to the dict keys previously returned by the
corresponding ``@agent.tool`` function in
:mod:`forecastability.adapters.agents.runtime.fingerprint_agent`.

``informative_horizons`` is stored as ``list[int]``.  ``confidence_label``
is serialised as a plain ``str`` (it is a ``Literal`` type alias at the source
boundary, not an enum subclass, so no conversion is required).

No new fields are added; semantics are unchanged.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = [
    "RunFingerprintResult",
    "GetInterpretationErrorResult",
    "InterpretationEvidenceResult",
    "GetInterpretationResult",
]


class RunFingerprintResult(BaseModel):
    """Result returned by the ``run_fingerprint`` tool.

    Attributes:
        target_name: Name of the series being fingerprinted.
        geometry_method: Deterministic geometry engine identifier.
        signal_to_noise: Geometry coverage statistic.
        geometry_information_horizon: Geometry-derived latest informative horizon.
        geometry_information_structure: Geometry-derived structure label.
        information_mass: Normalised masked area under the informative AMI profile.
        information_horizon: Latest informative horizon index (0 when none).
        information_structure: Shape label for the AMI profile.
        nonlinear_share: Fraction of informative AMI in excess of a linear baseline.
        directness_ratio: Direct vs. mediated lag structure ratio; ``None`` if not computed.
        informative_horizons: List of horizon indices in the informative set.
        primary_families: Primary model-family routing recommendations.
        secondary_families: Secondary / fallback model families.
        confidence_label: Deterministic routing confidence.
        caution_flags: Caution flags raised during routing.
        rationale: Human-readable routing rationale strings.
        profile_summary: Scalar summary of the underlying AMI profile.
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
    directness_ratio: float | None
    informative_horizons: list[int]
    primary_families: list[str]
    secondary_families: list[str]
    confidence_label: str
    caution_flags: list[str]
    rationale: list[str]
    profile_summary: dict[str, str | int | float]


class GetInterpretationErrorResult(BaseModel):
    """Result returned by ``get_interpretation`` when fingerprint is not yet computed.

    Attributes:
        error: Human-readable error string directing the caller to run ``run_fingerprint`` first.
    """

    model_config = ConfigDict(frozen=True)

    error: str


class InterpretationEvidenceResult(BaseModel):
    """Evidence section nested inside :class:`GetInterpretationResult`.

    Mirrors the fields of :class:`FingerprintInterpretationEvidence` as plain types.

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
    information_mass_bucket: str
    nonlinear_share_bucket: str
    signal_to_noise_bucket: str
    has_directness_ratio: bool
    caution_count: int


class GetInterpretationResult(BaseModel):
    """Result returned by the ``get_interpretation`` tool.

    Attributes:
        structure_bucket: Deterministic structure category from A1.
        confidence_label: Routing confidence label propagated from A1.
        deterministic_summary: Concise summary derived from A1 fields.
        rich_signal_narrative: Narrative for high-mass / well-structured signals.
        cautionary_narrative: Narrative for weak, blocked, or flagged signals.
        caution_flags: Caution flags propagated from A1.
        rationale: Routing rationale propagated from A1.
        evidence: Structured deterministic evidence used by the narrative.
    """

    model_config = ConfigDict(frozen=True)

    structure_bucket: str
    confidence_label: str
    deterministic_summary: str
    rich_signal_narrative: str | None
    cautionary_narrative: str | None
    caution_flags: list[str]
    rationale: list[str]
    evidence: InterpretationEvidenceResult
