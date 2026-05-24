"""RoutingConfidenceCalibrationAudit — frozen result for RVH-F08 calibration script."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ThresholdEntry(BaseModel):
    """A single calibrated threshold entry."""

    model_config = ConfigDict(frozen=True)

    label: Literal["high", "medium", "low"] = Field(description="Confidence label.")
    threshold: float = Field(description="Fitted threshold value.")
    achieved_precision: float = Field(
        description="Precision achieved at this threshold on the calibration set."
    )
    target_precision: float = Field(
        description="Target precision used to fit this threshold."
    )
    n_samples: int = Field(description="Number of calibration samples at this label.")


class RoutingConfidenceCalibrationAudit(BaseModel):
    """Audit record from scripts/run_routing_confidence_calibration.py (RVH-F08).

    Thresholds in RoutingPolicyAuditConfig are derived from this audit,
    not hand-picked. The word 'calibrated' in docstrings applies only when
    this audit was used to fit the threshold.
    """

    model_config = ConfigDict(frozen=True)

    version: str = Field(
        description="Release version this audit was generated for, e.g. '0.5.0'."
    )
    n_archetypes: int = Field(description="Number of synthetic archetypes used.")
    n_noise_replicates: int = Field(description="Number of noise replicates per archetype.")
    thresholds: list[ThresholdEntry] = Field(
        description="Calibrated thresholds per confidence label."
    )
    audit_timestamp: str = Field(description="ISO 8601 UTC timestamp of calibration run.")
    notes: str = Field(default="", description="Free-text notes from the calibration run.")
