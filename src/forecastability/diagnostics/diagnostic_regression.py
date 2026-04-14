"""Diagnostic regression fixture generation, rebuild, and verification.

Generates deterministic synthetic series for each diagnostic (F1–F6),
runs the corresponding service, serialises outputs to JSON, and verifies
rebuilt outputs against frozen expected files.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from forecastability.services.complexity_band_service import build_complexity_band
from forecastability.services.forecastability_profile_service import (
    build_forecastability_profile,
)
from forecastability.services.lyapunov_service import build_largest_lyapunov_exponent
from forecastability.services.predictive_info_learning_curve_service import (
    build_predictive_info_learning_curve,
)
from forecastability.services.spectral_predictability_service import (
    build_spectral_predictability,
)
from forecastability.services.theoretical_limit_diagnostics_service import (
    build_theoretical_limit_diagnostics,
)

# ---------------------------------------------------------------------------
# Fixture series generators (deterministic, seed=42)
# ---------------------------------------------------------------------------

_SEED: int = 42


def _generate_ar1(*, n: int = 500, phi: float = 0.85) -> np.ndarray:
    """AR(1) with φ=0.85 — smooth monotone decay."""
    rng = np.random.default_rng(_SEED)
    x = np.zeros(n, dtype=float)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + rng.normal()
    return x


def _generate_seasonal_ar(*, n: int = 500, period: int = 12, phi: float = 0.5) -> np.ndarray:
    """Seasonal AR with period 12 — produces non-monotone profile."""
    rng = np.random.default_rng(_SEED)
    x = np.zeros(n, dtype=float)
    for t in range(1, n):
        seasonal = 0.6 * np.sin(2.0 * np.pi * t / period)
        ar_part = phi * x[t - 1] if t >= 1 else 0.0
        x[t] = ar_part + seasonal + 0.3 * rng.normal()
    return x


def _generate_white_noise(*, n: int = 500) -> np.ndarray:
    """Gaussian white noise — null baseline."""
    return np.random.default_rng(_SEED).normal(size=n)


def _generate_sine_wave(*, n: int = 500, cycles: float = 10.0) -> np.ndarray:
    """Pure sine wave with negligible noise — maximal structure."""
    t = np.linspace(0.0, 2.0 * np.pi * cycles, n)
    noise = np.random.default_rng(_SEED).normal(scale=1e-6, size=n)
    return np.sin(t) + noise


def _generate_ar2_finite_memory(*, n: int = 1000) -> np.ndarray:
    """AR(2) with coefficients [0.5, 0.3] — finite-memory lookback plateau."""
    rng = np.random.default_rng(_SEED)
    x = np.zeros(n, dtype=float)
    for t in range(2, n):
        x[t] = 0.5 * x[t - 1] + 0.3 * x[t - 2] + rng.normal()
    return x


def _generate_logistic_map(*, n: int = 2000, r: float = 3.9, discard: int = 500) -> np.ndarray:
    """Logistic map r=3.9 — chaotic dynamics, positive LLE expected."""
    total = n + discard
    x = np.zeros(total, dtype=float)
    x[0] = 0.4
    for t in range(total - 1):
        x[t + 1] = r * x[t] * (1.0 - x[t])
    return x[discard:]


def _generate_mixed_ar1_noise(*, n: int = 500, phi: float = 0.5) -> np.ndarray:
    """AR(1) + substantial noise — medium complexity."""
    rng = np.random.default_rng(_SEED)
    x = np.zeros(n, dtype=float)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + rng.normal()
    noise = rng.normal(scale=1.0, size=n)
    return x + noise


# ---------------------------------------------------------------------------
# Fixture registry
# ---------------------------------------------------------------------------

FIXTURE_SERIES: dict[str, dict[str, Any]] = {
    "ar1_phi085": {
        "generator": _generate_ar1,
        "description": "AR(1) φ=0.85, n=500 — smooth monotone decay",
        "diagnostics": ["F1", "F2", "F4", "F6"],
    },
    "seasonal_ar_period12": {
        "generator": _generate_seasonal_ar,
        "description": "Seasonal AR + period 12, n=500 — non-monotone profile",
        "diagnostics": ["F1", "F2", "F4", "F6"],
    },
    "white_noise": {
        "generator": _generate_white_noise,
        "description": "White noise, n=500 — null baseline",
        "diagnostics": ["F1", "F2", "F4", "F6"],
    },
    "sine_wave": {
        "generator": _generate_sine_wave,
        "description": "Sine wave, n=500 — maximal structure",
        "diagnostics": ["F1", "F2", "F4", "F6"],
    },
    "ar2_finite_memory": {
        "generator": _generate_ar2_finite_memory,
        "description": "AR(2) finite-memory, n=1000 — lookback plateau",
        "diagnostics": ["F3"],
    },
    "logistic_map_r39": {
        "generator": _generate_logistic_map,
        "description": "Logistic map r=3.9, n=2000 — chaotic dynamics",
        "diagnostics": ["F5"],
    },
    "mixed_ar1_noise": {
        "generator": _generate_mixed_ar1_noise,
        "description": "Mixed AR(1)+noise, n=500 — medium complexity",
        "diagnostics": ["F4", "F6"],
    },
}

# ---------------------------------------------------------------------------
# AMI curve helper (for F1 / F2 which need an AMI curve, not raw series)
# ---------------------------------------------------------------------------

_AMI_HORIZONS: int = 12


def _compute_ami_curve(series: np.ndarray, *, max_h: int = _AMI_HORIZONS) -> np.ndarray:
    """Compute AMI curve from series using kNN MI estimator."""
    from sklearn.feature_selection import mutual_info_regression

    n = len(series)
    curve = np.zeros(max_h, dtype=float)
    for h in range(1, max_h + 1):
        past = series[: n - h].reshape(-1, 1)
        future = series[h:]
        if len(past) < 30:
            curve[h - 1] = 0.0
            continue
        mi = mutual_info_regression(
            past,
            future,
            n_neighbors=8,
            random_state=_SEED,
        )
        curve[h - 1] = float(max(0.0, mi[0]))
    return curve


# ---------------------------------------------------------------------------
# Diagnostic runners — each returns a JSON-serialisable dict
# ---------------------------------------------------------------------------


def _run_f1(series: np.ndarray) -> dict[str, Any]:
    """Run F1 ForecastabilityProfile and return serialisable fields."""
    ami_curve = _compute_ami_curve(series)
    profile = build_forecastability_profile(ami_curve)
    return {
        "horizons": profile.horizons,
        "values": profile.values.tolist(),
        "epsilon": profile.epsilon,
        "informative_horizons": profile.informative_horizons,
        "peak_horizon": profile.peak_horizon,
        "is_non_monotone": profile.is_non_monotone,
    }


def _run_f2(series: np.ndarray) -> dict[str, Any]:
    """Run F2 TheoreticalLimitDiagnostics and return serialisable fields."""
    ami_curve = _compute_ami_curve(series)
    diag = build_theoretical_limit_diagnostics(ami_curve)
    return {
        "forecastability_ceiling_by_horizon": diag.forecastability_ceiling_by_horizon.tolist(),
        "ceiling_summary": diag.ceiling_summary,
        "compression_warning": diag.compression_warning,
        "dpi_warning": diag.dpi_warning,
    }


def _run_f3(series: np.ndarray) -> dict[str, Any]:
    """Run F3 PredictiveInfoLearningCurve and return serialisable fields."""
    curve = build_predictive_info_learning_curve(series, random_state=_SEED)
    return {
        "window_sizes": curve.window_sizes,
        "information_values": curve.information_values,
        "recommended_lookback": curve.recommended_lookback,
        "plateau_detected": curve.plateau_detected,
    }


def _run_f4(series: np.ndarray) -> dict[str, Any]:
    """Run F4 SpectralPredictability and return serialisable fields."""
    result = build_spectral_predictability(series)
    return {"omega": result.score}


def _run_f5(series: np.ndarray) -> dict[str, Any]:
    """Run F5 LargestLyapunovExponent and return serialisable fields."""
    result = build_largest_lyapunov_exponent(series)
    lam = result.lambda_estimate
    return {
        "lambda_estimate": None if (isinstance(lam, float) and math.isnan(lam)) else lam,
        "is_experimental": result.is_experimental,
    }


def _run_f6(series: np.ndarray) -> dict[str, Any]:
    """Run F6 ComplexityBand and return serialisable fields."""
    result = build_complexity_band(series)
    return {
        "permutation_entropy": result.permutation_entropy,
        "spectral_entropy": result.spectral_entropy,
        "complexity_band": result.complexity_band,
    }


_DIAGNOSTIC_RUNNERS: dict[str, Any] = {
    "F1": _run_f1,
    "F2": _run_f2,
    "F3": _run_f3,
    "F4": _run_f4,
    "F5": _run_f5,
    "F6": _run_f6,
}

# ---------------------------------------------------------------------------
# Build all diagnostic regression outputs
# ---------------------------------------------------------------------------


def build_diagnostic_regression_outputs() -> dict[str, dict[str, Any]]:
    """Run all diagnostics on all fixture series and return nested dict.

    Returns:
        Nested dict: ``{series_name: {diagnostic_name: {field: value, ...}, ...}, ...}``
    """
    outputs: dict[str, dict[str, Any]] = {}
    for series_name, spec in FIXTURE_SERIES.items():
        series = spec["generator"]()
        diag_outputs: dict[str, Any] = {}
        for diag_name in spec["diagnostics"]:
            runner = _DIAGNOSTIC_RUNNERS[diag_name]
            diag_outputs[diag_name] = runner(series)
        outputs[series_name] = diag_outputs
    return outputs


# ---------------------------------------------------------------------------
# Write outputs to JSON files
# ---------------------------------------------------------------------------


def write_diagnostic_regression_outputs(
    *,
    output_dir: Path,
) -> list[Path]:
    """Build and write diagnostic regression outputs to JSON files.

    One JSON file per fixture series, containing all diagnostic results.

    Args:
        output_dir: Directory where JSON files will be written.

    Returns:
        Ordered list of written file paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = build_diagnostic_regression_outputs()
    written: list[Path] = []
    for series_name in sorted(outputs):
        path = output_dir / f"{series_name}.json"
        path.write_text(json.dumps(outputs[series_name], indent=2, sort_keys=True) + "\n")
        written.append(path)
    return written


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

# Tolerances per diagnostic (from development plan)
_TOLERANCES: dict[str, dict[str, float]] = {
    "F1": {"values": 1e-6},
    "F2": {"forecastability_ceiling_by_horizon": 1e-6},
    "F3": {"information_values": 1e-4},
    "F4": {"omega": 1e-8},
    "F5": {"lambda_estimate": 1e-4},
    "F6": {"permutation_entropy": 1e-8, "spectral_entropy": 1e-8},
}


def _compare_value(
    actual: Any,
    expected: Any,
    *,
    atol: float,
    field_path: str,
) -> list[str]:
    """Compare a single value pair and return a list of error strings."""
    errors: list[str] = []
    if isinstance(expected, list) and isinstance(actual, list):
        if len(actual) != len(expected):
            errors.append(
                f"{field_path}: length mismatch (actual={len(actual)}, expected={len(expected)})"
            )
            return errors
        for i, (a, e) in enumerate(zip(actual, expected, strict=True)):
            errors.extend(_compare_value(a, e, atol=atol, field_path=f"{field_path}[{i}]"))
    elif isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        if expected is None and actual is None:
            pass
        elif abs(float(actual) - float(expected)) > atol:
            errors.append(
                f"{field_path}: value mismatch (actual={actual}, expected={expected}, atol={atol})"
            )
    elif actual != expected:
        errors.append(f"{field_path}: mismatch (actual={actual!r}, expected={expected!r})")
    return errors


def _verify_diagnostic(
    actual: dict[str, Any],
    expected: dict[str, Any],
    *,
    diag_name: str,
    series_name: str,
) -> list[str]:
    """Verify one diagnostic output against its expected reference."""
    tolerances = _TOLERANCES.get(diag_name, {})
    errors: list[str] = []

    for field, exp_val in expected.items():
        if field not in actual:
            errors.append(f"{series_name}/{diag_name}: missing field '{field}'")
            continue
        act_val = actual[field]
        atol = tolerances.get(field, 0.0)
        prefix = f"{series_name}/{diag_name}/{field}"
        errors.extend(_compare_value(act_val, exp_val, atol=atol, field_path=prefix))

    return errors


def verify_diagnostic_regression_outputs(
    *,
    actual_dir: Path,
    expected_dir: Path,
) -> None:
    """Verify rebuilt diagnostic regression outputs against frozen expected.

    Args:
        actual_dir: Directory containing rebuilt JSON files.
        expected_dir: Directory containing frozen expected JSON files.

    Raises:
        ValueError: When any actual output diverges from expected.
    """
    errors: list[str] = []
    expected_files = sorted(expected_dir.glob("*.json"))
    if not expected_files:
        raise ValueError(f"No expected JSON files found in {expected_dir}")

    for expected_path in expected_files:
        series_name = expected_path.stem
        actual_path = actual_dir / expected_path.name
        if not actual_path.exists():
            errors.append(f"Missing rebuilt output: {actual_path.name}")
            continue
        expected_data: dict[str, Any] = json.loads(expected_path.read_text())
        actual_data: dict[str, Any] = json.loads(actual_path.read_text())

        for diag_name, exp_diag in expected_data.items():
            if diag_name not in actual_data:
                errors.append(f"{series_name}: missing diagnostic '{diag_name}'")
                continue
            errors.extend(
                _verify_diagnostic(
                    actual_data[diag_name],
                    exp_diag,
                    diag_name=diag_name,
                    series_name=series_name,
                )
            )

    if errors:
        error_block = "\n".join(f"- {line}" for line in errors)
        raise ValueError(f"Diagnostic regression verification failed:\n{error_block}")
