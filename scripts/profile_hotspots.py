"""Profile Phase 1 hotspot targets and emit coverage artifacts."""

from __future__ import annotations

import argparse
import cProfile
import csv
import io
import pstats
import time
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple, cast

import numpy as np

from forecastability.extensions import compute_target_baseline_by_horizon
from forecastability.metrics.metrics import compute_ami, compute_pami_linear_residual
from forecastability.metrics.scorers import DependenceScorer, default_registry
from forecastability.pipeline import run_rolling_origin_evaluation
from forecastability.services.partial_curve_service import compute_partial_curve
from forecastability.services.raw_curve_service import compute_raw_curve
from forecastability.triage import (
    BatchSeriesRequest,
    BatchTriageRequest,
    TriageRequest,
    build_forecast_prep_contract,
    run_batch_triage,
    run_batch_triage_with_details,
)
from forecastability.triage.models import TriageResult
from forecastability.use_cases import run_covariant_analysis, run_triage

try:
    from scripts.performance_common import (
        PerformanceCaseConfig,
        load_performance_config,
        make_synthetic_exog,
        make_synthetic_series,
        measured_runtime,
        runtime_metadata,
        sha256_file,
        threadpoolctl_snapshot,
        write_json,
    )
except ModuleNotFoundError:
    from performance_common import (
        PerformanceCaseConfig,
        load_performance_config,
        make_synthetic_exog,
        make_synthetic_series,
        measured_runtime,
        runtime_metadata,
        sha256_file,
        threadpoolctl_snapshot,
        write_json,
    )


class ProfileTarget(NamedTuple):
    """Coverage-manifest row plus optional callable target."""

    target_id: str
    surface_group: str
    entry_type: str
    command_or_callable: str
    optional_dependency_gate: str
    network_required: bool
    writes_artifacts: bool
    skip_reason: str
    runner: Callable[[PerformanceCaseConfig], None] | None = None


CSV_FIELDS: tuple[str, ...] = (
    "target_id",
    "surface_group",
    "entry_type",
    "command_or_callable",
    "input_size_label",
    "optional_dependency_gate",
    "network_required",
    "writes_artifacts",
    "profiled",
    "skip_reason",
    "wall_time_s",
    "cpu_time_s",
    "peak_memory_mb",
    "hotspot_artifact",
    "n_jobs_used",
    "thread_backend",
    "process_pool_workers",
    "random_state_base",
    "numpy_show_config_digest",
    "omp_num_threads",
    "mkl_num_threads",
    "threadpoolctl_snapshot",
    "forecastability_version",
    "uv_lock_hash",
)

_FORECAST_PREP_TRIAGE_CACHE: dict[str, TriageResult] = {}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Profile Phase 1 hotspot targets.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/performance_baseline.yaml"),
        help="Path to the performance baseline YAML config.",
    )
    return parser.parse_args()


def _run_triage_target(case: PerformanceCaseConfig) -> None:
    request = TriageRequest(
        series=make_synthetic_series(case),
        max_lag=case.max_lag,
        n_surrogates=case.n_surrogates,
        random_state=case.random_state,
    )
    run_triage(request)


def _run_batch_triage_target(case: PerformanceCaseConfig) -> None:
    base = make_synthetic_series(case)
    items = [
        BatchSeriesRequest(series_id="series_a", series=base.tolist(), max_lag=case.max_lag),
        BatchSeriesRequest(
            series_id="series_b",
            series=(base + 0.01 * np.arange(base.size)).tolist(),
            max_lag=case.max_lag,
        ),
    ]
    run_batch_triage(BatchTriageRequest(items=items, n_surrogates=case.n_surrogates))


def _run_batch_triage_details_target(case: PerformanceCaseConfig) -> None:
    base = make_synthetic_series(case)
    request = BatchTriageRequest(
        items=[
            BatchSeriesRequest(series_id="series_a", series=base.tolist(), max_lag=case.max_lag)
        ],
        n_surrogates=case.n_surrogates,
    )
    run_batch_triage_with_details(request)


def _run_compute_ami_target(case: PerformanceCaseConfig) -> None:
    compute_ami(make_synthetic_series(case), max_lag=case.max_lag, random_state=case.random_state)


def _run_compute_pami_target(case: PerformanceCaseConfig) -> None:
    compute_pami_linear_residual(
        make_synthetic_series(case),
        max_lag=case.max_lag,
        random_state=case.random_state,
    )


def _run_raw_curve_target(case: PerformanceCaseConfig) -> None:
    scorer = cast(DependenceScorer, default_registry().get("mi").scorer)
    compute_raw_curve(
        make_synthetic_series(case),
        max_lag=case.max_lag,
        scorer=scorer,
        min_pairs=30,
        random_state=case.random_state,
    )


def _run_partial_curve_target(case: PerformanceCaseConfig) -> None:
    scorer = cast(DependenceScorer, default_registry().get("mi").scorer)
    compute_partial_curve(
        make_synthetic_series(case),
        max_lag=case.max_lag,
        scorer=scorer,
        min_pairs=50,
        random_state=case.random_state,
    )


def _run_covariant_cross_ami_target(case: PerformanceCaseConfig) -> None:
    target = make_synthetic_series(case)
    driver = make_synthetic_exog(target, seed=case.random_state + 100)
    run_covariant_analysis(
        target,
        {"driver": driver},
        max_lag=min(case.max_lag, 4),
        methods=["cross_ami"],
        n_surrogates=case.n_surrogates,
        random_state=case.random_state,
    )


def _run_forecast_prep_target(case: PerformanceCaseConfig) -> None:
    result = _cached_forecast_prep_result(case)
    build_forecast_prep_contract(result, add_calendar_features=False)


def _cached_forecast_prep_result(case: PerformanceCaseConfig) -> TriageResult:
    cached = _FORECAST_PREP_TRIAGE_CACHE.get(case.case_id)
    if cached is not None:
        return cached
    request = TriageRequest(
        series=make_synthetic_series(case),
        max_lag=case.max_lag,
        n_surrogates=case.n_surrogates,
        random_state=case.random_state,
    )
    result = run_triage(request)
    _FORECAST_PREP_TRIAGE_CACHE[case.case_id] = result
    return result


def _run_rolling_origin_target(case: PerformanceCaseConfig) -> None:
    run_rolling_origin_evaluation(
        make_synthetic_series(case),
        series_id="profile_series",
        frequency="monthly",
        horizons=[1, 2],
        n_origins=2,
        seasonal_period=12,
        random_state=case.random_state,
    )


def _run_target_baseline_target(case: PerformanceCaseConfig) -> None:
    compute_target_baseline_by_horizon(
        series_name="profile_series",
        target=make_synthetic_series(case),
        horizons=[1, 2],
        n_origins=2,
        random_state=case.random_state,
        min_pairs_raw=30,
        min_pairs_partial=50,
        n_surrogates=case.n_surrogates,
    )


def _coverage_targets() -> list[ProfileTarget]:
    """Build the Phase 1 target coverage manifest."""
    callable_targets = [
        ProfileTarget(
            "callable.forecastability.run_triage",
            "Core triage",
            "callable",
            "forecastability.run_triage",
            "",
            False,
            False,
            "",
            _run_triage_target,
        ),
        ProfileTarget(
            "callable.forecastability.triage.run_batch_triage",
            "Core triage",
            "callable",
            "forecastability.triage.run_batch_triage",
            "",
            False,
            False,
            "",
            _run_batch_triage_target,
        ),
        ProfileTarget(
            "callable.forecastability.triage.run_batch_triage_with_details",
            "Core triage",
            "callable",
            "forecastability.triage.run_batch_triage_with_details",
            "",
            False,
            False,
            "not_in_phase1_smoke_budget",
            _run_batch_triage_details_target,
        ),
        ProfileTarget(
            "callable.metrics.compute_ami",
            "Analyzer kernels",
            "callable",
            "forecastability.metrics.compute_ami",
            "",
            False,
            False,
            "",
            _run_compute_ami_target,
        ),
        ProfileTarget(
            "callable.metrics.compute_pami_linear_residual",
            "Analyzer kernels",
            "callable",
            "forecastability.metrics.compute_pami_linear_residual",
            "",
            False,
            False,
            "",
            _run_compute_pami_target,
        ),
        ProfileTarget(
            "callable.services.compute_raw_curve",
            "Analyzer kernels",
            "callable",
            "forecastability.services.raw_curve_service.compute_raw_curve",
            "",
            False,
            False,
            "",
            _run_raw_curve_target,
        ),
        ProfileTarget(
            "callable.services.compute_partial_curve",
            "Analyzer kernels",
            "callable",
            "forecastability.services.partial_curve_service.compute_partial_curve",
            "",
            False,
            False,
            "",
            _run_partial_curve_target,
        ),
        ProfileTarget(
            "callable.use_cases.run_covariant_analysis.cross_ami",
            "Covariant tools",
            "callable",
            "forecastability.use_cases.run_covariant_analysis(methods=['cross_ami'])",
            "",
            False,
            False,
            "",
            _run_covariant_cross_ami_target,
        ),
        ProfileTarget(
            "callable.use_cases.build_forecast_prep_contract",
            "Forecast-prep hand-off",
            "callable",
            "forecastability.triage.build_forecast_prep_contract",
            "",
            False,
            False,
            "",
            _run_forecast_prep_target,
        ),
        ProfileTarget(
            "callable.pipeline.run_rolling_origin_evaluation",
            "Rolling-origin tools",
            "callable",
            "forecastability.pipeline.run_rolling_origin_evaluation",
            "",
            False,
            False,
            "",
            _run_rolling_origin_target,
        ),
        ProfileTarget(
            "callable.extensions.compute_target_baseline_by_horizon",
            "Rolling-origin tools",
            "callable",
            "forecastability.compute_target_baseline_by_horizon",
            "",
            False,
            False,
            "not_in_phase1_smoke_budget",
            _run_target_baseline_target,
        ),
    ]

    script_targets = [
        (
            "script.run_canonical_triage",
            "Canonical/showcase scripts",
            "scripts/run_canonical_triage.py --no-bands --max-workers 1",
        ),
        ("script.run_showcase", "Canonical/showcase scripts", "scripts/run_showcase.py"),
        (
            "script.run_triage_handoff_demo",
            "Canonical/showcase scripts",
            "scripts/run_triage_handoff_demo.py",
        ),
        ("script.run_exog_analysis", "Canonical/showcase scripts", "scripts/run_exog_analysis.py"),
        (
            "script.run_benchmark_panel",
            "Canonical/showcase scripts",
            "scripts/run_benchmark_panel.py",
        ),
        (
            "script.run_showcase_covariant",
            "Covariant tools",
            "scripts/run_showcase_covariant.py --smoke",
        ),
        (
            "script.run_showcase_lagged_exogenous",
            "Covariant tools",
            "scripts/run_showcase_lagged_exogenous.py --smoke",
        ),
        (
            "script.run_showcase_fingerprint",
            "Fingerprint/routing tools",
            "scripts/run_showcase_fingerprint.py --smoke",
        ),
        (
            "script.run_routing_validation_report",
            "Fingerprint/routing tools",
            "scripts/run_routing_validation_report.py --smoke --no-real-panel",
        ),
        (
            "script.run_ami_information_geometry_csv",
            "Fingerprint/routing tools",
            "scripts/run_ami_information_geometry_csv.py",
        ),
        (
            "script.run_showcase_forecast_prep",
            "Forecast-prep hand-off",
            "scripts/run_showcase_forecast_prep.py --smoke",
        ),
        (
            "script.rebuild_diagnostic_regression_fixtures",
            "Fixture rebuild scripts",
            "scripts/rebuild_diagnostic_regression_fixtures.py",
        ),
        (
            "script.rebuild_covariant_regression_fixtures",
            "Fixture rebuild scripts",
            "scripts/rebuild_covariant_regression_fixtures.py",
        ),
        (
            "script.rebuild_fingerprint_regression_fixtures",
            "Fixture rebuild scripts",
            "scripts/rebuild_fingerprint_regression_fixtures.py",
        ),
        (
            "script.rebuild_lagged_exog_regression_fixtures",
            "Fixture rebuild scripts",
            "scripts/rebuild_lagged_exog_regression_fixtures.py",
        ),
        (
            "script.rebuild_forecast_prep_regression_fixtures",
            "Fixture rebuild scripts",
            "scripts/rebuild_forecast_prep_regression_fixtures.py",
        ),
        (
            "script.rebuild_routing_validation_fixtures",
            "Fixture rebuild scripts",
            "scripts/rebuild_routing_validation_fixtures.py",
        ),
        (
            "script.rebuild_causal_rivers_fixtures",
            "Fixture rebuild scripts",
            "scripts/rebuild_causal_rivers_fixtures.py",
        ),
        (
            "script.rebuild_benchmark_fixture_artifacts",
            "Fixture rebuild scripts",
            "scripts/rebuild_benchmark_fixture_artifacts.py",
        ),
        (
            "script.build_report_artifacts",
            "Maintenance scripts",
            "scripts/build_report_artifacts.py",
        ),
        (
            "script.run_causal_rivers_analysis",
            "Real-data scripts",
            "scripts/run_causal_rivers_analysis.py",
        ),
    ]
    scripts = [
        ProfileTarget(
            target_id,
            group,
            "script",
            command,
            "causal-rivers-data" if target_id == "script.run_causal_rivers_analysis" else "",
            target_id == "script.run_causal_rivers_analysis",
            True,
            "script_command_recorded_not_executed_by_default",
            None,
        )
        for target_id, group, command in script_targets
    ]
    adapters = [
        ProfileTarget(
            "command.forecastability",
            "Packaged commands/adapters",
            "packaged_command",
            "forecastability --help",
            "",
            False,
            False,
            "packaged_command_recorded_not_executed_by_default",
            None,
        ),
        ProfileTarget(
            "command.forecastability-dashboard",
            "Packaged commands/adapters",
            "packaged_command",
            "forecastability-dashboard startup",
            "",
            False,
            False,
            "dashboard_startup_recorded_not_executed_by_default",
            None,
        ),
        ProfileTarget(
            "adapter.forecastability.adapters.pydantic_ai_agent",
            "Packaged commands/adapters",
            "adapter_import",
            "forecastability.adapters.pydantic_ai_agent",
            "ai-extra",
            False,
            False,
            "optional_dependency_gate=ai-extra",
            None,
        ),
    ]
    archived = [
        ProfileTarget(
            "script.archive.run_benchmark_exog_panel",
            "Archived scripts",
            "script",
            "scripts/archive/run_benchmark_exog_panel.py",
            "",
            False,
            True,
            "archived_script",
            None,
        )
    ]
    return callable_targets + scripts + adapters + archived


def _profile_target(
    *,
    target: ProfileTarget,
    case: PerformanceCaseConfig,
    output_dir: Path,
    top_n: int,
) -> tuple[dict[str, object], dict[str, object]]:
    if target.target_id == "callable.use_cases.build_forecast_prep_contract":
        _cached_forecast_prep_result(case)

    profile = cProfile.Profile()
    with measured_runtime() as measurement:
        profile.enable()
        assert target.runner is not None
        target.runner(case)
        profile.disable()
    runtime = measurement()

    artifact = output_dir / f"{target.target_id}.{case.size_label}.prof"
    profile.dump_stats(str(artifact))
    stats_stream = io.StringIO()
    pstats.Stats(profile, stream=stats_stream).sort_stats("cumtime").print_stats(top_n)
    top_artifact = artifact.with_suffix(".pstats.txt")
    top_artifact.write_text(stats_stream.getvalue(), encoding="utf-8")

    row = _base_row(target=target, case=case)
    row.update(
        {
            "profiled": True,
            "skip_reason": "",
            "wall_time_s": runtime.wall_time_s,
            "cpu_time_s": runtime.cpu_time_s,
            "peak_memory_mb": runtime.peak_memory_mb,
            "hotspot_artifact": str(artifact),
        }
    )
    return row, {
        "target_id": target.target_id,
        "size_label": case.size_label,
        "pstats_text_artifact": str(top_artifact),
    }


def _base_row(*, target: ProfileTarget, case: PerformanceCaseConfig | None) -> dict[str, object]:
    return {
        "target_id": target.target_id,
        "surface_group": target.surface_group,
        "entry_type": target.entry_type,
        "command_or_callable": target.command_or_callable,
        "input_size_label": "" if case is None else case.size_label,
        "optional_dependency_gate": target.optional_dependency_gate,
        "network_required": target.network_required,
        "writes_artifacts": target.writes_artifacts,
        "profiled": False,
        "skip_reason": target.skip_reason,
        "wall_time_s": "",
        "cpu_time_s": "",
        "peak_memory_mb": "",
        "hotspot_artifact": "",
        "n_jobs_used": 1,
        "thread_backend": "single_process",
        "process_pool_workers": 0,
        "random_state_base": "" if case is None else case.random_state,
    }


def main() -> None:
    """Profile enabled targets and write ``hotspots.csv`` plus ``.prof`` files."""
    args = _parse_args()
    config_hash = sha256_file(args.config)
    if config_hash is None:
        raise FileNotFoundError(args.config)
    config = load_performance_config(args.config)
    output_dir = Path(config.metadata.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = runtime_metadata(config_path=args.config, config_hash=config_hash)
    enabled = set(config.profile.enabled_targets)
    profile_cases = [
        case for case in config.cases if case.size_label in config.profile.profile_size_labels
    ]
    if not profile_cases:
        raise ValueError("profile.profile_size_labels did not match any configured cases")

    rows: list[dict[str, object]] = []
    top_artifacts: list[dict[str, object]] = []
    started = time.perf_counter()
    for target in _coverage_targets():
        if target.runner is None or target.target_id not in enabled:
            rows.append(_base_row(target=target, case=None))
            continue
        for case in profile_cases:
            row, artifact = _profile_target(
                target=target,
                case=case,
                output_dir=output_dir,
                top_n=config.profile.top_n,
            )
            rows.append(row)
            top_artifacts.append(artifact)

    common = {
        "numpy_show_config_digest": metadata["numpy_show_config_digest"],
        "omp_num_threads": metadata["omp_num_threads"] or "",
        "mkl_num_threads": metadata["mkl_num_threads"] or "",
        "threadpoolctl_snapshot": threadpoolctl_snapshot(),
        "forecastability_version": metadata["forecastability_version"],
        "uv_lock_hash": metadata["uv_lock_hash"] or "",
    }
    for row in rows:
        row.update(common)
        row["threadpoolctl_snapshot"] = repr(row["threadpoolctl_snapshot"])

    csv_path = output_dir / "hotspots.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "schema_version": 1,
        "artifact_type": "hotspot_profile_manifest",
        "metadata": config.metadata.model_dump(),
        "command_metadata": metadata,
        "total_wall_time_s": time.perf_counter() - started,
        "row_count": len(rows),
        "profiled_count": sum(1 for row in rows if row["profiled"]),
        "top_artifacts": top_artifacts,
    }
    write_json(output_dir / "hotspots_manifest.json", manifest)
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
