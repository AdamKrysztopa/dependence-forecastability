"""Fingerprint regression fixture generation, rebuild, and verification.

Generates deterministic univariate fingerprint bundles for canonical archetypes,
serializes compact geometry/fingerprint/routing outputs to JSON, and verifies
rebuilt outputs against frozen expected files.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from forecastability.use_cases.run_forecastability_fingerprint import (
    run_forecastability_fingerprint,
)
from forecastability.utils.synthetic import generate_fingerprint_archetypes

_ATOL = 5e-6
_RTOL = 5e-5

FINGERPRINT_FIXTURE_SERIES: dict[str, dict[str, int]] = {
    "white_noise": {"n": 320, "seed": 42},
    "ar1_monotonic": {"n": 320, "seed": 42},
    "seasonal_periodic": {"n": 320, "seed": 42},
    "nonlinear_mixed": {"n": 320, "seed": 42},
}


def _compact_bundle(target_name: str, *, n: int, seed: int) -> dict[str, Any]:
    """Build one compact regression payload from a deterministic fingerprint bundle."""
    series = generate_fingerprint_archetypes(n=n, seed=seed)[target_name]
    bundle = run_forecastability_fingerprint(
        series,
        target_name=target_name,
        max_lag=12,
        n_surrogates=99,
        random_state=42,
    )

    curve = [
        {
            "horizon": point.horizon,
            "ami_corrected": point.ami_corrected,
            "tau": point.tau,
            "accepted": point.accepted,
            "valid": point.valid,
        }
        for point in bundle.geometry.curve
    ]
    return {
        "target_name": bundle.target_name,
        "geometry": {
            "signal_to_noise": bundle.geometry.signal_to_noise,
            "information_horizon": bundle.geometry.information_horizon,
            "information_structure": bundle.geometry.information_structure,
            "informative_horizons": bundle.geometry.informative_horizons,
            "curve": curve,
        },
        "fingerprint": {
            "information_mass": bundle.fingerprint.information_mass,
            "information_horizon": bundle.fingerprint.information_horizon,
            "information_structure": bundle.fingerprint.information_structure,
            "nonlinear_share": bundle.fingerprint.nonlinear_share,
            "signal_to_noise": bundle.fingerprint.signal_to_noise,
            "directness_ratio": bundle.fingerprint.directness_ratio,
            "informative_horizons": bundle.fingerprint.informative_horizons,
        },
        "recommendation": {
            "primary_families": bundle.recommendation.primary_families,
            "secondary_families": bundle.recommendation.secondary_families,
            "confidence_label": bundle.recommendation.confidence_label,
            "caution_flags": bundle.recommendation.caution_flags,
        },
    }


def build_fingerprint_regression_outputs() -> dict[str, dict[str, Any]]:
    """Build compact regression outputs for all canonical fingerprint fixtures."""
    return {
        target_name: _compact_bundle(target_name, **spec)
        for target_name, spec in FINGERPRINT_FIXTURE_SERIES.items()
    }


def write_fingerprint_regression_outputs(*, output_dir: Path) -> list[Path]:
    """Build and write fingerprint regression outputs to JSON files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = build_fingerprint_regression_outputs()
    written: list[Path] = []
    for target_name in sorted(outputs):
        path = output_dir / f"{target_name}.json"
        path.write_text(json.dumps(outputs[target_name], indent=2, sort_keys=True) + "\n")
        written.append(path)
    return written


def _compare_value(actual: Any, expected: Any, *, field_path: str) -> list[str]:
    """Compare one possibly nested value and return human-readable mismatches."""
    errors: list[str] = []
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key, exp_value in expected.items():
            if key not in actual:
                errors.append(f"{field_path}: missing key '{key}'")
                continue
            errors.extend(
                _compare_value(
                    actual[key],
                    exp_value,
                    field_path=f"{field_path}/{key}",
                )
            )
        return errors

    if isinstance(expected, list) and isinstance(actual, list):
        if len(actual) != len(expected):
            errors.append(
                f"{field_path}: length mismatch (actual={len(actual)}, expected={len(expected)})"
            )
            return errors
        for idx, (actual_item, expected_item) in enumerate(zip(actual, expected, strict=True)):
            errors.extend(
                _compare_value(
                    actual_item,
                    expected_item,
                    field_path=f"{field_path}[{idx}]",
                )
            )
        return errors

    # Keep discrete semantics exact; only continuous float fields tolerate
    # small cross-platform numeric drift from dependency and BLAS variations.
    if isinstance(expected, float) and isinstance(actual, float):
        if not math.isclose(actual, expected, rel_tol=_RTOL, abs_tol=_ATOL):
            errors.append(
                f"{field_path}: value mismatch (actual={actual}, expected={expected}, "
                f"atol={_ATOL}, rtol={_RTOL})"
            )
        return errors

    if isinstance(expected, int) and isinstance(actual, int):
        if actual != expected:
            errors.append(f"{field_path}: mismatch (actual={actual!r}, expected={expected!r})")
        return errors

    if actual != expected:
        errors.append(f"{field_path}: mismatch (actual={actual!r}, expected={expected!r})")
    return errors


def verify_fingerprint_regression_outputs(*, actual_dir: Path, expected_dir: Path) -> None:
    """Verify rebuilt fingerprint regression outputs against frozen expected JSON."""
    expected_files = sorted(expected_dir.glob("*.json"))
    if not expected_files:
        msg = f"No expected JSON files found in {expected_dir}"
        raise ValueError(msg)

    errors: list[str] = []
    for expected_path in expected_files:
        actual_path = actual_dir / expected_path.name
        if not actual_path.exists():
            errors.append(f"Missing rebuilt output: {actual_path.name}")
            continue

        expected_payload = json.loads(expected_path.read_text())
        actual_payload = json.loads(actual_path.read_text())
        errors.extend(
            _compare_value(
                actual_payload,
                expected_payload,
                field_path=expected_path.stem,
            )
        )

    if errors:
        error_block = "\n".join(f"- {item}" for item in errors)
        raise ValueError(f"Fingerprint regression verification failed:\n{error_block}")