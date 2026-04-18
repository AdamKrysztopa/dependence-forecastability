"""F9 example: directional transfer entropy with lag-wise significance.

This example builds a deterministic lag-2 directional pair (X drives Y),
compares TE(X->Y) versus TE(Y->X), and verifies analyzer parity against the
direct TE implementation when using the exogenous path.

Usage:
    uv run python \
        examples/covariant_informative/directional_transfer/
        f9_transfer_entropy_directional.py
"""

from __future__ import annotations

import csv
import os
from pathlib import Path

import numpy as np

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt

from forecastability.pipeline.analyzer import ForecastabilityAnalyzerExog
from forecastability.services.significance_service import (
    compute_significance_bands_transfer_entropy,
)
from forecastability.services.transfer_entropy_service import compute_transfer_entropy_curve


def _generate_lag2_directional_pair(
    *,
    n_samples: int,
    random_state: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate a deterministic pair where X_{t-2} drives Y_t.

    Args:
        n_samples: Number of observations.
        random_state: Integer seed for deterministic generation.

    Returns:
        Tuple ``(x, y)`` where directional information transfer peaks at lag 2.
    """
    rng = np.random.default_rng(random_state)
    x = np.zeros(n_samples, dtype=float)
    y = np.zeros(n_samples, dtype=float)

    for index in range(1, n_samples):
        x[index] = 0.85 * x[index - 1] + rng.normal(scale=0.60)
    for index in range(2, n_samples):
        y[index] = 0.30 * y[index - 1] + 1.10 * x[index - 2] + rng.normal(scale=0.35)

    return x, y


def _build_csv_rows(
    *,
    te_xy: np.ndarray,
    te_yx: np.ndarray,
    te_xy_analyzer: np.ndarray,
    lower_xy: np.ndarray,
    upper_xy: np.ndarray,
) -> list[dict[str, float | int]]:
    """Build export rows for lag-wise directional TE diagnostics."""
    rows: list[dict[str, float | int]] = []
    for lag_index in range(te_xy.size):
        lag = lag_index + 1
        rows.append(
            {
                "lag": lag,
                "te_x_to_y": float(te_xy[lag_index]),
                "te_y_to_x": float(te_yx[lag_index]),
                "te_x_to_y_analyzer": float(te_xy_analyzer[lag_index]),
                "band_lower_x_to_y": float(lower_xy[lag_index]),
                "band_upper_x_to_y": float(upper_xy[lag_index]),
                "is_significant_x_to_y": int(te_xy[lag_index] > upper_xy[lag_index]),
            }
        )
    return rows


def _write_csv(*, csv_path: Path, rows: list[dict[str, float | int]]) -> None:
    """Write deterministic CSV output with a fixed column order."""
    columns = (
        "lag",
        "te_x_to_y",
        "te_y_to_x",
        "te_x_to_y_analyzer",
        "band_lower_x_to_y",
        "band_upper_x_to_y",
        "is_significant_x_to_y",
    )
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row[column] for column in columns})


def _plot_directional_curves(
    *,
    te_xy: np.ndarray,
    te_yx: np.ndarray,
    upper_xy: np.ndarray,
    significant_lags_xy: np.ndarray,
    output_path: Path,
) -> None:
    """Plot directional TE curves and X->Y significance upper band."""
    lags = np.arange(1, te_xy.size + 1, dtype=int)

    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    ax.plot(lags, te_xy, marker="o", lw=2.0, label="TE(X -> Y)", color="tab:blue")
    ax.plot(lags, te_yx, marker="s", lw=1.8, label="TE(Y -> X)", color="tab:orange")
    ax.plot(
        lags,
        upper_xy,
        ls="--",
        lw=1.4,
        color="tab:red",
        label="X->Y surrogate upper band (97.5%)",
    )

    if significant_lags_xy.size > 0:
        idx = significant_lags_xy - 1
        ax.scatter(
            significant_lags_xy,
            te_xy[idx],
            color="tab:red",
            s=60,
            zorder=3,
            label="Significant X->Y lags",
        )

    ax.set_title("F9 Directional Transfer Entropy: lag-wise comparison")
    ax.set_xlabel("Lag")
    ax.set_ylabel("Transfer entropy")
    ax.set_xticks(lags)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def main() -> None:
    """Run the F9 directional TE example and persist outputs."""
    random_state = 41
    max_lag = 8
    min_pairs = 50
    n_surrogates = 99

    source_x, target_y = _generate_lag2_directional_pair(
        n_samples=1200,
        random_state=17,
    )

    te_xy = compute_transfer_entropy_curve(
        source_x,
        target_y,
        max_lag=max_lag,
        min_pairs=min_pairs,
        random_state=random_state,
    )
    te_yx = compute_transfer_entropy_curve(
        target_y,
        source_x,
        max_lag=max_lag,
        min_pairs=min_pairs,
        random_state=random_state,
    )

    analyzer = ForecastabilityAnalyzerExog(
        n_surrogates=n_surrogates,
        random_state=random_state,
    )
    te_xy_analyzer = analyzer.compute_raw(
        target_y,
        max_lag=max_lag,
        method="te",
        exog=source_x,
        min_pairs=min_pairs,
    )

    if not np.allclose(te_xy_analyzer, te_xy, rtol=1e-12, atol=1e-12):
        max_abs_diff = float(np.max(np.abs(te_xy_analyzer - te_xy)))
        raise RuntimeError(
            "Analyzer TE raw curve does not match direct TE(X->Y) curve; "
            f"max_abs_diff={max_abs_diff:.3e}"
        )

    lower_xy, upper_xy = compute_significance_bands_transfer_entropy(
        target_y,
        n_surrogates=n_surrogates,
        random_state=random_state,
        max_lag=max_lag,
        source=source_x,
        min_pairs=min_pairs,
        n_jobs=1,
    )
    significant_lags_xy = np.where(te_xy > upper_xy)[0] + 1

    peak_xy_lag = int(np.argmax(te_xy)) + 1
    peak_yx_lag = int(np.argmax(te_yx)) + 1

    rows = _build_csv_rows(
        te_xy=te_xy,
        te_yx=te_yx,
        te_xy_analyzer=te_xy_analyzer,
        lower_xy=lower_xy,
        upper_xy=upper_xy,
    )

    csv_path = Path(
        "outputs/tables/examples/covariant_informative/directional_transfer/"
        "f9_transfer_entropy_directional_curve.csv"
    )
    figure_path = Path(
        "outputs/figures/examples/covariant_informative/directional_transfer/"
        "f9_transfer_entropy_directional_curves.png"
    )

    _write_csv(csv_path=csv_path, rows=rows)
    _plot_directional_curves(
        te_xy=te_xy,
        te_yx=te_yx,
        upper_xy=upper_xy,
        significant_lags_xy=significant_lags_xy,
        output_path=figure_path,
    )

    print("\n=== F9 Directional Transfer Entropy (V3-F01) ===")
    print("Synthetic setup: X drives Y with dominant lag 2.")
    print(f"max_lag={max_lag}, min_pairs={min_pairs}, n_surrogates={n_surrogates}")
    print(f"Peak lag TE(X->Y): {peak_xy_lag}")
    print(f"Peak lag TE(Y->X): {peak_yx_lag}")
    print(f"Parity check (analyzer vs direct X->Y): ok (max_abs_diff={0.0:.1e})")

    sig_lags_text = (
        ", ".join(str(int(lag)) for lag in significant_lags_xy)
        if significant_lags_xy.size > 0
        else "none"
    )
    print(f"Significant X->Y lags (above upper surrogate band): {sig_lags_text}")

    print("\nSaved artifacts:")
    print(f"- {csv_path}")
    print(f"- {figure_path}")


if __name__ == "__main__":
    main()
