"""Download and persist ALL datasets used in the analysis.

Part A: Canonical illustrative examples (generated/loaded, saved for reproducibility).
Part B: M4 competition training data across all six frequencies.
Part C: Financial canonical series via yfinance.
Part D: Exogenous cross-dependence datasets (UCI Bike Sharing, financial pairs, synthetic noise).

Usage:
    uv run python scripts/download_data.py
    uv run python scripts/download_data.py sunspots_monthly
"""

from __future__ import annotations

import argparse
import io
import logging
import zipfile
from pathlib import Path
from urllib.request import (
    urlopen,  # noqa: S310 — all URLs are hardcoded/trusted
    urlretrieve,
)

import numpy as np
import pandas as pd
import yfinance as yf

from forecastability.utils.datasets import (
    generate_henon_map,
    generate_simulated_stock_returns,
    generate_sine_wave,
    load_air_passengers,
)

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_CANONICAL_DIR = Path("data/raw/canonical")
_M4_DIR = Path("data/raw/m4")
_EXOG_DIR = Path("data/raw/exog")
_PROCESSED_DIR = Path("data/processed")

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
        # 240 points, 10 cycles (period=24), slight noise — matches paper Figure 2
        "sine_wave": generate_sine_wave(
            n_samples=240, cycles=10.0, noise_std=0.05, random_state=42
        ),
        "air_passengers": load_air_passengers(),
        # 240 points (deterministic, no random_state param)
        "henon_map": generate_henon_map(n_samples=240),
        # 400 points, near-zero drift, 2% daily volatility
        "stock_returns": generate_simulated_stock_returns(
            n_samples=400, mean=0.0, std=0.02, random_state=42
        ),
    }

    for name, values in examples.items():
        out_path = _CANONICAL_DIR / f"{name}.csv"
        if out_path.exists():
            _logger.info("  %s already exists, skipping.", out_path)
            continue
        df = pd.DataFrame({"timestamp": range(len(values)), "y": values})
        df.to_csv(out_path, index=False)
        _logger.info("  Saved %s (%d points)", out_path, len(values))


# ---------------------------------------------------------------------------
# Part B — M4 competition data
# ---------------------------------------------------------------------------
def _download_and_convert_m4(frequency: str, url: str) -> None:
    """Download one M4 frequency file and convert to long format."""
    _M4_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _M4_DIR / f"{frequency}.csv"
    if out_path.exists():
        _logger.info("  %s already exists, skipping download.", out_path)
        return

    tmp_path = _M4_DIR / f"{frequency}_raw.csv"
    _logger.info("  Downloading %s from M4 GitHub repository ...", frequency)
    urlretrieve(url, tmp_path)  # noqa: S310 — trusted, hardcoded URL

    wide = pd.read_csv(tmp_path)
    id_col = str(wide.columns[0])
    long_df = (
        wide.rename(columns={id_col: "unique_id"})
        .melt(id_vars="unique_id", value_name="y")
        .dropna(subset=["y"])
    )
    long_df["unique_id"] = long_df["unique_id"].astype(str)
    long_df["timestamp"] = long_df.groupby("unique_id").cumcount()
    long_df["y"] = long_df["y"].astype(float)
    long_df.loc[:, ["unique_id", "timestamp", "y"]].to_csv(out_path, index=False)
    tmp_path.unlink()
    n_series = wide.shape[0]
    _logger.info("  Saved %s (%d series, %d rows)", out_path, n_series, len(long_df))


# ---------------------------------------------------------------------------
# Part C — Financial canonical series (daily log-returns)
# ---------------------------------------------------------------------------
_FINANCIAL_SPECS: dict[str, tuple[str, str, str]] = {
    "bitcoin_returns": ("BTC-USD", "2015-01-01", "2024-12-31"),
    "gold_returns": ("GC=F", "2000-01-01", "2024-12-31"),
    "crude_oil_returns": ("CL=F", "2000-01-01", "2024-12-31"),
    "aapl_returns": ("AAPL", "2000-01-01", "2024-12-31"),
}


def _download_close_prices(ticker: str, *, start: str, end: str) -> np.ndarray:
    """Download adjusted close prices and return as a flat float array."""
    frame = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    close = frame["Close"]
    if hasattr(close, "squeeze"):
        close = close.squeeze()
    return close.dropna().to_numpy(dtype=float).ravel()


def _download_financial_canonical() -> None:
    """Download financial canonical series via yfinance and save log-returns."""
    _CANONICAL_DIR.mkdir(parents=True, exist_ok=True)
    for name, (ticker, start, end) in _FINANCIAL_SPECS.items():
        out_path = _CANONICAL_DIR / f"{name}.csv"
        if out_path.exists():
            _logger.info("  %s already exists, skipping.", out_path)
            continue
        _logger.info("  Downloading %s (%s to %s) ...", ticker, start, end)
        try:
            prices = _download_close_prices(ticker, start=start, end=end)
            if prices.size < 100:
                _logger.warning("  Only %d points for %s, skipping.", prices.size, ticker)
                continue
            log_returns = np.diff(np.log(np.maximum(prices, 1e-8)))
            log_returns = log_returns[np.isfinite(log_returns)]
            result_df = pd.DataFrame({"timestamp": range(len(log_returns)), "y": log_returns})
            result_df.to_csv(out_path, index=False)
            _logger.info("  Saved %s (%d log-return points)", out_path, len(log_returns))
        except Exception as exc:  # noqa: BLE001
            _logger.warning("  Failed to download %s: %s", ticker, exc)


# ---------------------------------------------------------------------------
# Part D — Exogenous cross-dependence datasets
# ---------------------------------------------------------------------------
_BIKE_URL = (
    "https://archive.ics.uci.edu/ml/machine-learning-databases/00275/Bike-Sharing-Dataset.zip"
)

_EXOG_FINANCIAL_SPECS: dict[str, tuple[str, str, str, bool]] = {
    # name → (ticker, start, end, log_returns)
    "spy_returns": ("SPY", "2000-01-01", "2024-12-31", True),
    "vix_daily": ("^VIX", "2000-01-01", "2024-12-31", False),
    "eth_returns": ("ETH-USD", "2017-11-01", "2024-12-31", True),
}

_SUNSPOTS_MONTHLY_URL = "https://www.sidc.be/SILSO/DATA/SN_m_tot_V2.0.csv"


def _download_sunspots_monthly() -> None:
    """Download SIDC monthly sunspot data and persist a compact processed CSV."""
    _PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _PROCESSED_DIR / "sunspots_monthly.csv"
    if out_path.exists():
        _logger.info("  %s already exists, skipping.", out_path)
        return

    _logger.info("  Downloading SIDC monthly sunspot data ...")
    raw = pd.read_csv(
        _SUNSPOTS_MONTHLY_URL,
        sep=";",
        header=None,
        names=["year", "month", "decimal_date", "ssn", "std", "n_obs", "provisional"],
    )
    filtered = raw[["year", "month", "ssn"]].copy()
    filtered = filtered.dropna(subset=["ssn"])
    filtered["ssn"] = filtered["ssn"].astype(float)
    filtered.to_csv(out_path, index=False)
    _logger.info("  Saved %s (%d rows)", out_path, len(filtered))


def _download_bike_sharing() -> None:
    """Download UCI Bike Sharing Dataset and save hourly subset to CSV.

    Fetches the ZIP archive from the UCI repository, extracts ``hour.csv``
    in memory, keeps columns ``cnt``, ``temp``, ``hum``, and ``windspeed``,
    and writes them to ``data/raw/exog/bike_sharing_hour.csv``.
    """
    out_path = _EXOG_DIR / "bike_sharing_hour.csv"
    _EXOG_DIR.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        _logger.info("  %s already exists, skipping.", out_path)
        return

    _logger.info("  Downloading UCI Bike Sharing Dataset ...")
    try:
        with urlopen(_BIKE_URL) as response:  # noqa: S310 — trusted, hardcoded URL
            raw_bytes = response.read()
    except Exception as exc:  # noqa: BLE001
        _logger.warning("  Failed to download UCI Bike Sharing data: %s", exc)
        return

    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
            with zf.open("hour.csv") as f:
                df = pd.read_csv(f)
    except (KeyError, zipfile.BadZipFile) as exc:
        _logger.warning("  Failed to extract hour.csv from ZIP: %s", exc)
        return

    keep = ["cnt", "temp", "hum", "windspeed"]
    missing = [c for c in keep if c not in df.columns]
    if missing:
        _logger.warning("  Expected columns missing: %s", missing)
        return

    df[keep].to_csv(out_path, index=False)
    _logger.info("  Saved %s (%d rows, columns: %s)", out_path, len(df), keep)


def _download_exog_financial() -> None:
    """Download financial exogenous pairs via yfinance and save to CSV.

    Saves log-returns for SPY and ETH-USD, and raw close levels for ^VIX.
    All output CSVs have columns ``timestamp`` (integer index) and ``y``.
    """
    _EXOG_DIR.mkdir(parents=True, exist_ok=True)
    for name, (ticker, start, end, use_log_returns) in _EXOG_FINANCIAL_SPECS.items():
        out_path = _EXOG_DIR / f"{name}.csv"
        if out_path.exists():
            _logger.info("  %s already exists, skipping.", out_path)
            continue
        _logger.info("  Downloading %s (%s to %s) ...", ticker, start, end)
        try:
            prices = _download_close_prices(ticker, start=start, end=end)
            if prices.size < 100:
                _logger.warning("  Only %d points for %s, skipping.", prices.size, ticker)
                continue
            if use_log_returns:
                values = np.diff(np.log(np.maximum(prices, 1e-8)))
                values = values[np.isfinite(values)]
            else:
                values = prices[np.isfinite(prices)]
            result_df = pd.DataFrame({"timestamp": range(len(values)), "y": values})
            result_df.to_csv(out_path, index=False)
            kind = "log-return" if use_log_returns else "close"
            _logger.info("  Saved %s (%d %s points)", out_path, len(values), kind)
        except Exception as exc:  # noqa: BLE001
            _logger.warning("  Failed to download %s: %s", ticker, exc)


def _generate_noise_control(*, n: int = 17521, random_state: int = 0) -> None:
    """Generate and save a white-noise control series for reproducibility.

    Args:
        n: Number of samples. Defaults to 17521 (≈ UCI hourly bike rows).
        random_state: Seed for the random number generator.
    """
    out_path = _EXOG_DIR / "noise_control.csv"
    if out_path.exists():
        _logger.info("  %s already exists, skipping.", out_path)
        return
    rng = np.random.default_rng(random_state)
    values = rng.standard_normal(n)
    df = pd.DataFrame({"timestamp": range(n), "y": values})
    df.to_csv(out_path, index=False)
    _logger.info("  Saved %s (%d white-noise points, random_state=%d)", out_path, n, random_state)


def _download_exog_datasets() -> None:
    """Download and generate all exogenous cross-dependence datasets.

    Downloads UCI Bike Sharing hourly data, financial exogenous pairs
    (SPY log-returns, VIX levels, ETH log-returns), and generates a
    synthetic white-noise control series for reproducibility.
    """
    _EXOG_DIR.mkdir(parents=True, exist_ok=True)
    _download_bike_sharing()
    _download_exog_financial()
    _generate_noise_control(n=17521, random_state=0)


def _parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description="Download and persist all project datasets.")
    parser.add_argument(
        "dataset",
        nargs="?",
        choices=["all", "sunspots_monthly"],
        default="all",
        help="Optional single dataset selector (default: all).",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging verbosity level (default: INFO).",
    )
    return parser.parse_args()


def main() -> None:
    """Download and persist all datasets."""
    args = _parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(message)s")

    if args.dataset == "sunspots_monthly":
        _download_sunspots_monthly()
        _logger.info("Done. sunspots_monthly is in data/processed/")
        return

    _logger.info("=== Part A: Canonical illustrative examples ===")
    _save_canonical()

    _download_financial_canonical()

    _logger.info("\n=== Part B: M4 competition data (all 6 frequencies) ===")
    for frequency, url in _M4_URLS.items():
        _download_and_convert_m4(frequency, url)

    _logger.info("\n=== Part C: Financial canonical series ===")
    _logger.info("  (already downloaded above alongside canonical examples)")

    _logger.info("\n=== Part D: Exogenous cross-dependence datasets ===")
    _download_exog_datasets()

    _logger.info("\n=== Summary ===")
    _logger.info("%-12s %-18s %s", "Frequency", "Survivor target", "Hmax")
    for freq in _M4_URLS:
        _logger.info("  %-10s %-18d %d", freq, _PAPER_TARGETS[freq], _PAPER_HMAX[freq])

    _logger.info("\nDone. All data is in data/raw/")


if __name__ == "__main__":
    main()
