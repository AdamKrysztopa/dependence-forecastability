"""TransferEntropyKsgResult — frozen result for compute_transfer_entropy_ksg (RVH-F02)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TransferEntropyKsgResult(BaseModel):
    """Result from compute_transfer_entropy_ksg (Frenzel-Pompe KSG-CMI).

    This is true Schreiber transfer entropy via KSG-CMI, introduced in v0.5.0.
    Not to be confused with the legacy compute_predictive_information_gain
    (residual-MI, not true TE).
    """

    model_config = ConfigDict(frozen=True)

    status: Literal["computed", "blocked"] = Field(
        description=(
            "'computed' if estimation succeeded; "
            "'blocked' if sample-size rule N < k^(d+2) was violated."
        )
    )
    value: float = Field(description="TE estimate in nats. NaN when status='blocked'.")
    lag: int = Field(description="Transfer lag L at which TE was estimated.")
    history_depth: int = Field(
        description="Number of target history lags used as conditioning set."
    )
    n_neighbors: int = Field(description="Neighbour count k used in the KSG-CMI estimator.")
    n_samples: int = Field(description="Effective sample size after lag alignment.")
    estimator: Literal["ksg_frenzel_pompe"] = Field(
        default="ksg_frenzel_pompe",
        description="Estimator identifier for provenance tracking.",
    )
