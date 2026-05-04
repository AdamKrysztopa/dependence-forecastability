"""Run the Phase 1 deterministic performance baseline."""

from __future__ import annotations

import argparse
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
        PublicWorkflowConfig,
        load_performance_config,
        make_synthetic_series,
        make_synthetic_series_spec,
        measured_runtime,
        resolve_forecastability_version,
        runtime_metadata,
        sha256_file,
        write_json,
    )
except ModuleNotFoundError:
    from performance_common import (
        PerformanceBaselineConfig,
        PerformanceCaseConfig,
        PublicWorkflowConfig,
        load_performance_config,
        make_synthetic_series,
        make_synthetic_series_spec,
        measured_runtime,
        resolve_forecastability_version,
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


def _bench_import_workflow(case: PublicWorkflowConfig, *, version: str) -> dict[str, object]:
    """Measure one subprocess-backed import statement."""
    import_statement = case.import_statement or "import forecastability"
    start = time.perf_counter()
    subprocess.run(
        [sys.executable, "-c", import_statement],
        check=True,
        capture_output=True,
    )
    return {
        "name": case.name,
        "method": case.method,
        "description": case.description,
        "import_statement": import_statement,
        "elapsed_s": time.perf_counter() - start,
        "version": version,
    }


def _build_public_workflow_series(case: PublicWorkflowConfig) -> np.ndarray:
    """Build the deterministic univariate series used by extended diagnostics."""
    if case.series_length is None:
        raise ValueError("series_length is required for univariate public workflows")
    return make_synthetic_series_spec(
        n_obs=case.series_length,
        signal=case.signal,
        random_state=case.random_state,
    )


def _benchmark_multiseries_workflow(
    case: PublicWorkflowConfig,
    rng: np.random.Generator,
    *,
    version: str,
) -> dict[str, object]:
    """Benchmark existing covariate-aware public workflows."""
    from forecastability.use_cases import (  # noqa: PLC0415
        run_covariant_analysis,
        run_lagged_exogenous_triage,
    )

    if case.series_length is None or case.max_lag is None:
        raise ValueError("series_length and max_lag are required for multiseries workflows")
    n_series = case.n_series or 2
    significance_mode = case.significance_mode or "phase"
    n_surrogates = case.n_surrogates or 99
    target = rng.normal(size=case.series_length)
    drivers = {f"driver_{i}": rng.normal(size=case.series_length) for i in range(n_series)}

    start = time.perf_counter()
    if case.method == "run_covariant_analysis":
        run_covariant_analysis(
            target,
            drivers,
            max_lag=case.max_lag,
            methods=case.methods,
            n_surrogates=n_surrogates,
            random_state=42,
            significance_mode=significance_mode,
        )
    else:
        run_lagged_exogenous_triage(
            target,
            drivers,
            target_name="bench_target",
            max_lag=case.max_lag,
            n_surrogates=n_surrogates,
            random_state=42,
            significance_mode=significance_mode,
        )
    return {
        "name": case.name,
        "method": case.method,
        "description": case.description,
        "elapsed_s": time.perf_counter() - start,
        "version": version,
        "series_length": case.series_length,
        "n_series": n_series,
        "max_lag": case.max_lag,
        "signal": case.signal,
        "significance_mode": significance_mode,
        "n_surrogates": n_surrogates,
    }


def _benchmark_extended_univariate_workflow(
    case: PublicWorkflowConfig,
    *,
    version: str,
) -> dict[str, object]:
    """Benchmark direct extended-diagnostic callables and the composite use case."""
    from forecastability.services.classical_structure_service import (  # noqa: PLC0415
        compute_classical_structure,
    )
    from forecastability.services.memory_structure_service import (  # noqa: PLC0415
        compute_memory_structure,
    )
    from forecastability.services.ordinal_complexity_service import (  # noqa: PLC0415
        compute_ordinal_complexity,
    )
    from forecastability.services.spectral_forecastability_service import (  # noqa: PLC0415
        compute_spectral_forecastability,
    )
    from forecastability.use_cases import run_extended_forecastability_analysis  # noqa: PLC0415

    series = _build_public_workflow_series(case)
    start = time.perf_counter()
    if case.method == "compute_spectral_forecastability":
        compute_spectral_forecastability(series)
    elif case.method == "compute_ordinal_complexity":
        compute_ordinal_complexity(
            series,
            embedding_dimension=case.ordinal_embedding_dimension,
            delay=case.ordinal_delay,
        )
    elif case.method == "compute_classical_structure":
        compute_classical_structure(
            series,
            period=case.period,
            max_lag=case.max_lag or 40,
        )
    elif case.method == "compute_memory_structure":
        compute_memory_structure(
            series,
            min_scale=case.memory_min_scale,
            max_scale=case.memory_max_scale,
        )
    else:
        run_extended_forecastability_analysis(
            series,
            max_lag=case.max_lag or 40,
            period=case.period,
            include_ami_geometry=case.include_ami_geometry,
            ordinal_embedding_dimension=case.ordinal_embedding_dimension,
            ordinal_delay=case.ordinal_delay,
            memory_min_scale=case.memory_min_scale,
            memory_max_scale=case.memory_max_scale,
            random_state=case.random_state,
        )
    return {
        "name": case.name,
        "method": case.method,
        "description": case.description,
        "elapsed_s": time.perf_counter() - start,
        "version": version,
        "series_length": case.series_length,
        "max_lag": case.max_lag,
        "signal": case.signal,
        "period": case.period,
        "include_ami_geometry": case.include_ami_geometry,
        "ordinal_embedding_dimension": case.ordinal_embedding_dimension,
        "ordinal_delay": case.ordinal_delay,
        "memory_min_scale": case.memory_min_scale,
        "memory_max_scale": case.memory_max_scale,
    }


def _skipped_public_workflow_result(
    case: PublicWorkflowConfig,
    *,
    version: str,
) -> dict[str, object]:
    """Build a stable skipped-row payload for unsupported workflow methods."""
    return {
        "name": case.name,
        "method": case.method,
        "description": case.description,
        "elapsed_s": 0.0,
        "version": version,
        "skip_reason": f"unknown method {case.method!r}",
    }


def _bench_public_workflows(
    cases: list[PublicWorkflowConfig],
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
    results: list[dict[str, object]] = []
    for case in cases:
        if case.method == "import":
            result = _bench_import_workflow(case, version=version)
        elif case.method in {"run_covariant_analysis", "run_lagged_exogenous_triage"}:
            result = _benchmark_multiseries_workflow(case, rng, version=version)
        elif case.method in {
            "run_extended_forecastability_analysis",
            "compute_spectral_forecastability",
            "compute_ordinal_complexity",
            "compute_classical_structure",
            "compute_memory_structure",
        }:
            result = _benchmark_extended_univariate_workflow(case, version=version)
        else:
            result = _skipped_public_workflow_result(case, version=version)
        results.append(result)
    return results


def main() -> None:
    """Run configured synthetic baselines and write ``performance_summary.json``."""
    args = _parse_args()
    config_hash = sha256_file(args.config)
    if config_hash is None:
        raise FileNotFoundError(args.config)
    config = load_performance_config(args.config)
    output_dir = Path(config.metadata.output_dir)

    installed_version = resolve_forecastability_version()
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
