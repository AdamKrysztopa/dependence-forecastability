"""Rebuild and verify forecast prep regression fixtures (FPC-F11).

Reproduction command (rebuild + verify):
    uv run python scripts/rebuild_forecast_prep_regression_fixtures.py --verify
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from forecastability.diagnostics.forecast_prep_regression import (
    FORECAST_PREP_FIXTURE_CASES,
    verify_forecast_prep_regression_outputs,
    write_forecast_prep_regression_outputs,
)

_DEFAULT_OUTPUT_DIR = Path("outputs/tables/forecast_prep_regression")
_DEFAULT_EXPECTED_DIR = Path("docs/fixtures/forecast_prep_regression/expected")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild forecast prep contract regression fixture outputs and optionally "
            "verify against frozen expected JSON files."
        )
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
        help="Verify rebuilt outputs against frozen expected.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run forecast prep fixture rebuild and optional drift verification."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _build_parser().parse_args(argv)

    logging.info(
        "Rebuilding forecast prep regression fixtures (%d cases)",
        len(FORECAST_PREP_FIXTURE_CASES),
    )
    written = write_forecast_prep_regression_outputs(output_dir=args.output_dir)
    for path in written:
        logging.info("  wrote %s", path)

    if not args.verify:
        return 0

    logging.info("Verifying against expected dir: %s", args.expected_dir)
    try:
        verify_forecast_prep_regression_outputs(
            actual_dir=args.output_dir,
            expected_dir=args.expected_dir,
        )
    except ValueError as exc:
        logging.error("Verification FAILED:\n%s", exc)
        return 2

    logging.info("Verification passed — all outputs match frozen expected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
