# 20. Cross-Series Aggregation

- [x] Implement:
  - [ ] per-horizon Spearman correlation between AMI and sMAPE
  - [ ] per-horizon Spearman correlation between pAMI and sMAPE
  - [ ] overall rank correlation summaries
  - [ ] tercile decision analysis
  - [ ] optional frequency-wise grouping

```python
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from forecastability.utils.types import SeriesEvaluationResult


def build_horizon_table(
    results: list[SeriesEvaluationResult],
) -> pd.DataFrame:
    """Build one row per series-horizon-model."""
    rows: list[dict[str, str | int | float]] = []

    for result in results:
        for forecast_result in result.forecast_results:
            for horizon, smape_value in forecast_result.smape_by_horizon.items():
                rows.append(
                    {
                        "series_id": result.series_id,
                        "frequency": result.frequency,
                        "model_name": forecast_result.model_name,
                        "horizon": horizon,
                        "ami": result.ami_by_horizon[horizon],
                        "pami": result.pami_by_horizon[horizon],
                        "smape": smape_value,
                    }
                )

    return pd.DataFrame(rows)


def compute_rank_associations(
    table: pd.DataFrame,
) -> pd.DataFrame:
    """Compute Spearman rank association by model and horizon."""
    rows: list[dict[str, str | int | float]] = []

    grouped = table.groupby(["model_name", "horizon"], sort=True)
    for (model_name, horizon), group in grouped:
        ami_corr, _ = spearmanr(group["ami"], group["smape"])
        pami_corr, _ = spearmanr(group["pami"], group["smape"])

        rows.append(
            {
                "model_name": model_name,
                "horizon": int(horizon),
                "spearman_ami_smape": float(ami_corr),
                "spearman_pami_smape": float(pami_corr),
                "delta_pami_minus_ami": float(pami_corr - ami_corr),
            }
        )

    return pd.DataFrame(rows)
```
