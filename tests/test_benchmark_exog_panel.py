from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from forecastability.exog_benchmark import run_benchmark_exog_panel


def test_exog_benchmark_runner_writes_expected_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg_path = tmp_path / "benchmark_exog_panel.yaml"
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "purpose": "benchmark_exog_panel",
                "rolling_origin": {"n_origins": 3, "horizons": [1, 2]},
                "metric": {"n_surrogates": 99, "random_state": 42},
                "slice_case_ids": [
                    "bike_cnt_temp",
                    "bike_cnt_hum",
                    "bike_cnt_noise",
                    "aapl_spy",
                    "aapl_noise",
                    "btc_eth",
                    "btc_noise",
                ],
                "analysis_scope": "both",
                "project_extension": True,
            }
        ),
        encoding="utf-8",
    )

    def _fake_load_slice(case_ids: list[str]) -> list[tuple[str, str, str, np.ndarray, np.ndarray]]:
        base = np.linspace(0.0, 1.0, 90)
        cases = []
        for offset, case_id in enumerate(case_ids):
            target = base + offset
            exog = base[::-1] + offset
            target_name, exog_name = case_id.split("_", maxsplit=1)
            cases.append((case_id, target_name, exog_name, target, exog))
        return cases

    monkeypatch.setattr("forecastability.exog_benchmark.load_benchmark_slice", _fake_load_slice)

    run_benchmark_exog_panel(cfg_path=cfg_path, output_root=tmp_path / "outputs")

    horizon_path = tmp_path / "outputs/tables/exog_benchmark/horizon_table.csv"
    summary_path = tmp_path / "outputs/tables/exog_benchmark/case_summary.csv"
    figure_path = tmp_path / "outputs/figures/exog_benchmark/raw_vs_conditioned.png"
    report_path = tmp_path / "outputs/reports/benchmark_exog_panel.md"

    assert horizon_path.exists()
    assert summary_path.exists()
    assert figure_path.exists()
    assert figure_path.stat().st_size > 0
    assert report_path.exists()

    horizon = pd.read_csv(horizon_path)
    summary = pd.read_csv(summary_path)
    report = report_path.read_text(encoding="utf-8")

    assert {
        "case_id",
        "target_name",
        "exog_name",
        "horizon",
        "raw_cross_mi",
        "conditioned_cross_mi",
        "directness_ratio",
        "origins_used",
        "warning_directness_gt_one",
    }.issubset(horizon.columns)
    assert {
        "case_id",
        "mean_raw_cross_mi",
        "mean_conditioned_cross_mi",
        "mean_directness_ratio",
        "warning_note",
    }.issubset(summary.columns)
    assert "both descriptive analysis and bounded model-selection guidance" in report
    assert "project extensions" in report
