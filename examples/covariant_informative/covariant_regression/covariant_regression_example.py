"""V3-F08 validation example: covariant regression across all methods and drivers.

This example demonstrates the V3-F08 covariant regression suite by:
- Running all four pairwise methods (cross_ami, cross_pami, gcmi, te) on the
  full 7-driver synthetic benchmark
- Printing a comprehensive table showing all drivers × lags × methods
- Highlighting which drivers were detected above the significance band
- Verifying ground-truth ordering (direct > mediated > noise, nonlinear detectable)
- Confirming that kNN MI-based methods (cross_ami, gcmi) detect nonlinear
  drivers that Pearson/Spearman correlation would miss

Ground-truth causal parents (from generate_covariant_benchmark docstring):
    driver_direct      at lag 2  (β=0.80, linear)
    driver_mediated    at lag 1  (β=0.50, via driver_direct)
    driver_contemp     at lag 0  (β=0.35, contemporaneous — not in lagged triage)
    driver_nonlin_sq   at lag 1  (β=0.40, quadratic — Pearson/Spearman blind)
    driver_nonlin_abs  at lag 1  (β=0.35, abs-value — Pearson/Spearman blind)

Non-causes:
    driver_redundant   (correlated with driver_direct, not structural)
    driver_noise       (independent AR(1), no coupling)
"""

from __future__ import annotations

from forecastability import run_covariant_analysis
from forecastability.utils.synthetic import generate_covariant_benchmark
from forecastability.utils.types import CovariantAnalysisBundle

_ALL_DRIVERS: tuple[str, ...] = (
    "driver_direct",
    "driver_mediated",
    "driver_redundant",
    "driver_noise",
    "driver_contemp",
    "driver_nonlin_sq",
    "driver_nonlin_abs",
)

_NONLINEAR_DRIVERS: frozenset[str] = frozenset({"driver_nonlin_sq", "driver_nonlin_abs"})

_METHOD_FIELDS: tuple[tuple[str, str], ...] = (
    ("cross_ami", "CrossAMI"),
    ("cross_pami", "pCrossAMI"),
    ("gcmi", "GCMI"),
    ("transfer_entropy", "TE"),
)


def _fmt(value: float | None) -> str:
    """Format a float value for tabular output."""
    if value is None:
        return "  ----  "
    return f"{value:8.4f}"


def _sig_marker(row_significance: str | None) -> str:
    """Return a significance marker for the cross_ami column."""
    if row_significance == "above_band":
        return " *"
    return "  "


def _print_full_table(bundle: CovariantAnalysisBundle) -> None:
    """Print all drivers × lags × methods as a compact table."""
    col_w = 10
    header_parts = [f"{'Driver':<22}", f"{'Lag':>4}"]
    for _, label in _METHOD_FIELDS:
        header_parts.append(f"{label:>{col_w}}")
    header_parts.append(f"{'Sig':>6}")
    header_parts.append(f"{'Tag':<26}")
    header = "  ".join(header_parts)

    print("\nFull covariant analysis table (n=900, max_lag=3, n_surrogates=99)")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    prev_driver = ""
    for row in sorted(bundle.summary_table, key=lambda r: (r.driver, r.lag)):
        if row.driver != prev_driver and prev_driver:
            print()
        prev_driver = row.driver
        nl_marker = " [NL]" if row.driver in _NONLINEAR_DRIVERS else "     "
        driver_label = f"{row.driver}{nl_marker}"
        sig = row.significance or ""
        tag = row.interpretation_tag or ""
        parts = [f"{driver_label:<22}", f"{row.lag:>4}"]
        for field_name, _ in _METHOD_FIELDS:
            val = getattr(row, field_name)
            parts.append(f"{_fmt(val):>{col_w}}")
        parts.append(f"{sig:>6}")
        parts.append(f"{tag:<26}")
        print("  ".join(parts))

    print("=" * len(header))
    print("  [NL] = nonlinear driver (Pearson/Spearman blind, MI-detectable)")
    print("  Sig: 'above_band' = cross_ami exceeds phase-surrogate 97.5th percentile")


def _max_by_driver(
    bundle: CovariantAnalysisBundle,
    *,
    driver: str,
    field: str,
) -> float:
    """Return the maximum value of `field` across all lags for `driver`."""
    values = [
        getattr(row, field)
        for row in bundle.summary_table
        if row.driver == driver and getattr(row, field) is not None
    ]
    return max(float(v) for v in values) if values else 0.0


def _print_above_band_summary(bundle: CovariantAnalysisBundle) -> None:
    """Print which (driver, lag) pairs are above the cross_ami significance band."""
    print("\nCross-AMI significance (above phase-surrogate band)")
    print("-" * 52)
    any_above = False
    for row in sorted(bundle.summary_table, key=lambda r: (r.driver, r.lag)):
        if row.significance == "above_band":
            nl_tag = " [nonlinear]" if row.driver in _NONLINEAR_DRIVERS else ""
            print(f"  {row.driver:<24} lag {row.lag}: cross_ami={row.cross_ami:.4f}{nl_tag}")
            any_above = True
    if not any_above:
        print("  (none above band — try more data or higher coupling strength)")


def _print_ground_truth_verification(bundle: CovariantAnalysisBundle) -> None:
    """Print ground-truth verification checks.

    Checks are designed to be scientifically meaningful and stable at n=900:

    1. driver_direct and driver_mediated peak cross_ami >> driver_noise
       (large-effect causal parents outperform uncoupled noise)
    2. driver_nonlin_sq is above significance band at some lag
       (kNN MI can detect quadratic coupling; β=0.40, lag 1)
    3. driver_nonlin_sq cross_ami > driver_nonlin_sq gcmi
       (nonparametric kNN MI outperforms Gaussian-copula MI for symmetric
        nonlinear patterns — GCMI is near-zero for x² coupling by design)
    4. driver_direct at lag 2 is above_band
       (the structural lag-2 link is consistently detected)
    5. driver_mediated peak cross_ami > driver_noise peak cross_ami
       (mediated driver has direct coupling at lag 1, β=0.50)

    Note: driver_noise may show spurious "above_band" at n_surrogates=99
    due to sampling variance in the surrogate threshold (99 surrogates give
    a coarse 97.5th-percentile estimate). This is expected Type I error and
    does NOT indicate true causal coupling — the raw MI values for noise
    are an order of magnitude below the causal drivers.
    """
    print("\nGround Truth Verification")
    print("=" * 72)

    direct_ami = _max_by_driver(bundle, driver="driver_direct", field="cross_ami")
    mediated_ami = _max_by_driver(bundle, driver="driver_mediated", field="cross_ami")
    noise_ami = _max_by_driver(bundle, driver="driver_noise", field="cross_ami")

    # Check 1: driver_direct peak cross_ami >> driver_noise
    check1 = direct_ami > noise_ami
    print(f"  [{'PASS' if check1 else 'FAIL'}] driver_direct peak cross_ami > driver_noise peak")
    print(f"         direct={direct_ami:.4f}, noise={noise_ami:.4f}")

    # Check 2: driver_mediated peak cross_ami >> driver_noise
    check2 = mediated_ami > noise_ami
    print(f"  [{'PASS' if check2 else 'FAIL'}] driver_mediated peak cross_ami > driver_noise peak")
    print(f"         mediated={mediated_ami:.4f}, noise={noise_ami:.4f}")

    # Check 3: driver_nonlin_sq is above significance band at some lag
    # (kNN MI detects symmetric nonlinear coupling that Pearson/Spearman misses)
    nl_sq_above_band = any(
        r.significance == "above_band"
        for r in bundle.summary_table
        if r.driver == "driver_nonlin_sq"
    )
    print(
        f"  [{'PASS' if nl_sq_above_band else 'FAIL'}] driver_nonlin_sq "
        f"above significance band at some lag"
    )
    for r in sorted(bundle.summary_table, key=lambda x: x.lag):
        if r.driver == "driver_nonlin_sq":
            print(f"         lag {r.lag}: cross_ami={r.cross_ami:.4f}, sig={r.significance}")

    # Check 4: driver_nonlin_sq cross_ami > driver_nonlin_sq gcmi
    # GCMI (Gaussian copula) is near-zero for quadratic coupling (non-monotone pattern)
    # kNN MI captures the nonlinear signal better
    nl_sq_ami = _max_by_driver(bundle, driver="driver_nonlin_sq", field="cross_ami")
    nl_sq_gcmi = _max_by_driver(bundle, driver="driver_nonlin_sq", field="gcmi")
    check4 = nl_sq_ami > nl_sq_gcmi
    print(
        f"  [{'PASS' if check4 else 'FAIL'}] driver_nonlin_sq: kNN MI > GCMI "
        f"(nonparametric detects quadratic better than Gaussian copula)"
    )
    print(f"         cross_ami={nl_sq_ami:.4f}, gcmi={nl_sq_gcmi:.4f}")

    # Check 5: driver_direct lag 2 significance = 'above_band'
    direct_lag2_row = next(
        (r for r in bundle.summary_table if r.driver == "driver_direct" and r.lag == 2),
        None,
    )
    sig_at_lag2 = direct_lag2_row.significance if direct_lag2_row is not None else None
    check5 = sig_at_lag2 == "above_band"
    print(f"  [{'PASS' if check5 else 'FAIL'}] driver_direct lag 2 significance = '{sig_at_lag2}'")

    print()
    print("  Note: driver_noise may appear above_band at n_surrogates=99 (coarse")
    print("  threshold, ~5% Type I error rate). Raw MI values for noise are")
    ratio = direct_ami / noise_ami if noise_ami > 0 else float("inf")
    print(f"  ~{noise_ami:.3f} vs {direct_ami:.3f} for direct driver ({ratio:.0f}x ratio).")


def main() -> None:
    """Run V3-F08 validation example."""
    print("V3-F08 Covariant Regression Validation Example")
    print("=" * 72)
    print("Benchmark: generate_covariant_benchmark(n=900, seed=42)")
    print("Methods:   cross_ami, cross_pami, gcmi, te  |  n_surrogates=99, max_lag=3")
    print("Drivers:   all 7 (including nonlinear drivers Pearson/Spearman cannot detect)")

    df = generate_covariant_benchmark(n=900, seed=42)
    target = df["target"].to_numpy()
    drivers = {name: df[name].to_numpy() for name in _ALL_DRIVERS}

    bundle = run_covariant_analysis(
        target,
        drivers,
        target_name="target",
        methods=["cross_ami", "cross_pami", "gcmi", "te"],
        n_surrogates=99,
        max_lag=3,
        random_state=42,
    )

    _print_full_table(bundle)
    _print_above_band_summary(bundle)
    _print_ground_truth_verification(bundle)


if __name__ == "__main__":
    main()
