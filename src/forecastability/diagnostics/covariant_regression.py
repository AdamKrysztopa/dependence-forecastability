"""Covariant regression fixture generation, rebuild, and verification.

Generates deterministic synthetic multivariate benchmarks, runs the
covariant analysis facade for each case, serialises outputs to JSON, and
verifies rebuilt outputs against frozen expected files.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from forecastability.use_cases.run_covariant_analysis import run_covariant_analysis
from forecastability.utils.synthetic import generate_covariant_benchmark

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fixture case registry
# ---------------------------------------------------------------------------

COVARIANT_FIXTURE_CASES: dict[str, dict[str, Any]] = {
    "benchmark_ami_pami": {
        "description": "CrossAMI + pCrossAMI on direct/mediated/noise drivers (n=900)",
        "n": 900,
        "seed": 42,
        "drivers": ["driver_direct", "driver_mediated", "driver_noise"],
        "methods": ["cross_ami", "cross_pami"],
        "n_surrogates": 99,
        "max_lag": 3,
    },
    "benchmark_gcmi": {
        "description": "GCMI on direct/mediated/noise drivers (n=900)",
        "n": 900,
        "seed": 42,
        "drivers": ["driver_direct", "driver_mediated", "driver_noise"],
        "methods": ["gcmi"],
        "n_surrogates": 99,
        "max_lag": 3,
    },
    "benchmark_te": {
        "description": "Transfer Entropy on direct/mediated/noise drivers (n=900)",
        "n": 900,
        "seed": 42,
        "drivers": ["driver_direct", "driver_mediated", "driver_noise"],
        "methods": ["te"],
        "n_surrogates": 99,
        "max_lag": 3,
    },
}

# Maps method name (as used in cases) to CovariantSummaryRow field name
_METHOD_TO_FIELD: dict[str, str] = {
    "cross_ami": "cross_ami",
    "cross_pami": "cross_pami",
    "gcmi": "gcmi",
    "te": "transfer_entropy",
}

# Float fields in the per-row JSON — use atol for comparison
_FLOAT_ROW_FIELDS: frozenset[str] = frozenset(
    {"cross_ami", "cross_pami", "gcmi", "transfer_entropy"}
)

_ATOL: float = 1e-6


# ---------------------------------------------------------------------------
# Single-case runner
# ---------------------------------------------------------------------------


def _run_case(*, case_name: str, case: dict[str, Any]) -> dict[str, Any]:
    """Run one fixture case and return its JSON-serialisable output dict.

    Args:
        case_name: Registry key used for logging.
        case: Case spec dict from COVARIANT_FIXTURE_CASES.

    Returns:
        Dict with keys ``rows``, ``peak_score_driver``, ``peak_score_lag``,
        ``direct_beats_noise``, ``mediated_beats_noise``.
    """
    _logger.info("Running covariant regression case: %s", case_name)

    df = generate_covariant_benchmark(n=case["n"], seed=case["seed"])
    target = df["target"].to_numpy()
    driver_names: list[str] = case["drivers"]
    drivers = {name: df[name].to_numpy() for name in driver_names}

    bundle = run_covariant_analysis(
        target,
        drivers,
        methods=case["methods"],
        n_surrogates=case["n_surrogates"],
        max_lag=case["max_lag"],
        random_state=42,
    )

    methods: list[str] = case["methods"]
    include_significance = "cross_ami" in methods

    # Build rows dict: sorted by driver then lag for determinism
    rows: dict[str, dict[str, Any]] = {}
    for row in sorted(bundle.summary_table, key=lambda r: (r.driver, r.lag)):
        key = f"{row.driver}:{row.lag}"
        row_data: dict[str, Any] = {}
        for method in methods:
            field = _METHOD_TO_FIELD[method]
            row_data[field] = getattr(row, field)
        if include_significance:
            row_data["significance"] = row.significance
        rows[key] = row_data

    # Determine primary field for peak scoring (first method in case)
    primary_field = _METHOD_TO_FIELD[methods[0]]

    # Find per-driver peak (value, lag) on the primary field
    driver_peaks: dict[str, tuple[float, int]] = {}
    for row in bundle.summary_table:
        if row.driver not in driver_names:
            continue
        value = getattr(row, primary_field)
        if value is None:
            continue
        current = driver_peaks.get(row.driver)
        if current is None or value > current[0]:
            driver_peaks[row.driver] = (value, row.lag)

    best_driver = max(driver_peaks, key=lambda d: driver_peaks[d][0])
    peak_score_driver: str = best_driver
    peak_score_lag: int = driver_peaks[best_driver][1]

    direct_peak = driver_peaks.get("driver_direct", (0.0, 0))[0]
    noise_peak = driver_peaks.get("driver_noise", (0.0, 0))[0]
    mediated_peak = driver_peaks.get("driver_mediated", (0.0, 0))[0]

    return {
        "rows": rows,
        "peak_score_driver": peak_score_driver,
        "peak_score_lag": peak_score_lag,
        "direct_beats_noise": direct_peak > noise_peak,
        "mediated_beats_noise": mediated_peak > noise_peak,
    }


# ---------------------------------------------------------------------------
# Build all outputs
# ---------------------------------------------------------------------------


def build_covariant_regression_outputs() -> dict[str, dict[str, Any]]:
    """Run all cases and return a nested dict of JSON-serialisable outputs.

    Returns:
        Nested dict: ``{case_name: {rows: {...}, peak_score_driver: ..., ...}}``
    """
    return {
        case_name: _run_case(case_name=case_name, case=case)
        for case_name, case in COVARIANT_FIXTURE_CASES.items()
    }


# ---------------------------------------------------------------------------
# Write outputs to JSON files
# ---------------------------------------------------------------------------


def write_covariant_regression_outputs(*, output_dir: Path) -> list[Path]:
    """Build and write covariant regression outputs to JSON files.

    One JSON file per fixture case, containing all analysis results.

    Args:
        output_dir: Directory where JSON files will be written.

    Returns:
        Ordered list of written file paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = build_covariant_regression_outputs()
    written: list[Path] = []
    for case_name in sorted(outputs):
        path = output_dir / f"{case_name}.json"
        path.write_text(json.dumps(outputs[case_name], indent=2, sort_keys=True) + "\n")
        written.append(path)
    return written


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def _compare_scalar(
    actual: Any,
    expected: Any,
    *,
    field_path: str,
) -> list[str]:
    """Compare a scalar value pair and return a list of error strings.

    Args:
        actual: Value from the rebuilt output.
        expected: Value from the frozen expected file.
        field_path: Dot-separated path for error messages.

    Returns:
        List of error strings; empty when values match within tolerance.
    """
    errors: list[str] = []
    if expected is None and actual is None:
        return errors
    if expected is None or actual is None:
        errors.append(f"{field_path}: None mismatch (actual={actual!r}, expected={expected!r})")
        return errors
    # bool must be checked before int (bool is a subclass of int in Python)
    if isinstance(expected, bool):
        if actual != expected:
            errors.append(f"{field_path}: bool mismatch (actual={actual!r}, expected={expected!r})")
    elif isinstance(expected, (float, int)) and isinstance(actual, (float, int)):
        if abs(float(actual) - float(expected)) > _ATOL:
            errors.append(
                f"{field_path}: float mismatch (actual={actual}, expected={expected}, atol={_ATOL})"
            )
    elif actual != expected:
        errors.append(f"{field_path}: mismatch (actual={actual!r}, expected={expected!r})")
    return errors


def _compare_case(
    actual: dict[str, Any],
    expected: dict[str, Any],
    *,
    case_name: str,
) -> list[str]:
    """Compare one rebuilt case dict against its expected reference.

    Args:
        actual: Rebuilt output dict for this case.
        expected: Frozen expected dict for this case.
        case_name: Case name used in error messages.

    Returns:
        List of error strings; empty when everything matches.
    """
    errors: list[str] = []

    # Compare rows nested dict
    actual_rows: dict[str, Any] = actual.get("rows", {})
    expected_rows: dict[str, Any] = expected.get("rows", {})
    for row_key, exp_row in expected_rows.items():
        if row_key not in actual_rows:
            errors.append(f"{case_name}/rows: missing row '{row_key}'")
            continue
        act_row = actual_rows[row_key]
        for field, exp_val in exp_row.items():
            if field not in act_row:
                errors.append(f"{case_name}/rows/{row_key}: missing field '{field}'")
                continue
            act_val = act_row[field]
            field_path = f"{case_name}/rows/{row_key}/{field}"
            errors.extend(_compare_scalar(act_val, exp_val, field_path=field_path))

    # Compare top-level scalar fields
    for field in (
        "peak_score_driver",
        "peak_score_lag",
        "direct_beats_noise",
        "mediated_beats_noise",
    ):
        if field not in expected:
            continue
        if field not in actual:
            errors.append(f"{case_name}: missing field '{field}'")
            continue
        errors.extend(
            _compare_scalar(
                actual[field],
                expected[field],
                field_path=f"{case_name}/{field}",
            )
        )

    return errors


def verify_covariant_regression_outputs(
    *,
    actual_dir: Path,
    expected_dir: Path,
) -> None:
    """Verify rebuilt covariant regression outputs against frozen expected.

    Args:
        actual_dir: Directory containing rebuilt JSON files.
        expected_dir: Directory containing frozen expected JSON files.

    Raises:
        ValueError: When any actual output diverges from expected, or when
            expected files are missing from the actual directory.
    """
    errors: list[str] = []
    expected_files = sorted(expected_dir.glob("*.json"))
    if not expected_files:
        raise ValueError(f"No expected JSON files found in {expected_dir}")

    for expected_path in expected_files:
        case_name = expected_path.stem
        actual_path = actual_dir / expected_path.name
        if not actual_path.exists():
            errors.append(f"Missing rebuilt output: {actual_path.name}")
            continue
        expected_data: dict[str, Any] = json.loads(expected_path.read_text())
        actual_data: dict[str, Any] = json.loads(actual_path.read_text())
        errors.extend(_compare_case(actual_data, expected_data, case_name=case_name))

    if errors:
        error_block = "\n".join(f"- {line}" for line in errors)
        raise ValueError(f"Covariant regression verification failed:\n{error_block}")
