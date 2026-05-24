"""PredictiveInformationGainResult — frozen result for compute_predictive_information_gain."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PredictiveInformationGainResult(BaseModel):
    """Result from compute_predictive_information_gain (residual-MI, renamed).

    This is the v0.4.3 residual-MI surface under its honest name.
    It is NOT Schreiber transfer entropy. For true TE use compute_transfer_entropy_ksg.

    See docs/migration/v0.4.x_to_v0.5.0.md for the migration recipe.
    """

    model_config = ConfigDict(frozen=True)

    status: Literal["computed", "blocked"] = Field(
        description=(
            "'computed' if estimation succeeded; "
            "'blocked' if residualization failed."
        )
    )
    value: float = Field(
        description="Predictive information gain estimate in nats. NaN when status='blocked'."
    )
    lag: int = Field(description="Lag L at which PIG was estimated.")
    backend: Literal["linear_residual", "rf", "et"] = Field(
        description="Residualization backend used."
    )
    n_samples: int = Field(description="Effective sample size after lag alignment.")
