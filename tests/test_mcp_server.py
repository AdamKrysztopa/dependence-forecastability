"""Tests for the MCP server transport adapter (AGT-011)."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import numpy as np
import pytest

from forecastability.adapters.mcp_server import (
    _MCP_AVAILABLE,
    _build_triage_request,
    _readiness_to_json,
    _triage_result_to_json,
)
from forecastability.triage.models import AnalysisGoal, TriageRequest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ar1(n: int = 150, *, phi: float = 0.85, seed: int = 42) -> list[float]:
    rng = np.random.default_rng(seed)
    ts = np.zeros(n)
    ts[0] = rng.standard_normal()
    for i in range(1, n):
        ts[i] = phi * ts[i - 1] + rng.standard_normal()
    return ts.tolist()


def _make_white_noise(n: int = 150, *, seed: int = 2) -> list[float]:
    rng = np.random.default_rng(seed)
    return rng.standard_normal(n).tolist()


def _make_short(n: int = 20) -> list[float]:
    rng = np.random.default_rng(0)
    return rng.standard_normal(n).tolist()


# ---------------------------------------------------------------------------
# _build_triage_request
# ---------------------------------------------------------------------------


class TestBuildTriageRequest:
    def test_returns_triage_request_instance(self) -> None:
        req = _build_triage_request([1.0, 2.0, 3.0])
        assert isinstance(req, TriageRequest)

    def test_series_is_float64_array(self) -> None:
        req = _build_triage_request([1, 2, 3])
        assert req.series.dtype == np.float64

    def test_default_goal_is_univariate(self) -> None:
        req = _build_triage_request([1.0, 2.0, 3.0])
        assert req.goal == AnalysisGoal.univariate

    def test_exog_goal_is_parsed(self) -> None:
        series = [1.0] * 10
        exog = [0.5] * 10
        req = _build_triage_request(series, exog=exog, goal="exogenous")
        assert req.goal == AnalysisGoal.exogenous
        assert req.exog is not None
        assert req.exog.shape == (10,)

    def test_none_exog_stays_none(self) -> None:
        req = _build_triage_request([1.0, 2.0], exog=None)
        assert req.exog is None

    def test_invalid_goal_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            _build_triage_request([1.0], goal="bad_goal")

    def test_parameters_are_passed_through(self) -> None:
        req = _build_triage_request([1.0] * 5, max_lag=15, n_surrogates=199, random_state=7)
        assert req.max_lag == 15
        assert req.n_surrogates == 199
        assert req.random_state == 7


# ---------------------------------------------------------------------------
# _readiness_to_json
# ---------------------------------------------------------------------------


class TestReadinessToJson:
    def test_returns_valid_json(self) -> None:
        from forecastability.triage.readiness import assess_readiness

        req = TriageRequest(series=np.asarray(_make_short()))
        report = assess_readiness(req)
        raw = _readiness_to_json(report)
        data = json.loads(raw)
        assert "status" in data
        assert "warnings" in data

    def test_clear_series_status_is_clear_or_warning(self) -> None:
        from forecastability.triage.readiness import assess_readiness

        req = TriageRequest(series=np.asarray(_make_ar1()), max_lag=20)
        report = assess_readiness(req)
        raw = _readiness_to_json(report)
        data = json.loads(raw)
        assert data["status"] in {"clear", "warning"}

    def test_short_series_status_is_blocked(self) -> None:
        from forecastability.triage.readiness import assess_readiness

        req = TriageRequest(series=np.asarray(_make_short()))
        report = assess_readiness(req)
        raw = _readiness_to_json(report)
        data = json.loads(raw)
        assert data["status"] == "blocked"


# ---------------------------------------------------------------------------
# _triage_result_to_json
# ---------------------------------------------------------------------------


class TestTriageResultToJson:
    def test_blocked_result_has_blocked_true(self) -> None:
        from forecastability.use_cases.run_triage import run_triage

        req = TriageRequest(series=np.asarray(_make_short()))
        result = run_triage(req)
        raw = _triage_result_to_json(result)
        data = json.loads(raw)
        assert data["blocked"] is True

    def test_complete_result_has_interpretation(self) -> None:
        from forecastability.use_cases.run_triage import run_triage

        req = TriageRequest(series=np.asarray(_make_ar1()), max_lag=20)
        result = run_triage(req)
        raw = _triage_result_to_json(result)
        data = json.loads(raw)
        assert data["blocked"] is False
        assert "interpretation" in data
        assert data["interpretation"]["forecastability_class"] in {"high", "medium", "low"}

    def test_result_json_is_valid_json(self) -> None:
        from forecastability.use_cases.run_triage import run_triage

        req = TriageRequest(series=np.asarray(_make_ar1()), max_lag=20)
        result = run_triage(req)
        raw = _triage_result_to_json(result)
        # Should not raise
        json.loads(raw)


# ---------------------------------------------------------------------------
# MCP tool functions (skip if mcp unavailable)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _MCP_AVAILABLE, reason="mcp package not installed")
class TestMcpToolFunctions:
    """Test the tool functions that are registered on the MCP server."""

    def test_validate_series_returns_json(self) -> None:
        from forecastability.adapters.mcp_server import validate_series

        result = validate_series(_make_ar1(), max_lag=20)
        data = json.loads(result)
        assert "status" in data
        assert "warnings" in data

    def test_validate_series_blocked_for_short(self) -> None:
        from forecastability.adapters.mcp_server import validate_series

        result = validate_series(_make_short())
        data = json.loads(result)
        assert data["status"] == "blocked"

    def test_validate_series_clear_for_adequate(self) -> None:
        from forecastability.adapters.mcp_server import validate_series

        result = validate_series(_make_ar1(), max_lag=20)
        data = json.loads(result)
        assert data["status"] in {"clear", "warning"}

    def test_run_triage_tool_returns_json(self) -> None:
        from forecastability.adapters.mcp_server import run_triage_tool

        result = run_triage_tool(_make_ar1(), max_lag=20)
        data = json.loads(result)
        assert "blocked" in data

    def test_run_triage_tool_ar1_gives_high(self) -> None:
        from forecastability.adapters.mcp_server import run_triage_tool

        result = run_triage_tool(_make_ar1(phi=0.9), max_lag=20)
        data = json.loads(result)
        assert data["blocked"] is False
        assert data["interpretation"]["forecastability_class"] == "high"

    def test_run_triage_tool_blocked_for_short(self) -> None:
        from forecastability.adapters.mcp_server import run_triage_tool

        result = run_triage_tool(_make_short())
        data = json.loads(result)
        assert data["blocked"] is True

    def test_list_scorers_tool_returns_json_list(self) -> None:
        from forecastability.adapters.mcp_server import list_scorers_tool

        result = list_scorers_tool()
        data = json.loads(result)
        assert isinstance(data, list)
        assert any(s["name"] == "mi" for s in data)

    def test_scorer_catalog_resource_returns_json(self) -> None:
        from forecastability.adapters.mcp_server import scorer_catalog

        result = scorer_catalog()
        data = json.loads(result)
        assert isinstance(data, list)

    def test_triage_request_schema_resource_returns_json(self) -> None:
        from forecastability.adapters.mcp_server import triage_request_schema

        result = triage_request_schema()
        data = json.loads(result)
        assert "series" in data
        assert "goal" in data

    def test_mcp_object_is_not_none(self) -> None:
        from forecastability.adapters.mcp_server import mcp

        assert mcp is not None


# ---------------------------------------------------------------------------
# Architecture boundary: mcp_server.py must not import domain-forbidden packages
# ---------------------------------------------------------------------------


def test_mcp_server_imports_no_domain_forbidden_packages() -> None:
    """AST check: mcp_server.py must not import fastapi, httpx, click, etc.

    The MCP server is an adapter; it is *allowed* to import mcp, but must
    not directly import packages that are forbidden in domain modules.  We
    specifically check that httpx, click, typer, and matplotlib are absent.
    """
    adapter_forbidden = {"httpx", "click", "typer", "matplotlib"}
    root = Path(__file__).parent.parent
    path = root / "src" / "forecastability" / "adapters" / "mcp_server.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split(".")[0])

    violations = [pkg for pkg in imports if pkg in adapter_forbidden]
    assert not violations, f"mcp_server.py imports forbidden packages: {violations}"


def test_api_imports_no_domain_forbidden_packages() -> None:
    """AST check: api.py must not import click, typer, or mcp."""
    api_forbidden = {"click", "typer", "mcp"}
    root = Path(__file__).parent.parent
    path = root / "src" / "forecastability" / "adapters" / "api.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split(".")[0])

    violations = [pkg for pkg in imports if pkg in api_forbidden]
    assert not violations, f"api.py imports forbidden packages: {violations}"
