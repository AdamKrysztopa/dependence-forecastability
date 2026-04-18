"""Rebuild and verify covariant regression fixtures.

Generates deterministic covariant benchmark data, runs the covariant
analysis facade for each case, writes outputs to JSON, and optionally
verifies them against frozen expected files.

Reproduction command (rebuild + verify):
    uv run python scripts/rebuild_covariant_regression_fixtures.py --verify

Rebuild only:
    uv run python scripts/rebuild_covariant_regression_fixtures.py
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from forecastability.diagnostics.covariant_regression import (
    COVARIANT_FIXTURE_CASES,
    verify_covariant_regression_outputs,
    write_covariant_regression_outputs,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
_logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = Path("outputs/tables/covariant_regression")
_DEFAULT_EXPECTED_DIR = Path("docs/fixtures/covariant_regression/expected")


def _build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild covariant regression fixture outputs and optionally verify "
            "against frozen expected JSON files."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_DEFAULT_OUTPUT_DIR,
        help="Directory for rebuilt JSON outputs.",
    )
    parser.add_argument(
        "--expected-dir",
        type=Path,
        default=_DEFAULT_EXPECTED_DIR,
        help="Directory with frozen expected JSON files.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify rebuilt outputs against frozen expected after writing.",
    )
    return parser


def main() -> None:
    """Entry point: rebuild fixtures and optionally verify."""
    args = _build_parser().parse_args()

    output_dir: Path = args.output_dir
    expected_dir: Path = args.expected_dir

    n_cases = len(COVARIANT_FIXTURE_CASES)
    _logger.info("Rebuilding covariant regression fixtures (%d cases)", n_cases)
    written = write_covariant_regression_outputs(output_dir=output_dir)
    for path in written:
        _logger.info("  wrote %s", path)

    _logger.info("Wrote %d files to %s", len(written), output_dir)

    if args.verify:
        _logger.info("Verifying against expected dir: %s", expected_dir)
        verify_covariant_regression_outputs(
            actual_dir=output_dir,
            expected_dir=expected_dir,
        )
        _logger.info("Verification passed — all outputs match frozen expected.")


if __name__ == "__main__":
    main()
