# 21. Tercile Analysis

- [x] Replicate paper-style ordinal screening.
- [x] Add pAMI terciles alongside AMI terciles.
- [x] Implement:
  - [ ] `add_terciles(...)`
  - [ ] `summarize_terciles(...)`

```python
from __future__ import annotations

import pandas as pd


def add_terciles(
    table: pd.DataFrame,
    *,
    metric_col: str,
    output_col: str,
) -> pd.DataFrame:
    """Add within-group terciles."""
    result = table.copy()
    result[output_col] = (
        result.groupby(["frequency", "horizon"])[metric_col]
        .transform(lambda s: pd.qcut(s, 3, labels=["low", "mid", "high"], duplicates="drop"))
    )
    return result


def summarize_terciles(
    table: pd.DataFrame,
    *,
    tercile_col: str,
) -> pd.DataFrame:
    """Summarize sMAPE by tercile."""
    return (
        table.groupby(["frequency", "model_name", "horizon", tercile_col], dropna=False)["smape"]
        .median()
        .reset_index()
        .rename(columns={"smape": "median_smape"})
    )
```
