# 37. Download All Paper Datasets (P0)

> **Priority**: P0 — blocking. Without real data the benchmark panel results are meaningless.

## Problem

The benchmark panel currently runs on **3 synthetic series** hardcoded in
`scripts/run_benchmark_panel.py::_make_panel_series()`. The `configs/benchmark_panel.yaml`
has `source: synthetic`. The `load_m4_subset()` function in `datasets.py` can generate mock
data via `allow_mock=True`, but no real M4 CSV files exist under `data/raw/m4/`.

The paper (arXiv 2601.10006) uses **two kinds of data**:

1. **Canonical illustrative examples** (Figure 2, interpretive only):
   - Sine wave (generated)
   - AirPassengers (classic dataset)
   - Hénon map (generated)
   - Simulated stock returns (generated)

2. **M4 competition benchmark panel** — **1,350 series** across **all six frequencies**:

| Frequency | M4 total | Paper survivor target | Hmax | Seasonal period |
|-----------|----------|----------------------|------|-----------------|
| Yearly    | 23,000   | 300                  | 6    | 1               |
| Quarterly | 24,000   | 300                  | 8    | 4               |
| Monthly   | 48,000   | 300                  | 18   | 12              |
| Weekly    | 359      | 150                  | 13   | 52              |
| Daily     | 4,227    | 200                  | 14   | 7               |
| Hourly    | 414      | 100                  | 48   | 24              |

We need **all** of the above persisted to `data/raw/` for the analysis to match the paper.

## What to do

### Part A — Canonical examples (simple, generated/loaded)

- [ ] Write `scripts/download_data.py` (single script for ALL data)
- [ ] Save canonical series to `data/raw/canonical/` as individual CSVs
- [ ] These are generated or loaded in code but should be persisted so `data/raw/` is a
      complete snapshot of every input series

### Part B — M4 competition data (downloaded)

- [ ] Download **all six** M4 frequency subsets from the M4 GitHub repository
- [ ] Convert to the format expected by `load_m4_subset()`: CSV with columns `unique_id`, `timestamp`, `y`
- [ ] Save to `data/raw/m4/{Frequency}.csv` for each of the six frequencies
- [ ] Update `configs/benchmark_panel.yaml` to use `source: m4_subset` with all six frequencies
- [ ] Add `.gitignore` exclusions for the large CSVs

## Expected file layout after running the script

```
data/raw/
├── canonical/
│   ├── sine_wave.csv          # columns: timestamp, y
│   ├── air_passengers.csv     # columns: timestamp, y
│   ├── henon_map.csv          # columns: timestamp, y
│   └── stock_returns.csv      # columns: timestamp, y
└── m4/
    ├── Yearly.csv             # columns: unique_id, timestamp, y
    ├── Quarterly.csv
    ├── Monthly.csv
    ├── Weekly.csv
    ├── Daily.csv
    └── Hourly.csv
```

## Expected M4 file format

`load_m4_subset()` in `src/forecastability/datasets.py` expects:

```
data/raw/m4/{Frequency}.csv
```

with columns:

| Column | Type | Description |
|--------|------|-------------|
| `unique_id` | str | M4 series ID (e.g. `M0001`) |
| `timestamp` | int | Integer time index (0, 1, 2, …) |
| `y` | float | Observed value |

Canonical CSVs use the simpler format:

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | int | Integer time index (0, 1, 2, …) |
| `y` | float | Observed value |

## Download script

Create `scripts/download_data.py` (replaces the old M4-only plan):

```python
"""Download and persist ALL datasets used in the analysis.

Part A: Canonical illustrative examples (generated/loaded, saved for reproducibility).
Part B: M4 competition training data across all six frequencies.
"""

from __future__ import annotations

from pathlib import Path
from urllib.request import urlretrieve

import numpy as np
import pandas as pd

from forecastability.utils.datasets import (
    generate_gaussian_returns,
    generate_henon_map,
    generate_sine_wave,
    load_air_passengers,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_CANONICAL_DIR = Path("data/raw/canonical")
_M4_DIR = Path("data/raw/m4")

# ---------------------------------------------------------------------------
# M4 GitHub raw URLs for training data — ALL six frequencies
# ---------------------------------------------------------------------------
_M4_URLS: dict[str, str] = {
    "Yearly": "https://raw.githubusercontent.com/Mcompetitions/M4-methods/master/Dataset/Train/Yearly-train.csv",
    "Quarterly": "https://raw.githubusercontent.com/Mcompetitions/M4-methods/master/Dataset/Train/Quarterly-train.csv",
    "Monthly": "https://raw.githubusercontent.com/Mcompetitions/M4-methods/master/Dataset/Train/Monthly-train.csv",
    "Weekly": "https://raw.githubusercontent.com/Mcompetitions/M4-methods/master/Dataset/Train/Weekly-train.csv",
    "Daily": "https://raw.githubusercontent.com/Mcompetitions/M4-methods/master/Dataset/Train/Daily-train.csv",
    "Hourly": "https://raw.githubusercontent.com/Mcompetitions/M4-methods/master/Dataset/Train/Hourly-train.csv",
}

# Paper Section 3.2 — survivor target counts per frequency
_PAPER_TARGETS: dict[str, int] = {
    "Yearly": 300,
    "Quarterly": 300,
    "Monthly": 300,
    "Weekly": 150,
    "Daily": 200,
    "Hourly": 100,
}

# Paper Section 3.1 — maximum forecast horizon per frequency
_PAPER_HMAX: dict[str, int] = {
    "Yearly": 6,
    "Quarterly": 8,
    "Monthly": 18,
    "Weekly": 13,
    "Daily": 14,
    "Hourly": 48,
}


# ---------------------------------------------------------------------------
# Part A — Canonical illustrative examples
# ---------------------------------------------------------------------------
def _save_canonical() -> None:
    """Generate and save all four canonical illustrative series."""
    _CANONICAL_DIR.mkdir(parents=True, exist_ok=True)

    examples: dict[str, np.ndarray] = {
        "sine_wave": generate_sine_wave(
            n_points=240, period=24, noise_std=0.05, random_state=42
        ),
        "air_passengers": load_air_passengers(),
        "henon_map": generate_henon_map(n_points=240, random_state=42),
        "stock_returns": generate_gaussian_returns(
            n_points=400, drift=0.0, volatility=0.02, random_state=42
        ),
    }

    for name, values in examples.items():
        out_path = _CANONICAL_DIR / f"{name}.csv"
        if out_path.exists():
            print(f"  {out_path} already exists, skipping.")
            continue
        df = pd.DataFrame({"timestamp": range(len(values)), "y": values})
        df.to_csv(out_path, index=False)
        print(f"  Saved {out_path} ({len(values)} points)")


# ---------------------------------------------------------------------------
# Part B — M4 competition data
# ---------------------------------------------------------------------------
def _download_and_convert_m4(frequency: str, url: str) -> None:
    """Download one M4 frequency file and convert to long format."""
    _M4_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _M4_DIR / f"{frequency}.csv"
    if out_path.exists():
        print(f"  {out_path} already exists, skipping download.")
        return

    tmp_path = _M4_DIR / f"{frequency}_raw.csv"
    print(f"  Downloading {frequency} from {url} ...")
    urlretrieve(url, tmp_path)  # noqa: S310  — trusted, hardcoded URL

    # M4 CSVs: rows = series, columns = V1, V2, ..., VN (wide format)
    # First column is the series ID (e.g. "M1", "M2", ...)
    wide = pd.read_csv(tmp_path)
    id_col = wide.columns[0]

    rows: list[dict[str, str | int | float]] = []
    for _, row in wide.iterrows():
        uid = str(row[id_col])
        values = row.iloc[1:].dropna().to_numpy(dtype=float)
        for t, value in enumerate(values):
            rows.append({"unique_id": uid, "timestamp": t, "y": float(value)})

    pd.DataFrame(rows).to_csv(out_path, index=False)
    tmp_path.unlink()
    n_series = wide.shape[0]
    print(f"  Saved {out_path} ({n_series} series, {len(rows)} rows)")


def main() -> None:
    """Download and persist all datasets."""
    print("=== Part A: Canonical illustrative examples ===")
    _save_canonical()

    print("\n=== Part B: M4 competition data (all 6 frequencies) ===")
    for frequency, url in _M4_URLS.items():
        _download_and_convert_m4(frequency, url)

    print("\n=== Paper reference ===")
    print("Frequency  | Survivor target | Hmax")
    for freq in _M4_URLS:
        print(f"  {freq:<11}| {_PAPER_TARGETS[freq]:<16}| {_PAPER_HMAX[freq]}")
    print("\nDone. All data is in data/raw/")


if __name__ == "__main__":
    main()
```

> [!IMPORTANT]
> Verify the actual column layout of the M4 CSV after download. The first column
> in the raw M4 CSVs is typically `V1` (the series ID). Adjust `id_col` parsing
> if the header differs. Print `wide.head()` to inspect before converting.

> [!NOTE]
> The canonical example generators (`generate_sine_wave`, `generate_henon_map`, etc.)
> are imported from `src/forecastability/datasets.py`. Check the exact function names
> match — the plan file [13_canonical_datasets.md](./13_canonical_datasets.md) has the
> original signatures, and the actual `datasets.py` may use slightly different names
> (e.g. `generate_gaussian_returns` vs `generate_simulated_stock_returns`). Verify with:
> ```bash
> grep "^def " src/forecastability/datasets.py
> ```

## Config update

After the CSVs exist, update `configs/benchmark_panel.yaml`:

```yaml
# BEFORE
data:
  source: synthetic
  frequencies: [Monthly]
  n_series_per_frequency: 20

# AFTER — all six frequencies, matching paper survivor targets
data:
  source: m4_subset
  frequencies: [Yearly, Quarterly, Monthly, Weekly, Daily, Hourly]
  n_series_per_frequency: 225
  # Paper targets: Y=300, Q=300, M=300, W=150, D=200, H=100
  # Start with 225 (= 1350 / 6) to match the paper's 1,350 total.
  # Some frequencies have fewer available series (Weekly=359, Hourly=414),
  # so the actual count will be min(n_series_per_frequency, available).

# ALSO update horizons to match the paper's Hmax per frequency.
# The current config uses horizons: [1..18] for all frequencies.
# Ideally, horizons should be frequency-specific (see note below).
rolling_origin:
  n_origins: 10
  horizons: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
  # NOTE: The paper uses frequency-specific Hmax:
  #   Yearly: 6, Quarterly: 8, Monthly: 18,
  #   Weekly: 13, Daily: 14, Hourly: 48
  # The runner should cap horizons to min(max(horizons), Hmax_for_freq).
  # See plan 38 for the runner code change needed.
```

> [!NOTE]
> **Frequency-specific horizons**: The paper caps horizons per frequency. The runner
> `scripts/run_benchmark_panel.py` currently applies the same horizon list to all
> series. You need to either:
> (a) add per-frequency horizon caps to the config, or
> (b) filter horizons in the runner based on `_PAPER_HMAX` constants.
> Option (b) is simpler — add a dict at the top of the runner and slice before calling
> `run_rolling_origin_evaluation()`.

## .gitignore update

Add to the project `.gitignore`:

```gitignore
# Downloaded data (large CSVs, regenerate locally)
data/raw/m4/*.csv
data/raw/canonical/*.csv
```

## Verification

After running the download script:

```bash
uv run python scripts/download_data.py
```

### Part A — Canonical examples

- [ ] `data/raw/canonical/sine_wave.csv` exists with 240 rows
- [ ] `data/raw/canonical/air_passengers.csv` exists with 144 rows
- [ ] `data/raw/canonical/henon_map.csv` exists with 240 rows
- [ ] `data/raw/canonical/stock_returns.csv` exists with 400 rows
- [ ] Each CSV has exactly 2 columns: `timestamp`, `y`
- [ ] No NaN values

### Part B — M4 data (all six frequencies)

- [ ] `data/raw/m4/Yearly.csv` exists and has ≥ 300 unique `unique_id` values
- [ ] `data/raw/m4/Quarterly.csv` exists and has ≥ 300 unique `unique_id` values
- [ ] `data/raw/m4/Monthly.csv` exists and has ≥ 300 unique `unique_id` values
- [ ] `data/raw/m4/Weekly.csv` exists and has ≥ 150 unique `unique_id` values
- [ ] `data/raw/m4/Daily.csv` exists and has ≥ 200 unique `unique_id` values
- [ ] `data/raw/m4/Hourly.csv` exists and has ≥ 100 unique `unique_id` values
- [ ] Each M4 CSV has exactly 3 columns: `unique_id`, `timestamp`, `y`
- [ ] No NaN values in the `y` column

Quick verification one-liner:

```bash
uv run python -c "
import pandas as pd
print('=== Canonical ===')
for name in ['sine_wave', 'air_passengers', 'henon_map', 'stock_returns']:
    df = pd.read_csv(f'data/raw/canonical/{name}.csv')
    print(f'  {name}: {len(df)} rows, NaN={df[\"y\"].isna().sum()}')

print('=== M4 ===')
for f in ['Yearly', 'Quarterly', 'Monthly', 'Weekly', 'Daily', 'Hourly']:
    df = pd.read_csv(f'data/raw/m4/{f}.csv')
    print(f'  {f}: {df[\"unique_id\"].nunique()} series, {len(df)} rows, NaN={df[\"y\"].isna().sum()}')
"
```

## Paper reference summary

| Aspect | Paper specification |
|--------|-------------------|
| **Canonical examples** | Sine wave, AirPassengers, Hénon map, simulated stock returns — interpretive only (Figure 2) |
| **Benchmark data** | M4 competition, 6 frequencies, 1,350 total survivor series |
| **Survivor targets** | Y=300, Q=300, M=300, W=150, D=200, H=100 |
| **Horizons (Hmax)** | Y=6, Q=8, M=18, W=13, D=14, H=48 |
| **Rolling origins** | 10 per series, expanding window |
| **Probe models** | Seasonal Naïve, ETS, N-BEATS |
| **MI estimator** | kNN, k=8 |
| **Error metric** | sMAPE (0–200 scale) |
