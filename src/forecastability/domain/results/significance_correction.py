"""SignificanceCorrectionResult — frozen result for SignificanceCorrectionService (RVH-F03)."""
from __future__ import annotations

from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field


class SignificanceCorrectionResult(BaseModel):
    """Output of SignificanceCorrectionService.correct(surrogate_matrix, observed).

    Holds the family-wise corrected significance mask for H lags.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    correction: Literal["romano_wolf", "bh", "none"] = Field(
        description="Correction method applied."
    )
    family_wise_alpha: float = Field(
        description="Nominal family-wise error rate (FWER) target. Applies only to romano_wolf."
    )
    corrected_mask: np.ndarray = Field(
        description="Boolean array shape (H,). True = lag is significant after correction."
    )
    raw_p_values: np.ndarray = Field(
        description="Per-lag p-values before correction, shape (H,), from surrogate rank."
    )
    n_surrogates: int = Field(description="Number of surrogates used.")
    low_surrogate_warning: bool = Field(
        default=False,
        description=(
            "True if n_surrogates < 999 and correction='romano_wolf' "
            "(statistical honesty warning)."
        ),
    )
