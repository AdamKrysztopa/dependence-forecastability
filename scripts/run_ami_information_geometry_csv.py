"""Run the CSV AMI Information Geometry adapter on a one-series-per-column file."""

from __future__ import annotations

import argparse
from pathlib import Path

from forecastability.adapters.csv import run_ami_geometry_csv_batch


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for the CSV geometry runner."""
    parser = argparse.ArgumentParser(
        description=(
            "Run the geometry-backed forecastability fingerprint workflow on a CSV "
            "with one target series per column."
        )
    )
    parser.add_argument("--input-csv", required=True, type=Path, help="Input CSV path.")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("outputs/ami_geometry_csv"),
        help="Root directory for summary CSV, markdown, figure, and JSON outputs.",
    )
    parser.add_argument("--max-lag", type=int, default=24, help="Maximum analyzed horizon.")
    parser.add_argument(
        "--n-surrogates",
        type=int,
        default=99,
        help="Shuffle-surrogate count used by the geometry engine.",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Deterministic seed for the geometry workflow.",
    )
    parser.add_argument(
        "--skip-bundle-json",
        action="store_true",
        help="Do not write one full bundle JSON file per analyzed series.",
    )
    return parser


def main() -> None:
    """Run the CSV geometry adapter and print emitted artifact paths."""
    args = _build_parser().parse_args()
    result = run_ami_geometry_csv_batch(
        args.input_csv,
        output_root=args.output_root,
        max_lag=args.max_lag,
        n_surrogates=args.n_surrogates,
        random_state=args.random_state,
        write_bundle_json=not args.skip_bundle_json,
    )

    print("AMI Information Geometry CSV Batch")
    print(f"  analyzed_series: {len(result.analyzed_items)}")
    print(f"  skipped_series: {len(result.skipped_items)}")
    print(f"  summary_csv: {result.summary_csv_path}")
    print(f"  figure: {result.figure_path}")
    print(f"  markdown: {result.markdown_path}")
    if result.warnings:
        print("  warnings:")
        for warning in result.warnings:
            print(f"    - {warning}")


if __name__ == "__main__":
    main()