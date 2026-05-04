"""Run the Phase 1 deterministic performance baseline."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import statistics
import subprocess
import sys
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


def _bench_public_workflows(
    cases: list[dict[str, object]],
    rng: np.random.Generator,
    *,
    version: str,
) -> list[dict[str, object]]:
    """Benchmark public-workflow entries from the ``public_workflows`` config section.

    Args:
        cases: Raw workflow case dicts from the YAML config.
        rng: NumPy random generator for deterministic test-data generation.
        version: Installed forecastability version string for artifact labelling.

    Returns:
        List of result dicts with keys ``name``, ``method``, ``elapsed_s``, ``version``.
    """
    from forecastability.use_cases import (  # noqa: PLC0415
        run_covariant_analysis,
        run_lagged_exogenous_triage,
    )

    results: list[dict[str, object]] = []
    for case in cases:
        name = str(case["name"])
        method = str(case["method"])

        if method == "import":
            start = time.perf_counter()
            subprocess.run(
                [sys.executable, "-c", "import forecastability"],
                check=True,
                capture_output=True,
            )
            elapsed: float = time.perf_counter() - start
            results.append(
                {"name": name, "method": method, "elapsed_s": elapsed, "version": version}
            )
            continue

        if method in {"run_covariant_analysis", "run_lagged_exogenous_triage"}:
            series_length = int(cast(int, case["series_length"]))
            n_series = int(cast(int, case.get("n_series", 2)))
            max_lag = int(cast(int, case["max_lag"]))
            significance_mode = str(case.get("significance_mode", "phase"))
            n_surrogates = int(cast(int, case.get("n_surrogates", 99)))
            target = rng.normal(size=series_length)
            drivers = {f"driver_{i}": rng.normal(size=series_length) for i in range(n_series)}

            start = time.perf_counter()
            if method == "run_covariant_analysis":
                raw_methods = case.get("methods")
                methods_arg: list[str] | None = (
                    [str(m) for m in cast(list[object], raw_methods)]
                    if raw_methods is not None
                    else None
                )
                run_covariant_analysis(
                    target,
                    drivers,
                    max_lag=max_lag,
                    methods=methods_arg,
                    n_surrogates=n_surrogates,
                    random_state=42,
                    significance_mode=significance_mode,  # type: ignore[arg-type]
                )
            else:
                run_lagged_exogenous_triage(
                    target,
                    drivers,
                    target_name="bench_target",
                    max_lag=max_lag,
                    n_surrogates=n_surrogates,
                    random_state=42,
                    significance_mode=significance_mode,  # type: ignore[arg-type]
                )
            elapsed = time.perf_counter() - start
            results.append(
                {"name": name, "method": method, "elapsed_s": elapsed, "version": version}
            )
        else:
            results.append(
                {
                    "name": name,
                    "method": method,
                    "elapsed_s": 0.0,
                    "version": version,
                    "skip_reason": f"unknown method {method!r}",
                }
            )
    return results


def main() -> None:
    """Run configured synthetic baselines and write ``performance_summary.json``."""
    args = _parse_args()
    config_hash = sha256_file(args.config)
    if config_hash is None:
        raise FileNotFoundError(args.config)
    config = load_performance_config(args.config)
    output_dir = Path(config.metadata.output_dir)

    installed_version = importlib.metadata.version("forecastability")
    prior_artifact = output_dir / "performance_summary.json"
    if prior_artifact.exists():
        try:
            prior_data = json.loads(prior_artifact.read_text(encoding="utf-8"))
            prior_version = str(
                prior_data.get("command_metadata", {}).get("forecastability_version", "")
            )
            if prior_version and prior_version != installed_version:
                print(
                    f"Warning: prior artifact was produced with "
                    f"forecastability {prior_version!r}; "
                    f"installed is {installed_version!r}. "
                    "Results may not be comparable.",
                    file=sys.stderr,
                )
        except (json.JSONDecodeError, KeyError):
            pass

    start_wall = time.perf_counter()
    start_cpu = time.process_time()
    case_summaries, repeat_rows = _run_baseline(config)
    rng = np.random.default_rng(config.metadata.random_state_base)
    public_workflow_results: list[dict[str, object]] = []
    if config.public_workflows is not None:
        public_workflow_results = _bench_public_workflows(
            config.public_workflows,
            rng,
            version=installed_version,
        )
    summary = {
        "schema_version": 1,
        "artifact_type": "performance_baseline_summary",
        "metadata": config.metadata.model_dump(),
        "command_metadata": runtime_metadata(config_path=args.config, config_hash=config_hash),
        "total_wall_time_s": time.perf_counter() - start_wall,
        "total_cpu_time_s": time.process_time() - start_cpu,
        "cases": case_summaries,
        "repeats": repeat_rows,
        "public_workflow_results": public_workflow_results,
    }
    write_json(output_dir / "performance_summary.json", summary)
    print(f"Wrote {output_dir / 'performance_summary.json'}")


if __name__ == "__main__":
    main()
