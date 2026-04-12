"""Optional FastAPI dashboard adapter for forecastability triage.

Provides a lightweight browser UI with two adapter endpoints:

- ``POST /api/triage`` for single-series deterministic triage.
- ``POST /api/triage-batch`` for deterministic batch triage.

Usage (requires ``transport`` optional group)::

    uv sync --extra transport
    forecastability-dashboard

Or run directly with uvicorn::

    uv run uvicorn forecastability.adapters.dashboard:app --host 127.0.0.1 --port 8765
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

import numpy as np
from pydantic import BaseModel, ConfigDict

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse

    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False

from forecastability.adapters.api import (
    TriageHTTPRequest,
    TriageHTTPResponse,
    _build_triage_response,
)
from forecastability.triage.batch_models import (
    BatchFailureRow,
    BatchSummaryRow,
    BatchTriageItemResult,
    BatchTriageRequest,
    BatchTriageResponse,
)
from forecastability.triage.models import AnalysisGoal, TriageRequest
from forecastability.triage.run_batch_triage import run_batch_triage
from forecastability.triage.run_triage import run_triage

_DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Forecastability Dashboard</title>
  <style>
    :root {
      --bg: #f4f7fb;
      --panel: #ffffff;
      --ink: #123048;
      --ink-soft: #4f6677;
      --accent: #00727f;
      --accent-soft: #d9f2f5;
      --border: #d9e2ea;
      --error: #a1292a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Avenir Next", "Avenir", "Helvetica Neue", Helvetica, sans-serif;
      color: var(--ink);
      background: radial-gradient(circle at top left, #ffffff 0%, var(--bg) 65%);
    }
    .wrap {
      max-width: 1120px;
      margin: 0 auto;
      padding: 24px 18px 40px;
    }
    .hero {
      margin-bottom: 18px;
      padding: 16px 18px;
      background: linear-gradient(130deg, #ffffff 0%, #e7f6f8 100%);
      border: 1px solid var(--border);
      border-radius: 12px;
    }
    h1 {
      margin: 0 0 8px;
      font-size: clamp(1.6rem, 2vw + 1rem, 2.25rem);
      letter-spacing: 0.02em;
    }
    p {
      margin: 0;
      color: var(--ink-soft);
      line-height: 1.5;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 14px;
      margin-top: 14px;
    }
    .card {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px;
    }
    h2 {
      margin: 0 0 10px;
      font-size: 1.1rem;
    }
    .controls {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 10px;
      margin: 10px 0;
    }
    label {
      display: grid;
      gap: 4px;
      font-size: 0.88rem;
      color: var(--ink-soft);
    }
    input,
    textarea {
      width: 100%;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px;
      font: inherit;
      color: var(--ink);
      background: #ffffff;
    }
    textarea {
      min-height: 150px;
      resize: vertical;
      font-family: "JetBrains Mono", "SFMono-Regular", Menlo, Consolas, monospace;
      font-size: 0.84rem;
    }
    button {
      margin-top: 4px;
      padding: 9px 14px;
      border: 0;
      border-radius: 999px;
      background: var(--accent);
      color: #ffffff;
      font: inherit;
      cursor: pointer;
    }
    button:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
    .result {
      margin-top: 10px;
      padding: 10px;
      border-radius: 8px;
      background: #0d2334;
      color: #e9f1f7;
      min-height: 220px;
      overflow: auto;
      font-family: "JetBrains Mono", "SFMono-Regular", Menlo, Consolas, monospace;
      font-size: 0.82rem;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .error {
      margin-top: 10px;
      padding: 8px 10px;
      border-radius: 8px;
      background: #fdeff0;
      color: var(--error);
      border: 1px solid #f5cfd2;
      display: none;
    }
    .footer {
      margin-top: 16px;
      font-size: 0.84rem;
      color: var(--ink-soft);
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>Forecastability Dashboard</h1>
      <p>
        Lightweight adapter over deterministic triage use cases.
        This UI does not implement domain logic.
      </p>
    </section>

    <div class="grid">
      <section class="card">
        <h2>Single-Series Triage</h2>
        <form id="single-form">
          <label>
            Series JSON
            <textarea id="single-series">[
  0.12, 0.18, 0.11, 0.21, 0.27,
  0.17, 0.24, 0.31, 0.29, 0.34
]</textarea>
          </label>
          <div class="controls">
            <label>
              Goal
              <input id="single-goal" type="text" value="univariate" />
            </label>
            <label>
              Max lag
              <input id="single-max-lag" type="number" value="10" min="1" />
            </label>
            <label>
              Surrogates
              <input id="single-surrogates" type="number" value="99" min="1" />
            </label>
            <label>
              Random state
              <input id="single-seed" type="number" value="42" />
            </label>
          </div>
          <button id="single-submit" type="submit">Run single triage</button>
        </form>
        <div class="error" id="single-error"></div>
        <pre class="result" id="single-result">Awaiting request...</pre>
      </section>

      <section class="card">
        <h2>Batch Triage</h2>
        <form id="batch-form">
          <label>
            Batch payload JSON
            <textarea id="batch-payload">{
  "items": [
    {
      "series_id": "demo_a",
      "series": [0.2, 0.25, 0.3, 0.28, 0.33, 0.36, 0.39, 0.41, 0.45, 0.48]
    },
    {
      "series_id": "demo_b",
      "series": [0.6, 0.2, -0.4, 0.1, -0.5, 0.3, -0.2, 0.4, -0.1, 0.2]
    }
  ],
  "max_lag": 10,
  "n_surrogates": 99,
  "random_state": 42
}</textarea>
          </label>
          <button id="batch-submit" type="submit">Run batch triage</button>
        </form>
        <div class="error" id="batch-error"></div>
        <pre class="result" id="batch-result">Awaiting request...</pre>
      </section>
    </div>

    <p class="footer">Health endpoint: /health</p>
  </div>

  <script>
    function setResult(id, value) {
      document.getElementById(id).textContent = JSON.stringify(value, null, 2);
    }

    function showError(id, message) {
      const panel = document.getElementById(id);
      panel.style.display = "block";
      panel.textContent = message;
    }

    function clearError(id) {
      const panel = document.getElementById(id);
      panel.style.display = "none";
      panel.textContent = "";
    }

    async function postJson(url, body) {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(JSON.stringify(payload));
      }
      return payload;
    }

    document.getElementById("single-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      clearError("single-error");

      try {
        const series = JSON.parse(document.getElementById("single-series").value);
        const payload = {
          series: series,
          goal: document.getElementById("single-goal").value,
          max_lag: Number(document.getElementById("single-max-lag").value),
          n_surrogates: Number(document.getElementById("single-surrogates").value),
          random_state: Number(document.getElementById("single-seed").value),
        };
        const result = await postJson("/api/triage", payload);
        setResult("single-result", result);
      } catch (error) {
        showError("single-error", String(error));
      }
    });

    document.getElementById("batch-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      clearError("batch-error");

      try {
        const payload = JSON.parse(document.getElementById("batch-payload").value);
        const result = await postJson("/api/triage-batch", payload);
        setResult("batch-result", result);
      } catch (error) {
        showError("batch-error", String(error));
      }
    });
  </script>
</body>
</html>
"""


class BatchDashboardResponse(BaseModel):
    """JSON-safe response model for dashboard batch triage requests.

    Attributes:
        n_items: Number of requested series items.
        n_failed: Number of items that failed with recoverable errors.
        items: Ranked per-series outcomes.
        summary_table: Flat summary rows for display/export.
        failure_table: Failed-series rows with code and message.
    """

    model_config = ConfigDict(frozen=True)

    n_items: int
    n_failed: int
    items: list[BatchTriageItemResult]
    summary_table: list[BatchSummaryRow]
    failure_table: list[BatchFailureRow]


def _to_triage_request(body: TriageHTTPRequest) -> TriageRequest:
    """Build a deterministic ``TriageRequest`` from dashboard HTTP payload.

    Args:
        body: Parsed HTTP request payload from the dashboard adapter.

    Returns:
        Validated triage request for the deterministic use case.

    Raises:
        ValueError: If the goal string does not map to ``AnalysisGoal``.
    """
    return TriageRequest(
        series=np.asarray(body.series, dtype=np.float64),
        exog=np.asarray(body.exog, dtype=np.float64) if body.exog is not None else None,
        goal=AnalysisGoal(body.goal),
        max_lag=body.max_lag,
        n_surrogates=body.n_surrogates,
        random_state=body.random_state,
    )


def _build_batch_response(result: BatchTriageResponse) -> BatchDashboardResponse:
    """Convert batch use-case output to a dashboard response payload."""
    return BatchDashboardResponse(
        n_items=len(result.items),
        n_failed=len(result.failure_table),
        items=result.items,
        summary_table=result.summary_table,
        failure_table=result.failure_table,
    )


def _build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for launching the optional dashboard server."""
    parser = argparse.ArgumentParser(
        prog="forecastability-dashboard",
        description="Run the lightweight forecastability dashboard adapter.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Dashboard host (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8765, help="Dashboard port (default: 8765).")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for local development.",
    )
    return parser


if not _FASTAPI_AVAILABLE:
    app = None
else:
    app = FastAPI(
        title="Forecastability Dashboard",
        description=(
            "Minimal dashboard adapter over deterministic triage use cases. "
            "No domain logic is implemented in this transport layer."
        ),
        version="0.1.0",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        """Return adapter liveness information."""
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def dashboard_home() -> HTMLResponse:
        """Serve the lightweight dashboard UI."""
        return HTMLResponse(content=_DASHBOARD_HTML)

    @app.post("/api/triage", response_model=TriageHTTPResponse)
    def triage_endpoint(body: TriageHTTPRequest) -> TriageHTTPResponse:
        """Run deterministic single-series triage from dashboard requests."""
        try:
            request = _to_triage_request(body)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Invalid goal '{body.goal}'. "
                    f"Valid values: {[goal.value for goal in AnalysisGoal]}"
                ),
            ) from exc

        return _build_triage_response(run_triage(request))

    @app.post("/api/triage-batch", response_model=BatchDashboardResponse)
    def triage_batch_endpoint(body: BatchTriageRequest) -> BatchDashboardResponse:
        """Run deterministic batch triage from dashboard requests."""
        return _build_batch_response(run_batch_triage(body))


def main(argv: Sequence[str] | None = None) -> None:
    """Run the dashboard server via uvicorn.

    Args:
        argv: Optional command arguments, mainly for testing.

    Raises:
        SystemExit: If required transport dependencies are missing.
    """
    if not _FASTAPI_AVAILABLE:
        raise SystemExit(
            "FastAPI is not installed. Run 'uv sync --extra transport' before launching "
            "the dashboard."
        )

    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "uvicorn is not installed. Run 'uv sync --extra transport' before "
            "launching the dashboard."
        ) from exc

    args = _build_parser().parse_args(argv)
    uvicorn.run(
        "forecastability.adapters.dashboard:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
