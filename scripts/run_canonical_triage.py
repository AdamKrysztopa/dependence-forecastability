"""Run canonical AMI/pAMI examples and persist artifacts."""

from __future__ import annotations

import argparse
import logging
import os
import time
from collections.abc import Sequence
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import NamedTuple, TypeAlias

import numpy as np
import pandas as pd

# Default to non-interactive plotting backend for script execution.
os.environ.setdefault("MPLBACKEND", "Agg")

from forecastability.pipeline import run_canonical_example
from forecastability.reporting import (
    build_canonical_panel_markdown,
    save_canonical_markdown,
    save_canonical_result_json,
)
from forecastability.utils.datasets import (
    generate_henon_map,
    generate_simulated_stock_returns,
    generate_sine_wave,
    load_aapl_returns,
    load_air_passengers,
    load_bitcoin_returns,
    load_crude_oil_returns,
    load_gold_returns,
)
from forecastability.utils.io_models import CanonicalPayload, CanonicalSummaryBundle
from forecastability.utils.plots import plot_canonical_panel_summary, save_all_canonical_plots
from forecastability.utils.types import CanonicalExampleResult

_logger = logging.getLogger(__name__)

CanonicalSpec: TypeAlias = tuple[str, np.ndarray, dict[str, str | int | float]]

CORE_CANONICAL_DATASET_NAMES = frozenset(
    {
        "sine_wave",
        "air_passengers",
        "henon_map",
        "simulated_stock_returns",
    }
)
EXTENDED_FINANCIAL_DATASET_NAMES = frozenset(
    {
        "bitcoin_returns",
        "gold_returns",
        "crude_oil_returns",
        "aapl_returns",
    }
)


class _DatasetRunOutput(NamedTuple):
    """In-memory output for one dataset before artifacts are written."""

    index: int
    result: CanonicalExampleResult
    report_payload: CanonicalPayload
    sensitivity_table: pd.DataFrame | None
    bootstrap_table: pd.DataFrame | None


def _log_progress(message: str, *, start_time: float | None = None) -> None:
    elapsed = f" (+{time.perf_counter() - start_time:.1f}s)" if start_time is not None else ""
    _logger.info("[%s]%s %s", time.strftime("%H:%M:%S"), elapsed, message)


def _extensions_enabled(*, with_extensions: bool, skip_bands: bool) -> bool:
    return with_extensions and not skip_bands


def _skip_bands_for_dataset(
    dataset_name: str,
    *,
    skip_bands: bool,
    full_bands: bool,
) -> bool:
    if skip_bands:
        return True
    if full_bands:
        return False
    return dataset_name in EXTENDED_FINANCIAL_DATASET_NAMES


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be >= 1")
    return parsed


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run canonical AMI/pAMI examples.")
    parser.add_argument(
        "--no-bands",
        action="store_true",
        help=(
            "Skip surrogate significance-band computation and bootstrap/k-sensitivity. "
            "Produces plots without significance bands but runs ~50x faster."
        ),
    )
    parser.add_argument(
        "--full-bands",
        action="store_true",
        help=(
            "Force surrogate significance-band computation for every canonical dataset, "
            "including the extended financial series."
        ),
    )
    parser.add_argument(
        "--with-extensions",
        action="store_true",
        help=(
            "Compute extension diagnostics (k-sensitivity and bootstrap uncertainty). "
            "Disabled by default because it is expensive."
        ),
    )
    parser.add_argument(
        "--max-workers",
        type=_positive_int,
        default=None,
        help=(
            "Dataset-level worker count for canonical runs. Defaults to "
            "min(4, cpu_count, n_datasets). Use 1 to force sequential execution."
        ),
    )
    return parser.parse_args(argv)


def _load_canonical_datasets() -> list[CanonicalSpec]:
    """Load the canonical dataset list in deterministic order."""
    datasets: list[CanonicalSpec] = [
        ("sine_wave", generate_sine_wave(), {"seasonal_period": 0}),
        ("air_passengers", load_air_passengers(), {"seasonal_period": 12}),
        ("henon_map", generate_henon_map(), {"seasonal_period": 0}),
        (
            "simulated_stock_returns",
            generate_simulated_stock_returns(),
            {"seasonal_period": 0},
        ),
    ]

    financial_loaders = {
        "bitcoin_returns": load_bitcoin_returns,
        "gold_returns": load_gold_returns,
        "crude_oil_returns": load_crude_oil_returns,
        "aapl_returns": load_aapl_returns,
    }
    for dataset_name in [
        "bitcoin_returns",
        "gold_returns",
        "crude_oil_returns",
        "aapl_returns",
    ]:
        try:
            datasets.append(
                (
                    dataset_name,
                    financial_loaders[dataset_name](),
                    {"seasonal_period": 0},
                )
            )
        except FileNotFoundError:
            _logger.warning(
                "  Skipping %s: CSV not found. Run scripts/download_data.py first.",
                dataset_name,
            )

    return datasets


def _resolve_max_workers(requested: int | None, *, n_datasets: int) -> int:
    if n_datasets < 1:
        raise ValueError("n_datasets must be at least 1")
    if requested is None:
        return max(1, min(4, os.cpu_count() or 1, n_datasets))
    return min(requested, n_datasets)


def _compute_lag_caps(series: np.ndarray) -> tuple[int, int]:
    """Compute adaptive lag caps without changing statistical logic."""
    n_obs = len(series)
    return min(120, n_obs - 31), min(80, n_obs - 51)


def _strip_payload_narrative(payload: CanonicalPayload) -> CanonicalPayload:
    """Preserve the existing summary payload shape by omitting narratives."""
    return payload.model_copy(
        update={
            "interpretation": payload.interpretation.model_copy(update={"narrative": None}),
        }
    )


def _run_dataset(
    index: int,
    n_datasets: int,
    spec: CanonicalSpec,
    *,
    skip_bands: bool,
    run_extensions: bool,
) -> _DatasetRunOutput:
    """Run the compute-heavy portion of one canonical dataset."""
    name, series, metadata = spec
    dataset_start = time.perf_counter()
    max_lag_ami, max_lag_pami = _compute_lag_caps(series)
    _log_progress(
        f"[{index}/{n_datasets}] {name}: core triage stage "
        f"(n={len(series)}, max_lag_ami={max_lag_ami}, max_lag_pami={max_lag_pami})"
    )

    triage_stage_start = time.perf_counter()
    result = run_canonical_example(
        name,
        series,
        max_lag_ami=max_lag_ami,
        max_lag_pami=max_lag_pami,
        n_neighbors=8,
        n_surrogates=99,
        alpha=0.05,
        random_state=42,
        metadata=metadata,
        skip_bands=skip_bands,
    )
    _log_progress(
        f"[{index}/{n_datasets}] {name}: core triage complete",
        start_time=triage_stage_start,
    )

    sensitivity_table: pd.DataFrame | None = None
    bootstrap_table: pd.DataFrame | None = None
    if run_extensions:
        from forecastability.extensions import (
            bootstrap_descriptor_uncertainty,
            compute_k_sensitivity,
        )

        extensions_stage_start = time.perf_counter()
        sensitivity_table = compute_k_sensitivity(
            series_name=name,
            ts=series,
            k_values=[4, 8, 12, 16],
            max_lag_ami=60,
            max_lag_pami=40,
            n_surrogates=99,
            alpha=0.05,
            random_state=42,
        )
        bootstrap_table = bootstrap_descriptor_uncertainty(
            result,
            n_bootstrap=300,
            ci_level=0.95,
            random_state=42,
        )
        _log_progress(
            f"[{index}/{n_datasets}] {name}: optional extensions complete",
            start_time=extensions_stage_start,
        )
    else:
        _log_progress(f"[{index}/{n_datasets}] {name}: optional extensions skipped")

    report_payload = CanonicalPayload.from_result(result, include_narrative=True)
    _log_progress(
        f"[{index}/{n_datasets}] {name}: compute pipeline complete",
        start_time=dataset_start,
    )
    return _DatasetRunOutput(
        index=index,
        result=result,
        report_payload=report_payload,
        sensitivity_table=sensitivity_table,
        bootstrap_table=bootstrap_table,
    )


def run_canonical_triage(
    *,
    skip_bands: bool,
    full_bands: bool = False,
    with_extensions: bool,
    max_workers: int | None = None,
    output_root: Path = Path("outputs"),
) -> None:
    """Run all canonical examples with deterministic aggregation and outputs."""
    run_start = time.perf_counter()
    figures_dir = output_root / "figures" / "canonical"
    json_dir = output_root / "json" / "canonical"
    markdown_dir = output_root / "reports" / "canonical"
    tables_dir = output_root / "tables"

    _log_progress("Starting canonical triage run")
    if skip_bands and full_bands:
        _log_progress("--full-bands requested with --no-bands; preserving no-bands override")
    if skip_bands:
        _log_progress("No-bands override enabled for all canonical datasets")
    elif full_bands:
        _log_progress("Full-bands mode enabled for all canonical datasets")
    else:
        _log_progress(
            "Default mixed mode enabled: core canonical examples keep bands; "
            "extended financial series skip bands"
        )

    if with_extensions and skip_bands:
        _log_progress(
            "--with-extensions requested with --no-bands; preserving "
            "no-bands behavior and skipping extensions"
        )
    elif with_extensions and not full_bands:
        _log_progress("Extension diagnostics enabled only for datasets that keep bands")
    elif with_extensions:
        _log_progress("Extension diagnostics enabled")
    else:
        _log_progress("Extension diagnostics disabled")

    datasets = _load_canonical_datasets()
    n_datasets = len(datasets)
    worker_count = _resolve_max_workers(max_workers, n_datasets=n_datasets)
    _log_progress(f"Loaded {n_datasets} canonical datasets")
    _log_progress(f"Using {worker_count} dataset worker(s)")

    dataset_outputs: dict[int, _DatasetRunOutput] = {}
    # Compute datasets independently in parallel, then write artifacts in a fixed order.
    with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="canonical") as executor:
        future_to_dataset: dict[Future[_DatasetRunOutput], tuple[int, str]] = {}
        for index, spec in enumerate(datasets, start=1):
            dataset_name = spec[0]
            dataset_skip_bands = _skip_bands_for_dataset(
                dataset_name,
                skip_bands=skip_bands,
                full_bands=full_bands,
            )
            dataset_run_extensions = _extensions_enabled(
                with_extensions=with_extensions,
                skip_bands=dataset_skip_bands,
            )
            queue_mode = "no-bands" if dataset_skip_bands else "bands"
            if dataset_run_extensions:
                queue_mode = f"{queue_mode}, extensions"
            _log_progress(f"[{index}/{n_datasets}] {dataset_name}: queued ({queue_mode})")
            future = executor.submit(
                _run_dataset,
                index,
                n_datasets,
                spec,
                skip_bands=dataset_skip_bands,
                run_extensions=dataset_run_extensions,
            )
            future_to_dataset[future] = (index, dataset_name)

        for future in as_completed(future_to_dataset):
            completed = future.result()
            dataset_outputs[completed.index] = completed
            _log_progress(
                f"[{completed.index}/{n_datasets}] {completed.result.series_name}: "
                "result collected for deterministic write stage"
            )

    ordered_outputs = [dataset_outputs[index] for index in range(1, n_datasets + 1)]
    report_payloads: list[CanonicalPayload] = []
    sensitivity_tables: list[pd.DataFrame] = []
    bootstrap_tables: list[pd.DataFrame] = []

    for output in ordered_outputs:
        result = output.result
        write_stage_start = time.perf_counter()
        save_all_canonical_plots(result, output_dir=figures_dir)
        save_canonical_result_json(result, output_path=json_dir / f"{result.series_name}.json")
        save_canonical_markdown(result, output_path=markdown_dir / f"{result.series_name}.md")
        _log_progress(
            f"{result.series_name}: plots/json/markdown write complete",
            start_time=write_stage_start,
        )
        report_payloads.append(output.report_payload)
        if output.sensitivity_table is not None:
            sensitivity_tables.append(output.sensitivity_table)
        if output.bootstrap_table is not None:
            bootstrap_tables.append(output.bootstrap_table)

    summary_stage_start = time.perf_counter()
    summary_path = output_root / "json" / "canonical_examples_summary.json"
    CanonicalSummaryBundle(
        examples=[_strip_payload_narrative(payload) for payload in report_payloads]
    ).to_json_file(summary_path, exclude_none=True)
    plot_canonical_panel_summary(
        report_payloads,
        save_path=figures_dir / "canonical_panel_summary.png",
    )
    panel_report_path = markdown_dir / "canonical_panel_summary.md"
    panel_report_path.parent.mkdir(parents=True, exist_ok=True)
    panel_report_path.write_text(
        build_canonical_panel_markdown(payloads=report_payloads),
        encoding="utf-8",
    )
    _log_progress("Cross-series summary artifacts written", start_time=summary_stage_start)

    tables_dir.mkdir(parents=True, exist_ok=True)
    if sensitivity_tables:
        pd.concat(sensitivity_tables, ignore_index=True).to_csv(
            tables_dir / "k_sensitivity.csv",
            index=False,
        )
    if bootstrap_tables:
        pd.concat(bootstrap_tables, ignore_index=True).to_csv(
            tables_dir / "bootstrap_uncertainty.csv",
            index=False,
        )

    if skip_bands:
        mode = "no-bands (fast)"
    elif full_bands:
        mode = "full-bands"
    else:
        mode = "mixed default (core banded, extended descriptive)"
    extensions_mode = "enabled" if with_extensions and not skip_bands else "disabled"
    _logger.info(
        "Saved canonical outputs for %d datasets (%s, extensions %s) in %.1fs.",
        len(report_payloads),
        mode,
        extensions_mode,
        time.perf_counter() - run_start,
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Run the canonical triage script from the command line."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args(argv)
    run_canonical_triage(
        skip_bands=args.no_bands,
        full_bands=args.full_bands,
        with_extensions=args.with_extensions,
        max_workers=args.max_workers,
    )


if __name__ == "__main__":
    main()
