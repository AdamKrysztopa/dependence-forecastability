"""Agent adapters package for the AMI → pAMI triage system."""

from forecastability.adapters.agents.triage_agent_payload_models import (
    F1ProfilePayload,
    F2LimitsPayload,
    F3LearningCurvePayload,
    F4SpectralPayload,
    F5LyapunovPayload,
    F6ComplexityPayload,
    F7BatchRankPayload,
    F8ExogDriverPayload,
    TriageAgentPayload,
)
from forecastability.adapters.agents.triage_summary_serializer import (
    SerialisedTriageSummary,
    serialise_batch,
    serialise_batch_to_json,
    serialise_payload,
    serialise_to_json,
)

__all__ = [
    # A1 payload models
    "F1ProfilePayload",
    "F2LimitsPayload",
    "F3LearningCurvePayload",
    "F4SpectralPayload",
    "F5LyapunovPayload",
    "F6ComplexityPayload",
    "F7BatchRankPayload",
    "F8ExogDriverPayload",
    "TriageAgentPayload",
    # A2 serialiser
    "SerialisedTriageSummary",
    "serialise_payload",
    "serialise_batch",
    "serialise_to_json",
    "serialise_batch_to_json",
]
