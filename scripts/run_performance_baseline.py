"""Run the Phase 1 deterministic performance baseline."""

from __future__ import annotations

import argparse
import statistics
import time
from pathlib import Path
from typing import cast

import numpy as np

from forecastability.triage.models import TriageRequest
from forecastability.use_cases import run_triage

try:
    from scripts.performance_common import (
        PerformanceBaselineConfig,
        PerformanceCaseConfig,
        load_performance_config,
        make_synthetic_series,
        measured_runtime,
        runtime_metadata,
        sha256_file,
        write_json,
    )
except ModuleNotFoundError:
    from performance_common import (
        PerformanceBaselineConfig,
        PerformanceCaseConfig,
        load_performance_config,
        make_synthetic_series,
        measured_runtime,
        runtime_metadata,
        sha256_file,
        write_json,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 1 performance baseline cases.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/performance_baseline.yaml"),
        help="Path to the performance baseline YAML config.",
    )
    return parser.parse_args()


def _run_case_once(case: PerformanceCaseConfig) -> dict[str, object]:
    series = make_synthetic_series(case)
    request = TriageRequest(
        series=series,
        max_lag=case.max_lag,
        n_surrogates=case.n_surrogates,
        random_state=case.random_state,
    )

    with measured_runtime() as measurement:
        result = run_triage(request)
    runtime = measurement()

    analyze = result.analyze_result
    compute_significance = (
        result.method_plan.compute_surrogates if result.method_plan is not None else False
    )
    raw_peak = float(np.max(analyze.raw)) if analyze is not None else float("nan")
    partial_peak = float(np.max(analyze.partial)) if analyze is not None else float("nan")
    return {
        "case_id": case.case_id,
        "size_label": case.size_label,
        "workflow": case.workflow,
        "n_obs": case.n_obs,
        "max_lag": case.max_lag,
        "n_surrogates": case.n_surrogates,
        "compute_significance_requested": case.compute_significance,
        "compute_significance": compute_significance,
        "random_state": case.random_state,
        "wall_time_s": runtime.wall_time_s,
        "cpu_time_s": runtime.cpu_time_s,
        "peak_memory_mb": runtime.peak_memory_mb,
        "blocked": result.blocked,
        "readiness_status": result.readiness.status.value,
        "raw_peak": raw_peak,
        "partial_peak": partial_peak,
    }


def _summarize_case(
    *,
    case: PerformanceCaseConfig,
    repeats: list[dict[str, object]],
) -> dict[str, object]:
    wall_times = [cast(float, item["wall_time_s"]) for item in repeats]
    cpu_times = [cast(float, item["cpu_time_s"]) for item in repeats]
    peak_memory = [cast(float, item["peak_memory_mb"]) for item in repeats]
    return {
        "case_id": case.case_id,
        "size_label": case.size_label,
        "workflow": case.workflow,
        "n_obs": case.n_obs,
        "max_lag": case.max_lag,
        "n_surrogates": case.n_surrogates,
        "compute_significance_requested": case.compute_significance,
        "compute_significance": bool(repeats[-1]["compute_significance"]),
        "random_state": case.random_state,
        "repeat_count": len(repeats),
        "median_wall_time_s": statistics.median(wall_times),
        "p95_wall_time_s": float(np.percentile(wall_times, 95)),
        "median_cpu_time_s": statistics.median(cpu_times),
        "p95_cpu_time_s": float(np.percentile(cpu_times, 95)),
        "max_peak_memory_mb": max(peak_memory),
        "blocked": cast(bool, repeats[-1]["blocked"]),
        "readiness_status": cast(str, repeats[-1]["readiness_status"]),
        "raw_peak": cast(float, repeats[-1]["raw_peak"]),
        "partial_peak": cast(float, repeats[-1]["partial_peak"]),
    }


def _run_baseline(
    config: PerformanceBaselineConfig,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    case_summaries: list[dict[str, object]] = []
    repeat_rows: list[dict[str, object]] = []

    for case in config.cases:
        repeats: list[dict[str, object]] = []
        for repeat_index in range(config.metadata.repeats):
            row = _run_case_once(case)
            row["repeat_index"] = repeat_index
            repeats.append(row)
            repeat_rows.append(row)
        case_summaries.append(_summarize_case(case=case, repeats=repeats))
    return case_summaries, repeat_rows


def main() -> None:
    """Run configured synthetic baselines and write ``performance_summary.json``."""
    args = _parse_args()
    config_hash = sha256_file(args.config)
    if config_hash is None:
        raise FileNotFoundError(args.config)
    config = load_performance_config(args.config)
    output_dir = Path(config.metadata.output_dir)

    start_wall = time.perf_counter()
    start_cpu = time.process_time()
    case_summaries, repeat_rows = _run_baseline(config)
    summary = {
        "schema_version": 1,
        "artifact_type": "performance_baseline_summary",
        "metadata": config.metadata.model_dump(),
        "command_metadata": runtime_metadata(config_path=args.config, config_hash=config_hash),
        "total_wall_time_s": time.perf_counter() - start_wall,
        "total_cpu_time_s": time.process_time() - start_cpu,
        "cases": case_summaries,
        "repeats": repeat_rows,
    }
    write_json(output_dir / "performance_summary.json", summary)
    print(f"Wrote {output_dir / 'performance_summary.json'}")


if __name__ == "__main__":
    main()
