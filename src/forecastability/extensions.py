"""Extension analyses: k-sensitivity and bootstrap uncertainty."""

from __future__ import annotations

import numpy as np
import pandas as pd

from forecastability.aggregation import summarize_canonical_result
from forecastability.pipeline import run_canonical_example
from forecastability.types import CanonicalExampleResult


def compute_k_sensitivity(
    *,
    series_name: str,
    ts: np.ndarray,
    k_values: list[int],
    max_lag_ami: int,
    max_lag_pami: int,
    n_surrogates: int,
    alpha: float,
    random_state: int,
) -> pd.DataFrame:
    """Run canonical AMI/pAMI analysis over a k-neighbor grid."""
    rows: list[dict[str, str | int | float]] = []
    for k in k_values:
        result = run_canonical_example(
            series_name=series_name,
            ts=ts,
            max_lag_ami=max_lag_ami,
            max_lag_pami=max_lag_pami,
            n_neighbors=k,
            n_surrogates=n_surrogates,
            alpha=alpha,
            random_state=random_state,
        )
        summary = summarize_canonical_result(result)
        rows.append(
            {
                "series_name": series_name,
                "k": int(k),
                "n_sig_ami": summary.n_sig_ami,
                "n_sig_pami": summary.n_sig_pami,
                "directness_ratio": summary.directness_ratio,
                "auc_ami": summary.auc_ami,
                "auc_pami": summary.auc_pami,
            }
        )
    return pd.DataFrame(rows)


def bootstrap_descriptor_uncertainty(
    result: CanonicalExampleResult,
    *,
    n_bootstrap: int,
    ci_level: float,
    random_state: int,
) -> pd.DataFrame:
    """Estimate uncertainty intervals for descriptor summaries via bootstrap."""
    if n_bootstrap < 1:
        raise ValueError("n_bootstrap must be >= 1")
    if not 0.0 < ci_level < 1.0:
        raise ValueError("ci_level must be in (0, 1)")

    rng = np.random.default_rng(random_state)
    ami = result.ami.values
    pami = result.pami.values
    n = min(ami.size, pami.size)

    directness_vals = np.empty(n_bootstrap, dtype=float)
    auc_ami_vals = np.empty(n_bootstrap, dtype=float)
    auc_pami_vals = np.empty(n_bootstrap, dtype=float)

    for idx in range(n_bootstrap):
        sample_idx = rng.integers(0, n, size=n)
        ami_s = ami[sample_idx]
        pami_s = pami[sample_idx]
        auc_ami = float(np.trapezoid(ami_s))
        auc_pami = float(np.trapezoid(pami_s))
        directness = auc_pami / max(auc_ami, 1e-12)
        auc_ami_vals[idx] = auc_ami
        auc_pami_vals[idx] = auc_pami
        directness_vals[idx] = directness

    lower_q = 100.0 * (1.0 - ci_level) / 2.0
    upper_q = 100.0 * (1.0 - (1.0 - ci_level) / 2.0)
    rows = [
        {
            "series_name": result.series_name,
            "metric": "auc_ami",
            "mean": float(np.mean(auc_ami_vals)),
            "ci_lower": float(np.percentile(auc_ami_vals, lower_q)),
            "ci_upper": float(np.percentile(auc_ami_vals, upper_q)),
        },
        {
            "series_name": result.series_name,
            "metric": "auc_pami",
            "mean": float(np.mean(auc_pami_vals)),
            "ci_lower": float(np.percentile(auc_pami_vals, lower_q)),
            "ci_upper": float(np.percentile(auc_pami_vals, upper_q)),
        },
        {
            "series_name": result.series_name,
            "metric": "directness_ratio",
            "mean": float(np.mean(directness_vals)),
            "ci_lower": float(np.percentile(directness_vals, lower_q)),
            "ci_upper": float(np.percentile(directness_vals, upper_q)),
        },
    ]
    return pd.DataFrame(rows)
