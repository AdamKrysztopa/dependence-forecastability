"""TransferEntropyKsgResult — frozen result for compute_transfer_entropy_ksg (RVH-F02)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TransferEntropyKsgResult(BaseModel):
    """Result from compute_transfer_entropy_ksg (Frenzel-Pompe KSG-CMI).

    This is true Schreiber transfer entropy via KSG-CMI, introduced in v0.5.0.
    Not to be confused with the legacy compute_predictive_information_gain
    (residual-MI, not true TE).

    The KSG-CMI estimator degrades with conditioning dimension d. Even before the
    hard cutoff N < k^(d+2), bias grows roughly with d*log(d) for fixed N. Check
    quality_warning before interpreting values at history_depth >= 3 with N < 5000.
    """

    model_config = ConfigDict(frozen=True)

    status: Literal[
        "computed",
        "blocked_sample_size",
        "blocked_low_cardinality",
        "blocked_constant_input",
    ] = Field(
        description=(
            "'computed' if estimation succeeded. "
            "'blocked_sample_size' if N < k^(d+2) (Frenzel-Pompe cutoff). "
            "'blocked_low_cardinality' if unique(X)/N < 0.1 "
            "(KSG unreliable on near-discrete data). "
            "'blocked_constant_input' if X or Y is constant (zero variance)."
        )
    )
    quality_warning: Literal["ok", "marginal", "unreliable"] = Field(
        description=(
            "Reliability indicator based on N / k^(d+2). "
            "'ok': N/k^(d+2) >= 10 (estimation is reliable). "
            "'marginal': 2 <= N/k^(d+2) < 10 (use with caution, bias may be significant). "
            "'unreliable': N/k^(d+2) < 2 (near the hard cutoff; result is noisy)."
        )
    )
    value: float = Field(description="TE estimate in nats. NaN when status != 'computed'.")
    raw_value: float = Field(
        default=float("nan"),
        description=(
            "Raw (unclamped) Frenzel-Pompe CMI estimate in nats, before non-negativity "
            "clamping. Equal to value when value >= 0; may be slightly negative near "
            "independence due to finite-sample digamma approximation. NaN when "
            "status != 'computed'."
        ),
    )
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
