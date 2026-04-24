"""Smoke-contract check for notebook-facing public API.

Verifies notebooks exist on disk, all notebook-facing imports resolve,
and a minimal representative computation runs without error.

Usage:
    uv run python scripts/check_notebook_contract.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).parent.parent
NOTEBOOKS_DIR = REPO_ROOT / "notebooks"

EXPECTED_NOTEBOOKS = [
    "walkthroughs/00_air_passengers_showcase.ipynb",
    "walkthroughs/01_covariant_informative_showcase.ipynb",
    "walkthroughs/02_forecastability_fingerprint_showcase.ipynb",
    "walkthroughs/03_lagged_exogenous_triage_showcase.ipynb",
    "walkthroughs/04_routing_validation_showcase.ipynb",
    "walkthroughs/01_canonical_forecastability.ipynb",
    "walkthroughs/02_exogenous_analysis.ipynb",
    "walkthroughs/03_triage_end_to_end.ipynb",
    "walkthroughs/04_screening_end_to_end.ipynb",
]

PASS = "\u2713"
FAIL = "\u2717"


def _check(label: str, ok: bool) -> bool:
    status = PASS if ok else FAIL
    print(f"  [{status}] {label}")
    return ok


def check_notebooks_exist() -> bool:
    print("Notebooks on disk:")
    all_ok = True
    for name in EXPECTED_NOTEBOOKS:
        exists = (NOTEBOOKS_DIR / name).is_file()
        all_ok = _check(name, exists) and all_ok
    return all_ok


def check_imports() -> bool:
    print("Import resolution:")
    results: list[bool] = []

    checks: list[tuple[str, str | None]] = [
        ("forecastability", None),
        ("forecastability", "ForecastabilityAnalyzer"),
        ("forecastability", "ForecastabilityAnalyzerExog"),
        ("forecastability", "LaggedExogBundle"),
        ("forecastability", "generate_lagged_exog_panel"),
        ("forecastability", "run_lagged_exogenous_triage"),
        ("forecastability.pipeline", None),
        ("forecastability.pipeline", "run_canonical_example"),
        ("forecastability.pipeline", "run_rolling_origin_evaluation"),
        ("forecastability.utils.config", "MetricConfig"),
        ("forecastability.utils.datasets", "generate_ar1"),
        ("forecastability.use_cases.run_covariant_analysis", "run_covariant_analysis"),
        ("forecastability.adapters.rendering", "save_lagged_exog_profile_figure"),
        ("forecastability.adapters.rendering", "save_lagged_exog_selection_heatmap"),
        ("forecastability.utils.synthetic", "generate_covariant_benchmark"),
        ("forecastability.reporting.covariant_walkthrough", "save_metric_heatmap"),
        ("forecastability", "generate_fingerprint_archetypes"),
        ("forecastability", "run_forecastability_fingerprint"),
        ("forecastability", "RoutingPolicyAuditConfig"),
        ("forecastability", "RoutingValidationCase"),
        ("forecastability", "run_routing_validation"),
        ("forecastability.reporting.fingerprint_showcase", "showcase_summary_frame"),
    ]

    for module_name, attr in checks:
        label = f"{module_name}.{attr}" if attr else module_name
        try:
            mod = importlib.import_module(module_name)
            ok = True
            if attr is not None:
                ok = hasattr(mod, attr)
        except Exception:
            ok = False
        results.append(_check(label, ok))

    return all(results)


def check_representative_call() -> bool:
    print("Representative computation:")
    checks: list[bool] = []
    try:
        from forecastability import ForecastabilityAnalyzer

        rng = np.random.default_rng(0)
        series = rng.standard_normal(200)
        analyzer = ForecastabilityAnalyzer(n_surrogates=99, random_state=42)
        result = analyzer.compute_ami(series)
        ok = isinstance(result, np.ndarray)
    except Exception as exc:
        print(f"    Error: {exc}")
        ok = False
    checks.append(_check("ForecastabilityAnalyzer.compute_ami returns ndarray", ok))

    try:
        from forecastability.use_cases.run_covariant_analysis import run_covariant_analysis
        from forecastability.utils.synthetic import generate_covariant_benchmark

        df = generate_covariant_benchmark(n=240, seed=42)
        target = df["target"].to_numpy()
        drivers = {name: df[name].to_numpy() for name in df.columns if name != "target"}
        bundle = run_covariant_analysis(
            target,
            drivers,
            methods=["cross_ami", "cross_pami", "te", "gcmi"],
            max_lag=3,
            n_surrogates=99,
            random_state=42,
        )
        covariant_ok = len(bundle.summary_table) == len(drivers) * 3
    except Exception as exc:
        print(f"    Error: {exc}")
        covariant_ok = False
    checks.append(_check("run_covariant_analysis returns the expected summary grid", covariant_ok))

    try:
        from forecastability import generate_fingerprint_archetypes, run_forecastability_fingerprint
        from forecastability.reporting.fingerprint_showcase import (
            build_fingerprint_showcase_record,
            showcase_summary_frame,
        )
        from forecastability.services.linear_information_service import (
            compute_linear_information_curve,
        )

        series = generate_fingerprint_archetypes(n=240, seed=42)["seasonal_periodic"]
        bundle = run_forecastability_fingerprint(
            series,
            target_name="seasonal_periodic",
            max_lag=24,
            n_surrogates=99,
            random_state=42,
        )
        baseline = compute_linear_information_curve(
            series,
            horizons=[point.horizon for point in bundle.geometry.curve if point.valid],
        )
        record = build_fingerprint_showcase_record(bundle=bundle, baseline=baseline)
        frame = showcase_summary_frame([record])
        fingerprint_ok = len(frame) == 1 and frame.iloc[0]["target_name"] == "seasonal_periodic"
    except Exception as exc:
        print(f"    Error: {exc}")
        fingerprint_ok = False
    checks.append(
        _check(
            "run_forecastability_fingerprint integrates with fingerprint_showcase reporting",
            fingerprint_ok,
        )
    )

    try:
        from forecastability import generate_lagged_exog_panel, run_lagged_exogenous_triage

        lagged_df = generate_lagged_exog_panel(n=700, seed=42)
        lagged_target = lagged_df["target"].to_numpy()
        lagged_drivers = {
            "known_future_calendar": lagged_df["known_future_calendar"].to_numpy(),
            "instant_only": lagged_df["instant_only"].to_numpy(),
        }

        default_bundle = run_lagged_exogenous_triage(
            lagged_target,
            lagged_drivers,
            target_name="target",
            max_lag=4,
            n_surrogates=99,
            random_state=42,
        )
        opt_in_bundle = run_lagged_exogenous_triage(
            lagged_target,
            lagged_drivers,
            target_name="target",
            max_lag=4,
            n_surrogates=99,
            random_state=42,
            known_future_drivers={"known_future_calendar": True},
        )

        default_has_lag_zero_selection = any(
            row.selected_for_tensor and row.lag == 0 for row in default_bundle.selected_lags
        )
        opt_in_known_future_has_lag_zero_selection = any(
            row.driver == "known_future_calendar" and row.selected_for_tensor and row.lag == 0
            for row in opt_in_bundle.selected_lags
        )
        opt_in_non_known_future_lag_zero_selected = any(
            row.driver != "known_future_calendar" and row.selected_for_tensor and row.lag == 0
            for row in opt_in_bundle.selected_lags
        )
        lagged_exog_opt_in_ok = (
            not default_has_lag_zero_selection
            and opt_in_known_future_has_lag_zero_selection
            and not opt_in_non_known_future_lag_zero_selected
        )
    except Exception as exc:
        print(f"    Error: {exc}")
        lagged_exog_opt_in_ok = False
    checks.append(
        _check(
            "run_lagged_exogenous_triage requires explicit known-future opt-in for lag=0 selection",
            lagged_exog_opt_in_ok,
        )
    )

    try:
        from forecastability import (
            ExpectedFamilyMetadata,
            RoutingPolicyAuditConfig,
            run_routing_validation,
        )

        routing_bundle = run_routing_validation(
            synthetic_panel=[
                ExpectedFamilyMetadata(
                    archetype_name="seasonal",
                    expected_primary_families=["seasonal_naive"],
                )
            ],
            real_panel_path=None,
            n_per_archetype=200,
            random_state=42,
            config=RoutingPolicyAuditConfig(),
        )
        routing_validation_ok = (
            routing_bundle.audit.total_cases == 1
            and len(routing_bundle.cases) == 1
            and routing_bundle.cases[0].case_name == "seasonal"
        )
    except Exception as exc:
        print(f"    Error: {exc}")
        routing_validation_ok = False
    checks.append(
        _check(
            "run_routing_validation returns a one-case synthetic bundle via the stable facade",
            routing_validation_ok,
        )
    )

    return all(checks)


def main() -> None:
    passed: list[bool] = []

    passed.append(check_notebooks_exist())
    passed.append(check_imports())
    passed.append(check_representative_call())

    print()
    if all(passed):
        print(f"{PASS} All notebook contract checks passed.")
        sys.exit(0)
    else:
        print(f"{FAIL} One or more notebook contract checks FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
