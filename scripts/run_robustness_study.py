"""Run pAMI robustness study comparing backends and sample-size stability."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

# Non-interactive plotting backend.
os.environ.setdefault("MPLBACKEND", "Agg")

from forecastability.config import RobustnessStudyConfig
from forecastability.datasets import (
    generate_henon_map,
    generate_simulated_stock_returns,
    generate_sine_wave,
    load_air_passengers,
)
from forecastability.robustness import run_robustness_study

_logger = logging.getLogger(__name__)


def _load_config(path: Path) -> RobustnessStudyConfig:
    """Load robustness study config from YAML."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    metric = raw.get("metric", {})
    stability = raw.get("stability", {})
    return RobustnessStudyConfig(
        backends=raw["backends"],
        sample_fractions=raw["sample_fractions"],
        max_lag_ami=metric.get("max_lag_ami", 60),
        max_lag_pami=metric.get("max_lag_pami", 40),
        n_neighbors=metric.get("n_neighbors", 8),
        n_surrogates=metric.get("n_surrogates", 99),
        alpha=metric.get("alpha", 0.05),
        random_state=metric.get("random_state", 42),
        rank_stability_threshold=stability.get("rank_stability_threshold", 0.8),
        directness_stability_threshold=stability.get("directness_stability_threshold", 0.15),
        min_series_length=stability.get("min_series_length", 100),
    )


def _load_datasets() -> list[tuple[str, np.ndarray]]:
    """Load canonical datasets for the robustness study."""
    datasets: list[tuple[str, np.ndarray]] = [
        ("sine_wave", generate_sine_wave()),
        ("air_passengers", load_air_passengers()),
        ("henon_map", generate_henon_map()),
        ("simulated_stock_returns", generate_simulated_stock_returns()),
    ]
    return datasets


def _save_backend_csv(result: object, path: Path) -> None:
    """Save backend comparison results as CSV."""
    from forecastability.types import RobustnessStudyResult

    assert isinstance(result, RobustnessStudyResult)
    rows: list[dict[str, str | int | float | bool | None]] = []
    for bc in result.backend_comparisons:
        for entry in bc.entries:
            rows.append(
                {
                    "series_name": bc.series_name,
                    "backend": entry.backend,
                    "n_sig_ami": entry.n_sig_ami,
                    "n_sig_pami": entry.n_sig_pami,
                    "n_sig_pami_delta_vs_linear": entry.n_sig_pami_delta_vs_linear,
                    "directness_ratio": entry.directness_ratio,
                    "directness_ratio_delta_vs_linear": entry.directness_ratio_delta_vs_linear,
                    "auc_ami": entry.auc_ami,
                    "auc_pami": entry.auc_pami,
                    "auc_pami_delta_vs_linear": entry.auc_pami_delta_vs_linear,
                    "directness_ratio_warning": entry.directness_ratio_warning,
                    "rank_correlation": bc.rank_correlation,
                    "lag_ranking_stable": bc.lag_ranking_stable,
                    "directness_ratio_stable": bc.directness_ratio_stable,
                }
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def _save_stress_csv(result: object, path: Path) -> None:
    """Save sample-size stress results as CSV."""
    from forecastability.types import RobustnessStudyResult

    assert isinstance(result, RobustnessStudyResult)
    rows: list[dict[str, str | int | float | bool]] = []
    for ss in result.sample_size_tests:
        for entry in ss.entries:
            rows.append(
                {
                    "series_name": ss.series_name,
                    "fraction": entry.fraction,
                    "n_observations": entry.n_observations,
                    "directness_ratio": entry.directness_ratio,
                    "auc_ami": entry.auc_ami,
                    "auc_pami": entry.auc_pami,
                    "n_sig_ami": entry.n_sig_ami,
                    "n_sig_pami": entry.n_sig_pami,
                    "directness_ratio_warning": entry.directness_ratio_warning,
                    "directness_ratio_stable": ss.directness_ratio_stable,
                }
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def main() -> None:
    """Run the full robustness study and save outputs."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    config_path = Path("configs/robustness_study.yaml")
    config = _load_config(config_path)
    _logger.info("Loaded config from %s", config_path)

    datasets = _load_datasets()
    _logger.info("Running robustness study on %d datasets", len(datasets))

    result = run_robustness_study(datasets, config=config)

    # Save JSON
    json_dir = Path("outputs/json")
    json_dir.mkdir(parents=True, exist_ok=True)
    json_path = json_dir / "robustness_study.json"
    json_path.write_text(
        result.model_dump_json(indent=2),
        encoding="utf-8",
    )
    _logger.info("Saved JSON to %s", json_path)

    # Save CSV tables
    tables_dir = Path("outputs/tables")
    _save_backend_csv(result, tables_dir / "robustness_backend_comparison.csv")
    _logger.info("Saved backend comparison CSV")
    _save_stress_csv(result, tables_dir / "robustness_sample_stress.csv")
    _logger.info("Saved sample stress CSV")

    _logger.info("Overall stable: %s", result.overall_stable)
    _logger.info("Narrative: %s", result.summary_narrative)


if __name__ == "__main__":
    main()
