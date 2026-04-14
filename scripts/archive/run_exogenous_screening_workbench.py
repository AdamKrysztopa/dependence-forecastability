"""Run a target-plus-many-drivers exogenous screening workbench."""

from __future__ import annotations

import argparse
import csv
import json
import logging
from pathlib import Path

import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from forecastability.use_cases.run_exogenous_screening_workbench import (
    DRIVER_SUMMARY_TABLE_COLUMNS,
    HORIZON_USEFULNESS_TABLE_COLUMNS,
    LAG_WINDOW_SUMMARY_TABLE_COLUMNS,
    build_workbench_markdown,
    driver_summary_table_rows,
    horizon_usefulness_table_rows,
    lag_window_summary_table_rows,
    run_exogenous_screening_workbench,
)
from forecastability.utils.config import ExogenousScreeningWorkbenchConfig

_logger = logging.getLogger(__name__)


class ExogenousScreeningInputPayload(BaseModel):
    """Input payload for one exogenous screening run."""

    model_config = ConfigDict(frozen=True)

    target_name: str
    target: list[float]
    drivers: dict[str, list[float]]

    @field_validator("target")
    @classmethod
    def _target_non_empty(cls, value: list[float]) -> list[float]:
        if len(value) == 0:
            raise ValueError("target must contain at least one observation")
        return value

    @field_validator("drivers")
    @classmethod
    def _drivers_non_empty(cls, value: dict[str, list[float]]) -> dict[str, list[float]]:
        if len(value) == 0:
            raise ValueError("drivers must contain at least one candidate")
        for driver_name, series in value.items():
            if len(series) == 0:
                raise ValueError(f"driver '{driver_name}' has an empty series")
        return value


def _load_input_payload(path: Path) -> ExogenousScreeningInputPayload:
    """Load and validate a workbench input JSON payload."""
    if not path.exists():
        raise FileNotFoundError(f"Input JSON payload not found: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Unable to read input JSON payload {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in input payload {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("Input payload root must be a JSON object.")

    try:
        return ExogenousScreeningInputPayload.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Invalid input payload schema: {exc}") from exc


def _load_config(path: Path) -> ExogenousScreeningWorkbenchConfig:
    """Load and validate a YAML workbench config."""
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    try:
        raw_cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Unable to read config file {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in config file {path}: {exc}") from exc

    if raw_cfg is None:
        raw_cfg = {}
    if not isinstance(raw_cfg, dict):
        raise ValueError("Config root must be a YAML mapping.")

    try:
        return ExogenousScreeningWorkbenchConfig.model_validate(raw_cfg)
    except ValidationError as exc:
        raise ValueError(f"Invalid screening config schema: {exc}") from exc


def _write_table_csv(
    path: Path,
    *,
    columns: tuple[str, ...],
    rows: list[dict[str, object]],
) -> None:
    """Write one deterministic CSV table with stable column order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in columns})


def _build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for workbench execution."""
    parser = argparse.ArgumentParser(
        description=(
            "Run an exogenous screening workbench for one target and many candidate drivers."
        )
    )
    parser.add_argument(
        "--input-json",
        required=True,
        help=(
            "Path to input JSON with target_name, target values, and a drivers "
            "name-to-series mapping."
        ),
    )
    parser.add_argument(
        "--config",
        default="configs/exogenous_screening_workbench.yaml",
        help="Path to YAML screening config.",
    )
    parser.add_argument(
        "--tables-dir",
        default="outputs/tables/exog_screening_workbench",
        help="Directory for screening CSV tables.",
    )
    parser.add_argument(
        "--report-path",
        default="outputs/reports/exogenous_screening_workbench.md",
        help="Output markdown summary path.",
    )
    parser.add_argument(
        "--json-path",
        default="outputs/json/exogenous_screening_workbench.json",
        help="Output JSON payload path.",
    )
    return parser


def main() -> None:
    """Script entrypoint."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _build_parser().parse_args()

    payload = _load_input_payload(Path(args.input_json))
    config = _load_config(Path(args.config))

    target = np.asarray(payload.target, dtype=np.float64)
    drivers = {
        driver_name: np.asarray(series, dtype=np.float64)
        for driver_name, series in payload.drivers.items()
    }

    result = run_exogenous_screening_workbench(
        target,
        drivers,
        target_name=payload.target_name,
        config=config,
    )

    tables_dir = Path(args.tables_dir)
    summary_csv = tables_dir / "driver_summary.csv"
    horizon_csv = tables_dir / "horizon_usefulness.csv"
    lag_window_csv = tables_dir / "lag_window_summary.csv"

    _write_table_csv(
        summary_csv,
        columns=DRIVER_SUMMARY_TABLE_COLUMNS,
        rows=driver_summary_table_rows(result),
    )
    _write_table_csv(
        horizon_csv,
        columns=HORIZON_USEFULNESS_TABLE_COLUMNS,
        rows=horizon_usefulness_table_rows(result),
    )
    _write_table_csv(
        lag_window_csv,
        columns=LAG_WINDOW_SUMMARY_TABLE_COLUMNS,
        rows=lag_window_summary_table_rows(result),
    )

    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(build_workbench_markdown(result), encoding="utf-8")

    json_path = Path(args.json_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    _logger.info("Driver summary table saved to %s", summary_csv)
    _logger.info("Horizon usefulness table saved to %s", horizon_csv)
    _logger.info("Lag-window summary table saved to %s", lag_window_csv)
    _logger.info("Markdown report saved to %s", report_path)
    _logger.info("JSON payload saved to %s", json_path)


if __name__ == "__main__":
    main()
