"""Run canonical AMI/pAMI examples and persist artifacts."""

from __future__ import annotations

import argparse
import logging
import os
import time
from collections.abc import Sequence
from pathlib import Path
from typing import TypeAlias

import numpy as np
import pandas as pd

# Default to non-interactive plotting backend for script execution.
os.environ.setdefault("MPLBACKEND", "Agg")

from forecastability.pipeline import run_canonical_example
from forecastability.reporting import save_canonical_markdown, save_canonical_result_json
from forecastability.reporting.interpretation import interpret_canonical_result
from forecastability.utils.aggregation import summarize_canonical_result
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
from forecastability.utils.plots import save_all_canonical_plots

_logger = logging.getLogger(__name__)

CanonicalSpec: TypeAlias = tuple[str, np.ndarray, dict[str, str | int | float]]


def _log_progress(message: str, *, start_time: float | None = None) -> None:
    elapsed = f" (+{time.perf_counter() - start_time:.1f}s)" if start_time is not None else ""
    _logger.info("[%s]%s %s", time.strftime("%H:%M:%S"), elapsed, message)


def _extensions_enabled(*, with_extensions: bool, skip_bands: bool) -> bool:
    return with_extensions and not skip_bands


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
        "--with-extensions",
        action="store_true",
        help=(
            "Compute extension diagnostics (k-sensitivity and bootstrap uncertainty). "
            "Disabled by default because it is expensive."
        ),
    )
    return parser.parse_args(argv)


def main() -> None:
    """Run all canonical examples with figures and JSON/markdown outputs."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run_start = time.perf_counter()
    args = _parse_args()
    skip_bands: bool = args.no_bands
    run_extensions = _extensions_enabled(
        with_extensions=args.with_extensions,
        skip_bands=skip_bands,
    )
    output_root = Path("outputs")
    figures_dir = output_root / "figures" / "canonical"
    json_dir = output_root / "json" / "canonical"
    markdown_dir = output_root / "reports" / "canonical"
    tables_dir = output_root / "tables"

    _log_progress("Starting canonical triage run")
    if args.with_extensions and skip_bands:
        _log_progress(
            "--with-extensions requested with --no-bands; preserving "
            "no-bands behavior and skipping extensions"
        )
    elif run_extensions:
        _log_progress("Extension diagnostics enabled")
    else:
        _log_progress("Extension diagnostics disabled")

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

    # Load financial canonical series if available; skip gracefully if not downloaded yet
    _financial: list[tuple[str, object, dict[str, str | int | float]]] = [
        ("bitcoin_returns", None, {"seasonal_period": 0}),
        ("gold_returns", None, {"seasonal_period": 0}),
        ("crude_oil_returns", None, {"seasonal_period": 0}),
        ("aapl_returns", None, {"seasonal_period": 0}),
    ]
    _loaders = {
        "bitcoin_returns": load_bitcoin_returns,
        "gold_returns": load_gold_returns,
        "crude_oil_returns": load_crude_oil_returns,
        "aapl_returns": load_aapl_returns,
    }
    for fname, _, fmeta in _financial:
        try:
            datasets.append((fname, _loaders[fname](), fmeta))
        except FileNotFoundError:
            _logger.warning(
                "  Skipping %s: CSV not found. Run scripts/download_data.py first.",
                fname,
            )

    summary_payloads: list[CanonicalPayload] = []
    sensitivity_tables: list[pd.DataFrame] = []
    bootstrap_tables: list[pd.DataFrame] = []

    if run_extensions:
        from forecastability.extensions import (
            bootstrap_descriptor_uncertainty,
            compute_k_sensitivity,
        )

    n_datasets = len(datasets)
    for index, (name, series, metadata) in enumerate(datasets, start=1):
        dataset_start = time.perf_counter()
        # Adaptive lag caps: compute_ami needs n >= max_lag + 31,
        # compute_pami_linear_residual needs n >= max_lag + 51
        n = len(series)
        max_lag_ami = min(120, n - 31)
        max_lag_pami = min(80, n - 51)
        _log_progress(
            f"[{index}/{n_datasets}] {name}: core triage stage "
            f"(n={n}, max_lag_ami={max_lag_ami}, max_lag_pami={max_lag_pami})"
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
        _log_progress(f"{name}: core triage complete", start_time=triage_stage_start)

        write_stage_start = time.perf_counter()
        save_all_canonical_plots(result, output_dir=figures_dir)
        save_canonical_result_json(result, output_path=json_dir / f"{name}.json")
        save_canonical_markdown(result, output_path=markdown_dir / f"{name}.md")
        _log_progress(f"{name}: plots/json/markdown write complete", start_time=write_stage_start)

        summary = summarize_canonical_result(result)
        interpretation = interpret_canonical_result(result)
        if run_extensions:
            extensions_stage_start = time.perf_counter()
            sensitivity_tables.append(
                compute_k_sensitivity(
                    series_name=name,
                    ts=series,
                    k_values=[4, 8, 12, 16],
                    max_lag_ami=60,
                    max_lag_pami=40,
                    n_surrogates=99,
                    alpha=0.05,
                    random_state=42,
                )
            )
            bootstrap_tables.append(
                bootstrap_descriptor_uncertainty(
                    result,
                    n_bootstrap=300,
                    ci_level=0.95,
                    random_state=42,
                )
            )
            _log_progress(
                f"{name}: optional extensions complete",
                start_time=extensions_stage_start,
            )
        else:
            _log_progress(f"{name}: optional extensions skipped")
        summary_payloads.append(
            CanonicalPayload.from_summary_and_interpretation(
                series_name=name,
                summary=summary,
                interpretation=interpretation,
                include_narrative=False,
            )
        )
        _log_progress(f"{name}: dataset complete", start_time=dataset_start)

    summary_path = output_root / "json" / "canonical_examples_summary.json"
    CanonicalSummaryBundle(examples=summary_payloads).to_json_file(
        summary_path,
        exclude_none=True,
    )
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

    mode = "no-bands (fast)" if skip_bands else "with significance bands"
    extensions_mode = "enabled" if run_extensions else "disabled"
    _logger.info(
        "Saved canonical outputs for %d datasets (%s, extensions %s) in %.1fs.",
        len(summary_payloads),
        mode,
        extensions_mode,
        time.perf_counter() - run_start,
    )


if __name__ == "__main__":
    main()
