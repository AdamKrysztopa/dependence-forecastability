# 14. Canonical Example Analysis Pipeline

- [x] Implement canonical example analysis with:
  - [ ] AMI
  - [ ] pAMI
  - [ ] significance bands
  - [ ] summary descriptors
  - [ ] interpretation
  - [ ] saved figures and JSON

```python
from __future__ import annotations

import numpy as np

from forecastability.metrics import compute_ami, compute_pami_linear_residual
from forecastability.diagnostics.surrogates import compute_significance_bands
from forecastability.utils.types import CanonicalExampleResult, MetricCurve


def _significant_lags(
    values: np.ndarray,
    upper_band: np.ndarray,
) -> np.ndarray:
    """Return 1-based significant lag indices."""
    return np.where(values > upper_band)[0] + 1


def run_canonical_example(
    series_name: str,
    ts: np.ndarray,
    *,
    max_lag_ami: int,
    max_lag_pami: int,
    n_neighbors: int,
    n_surrogates: int,
    alpha: float,
    random_state: int,
) -> CanonicalExampleResult:
    """Run AMI and pAMI analysis for one canonical series."""
    ami_values = compute_ami(
        ts,
        max_lag_ami,
        n_neighbors=n_neighbors,
        random_state=random_state,
    )
    ami_lower, ami_upper = compute_significance_bands(
        ts,
        metric_name="ami",
        max_lag=max_lag_ami,
        n_surrogates=n_surrogates,
        alpha=alpha,
        n_neighbors=n_neighbors,
        random_state=random_state,
    )
    ami_sig = _significant_lags(ami_values, ami_upper)

    pami_values = compute_pami_linear_residual(
        ts,
        max_lag_pami,
        n_neighbors=n_neighbors,
        random_state=random_state,
    )
    pami_lower, pami_upper = compute_significance_bands(
        ts,
        metric_name="pami_linear_residual",
        max_lag=max_lag_pami,
        n_surrogates=n_surrogates,
        alpha=alpha,
        n_neighbors=n_neighbors,
        random_state=random_state,
    )
    pami_sig = _significant_lags(pami_values, pami_upper)

    return CanonicalExampleResult(
        series_name=series_name,
        series=ts,
        ami=MetricCurve(
            values=ami_values,
            lower_band=ami_lower,
            upper_band=ami_upper,
            significant_lags=ami_sig,
        ),
        pami=MetricCurve(
            values=pami_values,
            lower_band=pami_lower,
            upper_band=pami_upper,
            significant_lags=pami_sig,
        ),
        metadata={},
    )
```
