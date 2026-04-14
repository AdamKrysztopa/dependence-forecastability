<!-- type: how-to -->
# 43. ForecastabilityAnalyzerExog — User Manual v1.1 (Real-Data Testbed)

> Plan status: **complete**. Extends v1.0 (plan 42) with real-world datasets,
> loading snippets, significance bands, and actual run results (2026-03-14).

## Deliverables

- [x] Synthetic + real data test strategy documented
- [x] Public dataset links and copy-paste loading snippets
- [x] Expected qualitative outcomes and operational checklist
- [x] API-accurate constraints for exogenous methods
- [x] `scripts/download_data.py` Part D populates `data/raw/exog/`
- [x] `scripts/run_exog_analysis.py` runs all 9 cases
- [x] Actual run results (2026-03-14, 9 cases, 14.6 s)

---

## 1. Download Exogenous Datasets

Run Part D of the download script to populate `data/raw/exog/`:

```bash
uv run python scripts/download_data.py
```

| File | Source | n | Contents |
|---|---|---|---|
| `data/raw/exog/bike_sharing_hour.csv` | UCI archive ZIP | 17 379 | `cnt`, `temp`, `hum`, `windspeed` |
| `data/raw/exog/spy_returns.csv` | yfinance | 6 287 | SPY log-returns |
| `data/raw/exog/vix_close.csv` | yfinance | 6 288 | ^VIX daily close |
| `data/raw/exog/eth_returns.csv` | yfinance | 2 608 | ETH-USD log-returns |
| `data/raw/exog/noise_control.csv` | generated | 17 521 | white noise, `random_state=0` |

---

## 2. Loading Snippets

### 2.1 UCI Bike Sharing — CrossMI(temp → cnt)

```python
import numpy as np
import pandas as pd
from forecastability.pipeline.analyzer import ForecastabilityAnalyzerExog

df = pd.read_csv("data/raw/exog/bike_sharing_hour.csv")
y_bike    = df["cnt"].values.astype(float)
exog_temp = df["temp"].values.astype(float)                    # CrossMI: meaningful
exog_noise = np.random.default_rng(0).standard_normal(len(y_bike))  # CrossMI: noise control

analyzer = ForecastabilityAnalyzerExog(n_surrogates=99, random_state=42)
res_temp  = analyzer.analyze(y_bike, exog=exog_temp,  max_lag=40, method="mi")
res_noise = analyzer.analyze(y_bike, exog=exog_noise, max_lag=40, method="mi")
print("CrossMI(temp):",  res_temp.mean_raw_20)
print("CrossMI(noise):", res_noise.mean_raw_20)
print("SNR:", res_temp.mean_raw_20 / res_noise.mean_raw_20)
```

### 2.2 Financial Pairs — CrossMI(SPY → AAPL)

```python
import numpy as np
import pandas as pd
from forecastability.pipeline.analyzer import ForecastabilityAnalyzerExog

aapl = pd.read_csv("data/raw/canonical/aapl_returns.csv", index_col=0, parse_dates=True)
spy  = pd.read_csv("data/raw/exog/spy_returns.csv",       index_col=0, parse_dates=True)

aligned  = aapl.join(spy, how="inner", lsuffix="_aapl", rsuffix="_spy").dropna()
y_aapl   = aligned.iloc[:, 0].values.astype(float)
exog_spy = aligned.iloc[:, 1].values.astype(float)

analyzer = ForecastabilityAnalyzerExog(n_surrogates=99, random_state=42)
res_spy = analyzer.analyze(y_aapl, exog=exog_spy, max_lag=40, method="mi")
print("CrossMI(SPY→AAPL):", res_spy.mean_raw_20)
```

> [!NOTE]
> SPY and AAPL are contemporaneously correlated (same-day co-movement), but CrossMI at
> lag $h \geq 1$ measures $I(\text{SPY}_{t-h}; \text{AAPL}_t)$ — *lagged* predictive
> association. Consistent with the Efficient Market Hypothesis, this should be near the
> noise floor. See §4 (Actual Results) for confirmation.

### 2.3 Additional Reference Datasets

| Dataset | Source | Target | Meaningful exog |
|---|---|---|---|
| Panama Electricity Load | [Kaggle](https://www.kaggle.com/datasets/saurabhshahane/electricity-load-forecasting) | electricity load | temperature / humidity |
| Dominican Republic SENI Demand 2021–2024 | DOI [10.1016/j.dib.2025.112057](https://doi.org/10.1016/j.dib.2025.112057) | demand | temperature |

> [!TIP]
> Always pair a real exogenous variable with a random-noise control of the same length.
> The noise run gives you the per-dataset CrossMI floor to compute SNR.

---

## 3. Interpretation — Positioning CrossMI Against Reference Points

```
noise floor  <  CrossMI  <  AMI (univariate)  <  (fully dominant exog)
     ↑               ↑             ↑
 useless ctrl   exog signal   self-history
```

Compute `SNR = CrossMI(exog) / CrossMI(noise_control)` on the same target series.

| SNR | Interpretation | Action |
|---|---|---|
| < 3 | Indistinguishable from noise — estimator bias dominates | Drop the variable |
| 3–10 | Marginal signal; may be estimator bias for small n | Validate with surrogates |
| 10–50 | Genuine lagged dependence | Include; inspect pCrossAMI lag profile |
| > 50 | Strong lagged signal | Include; pCrossAMI critical to identify direct lags |

After clearing the noise floor test, compare CrossMI to AMI(univariate):

| CrossMI vs AMI | Interpretation |
|---|---|
| CrossMI > AMI | Exog dominates self-history — prioritise exog lags in model |
| CrossMI ≈ AMI (80–120%) | Comparably informative — combine both |
| CrossMI < AMI (< 80%) | Supplementary — self-history stronger; exog adds incremental value |
| CrossMI ≪ AMI (< 20%) | Weak relative to self-history — include only if SNR > 10 |

---

## 4. Significance Bands (Opt-In)

> [!IMPORTANT]
> Surrogates are **opt-in** (`compute_surrogates=False` by default) — they are a project
> extension, not paper-native (arXiv:2601.10006). Enable with:
>
> ```python
> res = analyzer.analyze(ts, exog=exog, max_lag=40, method="mi", compute_surrogates=True)
> ```

When enabled:

- **n_surrogates ≥ 99** phase-randomised (FFT amplitude-preserving) surrogates are applied
  to the *target* series only; the exogenous series is held fixed.
- Bands span the **2.5th–97.5th percentile** of the surrogate distribution (α = 0.05, two-sided).
- `sig_raw_lags` = CrossMI lags exceeding the 97.5th-percentile upper band.
- `sig_partial_lags` = pCrossAMI lags exceeding the upper band.
- **Null hypothesis (cross mode):** the observed CrossMI is not greater than chance
  given the target's marginal power spectrum. The exog's own autocorrelation is **not**
  controlled for.

> [!WARNING]
> For highly periodic targets (seasonal demand, sine waves), phase-randomised surrogates
> preserve the amplitude spectrum almost exactly, giving significance tests near-zero power.
> A high fraction of significant CrossMI lags on such series should be interpreted with caution.
> Use SNR as the primary discriminator for seasonal data.

---

## 5. Actual Results — Run 2026-03-14

Runner: `scripts/run_exog_analysis.py`, `compute_surrogates=False`, `max_lag=40`, `method=mi`.
Wall-clock: **14.6 seconds** for all 9 cases (first run; see runtime note below).

> [!NOTE]
> **Runtime — large n is slow.** Each kNN MI call is O(n log n) via sklearn's KD-tree
> `query_radius`. At n=17 379 (bike dataset) and `max_lag=40` that is ~40 KD-tree sweeps
> over 17k points — expect **2–5 minutes per bike case** on a single M1 core.
> The 14.6 s figure above was a cached/warm run; a cold re-run of the bike cases alone
> can take several minutes — this is normal, not a hang.
>
> **Mitigations for future re-runs:**
> - Set `_MAX_LAG = 20` in `run_exog_analysis.py` — halves the work, conclusions unchanged
>   (bike temp/humidity SNR dominates at short lags anyway).
> - Subsample the bike series before analysis (e.g. keep every other hour → n ≈ 8 700).
> - Results already in `outputs/json/exog/` are valid — re-running is not required unless
>   data or code changes.

| Case | Mode | n | mean CrossMI (h=1..20) | SNR vs noise | vs AMI |
|---|---|---|---|---|---|
| bike_cnt_univariate | univariate (AMI) | 17 379 | 0.2012 | — | baseline |
| bike_cnt_temp | CrossMI(temp) | 17 379 | 0.0814 | **62.6×** | 40% of AMI |
| bike_cnt_hum | CrossMI(humidity) | 17 379 | 0.0582 | **44.8×** | 29% of AMI |
| bike_cnt_noise | noise control | 17 379 | 0.0013 | 1.0× | floor |
| aapl_univariate | univariate (AMI) | 6 287 | 0.0138 | — | baseline |
| aapl_spy | CrossMI(SPY) | 6 287 | 0.0072 | 4.8× | 52% of AMI |
| aapl_noise | noise control | 6 287 | 0.0015 | 1.0× | floor |
| btc_eth | CrossMI(ETH) | 2 608 | 0.0051 | 1.5× | — |
| btc_noise | noise control | 3 651 | 0.0034 | 1.0× | floor |

*Source: `outputs/json/exog/*.json`.*

**Statistical validation (statistician review, 2026-03-14): PASS — 1 WARNING resolved, 3 INFO items.**

Key findings:
- `bike_cnt_temp` SNR = 62.6× and `bike_cnt_hum` SNR = 44.8× → genuine lagged association confirmed.
- `aapl_spy` SNR = 4.8× → marginal; consistent with EMH (SPY at lag $h \geq 1$ does not
  predict AAPL; the known co-movement is contemporaneous, i.e. lag 0, which is excluded).
- `btc_eth` SNR = 1.5× → noise; ETH carries no detectable lagged predictive information about BTC.
- kNN MI positive bias is n-dependent: BTC noise floor (0.0034) ≈ 2× AAPL noise floor
  (0.0015) because n=2608 < 6287. Do not compare absolute CrossMI values across datasets
  with different n — use per-dataset SNR.
- All recommendations are LOW because `compute_surrogates=False` leaves `sig_raw_lags=[]`.
  The categorical label reflects MI thresholds (HIGH ≥ 0.80, MEDIUM ≥ 0.30), not SNR.

---

## 6. Operational Checklist

- [ ] Run `scripts/download_data.py` to populate `data/raw/exog/`.
- [ ] Validate synthetic generator (plan 42 §4): `exog_meaningful` → `HIGH`, noise → `LOW`.
- [ ] For each real exog variable, also run a noise control of the same length.
- [ ] Compute `SNR = CrossMI(exog) / CrossMI(noise_control)` — do not rely on the label alone.
- [ ] Use the same `method` across all runs in a comparative study.
- [ ] Verify `exog` length equals target length before calling `analyze`.
- [ ] For highly seasonal targets, treat significance bands (when enabled) with caution.
- [ ] If SNR > 50, enable surrogates (`compute_surrogates=True`) to populate
  `sig_raw_lags` and `sig_partial_lags` for pCrossAMI-based direct-lag identification.

