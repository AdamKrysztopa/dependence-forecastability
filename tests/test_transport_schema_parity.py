"""Schema-level parity tests for CLI/API/MCP triage outputs."""

from __future__ import annotations

import json
from typing import cast

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from forecastability.adapters.api import TriageHTTPResponse, app
from forecastability.adapters.cli import build_parser, cmd_triage
from forecastability.adapters.mcp_server import _triage_result_to_json
from forecastability.triage.models import TriageRequest, TriageResult
from forecastability.use_cases.run_triage import run_triage


@pytest.fixture(scope="module")
def api_client() -> TestClient:
    assert app is not None, "FastAPI app is None — fastapi not installed"
    return TestClient(app)


def _run_cli_triage(
    *,
    series: list[float],
    max_lag: int,
    capsys: pytest.CaptureFixture[str],
) -> dict[str, object]:
    parser = build_parser()
    args = parser.parse_args(
        [
            "triage",
            "--series",
            json.dumps(series),
            "--max-lag",
            str(max_lag),
            "--n-surrogates",
            "99",
            "--random-state",
            "42",
            "--format",
            "json",
        ]
    )
    code = cmd_triage(args)
    captured = capsys.readouterr()
    assert code == 0
    data = json.loads(captured.out)
    assert isinstance(data, dict)
    return data


def _run_api_triage(
    *,
    series: list[float],
    max_lag: int,
    client: TestClient,
) -> dict[str, object]:
    payload = {
        "series": series,
        "max_lag": max_lag,
        "n_surrogates": 99,
        "random_state": 42,
    }
    response = client.post("/triage", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    TriageHTTPResponse.model_validate(data)
    return data


def _run_mcp_triage(
    *,
    request: TriageRequest,
    cached_result: TriageResult | None,
) -> dict[str, object]:
    result = cached_result if cached_result is not None else run_triage(request)
    raw = _triage_result_to_json(result)
    data = json.loads(raw)
    assert isinstance(data, dict)
    return data


def _warning_codes_from_entries(entries: list[object]) -> list[str]:
    codes: list[str] = []
    for entry in entries:
        typed_entry = _as_object_dict(entry)
        if typed_entry is not None:
            code = typed_entry.get("code")
            if isinstance(code, str):
                codes.append(code)
    return sorted(codes)


def _as_object_dict(value: object) -> dict[str, object] | None:
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return None


def _as_object_list(value: object) -> list[object] | None:
    if isinstance(value, list):
        return cast(list[object], value)
    return None


def _normalize_cli_or_mcp(payload: dict[str, object]) -> dict[str, object]:
    readiness = payload.get("readiness")
    readiness_status = "unknown"
    warning_codes: list[str] = []
    typed_readiness = _as_object_dict(readiness)
    if typed_readiness is not None:
        status = typed_readiness.get("status")
        if isinstance(status, str):
            readiness_status = status
        warnings = _as_object_list(typed_readiness.get("warnings"))
        if warnings is not None:
            warning_codes = _warning_codes_from_entries(warnings)

    method_plan = payload.get("method_plan")
    route: str | None = None
    compute_surrogates: bool | None = None
    typed_method_plan = _as_object_dict(method_plan)
    if typed_method_plan is not None:
        route_value = typed_method_plan.get("route")
        if isinstance(route_value, str):
            route = route_value
        surrogates_value = typed_method_plan.get("compute_surrogates")
        if isinstance(surrogates_value, bool):
            compute_surrogates = surrogates_value

    interpretation = payload.get("interpretation")
    forecastability_class: str | None = None
    directness_class: str | None = None
    modeling_regime: str | None = None
    typed_interpretation = _as_object_dict(interpretation)
    if typed_interpretation is not None:
        forecastability = typed_interpretation.get("forecastability_class")
        if isinstance(forecastability, str):
            forecastability_class = forecastability
        directness = typed_interpretation.get("directness_class")
        if isinstance(directness, str):
            directness_class = directness
        regime = typed_interpretation.get("modeling_regime")
        if isinstance(regime, str):
            modeling_regime = regime

    n_sig_raw_lags: int | None = None
    n_sig_partial_lags: int | None = None
    analyze_summary = payload.get("analyze_summary")
    typed_analyze_summary = _as_object_dict(analyze_summary)
    if typed_analyze_summary is not None:
        raw_count = typed_analyze_summary.get("n_sig_raw_lags")
        if isinstance(raw_count, int):
            n_sig_raw_lags = raw_count
        partial_count = typed_analyze_summary.get("n_sig_partial_lags")
        if isinstance(partial_count, int):
            n_sig_partial_lags = partial_count

    blocked = payload.get("blocked")
    return {
        "blocked": bool(blocked),
        "readiness_status": readiness_status,
        "warning_codes": warning_codes,
        "route": route,
        "compute_surrogates": compute_surrogates,
        "forecastability_class": forecastability_class,
        "directness_class": directness_class,
        "modeling_regime": modeling_regime,
        "n_sig_raw_lags": n_sig_raw_lags,
        "n_sig_partial_lags": n_sig_partial_lags,
    }


def _normalize_api(payload: dict[str, object]) -> dict[str, object]:
    warnings = payload.get("readiness_warnings")
    warning_codes: list[str] = []
    typed_warnings = _as_object_list(warnings)
    if typed_warnings is not None:
        warning_codes = _warning_codes_from_entries(typed_warnings)

    blocked = payload.get("blocked")
    readiness_status = payload.get("readiness_status")
    route = payload.get("route")
    compute_surrogates = payload.get("compute_surrogates")
    forecastability_class = payload.get("forecastability_class")
    directness_class = payload.get("directness_class")
    modeling_regime = payload.get("modeling_regime")
    n_sig_raw_lags = payload.get("n_sig_raw_lags")
    n_sig_partial_lags = payload.get("n_sig_partial_lags")

    return {
        "blocked": bool(blocked),
        "readiness_status": readiness_status,
        "warning_codes": warning_codes,
        "route": route,
        "compute_surrogates": compute_surrogates,
        "forecastability_class": forecastability_class,
        "directness_class": directness_class,
        "modeling_regime": modeling_regime,
        "n_sig_raw_lags": n_sig_raw_lags,
        "n_sig_partial_lags": n_sig_partial_lags,
    }


def test_cli_api_mcp_parity_on_same_unblocked_input(
    deterministic_triage_series: list[float],
    deterministic_triage_request: TriageRequest,
    deterministic_triage_result: TriageResult,
    api_client: TestClient,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli_payload = _run_cli_triage(
        series=deterministic_triage_series,
        max_lag=deterministic_triage_request.max_lag,
        capsys=capsys,
    )
    api_payload = _run_api_triage(
        series=deterministic_triage_series,
        max_lag=deterministic_triage_request.max_lag,
        client=api_client,
    )
    mcp_payload = _run_mcp_triage(
        request=deterministic_triage_request,
        cached_result=deterministic_triage_result,
    )

    normalized_cli = _normalize_cli_or_mcp(cli_payload)
    normalized_api = _normalize_api(api_payload)
    normalized_mcp = _normalize_cli_or_mcp(mcp_payload)

    assert normalized_cli == normalized_api
    assert normalized_mcp == normalized_api


def test_cli_api_mcp_parity_on_same_blocked_input(
    deterministic_blocked_series: list[float],
    deterministic_blocked_request: TriageRequest,
    api_client: TestClient,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli_payload = _run_cli_triage(
        series=deterministic_blocked_series,
        max_lag=deterministic_blocked_request.max_lag,
        capsys=capsys,
    )
    api_payload = _run_api_triage(
        series=deterministic_blocked_series,
        max_lag=deterministic_blocked_request.max_lag,
        client=api_client,
    )
    mcp_payload = _run_mcp_triage(
        request=deterministic_blocked_request,
        cached_result=None,
    )

    normalized_cli = _normalize_cli_or_mcp(cli_payload)
    normalized_api = _normalize_api(api_payload)
    normalized_mcp = _normalize_cli_or_mcp(mcp_payload)

    assert normalized_cli == normalized_api
    assert normalized_mcp == normalized_api
