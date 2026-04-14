"""Phase 1 example: Information-Theoretic Limit Diagnostics (F2) + Spectral Utilities.

Demonstrates the newly implemented Phase 1 features on four synthetic series:

* AR(1) with φ=0.7   — moderate forecastability
* Seasonal 12-period — strong cyclic structure
* White noise         — no forecastability
* Downsampled AR(1)  — lossy compression simulation

Usage:
    uv run python scripts/archive/run_phase1_limit_diagnostics.py
"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib
import numpy as np
from scipy.signal import lfilter

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402 — must follow matplotlib.use()

from forecastability.diagnostics.spectral_utils import compute_normalised_psd, spectral_entropy
from forecastability.services.theoretical_limit_diagnostics_service import (
    build_theoretical_limit_diagnostics,
)
from forecastability.triage.models import TriageRequest, TriageResult
from forecastability.use_cases.run_triage import run_triage

_logger = logging.getLogger(__name__)

_NON_TRIVIAL_THRESHOLD = 0.01
_DPI = 150
_OUTPUT_DIR = Path("outputs/figures/phase1_limit_diagnostics")

# max_lag per series
_MAX_LAGS: dict[str, int] = {
    "AR(1) phi=0.7": 20,
    "Seasonal (12-period)": 20,
    "White Noise": 20,
    "Downsampled AR(1)": 10,
}


def _generate_series() -> dict[str, np.ndarray]:
    """Generate four synthetic series for Phase 1 demonstration.

    Returns:
        Ordered mapping of series name to 1-D float64 array.
    """
    rng = np.random.default_rng(42)
    n = 500

    # AR(1): y[t] = 0.7*y[t-1] + eps  (vectorised via IIR filter)
    eps_ar1 = rng.standard_normal(n)
    y_ar1: np.ndarray = lfilter([1.0], [1.0, -0.7], eps_ar1)

    # Seasonal: sin(2π·t/12) + 0.3·ε
    t_idx = np.arange(n, dtype=float)
    y_seasonal: np.ndarray = np.sin(2.0 * np.pi * t_idx / 12.0) + 0.3 * rng.standard_normal(n)

    # Pure white noise
    y_white: np.ndarray = rng.standard_normal(n)

    # Aggressively downsampled AR(1): every 4th point (~125 samples)
    y_downsampled: np.ndarray = y_ar1[::4]

    return {
        "AR(1) phi=0.7": y_ar1,
        "Seasonal (12-period)": y_seasonal,
        "White Noise": y_white,
        "Downsampled AR(1)": y_downsampled,
    }


def _run_triages(series_dict: dict[str, np.ndarray]) -> dict[str, TriageResult]:
    """Run ``run_triage`` for each series.

    Args:
        series_dict: Mapping of series name to 1-D float array.

    Returns:
        Mapping of series name to :class:`TriageResult`.
    """
    results: dict[str, TriageResult] = {}
    for name, series in series_dict.items():
        max_lag = _MAX_LAGS[name]
        request = TriageRequest(
            series=series,
            max_lag=max_lag,
            n_surrogates=99,
            random_state=42,
        )
        _logger.info("Triage: %s  n=%d  max_lag=%d ...", name, len(series), max_lag)
        results[name] = run_triage(request)
    return results


def _extract_ceiling(result: TriageResult) -> np.ndarray:
    """Return the forecastability ceiling array from a non-blocked TriageResult.

    Args:
        result: A completed (non-blocked) :class:`TriageResult`.

    Returns:
        Ceiling values per horizon, shape ``(H,)``.

    Raises:
        ValueError: When ``theoretical_limit_diagnostics`` is not populated.
    """
    tld = result.theoretical_limit_diagnostics
    if tld is None:
        raise ValueError("theoretical_limit_diagnostics not populated in TriageResult.")
    return tld.forecastability_ceiling_by_horizon


def _print_summary_table(
    series_names: list[str],
    results: dict[str, TriageResult],
) -> None:
    """Print a summary table of forecastability ceiling metrics.

    Args:
        series_names: Ordered list of series names.
        results: Mapping of series name to :class:`TriageResult`.
    """
    w_name, w_peak, w_nt = 26, 14, 24
    divider = "-" * (w_name + w_peak + w_nt + 4)
    header = (
        f"{'Series Name':<{w_name}} {'Peak Ceiling':>{w_peak}} {'Non-trivial Horizons':>{w_nt}}"
    )
    print("\n=== Phase 1 Forecastability Ceiling Summary ===")
    print(divider)
    print(header)
    print(divider)
    for name in series_names:
        ceiling = _extract_ceiling(results[name])
        tld = results[name].theoretical_limit_diagnostics
        assert tld is not None  # guaranteed by _extract_ceiling
        peak = float(np.max(ceiling))
        n_nt = int(np.sum(ceiling > _NON_TRIVIAL_THRESHOLD))
        print(f"{name:<{w_name}} {peak:>{w_peak}.4f} {n_nt:>{w_nt}}")
        print(f"  Summary: {tld.ceiling_summary}")
    print(divider)
    print()


def _plot_ceilings_comparison(
    series_names: list[str],
    results: dict[str, TriageResult],
    output_dir: Path,
) -> Path:
    """Save Figure 1: 2×2 forecastability ceiling subplots.

    Args:
        series_names: Ordered list of four series names.
        results: Mapping of series name to :class:`TriageResult`.
        output_dir: Directory for saved figure.

    Returns:
        Path to the saved PNG file.
    """
    save_path = output_dir / "forecastability_ceilings_comparison.png"
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for ax, name in zip(axes.flatten(), series_names, strict=True):
        ceiling = _extract_ceiling(results[name])
        horizons = np.arange(1, ceiling.size + 1)
        peak = float(np.max(ceiling))
        ax.plot(horizons, ceiling, color="tab:blue", lw=1.8, label="ceiling (AMI)")
        ax.axhline(
            _NON_TRIVIAL_THRESHOLD,
            color="tab:orange",
            ls="--",
            lw=1.2,
            label=f"ε = {_NON_TRIVIAL_THRESHOLD}",
        )
        ax.fill_between(horizons, 0, ceiling, alpha=0.15, color="tab:blue")
        ax.set_xlabel("Horizon")
        ax.set_ylabel("MI (nats)")
        ax.set_title(f"{name}\npeak ceiling = {peak:.4f}")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
    fig.suptitle("Forecastability Ceilings by Series Type", fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(save_path, dpi=_DPI)
    plt.close(fig)
    return save_path


def _plot_psd_comparison(
    series_names: list[str],
    series_dict: dict[str, np.ndarray],
    output_dir: Path,
) -> Path:
    """Save Figure 2: 1×4 normalised PSD subplots with spectral entropy.

    Args:
        series_names: Ordered list of four series names.
        series_dict: Mapping of series name to 1-D float array.
        output_dir: Directory for saved figure.

    Returns:
        Path to the saved PNG file.
    """
    save_path = output_dir / "psd_comparison.png"
    fig, axes = plt.subplots(1, 4, figsize=(18, 4))
    for ax, name in zip(axes, series_names, strict=True):
        freqs, p = compute_normalised_psd(series_dict[name])
        h_spec = spectral_entropy(p)
        ax.plot(freqs, p, color="tab:blue", lw=1.2)
        ax.set_xlabel("Frequency")
        ax.set_ylabel("Power weight")
        ax.set_title(name, fontsize=9)
        ax.annotate(
            f"H_spec={h_spec:.3f} nats",
            xy=(0.97, 0.95),
            xycoords="axes fraction",
            ha="right",
            va="top",
            fontsize=8,
            bbox={"boxstyle": "round,pad=0.3", "fc": "wheat", "alpha": 0.5},
        )
        ax.grid(alpha=0.3)
    fig.suptitle(
        "Normalised Power Spectral Density — Phase 1 Utilities",
        fontsize=12,
        fontweight="bold",
    )
    fig.tight_layout()
    fig.savefig(save_path, dpi=_DPI)
    plt.close(fig)
    return save_path


def _plot_it_limits_vs_downsampling(
    results: dict[str, TriageResult],
    output_dir: Path,
) -> Path:
    """Save Figure 3: original vs downsampled AR(1) information-theoretic limits.

    Args:
        results: Mapping of series name to :class:`TriageResult`.
        output_dir: Directory for saved figure.

    Returns:
        Path to the saved PNG file.
    """
    save_path = output_dir / "it_limits_vs_downsampling.png"
    ar1_key = "AR(1) phi=0.7"
    ds_key = "Downsampled AR(1)"

    fig, (ax_orig, ax_ds) = plt.subplots(1, 2, figsize=(12, 5))

    for ax, key, subtitle in (
        (ax_orig, ar1_key, "Original AR(1)  n=500"),
        (ax_ds, ds_key, "Downsampled AR(1)  n≈125"),
    ):
        ceiling = _extract_ceiling(results[key])
        horizons = np.arange(1, ceiling.size + 1)
        ax.plot(horizons, ceiling, color="tab:blue", lw=1.8)
        ax.fill_between(horizons, 0, ceiling, alpha=0.15, color="tab:blue")
        ax.set_xlabel("Horizon")
        ax.set_ylabel("MI (nats)")
        ax.set_title(subtitle)
        ax.grid(alpha=0.3)

    fig.text(
        0.5,
        0.02,
        "Information ceiling drops after lossy downsampling",
        ha="center",
        va="bottom",
        fontsize=10,
        style="italic",
        color="tab:red",
    )
    fig.suptitle(
        "Information-Theoretic Limit: Original vs Downsampled",
        fontsize=12,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0.0, 0.08, 1.0, 1.0))
    fig.savefig(save_path, dpi=_DPI)
    plt.close(fig)
    return save_path


def _demonstrate_compression_warning(results: dict[str, TriageResult]) -> None:
    """Call ``build_theoretical_limit_diagnostics`` with ``compression_suspected=True``.

    Prints the compression warning for the downsampled AR(1) series to show
    how the service communicates potential information loss from downsampling.

    Args:
        results: Mapping of series name to :class:`TriageResult`.
    """
    ds_key = "Downsampled AR(1)"
    ceiling = _extract_ceiling(results[ds_key])
    diag = build_theoretical_limit_diagnostics(ceiling, compression_suspected=True)
    print("=== Compression-suspected diagnostic (downsampled AR(1)) ===")
    print(f"compression_warning:\n  {diag.compression_warning}")
    print()


def main() -> None:
    """Run Phase 1 information-theoretic limit diagnostics and spectral utilities example."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    _logger.info("Generating synthetic series...")
    series_dict = _generate_series()
    series_names = list(series_dict)

    _logger.info(
        "Running triage for %d series (n_surrogates=99, may take ~30-60 s)...",
        len(series_names),
    )
    results = _run_triages(series_dict)

    _print_summary_table(series_names, results)
    _demonstrate_compression_warning(results)

    _logger.info("Saving figures to %s ...", _OUTPUT_DIR)
    fig1_path = _plot_ceilings_comparison(series_names, results, _OUTPUT_DIR)
    fig2_path = _plot_psd_comparison(series_names, series_dict, _OUTPUT_DIR)
    fig3_path = _plot_it_limits_vs_downsampling(results, _OUTPUT_DIR)

    print("=== Saved figures ===")
    for p in (fig1_path, fig2_path, fig3_path):
        print(f"  {p}")


if __name__ == "__main__":
    main()
