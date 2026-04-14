"""Generate multi-series comparison artifacts from batch triage payloads."""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

from pydantic import ValidationError

# Default to non-interactive plotting backend for script execution.
os.environ.setdefault("MPLBACKEND", "Agg")

from forecastability.triage.batch_models import BatchTriageRequest
from forecastability.triage.comparison_report import (
    build_multi_series_comparison_report,
    write_multi_series_comparison_artifacts,
)
from forecastability.use_cases.run_triage import run_triage

_logger = logging.getLogger(__name__)


def _load_batch_request(path: Path) -> BatchTriageRequest:
    """Load and validate one batch triage request JSON payload."""
    if not path.exists():
        raise FileNotFoundError(f"Batch JSON payload not found: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Unable to read batch JSON payload {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in batch payload {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("Batch payload root must be a JSON object.")

    try:
        return BatchTriageRequest.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Invalid batch payload schema: {exc}") from exc


def _build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for the multi-series comparison artifact script."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate standardized multi-series comparison tables, plots, and "
            "recommendation summary from a batch triage payload."
        )
    )
    parser.add_argument(
        "--batch-json",
        required=True,
        help="Path to the batch triage JSON payload used by triage-batch.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="Maximum number of series to recommend for deeper modeling.",
    )
    parser.add_argument(
        "--tables-dir",
        default="outputs/tables/comparison",
        help="Directory for standardized comparison CSV tables.",
    )
    parser.add_argument(
        "--figures-dir",
        default="outputs/figures/comparison",
        help="Directory for comparison PNG plots.",
    )
    parser.add_argument(
        "--report-path",
        default="outputs/reports/multi_series_comparison_report.md",
        help="Markdown summary output path.",
    )
    parser.add_argument(
        "--report-json-path",
        default=None,
        help="Optional JSON path for the full in-memory comparison payload.",
    )
    return parser


def main() -> None:
    """Script entrypoint."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _build_parser().parse_args()

    request = _load_batch_request(Path(args.batch_json))
    report = build_multi_series_comparison_report(
        request,
        triage_runner=run_triage,
        top_n=args.top_n,
    )

    paths = write_multi_series_comparison_artifacts(
        report,
        tables_dir=Path(args.tables_dir),
        figures_dir=Path(args.figures_dir),
        report_path=Path(args.report_path),
    )

    if args.report_json_path is not None:
        json_path = Path(args.report_json_path)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        _logger.info("Comparison payload JSON saved to %s", json_path)

    _logger.info("Series comparison table saved to %s", paths.series_table_csv)
    _logger.info("Horizon drop-off table saved to %s", paths.horizon_dropoff_csv)
    _logger.info("Recommendations table saved to %s", paths.recommendations_csv)
    _logger.info("AUC plot saved to %s", paths.auc_plot_png)
    _logger.info("Directness plot saved to %s", paths.directness_plot_png)
    _logger.info("Significance plot saved to %s", paths.significance_plot_png)
    _logger.info("Horizon drop-off plot saved to %s", paths.horizon_dropoff_plot_png)
    _logger.info("Report summary saved to %s", paths.report_markdown)


if __name__ == "__main__":
    main()
