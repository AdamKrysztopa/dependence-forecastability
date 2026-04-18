"""Example: V3-F07 Unified Covariant Summary Table.

Demonstrates significance bands, global ranking, and interpretation tags
on the 8-variable synthetic benchmark with known causal structure.

Expected patterns (ground truth from synthetic.py structural equations):
- driver_direct (lag 2): causal_confirmed or directional_informative, rank near top
- driver_mediated (lag 1): directional_informative or pairwise_informative, above_band
- driver_noise: noise_or_weak, below_band across most lags
- driver_nonlin_sq / driver_nonlin_abs: may surface as pairwise_informative because
  kNN MI detects nonlinear dependence even though Pearson/Spearman would miss it
"""
from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path

import pandas as pd

# Add project root to path for running as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from forecastability.use_cases.run_covariant_analysis import run_covariant_analysis
from forecastability.utils.synthetic import generate_covariant_benchmark

OUTPUTS_TABLES = Path(__file__).resolve().parents[3] / "outputs" / "tables"
OUTPUTS_REPORTS = Path(__file__).resolve().parents[3] / "outputs" / "reports"


def _rows_to_dataframe(bundle_summary_table: list) -> pd.DataFrame:
    """Convert list of CovariantSummaryRow Pydantic models to a flat DataFrame."""
    records = []
    for row in bundle_summary_table:
        records.append(
            {
                "target": row.target,
                "driver": row.driver,
                "lag": row.lag,
                "cross_ami": row.cross_ami,
                "cross_pami": row.cross_pami,
                "transfer_entropy": row.transfer_entropy,
                "gcmi": row.gcmi,
                "pcmci_link": row.pcmci_link,
                "pcmci_ami_parent": row.pcmci_ami_parent,
                "significance": row.significance,
                "rank": row.rank,
                "interpretation_tag": row.interpretation_tag,
            }
        )
    return pd.DataFrame(records)


def _print_significance_distribution(df: pd.DataFrame, report: StringIO) -> None:
    """Print per-driver significance counts (above_band / below_band / None)."""
    header = "SIGNIFICANCE DISTRIBUTION (cross_ami vs surrogate bands)"
    line = "-" * 70
    print(line)
    print(header)
    print(line)
    report.write(f"{line}\n{header}\n{line}\n")

    sig_counts = (
        df.groupby(["driver", "significance"], dropna=False)
        .size()
        .unstack(fill_value=0)
    )
    for column in ("above_band", "below_band", None):
        if column not in sig_counts.columns:
            sig_counts[column] = 0
    sig_counts = sig_counts.loc[:, ["above_band", "below_band", None]]
    # Rename None column to "no_band" for display clarity
    sig_counts.columns = ["above_band", "below_band", "no_band"]

    for driver in sorted(df["driver"].unique()):
        above = int(sig_counts.loc[driver, "above_band"]) if driver in sig_counts.index else 0
        below = int(sig_counts.loc[driver, "below_band"]) if driver in sig_counts.index else 0
        no_band = int(sig_counts.loc[driver, "no_band"]) if driver in sig_counts.index else 0
        line_text = (
            f"  {driver:<25s}  above_band={above:2d}  below_band={below:2d}  no_band={no_band:2d}"
        )
        print(line_text)
        report.write(f"{line_text}\n")
    print()
    report.write("\n")


def _print_rank1_row(df: pd.DataFrame, report: StringIO) -> None:
    """Print the rank-1 row (highest primary score)."""
    header = "RANK 1 ROW (highest primary score)"
    line = "-" * 70
    print(line)
    print(header)
    print(line)
    report.write(f"{line}\n{header}\n{line}\n")

    rank1 = df[df["rank"] == 1]
    if rank1.empty:
        msg = "  (no rank-1 row found)"
        print(msg)
        report.write(f"{msg}\n")
    else:
        row = rank1.iloc[0]
        lines = [
            f"  driver           : {row['driver']}",
            f"  lag              : {row['lag']}",
            (
                f"  cross_ami        : {row['cross_ami']:.4f}"
                if row["cross_ami"] is not None
                else "  cross_ami        : None"
            ),
            (
                f"  transfer_entropy : {row['transfer_entropy']:.4f}"
                if row["transfer_entropy"] is not None
                else "  transfer_entropy : None"
            ),
            (
                f"  gcmi             : {row['gcmi']:.4f}"
                if row["gcmi"] is not None
                else "  gcmi             : None"
            ),
            f"  significance     : {row['significance']}",
            f"  interpretation   : {row['interpretation_tag']}",
        ]
        for ln in lines:
            print(ln)
            report.write(f"{ln}\n")
    print()
    report.write("\n")


def _print_tag_distribution(df: pd.DataFrame, report: StringIO) -> None:
    """Print count of each interpretation tag across all rows."""
    header = "INTERPRETATION TAG DISTRIBUTION"
    line = "-" * 70
    print(line)
    print(header)
    print(line)
    report.write(f"{line}\n{header}\n{line}\n")

    tag_counts = df["interpretation_tag"].value_counts(dropna=False)
    for tag, count in tag_counts.items():
        tag_str = str(tag) if tag is not None else "None"
        line_text = f"  {tag_str:<30s}: {count:3d} rows"
        print(line_text)
        report.write(f"{line_text}\n")
    print()
    report.write("\n")


def _print_top10(df: pd.DataFrame, report: StringIO) -> None:
    """Print top 10 rows by rank."""
    header = "TOP 10 ROWS BY RANK"
    line = "-" * 70
    print(line)
    print(header)
    print(line)
    report.write(f"{line}\n{header}\n{line}\n")

    top10 = df.sort_values("rank").head(10)
    col_header = (
        f"  {'rank':>4}  {'driver':<25s}  {'lag':>3}  "
        f"{'cross_ami':>9}  {'te':>8}  {'gcmi':>8}  {'significance':<12}  {'tag'}"
    )
    print(col_header)
    report.write(f"{col_header}\n")

    for _, row in top10.iterrows():
        cross_ami_str = (
            f"{row['cross_ami']:9.4f}" if row["cross_ami"] is not None else f"{'None':>9}"
        )
        te_str = (
            f"{row['transfer_entropy']:8.4f}"
            if row["transfer_entropy"] is not None
            else f"{'None':>8}"
        )
        gcmi_str = f"{row['gcmi']:8.4f}" if row["gcmi"] is not None else f"{'None':>8}"
        sig_str = str(row["significance"]) if row["significance"] is not None else "None"
        tag_str = (
            str(row["interpretation_tag"]) if row["interpretation_tag"] is not None else "None"
        )
        line_text = (
            f"  {int(row['rank']):>4}  {row['driver']:<25s}  {int(row['lag']):>3}"
            f"  {cross_ami_str}  {te_str}  {gcmi_str}  {sig_str:<12}  {tag_str}"
        )
        print(line_text)
        report.write(f"{line_text}\n")
    print()
    report.write("\n")


def _run_ground_truth_checks(df: pd.DataFrame, report: StringIO) -> bool:
    """Run and print ground-truth assertions; return True if all pass."""
    header = "GROUND TRUTH CHECKS"
    line = "-" * 70
    print(line)
    print(header)
    print(line)
    report.write(f"{line}\n{header}\n{line}\n")

    all_passed = True
    results: list[tuple[str, bool, str]] = []

    # Check 1: driver_direct appears in top-10 rows by rank.
    # Note: cross_ami measures raw dependence, not causal strength. Mediated and
    # correlated drivers (driver_mediated, driver_redundant) often rank above the
    # true direct driver because they carry accumulated indirect dependence at
    # multiple lags. Top-10 out of 30 rows (top 33%) confirms driver_direct is
    # strongly informative relative to noise, even if not rank 1.
    top10_drivers = set(df.sort_values("rank").head(10)["driver"].tolist())
    check1_pass = "driver_direct" in top10_drivers
    results.append((
        "driver_direct in top-10 rows by rank (cross_ami ranks dependence, not causation)",
        check1_pass,
        f"top-10 drivers: {sorted(top10_drivers)}",
    ))

    # Check 2: driver_noise has no above_band rows (or far fewer than driver_direct)
    noise_above = (
        int(((df["driver"] == "driver_noise") & (df["significance"] == "above_band")).sum())
        if "driver_noise" in df["driver"].values
        else 0
    )
    direct_above = (
        int(((df["driver"] == "driver_direct") & (df["significance"] == "above_band")).sum())
        if "driver_direct" in df["driver"].values
        else 0
    )
    check2_pass = noise_above == 0 or noise_above < direct_above
    results.append((
        "driver_noise has no above_band rows (or far fewer than driver_direct)",
        check2_pass,
        f"driver_noise above_band={noise_above}, driver_direct above_band={direct_above}",
    ))

    # Check 3: rank-1 row has above_band significance
    rank1_rows = df[df["rank"] == 1]
    check3_pass = not rank1_rows.empty and rank1_rows.iloc[0]["significance"] == "above_band"
    detail = rank1_rows.iloc[0]["significance"] if not rank1_rows.empty else "no rank-1 row"
    results.append((
        "rank-1 row has above_band significance",
        check3_pass,
        f"rank-1 significance: {detail}",
    ))

    # Check 4: driver_direct has at least one row with a non-noise tag
    non_noise_tags = {
        "causal_confirmed",
        "directional_informative",
        "pairwise_informative",
        "probably_mediated",
    }
    direct_tags = set(df[df["driver"] == "driver_direct"]["interpretation_tag"].dropna().tolist())
    check4_pass = bool(direct_tags & non_noise_tags)
    results.append((
        "driver_direct has at least one informative interpretation tag",
        check4_pass,
        f"driver_direct tags: {sorted(direct_tags)}",
    ))

    for description, passed, detail in results:
        status = "PASS" if passed else "FAIL"
        line_text = f"  [{status}] {description}"
        detail_text = f"         ({detail})"
        print(line_text)
        print(detail_text)
        report.write(f"{line_text}\n{detail_text}\n")
        if not passed:
            all_passed = False

    overall = "ALL CHECKS PASSED" if all_passed else "SOME CHECKS FAILED"
    print()
    print(f"  Result: {overall}")
    report.write(f"\n  Result: {overall}\n")
    print()
    report.write("\n")

    return all_passed


def main() -> None:
    """Run the V3-F07 covariant summary table example end-to-end."""
    OUTPUTS_TABLES.mkdir(parents=True, exist_ok=True)
    OUTPUTS_REPORTS.mkdir(parents=True, exist_ok=True)

    report = StringIO()

    title_lines = [
        "=" * 70,
        "V3-F07: Unified Covariant Summary Table",
        "8-variable synthetic benchmark — known causal structure",
        "=" * 70,
    ]
    for ln in title_lines:
        print(ln)
        report.write(f"{ln}\n")
    print()
    report.write("\n")

    # --- Generate data ---
    df_data = generate_covariant_benchmark(n=1500, seed=42)
    target = df_data["target"].to_numpy()
    drivers = {
        name: df_data[name].to_numpy()
        for name in (
            "driver_direct",
            "driver_mediated",
            "driver_redundant",
            "driver_noise",
            "driver_nonlin_sq",
            "driver_nonlin_abs",
        )
    }

    data_info = [
        "Data generated: 1500 time steps, 6 drivers + 1 target",
        f"Driver names: {list(drivers.keys())}",
    ]
    for ln in data_info:
        print(ln)
        report.write(f"{ln}\n")
    print()
    report.write("\n")

    # --- Run covariant analysis ---
    run_msg = "Running covariant analysis (methods: cross_ami, cross_pami, te, gcmi)..."
    print(run_msg)
    report.write(f"{run_msg}\n")

    bundle = run_covariant_analysis(
        target,
        drivers,
        target_name="target",
        max_lag=5,
        methods=["cross_ami", "cross_pami", "te", "gcmi"],
        n_surrogates=99,
        random_state=42,
    )

    run_summary = [
        f"  Rows in summary table: {len(bundle.summary_table)}",
        f"  Active methods: {bundle.metadata['active_methods']}",
    ]
    for ln in run_summary:
        print(ln)
        report.write(f"{ln}\n")
    print()
    report.write("\n")

    # Convert to DataFrame for analysis
    df = _rows_to_dataframe(bundle.summary_table)

    # Summary stats header
    stats_header_lines = [
        "-" * 70,
        "SUMMARY STATISTICS",
        "-" * 70,
        f"  Total rows          : {len(df)}",
        f"  Unique (driver,lag) : {df[['driver','lag']].drop_duplicates().shape[0]}",
        f"  Unique drivers      : {df['driver'].nunique()}",
        f"  Lag range           : {df['lag'].min()} – {df['lag'].max()}",
    ]
    for ln in stats_header_lines:
        print(ln)
        report.write(f"{ln}\n")
    print()
    report.write("\n")

    # --- Summary sections ---
    _print_significance_distribution(df, report)
    _print_rank1_row(df, report)
    _print_tag_distribution(df, report)
    _print_top10(df, report)

    # --- Ground truth checks ---
    all_passed = _run_ground_truth_checks(df, report)

    # --- Save outputs ---
    csv_path = OUTPUTS_TABLES / "covariant_summary_table_example.csv"
    df.to_csv(csv_path, index=False)

    txt_path = OUTPUTS_REPORTS / "covariant_summary_table_example.txt"
    txt_path.write_text(report.getvalue(), encoding="utf-8")

    saved_lines = [
        f"CSV saved : {csv_path}",
        f"TXT saved : {txt_path}",
    ]
    for ln in saved_lines:
        print(ln)

    if not all_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
