"""Agent adapters package for the AMI → pAMI triage and fingerprint systems."""

from forecastability.adapters.agents.fingerprint_agent_interpretation_adapter import (
    FingerprintAgentInterpretation,
    FingerprintInterpretationEvidence,
    interpret_fingerprint_batch,
    interpret_fingerprint_payload,
)
from forecastability.adapters.agents.fingerprint_agent_payload_models import (
    FingerprintAgentPayload,
    fingerprint_agent_payload,
)
from forecastability.adapters.agents.fingerprint_summary_serializer import (
    SerialisedFingerprintSummary,
    serialise_fingerprint_payload,
    serialise_fingerprint_to_json,
)
from forecastability.adapters.agents.triage_agent_interpretation_adapter import (
    InterpretationEvidence,
    TriageAgentInterpretation,
    interpret_batch,
    interpret_payload,
)
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
    # A3 interpretation adapter
    "InterpretationEvidence",
    "TriageAgentInterpretation",
    "interpret_payload",
    "interpret_batch",
    # A2 serialiser
    "SerialisedTriageSummary",
    "serialise_payload",
    "serialise_batch",
    "serialise_to_json",
    "serialise_batch_to_json",
    # Fingerprint A1 payload models (V3_1-F05.1)
    "FingerprintAgentPayload",
    "fingerprint_agent_payload",
    # Fingerprint A2 serialiser (V3_1-F05.1)
    "SerialisedFingerprintSummary",
    "serialise_fingerprint_payload",
    "serialise_fingerprint_to_json",
    # Fingerprint A3 interpretation adapter (V3_1-F05.1)
    "FingerprintAgentInterpretation",
    "FingerprintInterpretationEvidence",
    "interpret_fingerprint_payload",
    "interpret_fingerprint_batch",
]
