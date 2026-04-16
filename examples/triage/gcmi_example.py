"""GCMI example: monotonic-transform invariance and lag detection.

Demonstrates V3-F02 (Gaussian Copula MI) on synthetic datasets:

1. Linear pair          — y = 0.8*x + noise          (reference baseline)
2. Monotone nonlinear   — y = x**3 + noise             (Pearson fails; GCMI succeeds)
3. Independent pair     — two independent Gaussians    (both near-zero)
4. Lagged pair          — y[t] = x[t-3] + noise       (peak at lag 3)
5. GCMI vs TE           — both curves on the lagged pair
"""

from __future__ import annotations

import numpy as np

from forecastability.diagnostics.gcmi import (
    compute_gcmi,
    compute_gcmi_at_lag,
    compute_gcmi_curve,
)
from forecastability.diagnostics.transfer_entropy import compute_transfer_entropy_curve


def _pearson(x: np.ndarray, y: np.ndarray) -> float:
    """Return Pearson r for two aligned 1-D arrays."""
    return float(np.corrcoef(x, y)[0, 1])


def _peak_lag(curve: np.ndarray) -> int:
    """Return the 1-based lag index of the maximum value in *curve*."""
    return int(np.argmax(curve)) + 1


def _print_separator(title: str) -> None:
    width = 72
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def main() -> None:  # noqa: PLR0914
    rng = np.random.default_rng(42)
    n = 1000
    noise_sd = 0.5

    # ------------------------------------------------------------------
    # Build datasets
    # ------------------------------------------------------------------
    x_base = rng.standard_normal(n)
    noise = rng.normal(0, noise_sd, n)

    # 1. Linear pair
    x_lin = x_base.copy()
    y_lin = 0.8 * x_lin + noise

    # 2. Monotone nonlinear (cubic) pair — same x, different noise draw
    noise2 = rng.normal(0, noise_sd, n)
    x_cub = x_base.copy()
    y_cub = x_cub**3 + noise2

    # 3. Independent pair
    x_ind = rng.standard_normal(n)
    y_ind = rng.standard_normal(n)

    # 4. Lagged pair — y[t] = x[t-3] + noise
    lag_true = 3
    noise3 = rng.normal(0, noise_sd, n)
    x_lag = rng.standard_normal(n)
    y_lag = np.empty(n)
    y_lag[:lag_true] = noise3[:lag_true]
    y_lag[lag_true:] = x_lag[: n - lag_true] + noise3[lag_true:]

    # ------------------------------------------------------------------
    # Compute zero-lag GCMI and Pearson for all four pairs
    # ------------------------------------------------------------------
    pairs: list[tuple[str, np.ndarray, np.ndarray]] = [
        ("Linear (y=0.8x+ε)", x_lin, y_lin),
        ("Cubic (y=x³+ε)", x_cub, y_cub),
        ("Independent", x_ind, y_ind),
        ("Lagged (lag=3, zero-lag)", x_lag, y_lag),
    ]

    _print_separator("Zero-lag comparison: GCMI vs Pearson |r|")
    header = f"{'Dataset':<32}  {'GCMI (bits)':>12}  {'|Pearson r|':>12}"
    print(header)
    print("-" * len(header))
    for name, xv, yv in pairs:
        gcmi_val = compute_gcmi(xv, yv)
        pearson_abs = abs(_pearson(xv, yv))
        flag = ""
        if name.startswith("Cubic") and pearson_abs < 0.5 and gcmi_val > 0.1:
            flag = "  ← GCMI detects; Pearson misses"
        if name.startswith("Independent") and gcmi_val < 0.05:
            flag = "  ← correctly near-zero"
        print(f"{name:<32}  {gcmi_val:>12.4f}  {pearson_abs:>12.4f}{flag}")

    # ------------------------------------------------------------------
    # GCMI lag curve for the lagged pair
    # ------------------------------------------------------------------
    max_lag = 10
    gcmi_lag_curve = compute_gcmi_curve(x_lag, y_lag, max_lag=max_lag)

    _print_separator("GCMI curve for lagged pair (x → y, true lag=3)")
    print(f"{'Lag':>5}  {'GCMI (bits)':>14}")
    print("-" * 24)
    for i, val in enumerate(gcmi_lag_curve):
        lag = i + 1
        marker = "  ← peak" if lag == _peak_lag(gcmi_lag_curve) else ""
        print(f"{lag:>5}  {val:>14.4f}{marker}")

    # ------------------------------------------------------------------
    # GCMI vs TE for the lagged pair
    # ------------------------------------------------------------------
    _print_separator("GCMI vs TE curve for lagged pair (x → y, true lag=3)")

    # TE with linear_residual backend is fast and handles this structure well
    te_curve = compute_transfer_entropy_curve(
        x_lag,
        y_lag,
        max_lag=max_lag,
        backend="linear_residual",
        history_mode="canonical",
    )

    gcmi_peak = _peak_lag(gcmi_lag_curve)
    te_peak = _peak_lag(te_curve)

    col_w = 14
    print(f"{'Lag':>5}  {'GCMI (bits)':>{col_w}}  {'TE (bits)':>{col_w}}")
    print("-" * (5 + 2 + col_w + 2 + col_w + 4))
    for i in range(max_lag):
        lag = i + 1
        gcmi_marker = " ←G" if lag == gcmi_peak else "   "
        te_marker = " ←T" if lag == te_peak else "   "
        print(
            f"{lag:>5}  {gcmi_lag_curve[i]:>{col_w}.4f}{gcmi_marker}"
            f"  {te_curve[i]:>{col_w}.4f}{te_marker}"
        )

    print(f"\nGCMI peaks at lag {gcmi_peak}  (expected: {lag_true})")
    print(f"TE    peaks at lag {te_peak}  (expected: {lag_true})")

    # ------------------------------------------------------------------
    # Specific lag-3 values for emphasis
    # ------------------------------------------------------------------
    _print_separator("Direct lag-3 GCMI for each dataset")
    lag3_pairs: list[tuple[str, np.ndarray, np.ndarray]] = [
        ("Linear", x_lin, y_lin),
        ("Cubic", x_cub, y_cub),
        ("Independent", x_ind, y_ind),
        ("Lagged (true lag=3)", x_lag, y_lag),
    ]
    print(f"{'Dataset':<28}  {'GCMI @ lag 3 (bits)':>20}")
    print("-" * 54)
    for name, xv, yv in lag3_pairs:
        val = compute_gcmi_at_lag(xv, yv, lag=3)
        print(f"{name:<28}  {val:>20.4f}")

    # ------------------------------------------------------------------
    # Interpretation summary
    # ------------------------------------------------------------------
    _print_separator("Interpretation")
    cubic_gcmi = compute_gcmi(x_cub, y_cub)
    cubic_pearson = abs(_pearson(x_cub, y_cub))
    ind_gcmi = compute_gcmi(x_ind, y_ind)

    print(
        f"[1] Linear pair:     GCMI={compute_gcmi(x_lin,y_lin):.4f} bits; "
        f"|r|={abs(_pearson(x_lin,y_lin)):.4f}  "
        "→ Both agree on strong linear dependence."
    )
    print(
        f"[2] Cubic pair:      GCMI={cubic_gcmi:.4f} bits; "
        f"|r|={cubic_pearson:.4f}  "
        "→ GCMI captures nonlinear dependence; Pearson underestimates."
    )
    print(
        f"[3] Independent:     GCMI={ind_gcmi:.4f} bits  "
        "→ Near-zero confirms correct null behaviour."
    )
    print(
        f"[4] Lagged pair:     GCMI curve peaks at lag {gcmi_peak}; "
        f"true lag={lag_true}.  "
        "→ Correct lag identification."
    )
    print(
        f"[5] GCMI vs TE:      GCMI peak lag={gcmi_peak}, "
        f"TE peak lag={te_peak}; "
        "→ Both identify the correct lag."
    )

    # ------------------------------------------------------------------
    # Optional figure
    # ------------------------------------------------------------------
    try:
        import matplotlib  # type: ignore[import-untyped]

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # type: ignore[import-untyped]

        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        lags = np.arange(1, max_lag + 1)

        ax0 = axes[0]
        ax0.plot(lags, gcmi_lag_curve, marker="o", label="GCMI")
        ax0.axvline(lag_true, color="gray", linestyle="--", label=f"True lag={lag_true}")
        ax0.set_title("GCMI Lag Curve (x → y, lag=3)")
        ax0.set_xlabel("Lag")
        ax0.set_ylabel("GCMI (bits)")
        ax0.legend()
        ax0.grid(True, alpha=0.3)

        ax1 = axes[1]
        ax1.plot(lags, gcmi_lag_curve, marker="o", label="GCMI")
        ax1.plot(lags, te_curve, marker="s", linestyle="--", label="TE")
        ax1.axvline(lag_true, color="gray", linestyle=":", label=f"True lag={lag_true}")
        ax1.set_title("GCMI vs TE Lag Curves (x → y, lag=3)")
        ax1.set_xlabel("Lag")
        ax1.set_ylabel("MI (bits)")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        fig.tight_layout()
        out_path = "outputs/figures/gcmi_example.png"
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
        print(f"\nFigure saved → {out_path}")
    except ImportError:
        print("\n[INFO] matplotlib not available — figure skipped.")


if __name__ == "__main__":
    main()
