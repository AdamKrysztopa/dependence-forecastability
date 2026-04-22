"""Rebuild and verify lagged-exogenous regression fixtures.

Reproduction command (rebuild + verify):
    uv run python scripts/rebuild_lagged_exog_regression_fixtures.py --verify

Rebuild only:
    uv run python scripts/rebuild_lagged_exog_regression_fixtures.py
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from forecastability.diagnostics.lagged_exog_regression import (
    LAGGED_EXOG_FIXTURE_CASES,
    verify_lagged_exog_regression_outputs,
    write_lagged_exog_regression_outputs,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
_logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = Path("outputs/tables/lagged_exog_regression")
_DEFAULT_EXPECTED_DIR = Path("docs/fixtures/lagged_exog_regression/expected")


def _build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild lagged-exogenous regression fixture outputs and optionally "
            "verify against frozen expected JSON files."
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

    _logger.info(
        "Rebuilding lagged-exogenous regression fixtures (%d cases)",
        len(LAGGED_EXOG_FIXTURE_CASES),
    )
    written = write_lagged_exog_regression_outputs(output_dir=args.output_dir)
    for path in written:
        _logger.info("  wrote %s", path)

    _logger.info("Wrote %d files to %s", len(written), args.output_dir)

    if args.verify:
        _logger.info("Verifying against expected dir: %s", args.expected_dir)
        verify_lagged_exog_regression_outputs(
            actual_dir=args.output_dir,
            expected_dir=args.expected_dir,
        )
        _logger.info("Verification passed -- all outputs match frozen expected.")


if __name__ == "__main__":
    main()
