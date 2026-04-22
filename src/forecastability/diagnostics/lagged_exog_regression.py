"""Lagged-exogenous regression fixture generation and verification.

Builds deterministic regression payloads for the v0.3.2 lagged-exogenous
surfaces and verifies rebuilt outputs against frozen expected JSON fixtures.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import cast

import numpy as np

from forecastability import (
    default_registry,
    generate_covariant_benchmark,
    generate_lagged_exog_panel,
    run_covariant_analysis,
    run_lagged_exogenous_triage,
)
from forecastability.metrics.scorers import DependenceScorer
from forecastability.services.exog_partial_curve_service import compute_exog_partial_curve
from forecastability.services.exog_raw_curve_service import compute_exog_raw_curve

_ATOL = 1e-6
_RTOL = 1e-2

LAGGED_EXOG_FIXTURE_CASES: tuple[str, ...] = (
    "cross_pami_target_only_contract",
    "default_curve_call_path",
    "selected_lag_map_panel",
)


def _resolve_mi_scorer() -> DependenceScorer:
    """Resolve the stable MI scorer from the registry."""
    registry = default_registry()
    scorer = registry.get("mi").scorer
    if not isinstance(scorer, DependenceScorer):
        raise TypeError("Expected MI scorer to satisfy DependenceScorer protocol")
    return scorer


def _build_selected_lag_map_panel_case() -> dict[str, object]:
    """Build deterministic selected-lag map payload for lagged exog panel."""
    panel = generate_lagged_exog_panel(n=1500, seed=42)
    target = panel["target"].to_numpy()
    drivers = {
        "direct_lag2": panel["direct_lag2"].to_numpy(),
        "mediated_lag1": panel["mediated_lag1"].to_numpy(),
        "redundant": panel["redundant"].to_numpy(),
    }

    bundle = run_lagged_exogenous_triage(
        target,
        drivers,
        target_name="target",
        max_lag=6,
        n_surrogates=99,
        random_state=42,
    )

    selected_rows = sorted(
        (row for row in bundle.selected_lags if row.selected_for_tensor),
        key=lambda row: (row.driver, row.lag),
    )

    selected_lag_map: dict[str, list[int]] = {}
    selected_score_map: dict[str, list[float]] = {}
    for row in selected_rows:
        selected_lag_map.setdefault(row.driver, []).append(int(row.lag))
        selected_score_map.setdefault(row.driver, []).append(float(row.score or 0.0))

    lag0_rows = sorted(
        (row for row in bundle.profile_rows if row.lag == 0),
        key=lambda row: row.driver,
    )

    return {
        "selected_lag_map": selected_lag_map,
        "selected_score_map": selected_score_map,
        "lag0_tensor_roles": {row.driver: row.tensor_role for row in lag0_rows},
        "lag0_role_labels": {row.driver: row.lag_role for row in lag0_rows},
        "selected_row_count": len(selected_rows),
    }


def _build_default_curve_call_path_case() -> dict[str, object]:
    """Build payload that guards legacy default curve call-path semantics."""
    benchmark = generate_covariant_benchmark(n=900, seed=42)
    target = benchmark["target"].to_numpy()
    driver = benchmark["driver_direct"].to_numpy()
    scorer = _resolve_mi_scorer()
    max_lag = 3

    raw_default = compute_exog_raw_curve(
        target,
        driver,
        max_lag,
        scorer,
        min_pairs=30,
        random_state=42,
    )
    raw_explicit = compute_exog_raw_curve(
        target,
        driver,
        max_lag,
        scorer,
        min_pairs=30,
        random_state=42,
        lag_range=(1, max_lag),
    )

    partial_default = compute_exog_partial_curve(
        target,
        driver,
        max_lag,
        scorer,
        min_pairs=50,
        random_state=42,
    )
    partial_explicit = compute_exog_partial_curve(
        target,
        driver,
        max_lag,
        scorer,
        min_pairs=50,
        random_state=42,
        lag_range=(1, max_lag),
    )

    return {
        "max_lag": max_lag,
        "raw_default_curve": [float(value) for value in raw_default],
        "raw_explicit_predictive_curve": [float(value) for value in raw_explicit],
        "partial_default_curve": [float(value) for value in partial_default],
        "partial_explicit_predictive_curve": [float(value) for value in partial_explicit],
        "raw_curves_match": bool(np.allclose(raw_default, raw_explicit)),
        "partial_curves_match": bool(np.allclose(partial_default, partial_explicit)),
    }


def _build_cross_pami_target_only_contract_case() -> dict[str, object]:
    """Build payload that guards shipped cross_pami target_only semantics."""
    benchmark = generate_covariant_benchmark(n=900, seed=42)
    target = benchmark["target"].to_numpy()
    drivers = {"driver_direct": benchmark["driver_direct"].to_numpy()}

    bundle = run_covariant_analysis(
        target,
        drivers,
        max_lag=3,
        methods=["cross_pami"],
        random_state=42,
    )

    conditioning_tags = [
        cast(str | None, row.lagged_exog_conditioning.cross_pami)
        for row in sorted(bundle.summary_table, key=lambda row: row.lag)
    ]
    disclaimer = str(bundle.metadata.get("conditioning_scope_disclaimer", ""))

    return {
        "conditioning_tags": conditioning_tags,
        "all_target_only": all(tag == "target_only" for tag in conditioning_tags),
        "disclaimer_mentions_target_only": "target_only" in disclaimer,
        "contains_target_only_methods": int(bundle.metadata.get("contains_target_only_methods", 0)),
    }


def build_lagged_exog_regression_outputs() -> dict[str, dict[str, object]]:
    """Build deterministic outputs for all lagged-exogenous regression cases."""
    return {
        "cross_pami_target_only_contract": _build_cross_pami_target_only_contract_case(),
        "default_curve_call_path": _build_default_curve_call_path_case(),
        "selected_lag_map_panel": _build_selected_lag_map_panel_case(),
    }


def write_lagged_exog_regression_outputs(*, output_dir: Path) -> list[Path]:
    """Write lagged-exogenous regression outputs to JSON files.

    Args:
        output_dir: Destination directory for rebuilt JSON outputs.

    Returns:
        Ordered list of written JSON file paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = build_lagged_exog_regression_outputs()
    written: list[Path] = []
    for case_name in sorted(outputs):
        path = output_dir / f"{case_name}.json"
        path.write_text(json.dumps(outputs[case_name], indent=2, sort_keys=True) + "\n")
        written.append(path)
    return written


def _compare_json(
    actual: object,
    expected: object,
    *,
    field_path: str,
) -> list[str]:
    """Recursively compare two JSON-like values with tolerant float handling."""
    errors: list[str] = []

    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{field_path}: expected object, got {type(actual).__name__}"]

        expected_dict = cast(dict[str, object], expected)
        actual_dict = cast(dict[str, object], actual)
        expected_keys = set(expected_dict)
        actual_keys = set(actual_dict)

        for missing_key in sorted(expected_keys - actual_keys):
            errors.append(f"{field_path}: missing key '{missing_key}'")
        for extra_key in sorted(actual_keys - expected_keys):
            errors.append(f"{field_path}: unexpected key '{extra_key}'")

        for key in sorted(expected_keys & actual_keys):
            errors.extend(
                _compare_json(
                    actual_dict[key],
                    expected_dict[key],
                    field_path=f"{field_path}/{key}",
                )
            )
        return errors

    if isinstance(expected, list):
        if not isinstance(actual, list):
            return [f"{field_path}: expected list, got {type(actual).__name__}"]

        expected_list = cast(list[object], expected)
        actual_list = cast(list[object], actual)
        if len(actual_list) != len(expected_list):
            errors.append(
                f"{field_path}: length mismatch "
                f"(actual={len(actual_list)}, expected={len(expected_list)})"
            )
            return errors

        for index, (actual_item, expected_item) in enumerate(
            zip(actual_list, expected_list, strict=True)
        ):
            errors.extend(
                _compare_json(
                    actual_item,
                    expected_item,
                    field_path=f"{field_path}[{index}]",
                )
            )
        return errors

    if isinstance(expected, bool):
        if actual is not expected:
            errors.append(f"{field_path}: bool mismatch (actual={actual!r}, expected={expected!r})")
        return errors

    if isinstance(expected, int):
        if not isinstance(actual, int) or isinstance(actual, bool):
            errors.append(f"{field_path}: expected int, got {type(actual).__name__}")
            return errors
        if actual != expected:
            errors.append(f"{field_path}: int mismatch (actual={actual}, expected={expected})")
        return errors

    if isinstance(expected, float):
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            errors.append(f"{field_path}: expected float, got {type(actual).__name__}")
            return errors
        if not math.isclose(float(actual), expected, rel_tol=_RTOL, abs_tol=_ATOL):
            errors.append(
                f"{field_path}: float mismatch (actual={actual}, expected={expected}, "
                f"atol={_ATOL}, rtol={_RTOL})"
            )
        return errors

    if actual != expected:
        errors.append(f"{field_path}: mismatch (actual={actual!r}, expected={expected!r})")
    return errors


def verify_lagged_exog_regression_outputs(*, actual_dir: Path, expected_dir: Path) -> None:
    """Verify rebuilt lagged-exog outputs against frozen expected fixtures.

    Args:
        actual_dir: Directory containing rebuilt JSON files.
        expected_dir: Directory containing frozen expected JSON files.

    Raises:
        ValueError: If any rebuilt file is missing or contains drift.
    """
    expected_files = sorted(expected_dir.glob("*.json"))
    if not expected_files:
        raise ValueError(f"No expected JSON files found in {expected_dir}")

    errors: list[str] = []
    for expected_path in expected_files:
        actual_path = actual_dir / expected_path.name
        if not actual_path.exists():
            errors.append(f"Missing rebuilt output: {actual_path.name}")
            continue

        expected_payload_obj: object = json.loads(expected_path.read_text())
        actual_payload_obj: object = json.loads(actual_path.read_text())
        errors.extend(
            _compare_json(
                actual_payload_obj,
                expected_payload_obj,
                field_path=expected_path.stem,
            )
        )

    if errors:
        error_block = "\n".join(f"- {line}" for line in errors)
        raise ValueError(f"Lagged-exog regression verification failed:\n{error_block}")
