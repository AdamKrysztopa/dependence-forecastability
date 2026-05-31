"""Backward-compatible re-export shim (RVH-F11).

Triage payload models have moved to
:mod:`forecastability.adapters.agents.payloads.triage_agent_payload_models`.
This shim will be removed in v0.6.0.
"""

import warnings as _warnings

_warnings.warn(
    "forecastability.adapters.agents.triage_agent_payload_models is deprecated. "
    "Import from forecastability.adapters.agents.payloads.triage_agent_payload_models instead.",
    DeprecationWarning,
    stacklevel=2,
)

from forecastability.adapters.agents.payloads.triage_agent_payload_models import (  # noqa: E402, F401
    F1ProfilePayload,
    F2LimitsPayload,
    F3LearningCurvePayload,
    F4SpectralPayload,
    F5LyapunovPayload,
    F6ComplexityPayload,
    F7BatchRankPayload,
    F8ExogDriverPayload,
    TriageAgentPayload,
    f1_profile_payload,
    f2_limits_payload,
    f3_learning_curve_payload,
    f4_spectral_payload,
    f5_lyapunov_payload,
    f6_complexity_payload,
    f7_batch_rank_payload,
    f8_exog_driver_payload,
    triage_agent_payload,
)

__all__ = [
    "F1ProfilePayload",
    "F2LimitsPayload",
    "F3LearningCurvePayload",
    "F4SpectralPayload",
    "F5LyapunovPayload",
    "F6ComplexityPayload",
    "F7BatchRankPayload",
    "F8ExogDriverPayload",
    "TriageAgentPayload",
    "f1_profile_payload",
    "f2_limits_payload",
    "f3_learning_curve_payload",
    "f4_spectral_payload",
    "f5_lyapunov_payload",
    "f6_complexity_payload",
    "f7_batch_rank_payload",
    "f8_exog_driver_payload",
    "triage_agent_payload",
]
