"""Focused tests for the optional lightweight dashboard adapter."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from forecastability.adapters.dashboard import app


def _make_ar1(n: int = 120, *, phi: float = 0.8, seed: int = 123) -> list[float]:
    """Generate a deterministic AR(1)-like series for adapter tests."""
    rng = np.random.default_rng(seed)
    series = np.zeros(n)
    series[0] = rng.standard_normal()
    for idx in range(1, n):
        series[idx] = phi * series[idx - 1] + rng.standard_normal()
    return series.tolist()


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Provide a FastAPI test client for the dashboard adapter."""
    assert app is not None, "Dashboard app is None — transport extras are missing"
    return TestClient(app)


def test_dashboard_health_endpoint_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dashboard_home_serves_html(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Forecastability Dashboard" in response.text


def test_single_triage_endpoint_returns_response_payload(client: TestClient) -> None:
    payload = {
        "series": _make_ar1(),
        "goal": "univariate",
        "max_lag": 12,
        "n_surrogates": 99,
        "random_state": 42,
    }
    response = client.post("/api/triage", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "blocked" in data
    assert "readiness_status" in data
    assert "forecastability_class" in data


def test_single_triage_endpoint_rejects_invalid_goal(client: TestClient) -> None:
    payload = {
        "series": _make_ar1(),
        "goal": "invalid_goal",
    }
    response = client.post("/api/triage", json=payload)
    assert response.status_code == 422


def test_batch_triage_endpoint_returns_summary_table(client: TestClient) -> None:
    payload = {
        "items": [
            {
                "series_id": "alpha",
                "series": _make_ar1(seed=11),
            },
            {
                "series_id": "beta",
                "series": _make_ar1(seed=22),
            },
        ],
        "max_lag": 12,
        "n_surrogates": 99,
        "random_state": 42,
    }
    response = client.post("/api/triage-batch", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["n_items"] == 2
    assert isinstance(data["summary_table"], list)
    assert len(data["summary_table"]) == 2
