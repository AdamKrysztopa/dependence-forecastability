# 41. Expand Benchmark Panel for Robustness (P4)

> **Priority**: P4 — optional, do after P0-P2 are confirmed working.

## Problem

Even with real M4 data (plan 37), the default config uses only **20 series per frequency**.
The paper uses a broader panel. More series → more stable Spearman correlations and more
convincing tercile analysis.

Additionally, the current config only includes `naive` and `ets` models. Adding
`seasonal_naive` provides a stronger baseline comparison, and optionally including
`lightgbm_autoreg` (if the package is installed) would test ML model performance.

## What to do

- [ ] Increase `n_series_per_frequency` in `configs/benchmark_panel.yaml`
- [ ] Consider adding Daily and/or Weekly M4 frequencies
- [ ] Enable `seasonal_naive` model if not already active
- [ ] Optionally enable `lightgbm_autoreg` if LightGBM is installed
- [ ] Re-run benchmark and verify robustness

## Config changes

### Option A: Moderate expansion (recommended first pass)

```yaml
data:
  source: m4_subset
  frequencies: [Monthly, Quarterly, Yearly]
  n_series_per_frequency: 40

models:
  include_lightgbm_autoreg: false
  include_nbeats: false
```

### Option B: Full expansion (final run)

```yaml
data:
  source: m4_subset
  frequencies: [Monthly, Quarterly, Yearly]
  n_series_per_frequency: 80

rolling_origin:
  n_origins: 10
  horizons: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]

models:
  include_lightgbm_autoreg: true
  include_nbeats: false
```

> [!WARNING]
> Option B with 80 series × 3 frequencies × 18 horizons × 10 origins will take
> a long time. Consider running overnight or on a fast machine.

## Additional M4 frequencies

If you want Weekly or Daily, you also need to:

1. Add the download URLs to `scripts/download_m4_data.py`:

```python
_M4_URLS["Weekly"] = "https://raw.githubusercontent.com/Mcompetitions/M4-methods/master/Dataset/Train/Weekly-train.csv"
_M4_URLS["Daily"] = "https://raw.githubusercontent.com/Mcompetitions/M4-methods/master/Dataset/Train/Daily-train.csv"
```

2. Add them to the config:

```yaml
frequencies: [Monthly, Quarterly, Yearly, Weekly, Daily]
```

3. Note that Weekly and Daily series are typically longer but may have different
   seasonal patterns. The seasonal period mapping in `datasets.py::m4_seasonal_period()`
   already supports Weekly (52) and Daily (7).

## Enabling LightGBM

If LightGBM is not currently installed:

```bash
uv add lightgbm
```

Then set in config:

```yaml
models:
  include_lightgbm_autoreg: true
```

The `models.py` module already has `forecast_lightgbm_autoreg()` with graceful import
fallback — it will skip if the package is missing.

## Verification after expansion

```python
import pandas as pd

ht = pd.read_csv("outputs/tables/horizon_table.csv")
print(f"Total rows: {len(ht)}")
print(f"Unique series: {ht['series_id'].nunique()}")
print(f"Frequencies: {ht['frequency'].value_counts().to_dict()}")
print(f"Models: {ht['model_name'].unique()}")

ra = pd.read_csv("outputs/tables/rank_associations.csv")
print(f"\nMean Spearman AMI: {ra['spearman_ami_smape'].mean():.3f}")
print(f"Mean Spearman pAMI: {ra['spearman_pami_smape'].mean():.3f}")
print(f"Mean delta: {ra['delta_pami_minus_ami'].mean():.3f}")

# With ≥ 40 series, extreme correlations should be rare
extreme = ra[["spearman_ami_smape", "spearman_pami_smape"]].abs().eq(1.0).mean()
print(f"\nFraction extreme values: {extreme.mean():.2f} (should be < 0.2)")
```

- [ ] `n_series_per_frequency` × number of frequencies ≥ 60 total series
- [ ] Fraction of extreme Spearman values < 0.2
- [ ] All 3+ frequencies present in `frequency_panel_summary.csv`
- [ ] If LightGBM enabled: `lightgbm` appears in `model_name` column
