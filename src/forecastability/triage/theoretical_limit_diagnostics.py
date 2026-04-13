"""Domain model for Information-Theoretic Limit Diagnostics (F2)."""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel, ConfigDict


class TheoreticalLimitDiagnostics(BaseModel):
    """Information-theoretic ceiling on predictive improvement by horizon.

    Under log loss, the mutual information at horizon h equals the maximum
    achievable predictive gain for that horizon.  This model surfaces that
    ceiling together with applicable data-processing warnings.

    Attributes:
        forecastability_ceiling_by_horizon: MI value at each horizon.  Under
            log loss this equals the maximum achievable predictive improvement.
            Shape ``(H,)``, indexed by 0-based position (horizon = index + 1).
        ceiling_summary: One-sentence human-readable summary of the ceiling.
        compression_warning: Warning text when destructive transforms are
            suspected (aggregation / downsampling), or ``None`` if no warning.
        dpi_warning: Warning text about the data-processing inequality, or
            ``None`` when the data-processing inequality is not triggered.
        exploitation_ratio_supported: Always ``False`` in this pre-model repo.
            Placeholder for future model-evaluation layer integration.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    forecastability_ceiling_by_horizon: np.ndarray
    ceiling_summary: str
    compression_warning: str | None
    dpi_warning: str | None
    exploitation_ratio_supported: bool
