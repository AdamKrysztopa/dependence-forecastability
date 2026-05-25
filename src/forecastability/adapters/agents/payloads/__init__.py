"""Agent payload data models — serialisation boundary between domain and LLM consumers.

This subpackage contains the A1 payload schemas and bundle-to-payload mapping
functions for every agent surface.  No pydantic-ai, provider SDK, or prompt
text belongs here.
"""

from forecastability.adapters.agents.payloads.covariant_agent_payload_models import (
    CovariantAgentExplanation,
    explanation_from_interpretation,
)
from forecastability.adapters.agents.payloads.fingerprint_agent_interpretation_adapter import (
    FingerprintAgentInterpretation,
    FingerprintInterpretationEvidence,
    interpret_fingerprint_batch,
    interpret_fingerprint_payload,
)
from forecastability.adapters.agents.payloads.fingerprint_agent_payload_models import (
    FingerprintAgentPayload,
    fingerprint_agent_payload,
)
from forecastability.adapters.agents.payloads.fingerprint_summary_serializer import (
    SerialisedFingerprintSummary,
    serialise_fingerprint_payload,
    serialise_fingerprint_to_json,
)
from forecastability.adapters.agents.payloads.routing_validation_agent_payload_models import (
    RoutingValidationAgentPayload,
    routing_validation_agent_payload,
)
from forecastability.adapters.agents.payloads.routing_validation_summary_serializer import (
    SerialisedRoutingValidationSummary,
    serialise_routing_validation_payload,
    serialise_routing_validation_to_json,
)
from forecastability.adapters.agents.payloads.triage_agent_interpretation_adapter import (
    InterpretationEvidence,
    TriageAgentInterpretation,
    interpret_batch,
    interpret_payload,
)
from forecastability.adapters.agents.payloads.triage_agent_payload_models import (
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
from forecastability.adapters.agents.payloads.triage_summary_serializer import (
    SerialisedTriageSummary,
    serialise_batch,
    serialise_batch_to_json,
    serialise_payload,
    serialise_to_json,
)

__all__ = [
    # Covariant payload
    "CovariantAgentExplanation",
    "explanation_from_interpretation",
    # Fingerprint A1 payload
    "FingerprintAgentPayload",
    "fingerprint_agent_payload",
    # Fingerprint A3 interpretation adapter
    "FingerprintAgentInterpretation",
    "FingerprintInterpretationEvidence",
    "interpret_fingerprint_payload",
    "interpret_fingerprint_batch",
    # Fingerprint A2 serialiser
    "SerialisedFingerprintSummary",
    "serialise_fingerprint_payload",
    "serialise_fingerprint_to_json",
    # Routing validation payload
    "RoutingValidationAgentPayload",
    "routing_validation_agent_payload",
    # Routing validation serialiser
    "SerialisedRoutingValidationSummary",
    "serialise_routing_validation_payload",
    "serialise_routing_validation_to_json",
    # Triage A3 interpretation adapter
    "InterpretationEvidence",
    "TriageAgentInterpretation",
    "interpret_payload",
    "interpret_batch",
    # Triage A1 payload models
    "F1ProfilePayload",
    "F2LimitsPayload",
    "F3LearningCurvePayload",
    "F4SpectralPayload",
    "F5LyapunovPayload",
    "F6ComplexityPayload",
    "F7BatchRankPayload",
    "F8ExogDriverPayload",
    "TriageAgentPayload",
    # Triage A2 serialiser
    "SerialisedTriageSummary",
    "serialise_payload",
    "serialise_batch",
    "serialise_to_json",
    "serialise_batch_to_json",
]
