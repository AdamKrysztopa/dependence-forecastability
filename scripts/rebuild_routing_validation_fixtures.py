"""Rebuild and verify routing validation regression fixtures.

Mirrors ``scripts/rebuild_fingerprint_regression_fixtures.py`` and follows the
same pattern established by the existing fixture rebuild scripts.

Three modes:

Calibrate (run once before first rebuild):
    uv run python scripts/rebuild_routing_validation_fixtures.py --calibrate-near-threshold

Rebuild (standard — reads calibration.json if present):
    uv run python scripts/rebuild_routing_validation_fixtures.py

Verify (CI / release-gate):
    uv run python scripts/rebuild_routing_validation_fixtures.py --verify
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from forecastability.diagnostics.routing_validation_regression import (
    _CALIBRATION_FILE,
    _EXPECTED_SUBDIR,
    calibrate_near_threshold_amplitude,
    rebuild_fixtures,
    verify_fixtures,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--verify",
        action="store_true",
        help=(
            "Verify rebuilt outputs against frozen expected fixtures. "
            "Exits non-zero on any drift; does not modify the working tree."
        ),
    )
    mode.add_argument(
        "--calibrate-near-threshold",
        action="store_true",
        dest="calibrate",
        help=(
            "Run the amplitude calibration sweep for the weak_seasonal_near_threshold "
            "archetype, write calibration.json, then rebuild all fixtures using the "
            "pinned amplitude (plan §6.3).  Required before the first fixture freeze."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run fixture rebuild, verify, or calibrate as requested."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _build_parser().parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]

    if args.calibrate:
        logging.info("--- Calibration sweep ---")
        try:
            cal = calibrate_near_threshold_amplitude()
        except RuntimeError as exc:
            logging.error("Calibration failed: %s", exc)
            return 1

        expected_dir = repo_root / _EXPECTED_SUBDIR
        expected_dir.mkdir(parents=True, exist_ok=True)
        cal_path = expected_dir / _CALIBRATION_FILE
        cal_path.write_text(json.dumps(cal, indent=2) + "\n", encoding="utf-8")
        logging.info("Wrote calibration result to %s", cal_path)
        logging.info(
            "Calibrated amplitude: %.4f (d_theta=%.6f)",
            cal["calibrated_amplitude"],
            cal["threshold_margin_at_calibration"],
        )
        logging.info("--- Rebuilding fixtures with calibrated amplitude ---")
        return rebuild_fixtures(repo_root)

    if args.verify:
        logging.info("--- Verifying routing validation regression fixtures ---")
        return verify_fixtures(repo_root)

    logging.info("--- Rebuilding routing validation regression fixtures ---")
    return rebuild_fixtures(repo_root)


if __name__ == "__main__":
    raise SystemExit(main())
