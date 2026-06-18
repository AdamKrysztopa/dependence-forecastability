"""Forecast prep contract regression fixture generation and verification (FPC-F11).

Builds deterministic ForecastPrepContract payloads for canonical scenarios,
serialises them to JSON and text, and verifies rebuilt outputs against frozen
expected files.

Scenarios
---------
- ``contract_univariate``: minimal non-blocked univariate contract, no calendar.
- ``contract_blocked``: blocked triage result.
- ``contract_with_calendar``: non-blocked contract with calendar features enabled.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from forecastability.services.forecast_prep_export import (
    forecast_prep_contract_to_lag_table,
    forecast_prep_contract_to_markdown,
)
from forecastability.triage.models import (
    AnalysisGoal,
    ReadinessReport,
    ReadinessStatus,
    TriageRequest,
    TriageResult,
)
from forecastability.use_cases.build_forecast_prep_contract import build_forecast_prep_contract
from forecastability.utils.types import Diagnostics, InterpretationResult, RoutingRecommendation

_ATOL = 1e-6
_RTOL = 1e-2

FORECAST_PREP_FIXTURE_CASES: tuple[str, ...] = (
    "contract_univariate",
    "contract_blocked",
    "contract_with_calendar",
)


# ---------------------------------------------------------------------------
# Deterministic scenario builders
# ---------------------------------------------------------------------------


def _triage_result(*, blocked: bool, primary_lags: list[int] | None = None) -> TriageResult:
    """Build a minimal deterministic TriageResult for regression fixture generation."""
    return TriageResult(
        request=TriageRequest(
            series=np.linspace(0.0, 1.0, 120),
            goal=AnalysisGoal.univariate,
            max_lag=24,
            n_surrogates=99,
            random_state=42,
        ),
        readiness=ReadinessReport(
            status=ReadinessStatus.blocked if blocked else ReadinessStatus.clear,
            warnings=[],
        ),
        blocked=blocked,
        interpretation=None
        if blocked
        else InterpretationResult(
            forecastability_class="high",
            directness_class="high",
            primary_lags=primary_lags or [1, 12],
            modeling_regime="deterministic triage",
            narrative="regression fixture narrative",
            diagnostics=Diagnostics(
                peak_ami_first_5=0.35,
                directness_ratio=0.65,
                n_sig_ami=5,
                n_sig_pami=3,
                exploitability_mismatch=0,
                best_smape=0.08,
            ),
        ),
    )


def _routing(*, confidence_label: str = "high") -> RoutingRecommendation:
    """Build a deterministic routing recommendation for regression fixtures."""
    return RoutingRecommendation(
        primary_families=["arima", "ets"],
        secondary_families=["linear_state_space"],
        rationale=["deterministic routing for regression fixture"],
        caution_flags=[],
        confidence_label=confidence_label,  # type: ignore[arg-type]
    )


def _build_contract_univariate() -> dict[str, Any]:
    """Minimal non-blocked univariate contract payload."""
    contract = build_forecast_prep_contract(
        _triage_result(blocked=False, primary_lags=[1, 12]),
        routing_recommendation=_routing(confidence_label="high"),
        add_calendar_features=False,
    )
    return _contract_to_payload(contract)


def _build_contract_blocked() -> dict[str, Any]:
    """Blocked triage produces conservative empty payload."""
    contract = build_forecast_prep_contract(
        _triage_result(blocked=True),
        routing_recommendation=_routing(confidence_label="high"),
        add_calendar_features=False,
    )
    return _contract_to_payload(contract)


def _build_contract_with_calendar() -> dict[str, Any]:
    """Non-blocked contract with deterministic calendar features."""
    dt_index = pd.date_range("2023-01-01", periods=120, freq="D")
    contract = build_forecast_prep_contract(
        _triage_result(blocked=False, primary_lags=[1, 7]),
        routing_recommendation=_routing(confidence_label="medium"),
        add_calendar_features=True,
        calendar_locale=None,
        datetime_index=dt_index,
    )
    return _contract_to_payload(contract)


def _contract_to_payload(contract: object) -> dict[str, Any]:
    """Serialise a ForecastPrepContract to a regression-friendly dict."""
    from forecastability.utils.types import ForecastPrepContract

    assert isinstance(contract, ForecastPrepContract)
    markdown = forecast_prep_contract_to_markdown(contract)
    lag_table = forecast_prep_contract_to_lag_table(contract)
    return {
        "contract": json.loads(contract.model_dump_json()),
        "markdown_length": len(markdown),
        "lag_table": lag_table,
    }


_CASE_BUILDERS: dict[str, Any] = {
    "contract_univariate": _build_contract_univariate,
    "contract_blocked": _build_contract_blocked,
    "contract_with_calendar": _build_contract_with_calendar,
}


# ---------------------------------------------------------------------------
# Build and write
# ---------------------------------------------------------------------------


def build_forecast_prep_regression_outputs() -> dict[str, dict[str, Any]]:
    """Build all forecast prep contract regression payloads deterministically."""
    return {case: _CASE_BUILDERS[case]() for case in FORECAST_PREP_FIXTURE_CASES}


def write_forecast_prep_regression_outputs(*, output_dir: Path) -> list[Path]:
    """Build and write forecast prep regression outputs to JSON files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = build_forecast_prep_regression_outputs()
    written: list[Path] = []
    for case_name in sorted(outputs):
        path = output_dir / f"{case_name}.json"
        path.write_text(json.dumps(outputs[case_name], indent=2, sort_keys=True) + "\n")
        written.append(path)
    return written


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def _compare_value(actual: Any, expected: Any, *, field_path: str) -> list[str]:
    """Compare one possibly-nested value; return human-readable mismatch messages."""
    errors: list[str] = []
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key, exp_value in expected.items():
            if key not in actual:
                errors.append(f"{field_path}: missing key '{key}'")
                continue
            errors.extend(_compare_value(actual[key], exp_value, field_path=f"{field_path}/{key}"))
        return errors

    if isinstance(expected, list) and isinstance(actual, list):
        if len(actual) != len(expected):
            errors.append(
                f"{field_path}: length mismatch (actual={len(actual)}, expected={len(expected)})"
            )
            return errors
        for idx, (act_item, exp_item) in enumerate(zip(actual, expected, strict=True)):
            errors.extend(_compare_value(act_item, exp_item, field_path=f"{field_path}[{idx}]"))
        return errors

    if isinstance(expected, float) and isinstance(actual, (int, float)):
        if not math.isclose(float(actual), expected, rel_tol=_RTOL, abs_tol=_ATOL):
            errors.append(
                f"{field_path}: float mismatch (actual={actual}, expected={expected}, "
                f"atol={_ATOL}, rtol={_RTOL})"
            )
        return errors

    if actual != expected:
        errors.append(f"{field_path}: mismatch (actual={actual!r}, expected={expected!r})")
    return errors


def verify_forecast_prep_regression_outputs(*, actual_dir: Path, expected_dir: Path) -> None:
    """Verify rebuilt regression outputs against frozen expected JSON files.

    Raises:
        ValueError: When any mismatch is found or expected files are missing.
    """
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
            _compare_value(actual_payload, expected_payload, field_path=expected_path.stem)
        )

    if errors:
        error_block = "\n".join(f"- {item}" for item in errors)
        raise ValueError(f"Forecast prep regression verification failed:\n{error_block}")
