"""Run ForecastabilityAnalyzerExog cross-dependence analysis on all exogenous pairs.

Produces per-case PNG figures in ``outputs/figures/exog/`` and JSON result summaries
in ``outputs/json/exog/``.  Prints a summary table on completion.

Usage:
    MPLBACKEND=Agg uv run python scripts/run_exog_analysis.py
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402 — must follow matplotlib.use()

from forecastability.pipeline.analyzer import ForecastabilityAnalyzerExog
from forecastability.utils.io_models import ExogCaseRecord

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Output directories
# ---------------------------------------------------------------------------
_FIG_DIR = Path("outputs/figures/exog")
_JSON_DIR = Path("outputs/json/exog")

# ---------------------------------------------------------------------------
# Data paths
# ---------------------------------------------------------------------------
_EXOG_DIR = Path("data/raw/exog")
_CANONICAL_DIR = Path("data/raw/canonical")

# ---------------------------------------------------------------------------
# Analysis parameters
# ---------------------------------------------------------------------------
_MAX_LAG = 40
_METHOD = "mi"
_N_SURROGATES = 99
_RANDOM_STATE = 42
# Surrogates are a project extension (not paper-native); expensive at 99× MI.
# Set True to compute phase-surrogate significance bands (parallelised).
_COMPUTE_SURROGATES: bool = False


# ---------------------------------------------------------------------------
# Case definition
# ---------------------------------------------------------------------------
class AnalysisCase(BaseModel):
    """One analysis case to run through ForecastabilityAnalyzerExog.

    Attributes:
        name: Short identifier used for filenames.
        target_series: 1-D array of the target time series.
        exog_series: Optional 1-D exogenous series (None → univariate).
        description: One-line human-readable description of the case.
        target_name: Short identifier for the target series (e.g. ``"bike_cnt"``).
        exog_name: Short identifier for the exogenous series (``"none"`` for univariate).
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: str
    target_series: np.ndarray
    exog_series: np.ndarray | None
    description: str
    target_name: str = ""
    exog_name: str = "none"


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------
def _load_y(path: Path) -> np.ndarray | None:
    """Load a single ``y`` column from a two-column (timestamp, y) CSV.

    Args:
        path: Path to the CSV file.

    Returns:
        1-D float64 array, or ``None`` if the file does not exist.
    """
    if not path.exists():
        _logger.warning("  WARNING: %s not found — skipping dependent cases.", path)
        return None
    return pd.read_csv(path)["y"].to_numpy(dtype=float)


def _load_bike_column(col: str) -> np.ndarray | None:
    """Load a single column from the UCI Bike Sharing hourly CSV.

    Args:
        col: Column name to extract (e.g. ``"cnt"``, ``"temp"``).

    Returns:
        1-D float64 array, or ``None`` if the file does not exist.
    """
    path = _EXOG_DIR / "bike_sharing_hour.csv"
    if not path.exists():
        _logger.warning("  WARNING: %s not found — skipping bike cases.", path)
        return None
    return pd.read_csv(path)[col].to_numpy(dtype=float)


def _noise(n: int) -> np.ndarray:
    """Return a standard-normal noise vector of length *n* with seed 42.

    Args:
        n: Number of samples.

    Returns:
        1-D float64 array of i.i.d. N(0, 1) values.
    """
    return np.random.default_rng(42).normal(0.0, 1.0, n)


def _align_tail(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Trim both arrays to ``min(len(a), len(b))`` from the end (calendar-aligned).

    Args:
        a: First time series.
        b: Second time series.

    Returns:
        Tuple of (a_trimmed, b_trimmed) with equal length.
    """
    n = min(len(a), len(b))
    return a[-n:], b[-n:]


# ---------------------------------------------------------------------------
# Build analysis cases
# ---------------------------------------------------------------------------
def _build_cases() -> list[AnalysisCase]:
    """Construct all analysis cases from available data files.

    Returns:
        List of :class:`AnalysisCase` instances to evaluate.  Cases whose
        required data files are missing are silently omitted.
    """
    cases: list[AnalysisCase] = []

    # -- Bike Sharing -------------------------------------------------------
    cnt = _load_bike_column("cnt")
    if cnt is not None:
        # temp and hum are already normalised to [0, 1] in the UCI dataset;
        # we document this explicitly but do not re-normalise.
        temp = _load_bike_column("temp")
        hum = _load_bike_column("hum")

        cases.append(
            AnalysisCase(
                name="bike_cnt_univariate",
                target_series=cnt.astype(float),
                exog_series=None,
                description="Bike demand (cnt) — univariate baseline",
                target_name="bike_cnt",
                exog_name="none",
            )
        )
        if temp is not None:
            cases.append(
                AnalysisCase(
                    name="bike_cnt_temp",
                    target_series=cnt.astype(float),
                    exog_series=temp.astype(float),
                    description="Bike demand → temperature (normalised [0,1], meaningful covariate)",  # noqa: E501
                    target_name="bike_cnt",
                    exog_name="temp",
                )
            )
        if hum is not None:
            cases.append(
                AnalysisCase(
                    name="bike_cnt_hum",
                    target_series=cnt.astype(float),
                    exog_series=hum.astype(float),
                    description=(
                        "Bike demand → humidity (normalised [0,1], moderate dependence expected)"
                    ),
                    target_name="bike_cnt",
                    exog_name="hum",
                )
            )
        cases.append(
            AnalysisCase(
                name="bike_cnt_noise",
                target_series=cnt.astype(float),
                exog_series=_noise(len(cnt)),
                description="Bike demand → white noise (useless control)",
                target_name="bike_cnt",
                exog_name="noise",
            )
        )

    # -- AAPL ---------------------------------------------------------------
    aapl = _load_y(_CANONICAL_DIR / "aapl_returns.csv")
    spy = _load_y(_EXOG_DIR / "spy_returns.csv")

    if aapl is not None:
        cases.append(
            AnalysisCase(
                name="aapl_univariate",
                target_series=aapl,
                exog_series=None,
                description="AAPL log-returns — univariate baseline",
                target_name="aapl",
                exog_name="none",
            )
        )
        if spy is not None:
            aapl_al, spy_al = _align_tail(aapl, spy)
            cases.append(
                AnalysisCase(
                    name="aapl_spy",
                    target_series=aapl_al,
                    exog_series=spy_al,
                    description=(
                        "AAPL log-returns → SPY log-returns (market factor, strong expected)"
                    ),
                    target_name="aapl",
                    exog_name="spy",
                )
            )
        cases.append(
            AnalysisCase(
                name="aapl_noise",
                target_series=aapl,
                exog_series=_noise(len(aapl)),
                description="AAPL log-returns → white noise (useless control)",
                target_name="aapl",
                exog_name="noise",
            )
        )

    # -- BTC / ETH ----------------------------------------------------------
    btc = _load_y(_CANONICAL_DIR / "bitcoin_returns.csv")
    eth = _load_y(_EXOG_DIR / "eth_returns.csv")

    if btc is not None:
        if eth is not None:
            # BTC available from 2015, ETH from 2017-11; align by tail
            btc_al, eth_al = _align_tail(btc, eth)
            cases.append(
                AnalysisCase(
                    name="btc_eth",
                    target_series=btc_al,
                    exog_series=eth_al,
                    description="BTC log-returns → ETH log-returns (crypto pair, aligned by tail)",
                    target_name="btc",
                    exog_name="eth",
                )
            )
        cases.append(
            AnalysisCase(
                name="btc_noise",
                target_series=btc,
                exog_series=_noise(len(btc)),
                description="BTC log-returns → white noise (useless control)",
                target_name="btc",
                exog_name="noise",
            )
        )

    return cases


# ---------------------------------------------------------------------------
# Per-case analysis
# ---------------------------------------------------------------------------
def _log(msg: str, t0: float | None = None) -> None:
    """Emit a timestamped log line via logging.

    Args:
        msg: Message to emit.
        t0: Optional start time from :func:`time.time`; elapsed seconds appended when given.
    """
    elapsed = f"  (+{time.time() - t0:.1f}s)" if t0 is not None else ""
    _logger.info("    [%s]%s %s", time.strftime("%H:%M:%S"), elapsed, msg)


def _run_case(case: AnalysisCase) -> ExogCaseRecord:
    """Run one analysis case and return the JSON-serialisable result dict.

    Args:
        case: The :class:`AnalysisCase` to analyse.

    Returns:
        Dictionary with analysis metadata and significance counts suitable
        for JSON serialisation (all numpy scalars converted to Python natives).
    """
    t_case = time.time()
    mode = "cross" if case.exog_series is not None else "univariate"
    n_target = len(case.target_series)
    n_exog = len(case.exog_series) if case.exog_series is not None else 0
    _logger.info(
        "  [%s] START '%s' (%s, n_target=%d%s) — %s",
        time.strftime("%H:%M:%S"),
        case.name,
        mode,
        n_target,
        f", n_exog={n_exog}" if n_exog else "",
        case.description,
    )

    surr_note = f"surrogates={'ON (parallelised)' if _COMPUTE_SURROGATES else 'OFF (skipped)'}"
    _log(f"method={_METHOD!r}, max_lag={_MAX_LAG}, {surr_note}", t_case)

    analyzer = ForecastabilityAnalyzerExog(n_surrogates=_N_SURROGATES, random_state=_RANDOM_STATE)
    _log("Running analyze() ...", t_case)
    result = analyzer.analyze(
        case.target_series,
        exog=case.exog_series,
        max_lag=_MAX_LAG,
        method=_METHOD,
        compute_surrogates=_COMPUTE_SURROGATES,
    )
    _log(f"  → recommendation: {result.recommendation}", t_case)
    n_raw, n_part = len(result.raw), len(result.partial)
    _log(f"  → raw curve computed ({n_raw} lags), partial ({n_part} lags)", t_case)

    # Save figure
    _log("Saving figure ...", t_case)
    fig_path = _FIG_DIR / f"{case.name}.png"
    fig = analyzer.plot(show=False)
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    _log(f"Figure saved → {fig_path}", t_case)

    sig_raw = result.sig_raw_lags.tolist()
    sig_partial = result.sig_partial_lags.tolist()
    raw_arr = result.raw
    part_arr = result.partial
    raw_slice = raw_arr[:20] if len(raw_arr) >= 20 else raw_arr
    mean_raw_20 = float(np.mean(raw_slice))

    auc_raw = float(np.trapezoid(raw_arr, dx=1.0))
    auc_partial = float(np.trapezoid(part_arr, dx=1.0))
    peak_raw_idx = int(np.argmax(raw_arr))
    peak_partial_idx = int(np.argmax(part_arr))
    top5_idx = np.argsort(part_arr)[::-1][:5]
    recommended_lags = sorted((top5_idx + 1).tolist())
    directness_ratio = auc_partial / auc_raw if auc_raw > 1e-9 else 0.0
    mean_partial_20 = float(np.mean(part_arr[: min(20, part_arr.size)]))

    record = ExogCaseRecord.from_fields(
        case_name=case.name,
        description=case.description,
        method=_METHOD,
        max_lag=_MAX_LAG,
        recommendation=result.recommendation,
        n_sig_raw_lags=int(len(sig_raw)),
        n_sig_partial_lags=int(len(sig_partial)),
        sig_raw_lags=sig_raw,
        sig_partial_lags=sig_partial,
        mean_raw_20=mean_raw_20,
        mode="cross" if case.exog_series is not None else "univariate",
        target_name=case.target_name,
        exog_name=case.exog_name,
        n_target=int(len(case.target_series)),
        n_exog=int(len(case.exog_series)) if case.exog_series is not None else 0,
        raw_curve=raw_arr.tolist(),
        partial_curve=part_arr.tolist(),
        auc_raw=auc_raw,
        auc_partial=auc_partial,
        peak_raw_lag=peak_raw_idx + 1,
        peak_raw_value=float(raw_arr[peak_raw_idx]),
        peak_partial_lag=peak_partial_idx + 1,
        peak_partial_value=float(part_arr[peak_partial_idx]),
        mean_partial_20=mean_partial_20,
        directness_ratio=directness_ratio,
        recommended_lags=recommended_lags,
        compute_surrogates=_COMPUTE_SURROGATES,
    )

    _log("Saving JSON ...", t_case)
    json_path = _JSON_DIR / f"{case.name}.json"
    record.to_json_file(json_path)
    _log(f"JSON saved → {json_path}", t_case)

    _log(
        f"DONE '{case.name}' — sig_raw={len(sig_raw)}, sig_partial={len(sig_partial)}, "
        f"mean_raw_20={mean_raw_20:.4f}",
        t_case,
    )
    return record


# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------
def _print_summary(records: list[ExogCaseRecord]) -> None:
    """Log a formatted summary table of all analysis results.

    Args:
        records: List of :class:`ExogCaseRecord` rows returned by :func:`_run_case`.
    """
    header = f"{'Case':<28} {'Recommendation':<35} {'SigRaw':>6} {'SigPart':>7}"
    _logger.info("\n" + "=" * len(header))
    _logger.info(header)
    _logger.info("-" * len(header))
    for r in records:
        _logger.info(
            "  %-26s %-35s %6d %7d",
            r.case_name,
            r.recommendation[:33],
            r.n_sig_raw_lags,
            r.n_sig_partial_lags,
        )
    _logger.info("=" * len(header))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Run all exogenous analysis cases and save outputs."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    t_total = time.time()
    _FIG_DIR.mkdir(parents=True, exist_ok=True)
    _JSON_DIR.mkdir(parents=True, exist_ok=True)

    _logger.info("=== Building analysis cases ===")
    cases = _build_cases()
    if not cases:
        _logger.info("No cases to run — check that data/raw/exog/ is populated.")
        return

    n = len(cases)
    _logger.info("  %d cases to run.\n", n)

    _logger.info("=== Running analyses ===")
    records: list[ExogCaseRecord] = []
    for i, case in enumerate(cases, start=1):
        _logger.info("\n--- Case %d/%d ---", i, n)
        record = _run_case(case)
        records.append(record)

    _print_summary(records)
    _logger.info("\nOutputs: figures → %s   JSON → %s", _FIG_DIR, _JSON_DIR)
    _logger.info("Total elapsed: %.1fs", time.time() - t_total)

    from forecastability.reporting import save_exog_reports  # noqa: PLC0415

    _REPORT_DIR = Path("outputs/reports/exog")
    save_exog_reports(json_dir=_JSON_DIR, report_dir=_REPORT_DIR)
    _logger.info("Exog reports → %s", _REPORT_DIR)


if __name__ == "__main__":
    main()
