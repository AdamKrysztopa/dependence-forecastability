"""Run canonical AMI/pAMI examples and persist artifacts."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import TypeAlias

import numpy as np
import pandas as pd

# Default to non-interactive plotting backend for script execution.
os.environ.setdefault("MPLBACKEND", "Agg")

from forecastability.extensions import bootstrap_descriptor_uncertainty, compute_k_sensitivity
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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run canonical AMI/pAMI examples.")
    parser.add_argument(
        "--no-bands",
        action="store_true",
        help=(
            "Skip surrogate significance-band computation and bootstrap/k-sensitivity. "
            "Produces plots without significance bands but runs ~50x faster."
        ),
    )
    return parser.parse_args()


def main() -> None:
    """Run all canonical examples with figures and JSON/markdown outputs."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args()
    skip_bands: bool = args.no_bands
    output_root = Path("outputs")
    figures_dir = output_root / "figures" / "canonical"
    json_dir = output_root / "json" / "canonical"
    markdown_dir = output_root / "reports" / "canonical"
    tables_dir = output_root / "tables"

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

    for name, series, metadata in datasets:
        # Adaptive lag caps: compute_ami needs n >= max_lag + 31,
        # compute_pami_linear_residual needs n >= max_lag + 51
        n = len(series)
        max_lag_ami = min(120, n - 31)
        max_lag_pami = min(80, n - 51)
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

        save_all_canonical_plots(result, output_dir=figures_dir)
        save_canonical_result_json(result, output_path=json_dir / f"{name}.json")
        save_canonical_markdown(result, output_path=markdown_dir / f"{name}.md")

        summary = summarize_canonical_result(result)
        interpretation = interpret_canonical_result(result)
        if not skip_bands:
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
        summary_payloads.append(
            CanonicalPayload.from_summary_and_interpretation(
                series_name=name,
                summary=summary,
                interpretation=interpretation,
                include_narrative=False,
            )
        )

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
    _logger.info("Saved canonical outputs for %d datasets (%s).", len(summary_payloads), mode)


if __name__ == "__main__":
    main()
