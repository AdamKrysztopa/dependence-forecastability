"""Tests for the FastAPI HTTP transport adapter (AGT-010)."""

from __future__ import annotations

import numpy as np
import pytest
from typing import Generator

# Skip the entire module if fastapi or httpx are not installed
pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from forecastability.adapters.api import (
    TriageHTTPRequest,
    TriageHTTPResponse,
    _build_triage_response,
    app,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ar1(n: int = 150, *, phi: float = 0.85, seed: int = 42) -> list[float]:
    """Generate a simple AR(1) series."""
    rng = np.random.default_rng(seed)
    ts = np.zeros(n)
    ts[0] = rng.standard_normal()
    for i in range(1, n):
        ts[i] = phi * ts[i - 1] + rng.standard_normal()
    return ts.tolist()


def _make_white_noise(n: int = 150, *, seed: int = 2) -> list[float]:
    rng = np.random.default_rng(seed)
    return rng.standard_normal(n).tolist()


@pytest.fixture(scope="module")
def client() -> TestClient:
    assert app is not None, "FastAPI app is None — fastapi not installed"
    return TestClient(app)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    def test_returns_200(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_returns_status_ok(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# /scorers
# ---------------------------------------------------------------------------


class TestScorersEndpoint:
    def test_returns_200(self, client: TestClient) -> None:
        resp = client.get("/scorers")
        assert resp.status_code == 200

    def test_returns_list(self, client: TestClient) -> None:
        data = client.get("/scorers").json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_each_entry_has_required_keys(self, client: TestClient) -> None:
        data = client.get("/scorers").json()
        for entry in data:
            assert "name" in entry
            assert "family" in entry
            assert "description" in entry

    def test_mi_scorer_present(self, client: TestClient) -> None:
        data = client.get("/scorers").json()
        names = [s["name"] for s in data]
        assert "mi" in names


# ---------------------------------------------------------------------------
# POST /triage — happy path
# ---------------------------------------------------------------------------


class TestTriageEndpointHappyPath:
    def test_returns_200(self, client: TestClient) -> None:
        payload = {"series": _make_ar1(), "max_lag": 20}
        resp = client.post("/triage", json=payload)
        assert resp.status_code == 200

    def test_response_not_blocked_for_adequate_series(self, client: TestClient) -> None:
        payload = {"series": _make_ar1(), "max_lag": 20}
        data = client.post("/triage", json=payload).json()
        assert data["blocked"] is False

    def test_response_has_forecastability_class(self, client: TestClient) -> None:
        payload = {"series": _make_ar1(), "max_lag": 20}
        data = client.post("/triage", json=payload).json()
        assert data["forecastability_class"] in {"high", "medium", "low"}

    def test_ar1_forecastability_is_high(self, client: TestClient) -> None:
        payload = {"series": _make_ar1(phi=0.9), "max_lag": 20}
        data = client.post("/triage", json=payload).json()
        assert data["forecastability_class"] == "high"

    def test_white_noise_forecastability_is_low(self, client: TestClient) -> None:
        payload = {"series": _make_white_noise(), "max_lag": 20}
        data = client.post("/triage", json=payload).json()
        assert data["forecastability_class"] == "low"

    def test_response_has_recommendation(self, client: TestClient) -> None:
        payload = {"series": _make_ar1(), "max_lag": 20}
        data = client.post("/triage", json=payload).json()
        assert data["recommendation"] is not None
        assert len(data["recommendation"]) > 0

    def test_response_has_readiness_status(self, client: TestClient) -> None:
        payload = {"series": _make_ar1(), "max_lag": 20}
        data = client.post("/triage", json=payload).json()
        assert data["readiness_status"] in {"clear", "warning", "blocked"}

    def test_default_parameters_are_applied(self, client: TestClient) -> None:
        """POST with only series should use all defaults without error."""
        payload = {"series": _make_ar1()}
        resp = client.post("/triage", json=payload)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /triage — blocked request
# ---------------------------------------------------------------------------


class TestTriageEndpointBlocked:
    def test_short_series_returns_blocked_true(self, client: TestClient) -> None:
        short = np.random.default_rng(0).standard_normal(20).tolist()
        payload = {"series": short, "max_lag": 40}
        data = client.post("/triage", json=payload).json()
        assert data["blocked"] is True

    def test_blocked_response_has_readiness_warnings(self, client: TestClient) -> None:
        short = np.random.default_rng(0).standard_normal(20).tolist()
        payload = {"series": short}
        data = client.post("/triage", json=payload).json()
        assert data["blocked"] is True
        assert isinstance(data["readiness_warnings"], list)
        assert len(data["readiness_warnings"]) > 0

    def test_blocked_response_null_forecastability_class(self, client: TestClient) -> None:
        short = np.random.default_rng(0).standard_normal(20).tolist()
        payload = {"series": short}
        data = client.post("/triage", json=payload).json()
        assert data["forecastability_class"] is None


# ---------------------------------------------------------------------------
# POST /triage — validation errors
# ---------------------------------------------------------------------------


class TestTriageEndpointValidation:
    def test_empty_series_returns_422(self, client: TestClient) -> None:
        resp = client.post("/triage", json={"series": []})
        assert resp.status_code == 422

    def test_missing_series_returns_422(self, client: TestClient) -> None:
        resp = client.post("/triage", json={"max_lag": 20})
        assert resp.status_code == 422

    def test_invalid_goal_returns_422(self, client: TestClient) -> None:
        payload = {"series": _make_ar1(), "goal": "bad_goal", "max_lag": 20}
        resp = client.post("/triage", json=payload)
        assert resp.status_code == 422

    def test_zero_surrogates_returns_422(self, client: TestClient) -> None:
        payload = {"series": _make_ar1(), "n_surrogates": 0}
        resp = client.post("/triage", json=payload)
        assert resp.status_code == 422

    def test_non_json_body_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/triage",
            content="not-json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# TriageHTTPRequest model validation (unit-level)
# ---------------------------------------------------------------------------


class TestTriageHTTPRequest:
    def test_valid_request_is_created(self) -> None:
        req = TriageHTTPRequest(series=[1.0, 2.0, 3.0])
        assert req.series == [1.0, 2.0, 3.0]

    def test_empty_series_raises(self) -> None:
        with pytest.raises(ValueError):
            TriageHTTPRequest(series=[])

    def test_zero_surrogates_raises(self) -> None:
        with pytest.raises(ValueError):
            TriageHTTPRequest(series=[1.0], n_surrogates=0)

    def test_default_goal_is_univariate(self) -> None:
        req = TriageHTTPRequest(series=[1.0])
        assert req.goal == "univariate"


# ---------------------------------------------------------------------------
# _build_triage_response unit-level — exercised without HTTP overhead
# ---------------------------------------------------------------------------


class TestBuildTriageResponse:
    def test_blocked_result_maps_correctly(self) -> None:
        from forecastability.triage.models import (
            ReadinessReport,
            ReadinessStatus,
            ReadinessWarning,
            TriageRequest,
            TriageResult,
        )

        readiness = ReadinessReport(
            status=ReadinessStatus.blocked,
            warnings=[ReadinessWarning(code="TOO_SHORT", message="too short")],
        )
        req = TriageRequest(series=np.zeros(5))
        result = TriageResult(request=req, readiness=readiness, blocked=True)

        resp = _build_triage_response(result)
        assert isinstance(resp, TriageHTTPResponse)
        assert resp.blocked is True
        assert resp.readiness_status == "blocked"
        assert len(resp.readiness_warnings) == 1
        assert resp.forecastability_class is None


# ---------------------------------------------------------------------------
# GET /triage/stream — SSE streaming contract (AGT-024)
# ---------------------------------------------------------------------------


class TestTriageStreamEndpoint:
    """AGT-024: SSE streaming endpoint contract tests."""

    @pytest.fixture()
    def streaming_client(self) -> Generator[TestClient, None, None]:
        """TestClient wired to the app with streaming enabled."""
        from unittest.mock import patch

        assert app is not None, "FastAPI app is None — fastapi not installed"
        with patch(
            "forecastability.adapters.api.InfraSettings",
            return_value=type(
                "_MockSettings", (), {"triage_enable_streaming": True}
            )(),
        ):
            yield TestClient(app)

    def test_stream_disabled_returns_503(self, client: TestClient) -> None:
        """When streaming is off (default), GET /triage/stream must return 503."""
        from unittest.mock import patch

        with patch(
            "forecastability.adapters.api.InfraSettings",
            return_value=type(
                "_MockSettings", (), {"triage_enable_streaming": False}
            )(),
        ):
            resp = client.get(
                "/triage/stream",
                params={"series": "[1.0, 2.0, 3.0]"},
            )
        assert resp.status_code == 503

    def test_stream_invalid_json_series_returns_422(
        self, streaming_client: TestClient
    ) -> None:
        """Malformed JSON in 'series' query param must return 422."""
        resp = streaming_client.get(
            "/triage/stream",
            params={"series": "not-valid-json"},
        )
        assert resp.status_code == 422

    def test_stream_ends_with_done_sentinel(
        self, streaming_client: TestClient
    ) -> None:
        """Stream must end with a 'done' event as the final SSE data line."""
        import json as _json

        series = _make_ar1(n=50)
        resp = streaming_client.get(
            "/triage/stream",
            params={"series": _json.dumps(series), "max_lag": 10, "n_surrogates": 10},
        )
        assert resp.status_code == 200
        lines = [
            line[len("data: "):].strip()
            for line in resp.text.splitlines()
            if line.startswith("data: ")
        ]
        assert len(lines) >= 1
        last_event = _json.loads(lines[-1])
        assert last_event["event_type"] == "done"

    def test_stream_events_have_event_type_field(
        self, streaming_client: TestClient
    ) -> None:
        """Every SSE data payload must have an 'event_type' key."""
        import json as _json

        series = _make_ar1(n=50)
        resp = streaming_client.get(
            "/triage/stream",
            params={"series": _json.dumps(series), "max_lag": 10, "n_surrogates": 10},
        )
        assert resp.status_code == 200
        data_lines = [
            line[len("data: "):].strip()
            for line in resp.text.splitlines()
            if line.startswith("data: ")
        ]
        for raw in data_lines:
            event = _json.loads(raw)
            assert "event_type" in event, f"Missing event_type in: {event}"
