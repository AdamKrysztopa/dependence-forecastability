# 38. Re-run Benchmark Panel on Real M4 Data and Verify Results (P1)

> **Priority**: P1 — depends on P0 (plan 37, real M4 data must exist first).

## ⚠️ Runtime Problem — Benchmark Skipped

The M4 benchmark run was **killed intentionally** after ~90 minutes without completing.

**Why it was slow (before the surrogate opt-in change):**
- Old behaviour: 10 rolling origins × up to 24 horizons × (AMI + pAMI + 99 surrogates × 2) per series
  = ~24,000 kNN MI evaluations per series → ~2.9 million kNN queries for 120 series

**Current behaviour (`compute_surrogates=False` is the default):**
- Surrogates are **off by default** — they are a project extension, not paper-native.
  See `scripts/run_benchmark_panel.py` (`_COMPUTE_SURROGATES` constant).
- Per series: 10 rolling origins × up to 24 horizons × (AMI + pAMI) only
  = ~480 kNN MI evaluations per series
- Total: ~58,000 kNN queries for 120 series
- Wall-clock estimate on a single M1 core: **5–15 minutes** (down from 3–5 hours)

**What still needs to be run (in order):**

```bash
# Option A — quick pass (reduce series count first):
# Edit configs/benchmark_panel.yaml: n_series_per_frequency: 5
MPLBACKEND=Agg uv run python scripts/run_benchmark_panel.py

# Option B — full paper-aligned run (overnight):
MPLBACKEND=Agg uv run python scripts/run_benchmark_panel.py

# After benchmark completes:
MPLBACKEND=Agg uv run python scripts/build_report_artifacts.py
```

**Current state of `outputs/tables/`:**
- `horizon_table.csv` — **STALE**: contains only 3 synthetic series from a pre-M4 run.
  All downstream rank/tercile tables are also stale.
- Do NOT use these tables for the final report without re-running.

**To reduce runtime for a smoke test**, set `n_series_per_frequency: 3` or `5` in
`configs/benchmark_panel.yaml`. That gives ~15–30 series — enough to produce
non-trivial Spearman ρ while running in <10 minutes.

---

## Problem (original)

The current benchmark results are based on **3 synthetic series**. This is too few to produce
meaningful Spearman rank correlations — the current `rank_associations.csv` shows values like
`-1.0`, `-0.5`, `0.5` because you cannot meaningfully rank 3 data points. The paper uses
**1,350 M4 series across all six frequencies** (Yearly, Quarterly, Monthly, Weekly, Daily, Hourly).

## What to do

- [x] Confirm all six M4 CSV files exist in `data/raw/m4/` (from plan 37)
- [x] Confirm canonical CSVs exist in `data/raw/canonical/` (from plan 37)
- [x] Update `configs/benchmark_panel.yaml` (see plan 37 for the config change)
- [x] Add frequency-specific horizon caps to the runner (see below)
- [ ] Re-run the benchmark panel *(was killed after ~90 min — too slow, see above)*
- [ ] Verify the outputs
- [ ] Have the statistician agent review Spearman results

**Canonical examples:** All 8 series complete. See `outputs/json/canonical/` and `outputs/figures/canonical/`.
`crude_oil_returns` has `directness_ratio=8.276` — ARCH-suspected class added to interpretation.py; theory.md updated. See `## Edge Case: pAMI > AMI (Volatility Clustering)` in docs/theory.md.

## Frequency-specific horizon caps

The paper uses different maximum horizons per frequency. Add this to the top of
`scripts/run_benchmark_panel.py` and filter horizons before each series:

```python
# Paper Section 3.1 — maximum forecast horizon by frequency
_HMAX: dict[str, int] = {
    "yearly": 6,
    "quarterly": 8,
    "monthly": 18,
    "weekly": 13,
    "daily": 14,
    "hourly": 48,
}
```

Then in the loop where `run_rolling_origin_evaluation` is called, cap the horizons:

```python
    for series_id, frequency, seasonal_period, ts in panel:
        hmax = _HMAX.get(frequency, max(rolling_cfg.horizons))
        series_horizons = [h for h in rolling_cfg.horizons if h <= hmax]
        result = run_rolling_origin_evaluation(
            ts,
            series_id=series_id,
            frequency=frequency,
            horizons=series_horizons,  # <-- capped
            ...
        )
```

## Execution

```bash
# Step 1: Ensure dependencies are installed
uv sync

# Step 2: Re-run the benchmark panel
MPLBACKEND=Agg uv run python scripts/run_benchmark_panel.py

# Step 3: Re-build the report artifacts
MPLBACKEND=Agg uv run python scripts/build_report_artifacts.py
```

> [!NOTE]
> With `compute_surrogates=False` (the default), expect **5–15 minutes** for
> `n_series_per_frequency=20` on an M1 Mac. The old 3–5 hour estimate assumed surrogates
> enabled for every series and origin — that is no longer the default.
>
> To enable surrogates for a subset of series (optional validation), set
> `_COMPUTE_SURROGATES = True` in `scripts/run_benchmark_panel.py`.
> That will restore the longer runtime. Parallelisation (`ProcessPoolExecutor` /
> `ThreadPoolExecutor`) is already in place when surrogates are enabled.

## Post-run verification checklist

After `run_benchmark_panel.py`:

- [ ] `outputs/tables/horizon_table.csv` has rows for all 6 frequencies (Yearly, Quarterly, Monthly, Weekly, Daily, Hourly)
- [ ] Row count: at least `n_series_per_frequency × len(horizons) × n_models` per frequency
- [ ] `series_id` column contains real M4 IDs (e.g. `M0042`) not synthetic names
- [ ] No NaN values in `ami`, `pami`, or `smape` columns

Quick verification:

```python
import pandas as pd

ht = pd.read_csv("outputs/tables/horizon_table.csv")
print(f"Total rows: {len(ht)}")
print(f"Series: {ht['series_id'].nunique()}")
print(f"Frequencies:\n{ht['frequency'].value_counts()}")
print(f"NaN counts:\n{ht[['ami', 'pami', 'smape']].isna().sum()}")
print(f"\nSample series IDs: {ht['series_id'].unique()[:5]}")
```

After `build_report_artifacts.py`:

- [ ] `outputs/tables/rank_associations.csv` has meaningful Spearman values (not all -1.0)
- [ ] `outputs/tables/ami_terciles.csv` has 3 distinct tercile groups with reasonable counts
- [ ] `outputs/tables/pami_terciles.csv` has 3 distinct tercile groups with reasonable counts
- [ ] `outputs/figures/frequency_panel.png` shows bars for Monthly, Quarterly, and Yearly
- [ ] `outputs/figures/rank_association_delta.png` shows meaningful delta values

Rank association quality check:

```python
import pandas as pd

ra = pd.read_csv("outputs/tables/rank_associations.csv")
print(ra.describe())

# Flag if all correlations are extreme (-1 or 1) — suggests too few series
extreme = ra[["spearman_ami_smape", "spearman_pami_smape"]].abs().eq(1.0).mean()
print(f"\nFraction of extreme correlations:\n{extreme}")
# Should be < 0.5; if > 0.8, increase n_series_per_frequency
```

## Statistician review points

After results are generated, the statistician should verify:

1. **H5**: Spearman ρ(AMI, sMAPE) ≠ 0 — there should be a negative correlation
   (higher AMI → lower sMAPE) for at least some model/horizon combinations
2. **Delta (pAMI - AMI)**: look for horizons where pAMI rank correlation with sMAPE
   is stronger (more negative) than AMI — this is the "pAMI adds value" evidence
3. **Tercile separation**: the top AMI tercile should have systematically lower sMAPE
   than the bottom tercile — if not, investigate whether the series panel is too
   homogeneous
4. **Directness ratio distribution**: across M4 series, `directness_ratio` should vary
   (not all near 0 or all near 1)

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `FileNotFoundError: Missing cached M4 file` | M4 CSVs not downloaded | Run plan 37 first |
| `ValueError: Requested 20 series but cache has only N` | Too few series in CSV | Increase download or reduce `n_series_per_frequency` |
| All sMAPE values are very large (> 100) | Series may need log transform or different model | Check if Yearly series are very short |
| Script runs out of memory | Too many series × horizons × origins | Reduce `n_series_per_frequency` to 10 |
| ETS fails on some series | Numerical convergence issues | Expected — ETS returns NaN, pipeline handles gracefully |
