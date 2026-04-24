<!-- type: how-to -->
# Data Download Commands

Use these commands to fetch on-demand datasets that are referenced by manifests.

## Sunspots monthly series

```bash
uv run python scripts/download_data.py sunspots_monthly
```

This writes [data/processed/sunspots_monthly.csv](data/processed/sunspots_monthly.csv) with columns:
- `year`
- `month`
- `ssn`

The routing-validation real panel manifest references this file in [configs/routing_validation_real_panel.yaml](configs/routing_validation_real_panel.yaml).
