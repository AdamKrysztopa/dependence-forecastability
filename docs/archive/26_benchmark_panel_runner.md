# 26. Benchmark Panel Runner

- [x] `scripts/run_benchmark_panel.py` must support:
  - [ ] one or more time series
  - [ ] frequency metadata
  - [ ] seasonal period
  - [ ] `10` origins
  - [ ] per-horizon aggregation
  - [ ] saved tables

```python
from __future__ import annotations

from pathlib import Path
import pandas as pd

from forecastability.aggregation import (
    add_terciles,
    build_horizon_table,
    compute_rank_associations,
    summarize_terciles,
)
from forecastability.datasets import load_air_passengers
from forecastability.pipeline import run_rolling_origin_evaluation


def main() -> None:
    """Run rolling-origin benchmark on a small starter panel."""
    output_root = Path("outputs")
    tables_dir = output_root / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    # Replace with real panel loader later.
    panel = [
        {
            "series_id": "air_passengers",
            "frequency": "monthly",
            "seasonal_period": 12,
            "ts": load_air_passengers(),
        },
    ]

    results = []
    for item in panel:
        result = run_rolling_origin_evaluation(
            item["ts"],
            series_id=item["series_id"],
            frequency=item["frequency"],
            horizons=list(range(1, 13)),
            n_origins=10,
            seasonal_period=item["seasonal_period"],
            random_state=42,
        )
        results.append(result)

    horizon_table = build_horizon_table(results)
    horizon_table.to_csv(tables_dir / "horizon_table.csv", index=False)

    corr_table = compute_rank_associations(horizon_table)
    corr_table.to_csv(tables_dir / "rank_associations.csv", index=False)

    ami_terciles = add_terciles(horizon_table, metric_col="ami", output_col="ami_tercile")
    ami_summary = summarize_terciles(ami_terciles, tercile_col="ami_tercile")
    ami_summary.to_csv(tables_dir / "ami_terciles.csv", index=False)

    pami_terciles = add_terciles(horizon_table, metric_col="pami", output_col="pami_tercile")
    pami_summary = summarize_terciles(pami_terciles, tercile_col="pami_tercile")
    pami_summary.to_csv(tables_dir / "pami_terciles.csv", index=False)

    print("Benchmark panel run complete.")


if __name__ == "__main__":
    main()
```
