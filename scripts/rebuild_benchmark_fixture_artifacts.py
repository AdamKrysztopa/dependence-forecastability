"""Rebuild and verify benchmark summary artifacts from fixed fixtures.

Reproduction command (summary table + consistency check):
    uv run python scripts/rebuild_benchmark_fixture_artifacts.py --verify
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from forecastability.utils.reproducibility import (
    verify_fixture_benchmark_artifacts,
    write_fixture_benchmark_artifacts,
)

_logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    """Build command-line parser for fixture artifact rebuilds.

    Returns:
        Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild benchmark summary artifacts from a tiny frozen horizon-table fixture "
            "and optionally verify them against expected outputs."
        ),
        epilog=(
            "Examples:\n"
            "  uv run python scripts/rebuild_benchmark_fixture_artifacts.py\n"
            "  uv run python scripts/rebuild_benchmark_fixture_artifacts.py --verify\n"
            "  uv run python scripts/rebuild_benchmark_fixture_artifacts.py "
            "--output-dir outputs/tables/benchmark_fixture\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--fixture-horizon-table",
        type=Path,
        default=Path("docs/fixtures/benchmark_examples/raw_horizon_table.csv"),
        help="Path to raw benchmark fixture horizon-table CSV.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/tables/benchmark_fixture"),
        help="Directory where rebuilt artifact CSVs will be written.",
    )
    parser.add_argument(
        "--expected-dir",
        type=Path,
        default=Path("docs/fixtures/benchmark_examples/expected"),
        help="Directory containing frozen expected artifact CSVs.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify rebuilt artifacts against frozen expected CSVs.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Execute fixture artifact rebuild and optional consistency verification.

    Args:
        argv: Optional CLI arguments for programmatic invocation.

    Returns:
        Process exit code (0 for success, 2 for verification failure).
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _build_parser().parse_args(argv)

    written_paths = write_fixture_benchmark_artifacts(
        fixture_horizon_path=args.fixture_horizon_table,
        output_dir=args.output_dir,
    )
    _logger.info("Wrote %d fixture artifact files under %s", len(written_paths), args.output_dir)
    _logger.info("Summary table path: %s", args.output_dir / "benchmark_summary_table.csv")

    if not args.verify:
        return 0

    try:
        verify_fixture_benchmark_artifacts(
            actual_dir=args.output_dir,
            expected_dir=args.expected_dir,
        )
    except ValueError as exc:
        _logger.error(str(exc))
        return 2

    _logger.info("Fixture artifacts match frozen expected outputs in %s", args.expected_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
