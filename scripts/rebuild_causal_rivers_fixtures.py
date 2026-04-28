"""Rebuild and verify deterministic causal-rivers regression fixtures.

Reproduction command (rebuild + verify):
    uv run python scripts/rebuild_causal_rivers_fixtures.py --verify
"""

from __future__ import annotations

import argparse
import json
import logging
import math
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from forecastability.adapters.causal_rivers import (
    evaluate_causal_rivers_pair,
    extract_aligned_station_pair,
    extract_station_series,
    load_causal_rivers_config,
    load_resampled_causal_rivers_frame,
)
from forecastability.extensions import compute_target_baseline_by_horizon

_LOGGER = logging.getLogger(__name__)
_DEFAULT_CONFIG_PATH = Path("configs/causal_rivers_analysis.yaml")
_DEFAULT_OUTPUT_DIR = Path("outputs/tables/extensions")
_DEFAULT_EXPECTED_DIR = Path("docs/fixtures/extensions/expected")
_FIXTURE_NAME = "causal_rivers_horizon4.json"
_ABS_TOL = 1e-6
_REL_TOL = 1e-4


class CausalRiversFixturePair(BaseModel):
    """Snapshot for one driver at one fixed horizon."""

    model_config = ConfigDict(frozen=True)

    driver_id: int
    role: Literal["positive", "negative"]
    raw_cross_mi: float
    conditioned_cross_mi: float
    directness_ratio: float


class CausalRiversFixtureSnapshot(BaseModel):
    """Frozen horizon-4 snapshot for the causal-rivers extension surface."""

    model_config = ConfigDict(frozen=True)

    target_id: int
    horizon: int
    random_state: int
    target_ami: float
    target_pami: float
    pairs: list[CausalRiversFixturePair]


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser.

    Returns:
        Configured CLI parser.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=_DEFAULT_CONFIG_PATH,
        help="Path to the causal-rivers YAML config.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_DEFAULT_OUTPUT_DIR,
        help="Directory for the rebuilt fixture JSON.",
    )
    parser.add_argument(
        "--expected-dir",
        type=Path,
        default=_DEFAULT_EXPECTED_DIR,
        help="Directory containing the frozen expected fixture JSON.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify rebuilt output against the frozen expected fixture.",
    )
    return parser


def _build_snapshot(config_path: Path) -> CausalRiversFixtureSnapshot:
    """Build the deterministic horizon-4 snapshot.

    Args:
        config_path: YAML config path.

    Returns:
        Rebuilt fixture snapshot.
    """
    config = load_causal_rivers_config(config_path)
    frame = load_resampled_causal_rivers_frame(config)
    horizon = 4
    target = extract_station_series(frame, config.station_selection.target_id)
    target_baseline = compute_target_baseline_by_horizon(
        series_name=f"station_{config.station_selection.target_id}",
        target=target,
        horizons=[horizon],
        n_origins=config.rolling_origin.n_origins,
        random_state=config.metric.random_state,
        min_pairs_raw=config.metric.min_pairs_raw,
        min_pairs_partial=config.metric.min_pairs_partial,
        n_surrogates=config.metric.n_surrogates,
    )
    positive_driver_id = config.station_selection.positive_upstream[0]
    negative_driver_id = config.station_selection.negative_control[0]
    positive_target, positive_driver = extract_aligned_station_pair(
        frame,
        config.station_selection.target_id,
        positive_driver_id,
    )
    positive_pair = evaluate_causal_rivers_pair(
        config=config,
        target=positive_target,
        driver=positive_driver,
        station_id=positive_driver_id,
        role="positive",
    )
    negative_target, negative_driver = extract_aligned_station_pair(
        frame,
        config.station_selection.target_id,
        negative_driver_id,
    )
    negative_pair = evaluate_causal_rivers_pair(
        config=config,
        target=negative_target,
        driver=negative_driver,
        station_id=negative_driver_id,
        role="negative",
    )
    if (
        horizon not in target_baseline.ami_by_horizon
        or horizon not in target_baseline.pami_by_horizon
    ):
        raise ValueError(f"Missing target baseline values for horizon {horizon}")
    return CausalRiversFixtureSnapshot(
        target_id=config.station_selection.target_id,
        horizon=horizon,
        random_state=config.metric.random_state,
        target_ami=target_baseline.ami_by_horizon[horizon],
        target_pami=target_baseline.pami_by_horizon[horizon],
        pairs=[
            CausalRiversFixturePair(
                driver_id=positive_driver_id,
                role="positive",
                raw_cross_mi=positive_pair.raw_cross_mi_by_horizon[horizon],
                conditioned_cross_mi=positive_pair.conditioned_cross_mi_by_horizon[horizon],
                directness_ratio=positive_pair.directness_ratio_by_horizon[horizon],
            ),
            CausalRiversFixturePair(
                driver_id=negative_driver_id,
                role="negative",
                raw_cross_mi=negative_pair.raw_cross_mi_by_horizon[horizon],
                conditioned_cross_mi=negative_pair.conditioned_cross_mi_by_horizon[horizon],
                directness_ratio=negative_pair.directness_ratio_by_horizon[horizon],
            ),
        ],
    )


def _compare_payloads(
    actual: object,
    expected: object,
    *,
    path: str = "$",
) -> list[str]:
    """Compare nested payloads using ``math.isclose`` for floats.

    Args:
        actual: Rebuilt payload.
        expected: Frozen expected payload.
        path: Breadcrumb used in mismatch messages.

    Returns:
        List of mismatch descriptions.
    """
    if isinstance(expected, bool) or expected is None or isinstance(expected, str):
        return [] if actual == expected else [f"{path}: expected {expected!r}, got {actual!r}"]

    if isinstance(expected, int) and not isinstance(expected, bool):
        return [] if actual == expected else [f"{path}: expected {expected!r}, got {actual!r}"]

    if isinstance(expected, float):
        if isinstance(actual, bool) or not isinstance(actual, (int, float)):
            return [f"{path}: expected float {expected!r}, got {actual!r}"]
        if math.isclose(float(actual), expected, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
            return []
        return [f"{path}: expected {expected:.12g}, got {float(actual):.12g}"]

    if isinstance(expected, list):
        if not isinstance(actual, list):
            return [f"{path}: expected list, got {type(actual).__name__}"]
        errors: list[str] = []
        if len(actual) != len(expected):
            errors.append(f"{path}: expected length {len(expected)}, got {len(actual)}")
            return errors
        for index, (actual_item, expected_item) in enumerate(zip(actual, expected, strict=True)):
            errors.extend(_compare_payloads(actual_item, expected_item, path=f"{path}[{index}]"))
        return errors

    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected dict, got {type(actual).__name__}"]
        errors = []
        actual_keys = set(actual)
        expected_keys = set(expected)
        if actual_keys != expected_keys:
            missing = sorted(expected_keys - actual_keys)
            extra = sorted(actual_keys - expected_keys)
            if missing:
                errors.append(f"{path}: missing keys {missing}")
            if extra:
                errors.append(f"{path}: extra keys {extra}")
            return errors
        for key in sorted(expected):
            errors.extend(_compare_payloads(actual[key], expected[key], path=f"{path}.{key}"))
        return errors

    return [] if actual == expected else [f"{path}: expected {expected!r}, got {actual!r}"]


def main(argv: list[str] | None = None) -> int:
    """Rebuild the fixture and optionally verify against the frozen snapshot.

    Args:
        argv: Optional CLI args for programmatic invocation.

    Returns:
        Process exit code.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _build_parser().parse_args(argv)
    snapshot = _build_snapshot(args.config)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / _FIXTURE_NAME
    output_path.write_text(snapshot.model_dump_json(indent=2) + "\n", encoding="utf-8")
    _LOGGER.info("Wrote rebuilt fixture to %s", output_path)

    if not args.verify:
        return 0

    expected_path = args.expected_dir / _FIXTURE_NAME
    if not expected_path.exists():
        _LOGGER.error("Expected fixture not found: %s", expected_path)
        return 2

    expected_payload = json.loads(expected_path.read_text(encoding="utf-8"))
    actual_payload = json.loads(output_path.read_text(encoding="utf-8"))
    errors = _compare_payloads(actual_payload, expected_payload)
    if errors:
        _LOGGER.error("Verification FAILED:\n%s", "\n".join(errors))
        return 2

    _LOGGER.info("Verification passed — %s matches frozen expected.", expected_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
