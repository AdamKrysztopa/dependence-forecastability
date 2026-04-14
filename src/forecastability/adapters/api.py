"""FastAPI HTTP transport adapter for the forecastability triage pipeline (AGT-010).

Exposes three endpoints:

- ``POST /triage`` — run deterministic forecastability triage.
- ``GET /scorers`` — list registered dependence scorers.
- ``GET /health`` — liveness check.

The ``app`` object is ``None`` when FastAPI is not installed; all code guarded by
``if _FASTAPI_AVAILABLE``.

Usage (requires ``transport`` optional group)::

    uv sync --extra transport
    uvicorn forecastability.adapters.api:app --reload

Or with the settings-configured port::

    uvicorn forecastability.adapters.api:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import threading

import numpy as np
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import StreamingResponse

    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False

from forecastability.adapters.settings import InfraSettings
from forecastability.adapters.triage_presenter import present_triage_result
from forecastability.metrics.scorers import default_registry
from forecastability.triage.models import AnalysisGoal, TriageRequest, TriageResult
from forecastability.use_cases.run_triage import run_triage

# ---------------------------------------------------------------------------
# HTTP-layer Pydantic I/O models (JSON-serializable — no numpy)
# ---------------------------------------------------------------------------


class TriageHTTPRequest(BaseModel):
    """HTTP request body for ``POST /triage``.

    All numeric values use plain Python types for JSON compatibility; the
    adapter converts them to numpy arrays before calling ``run_triage()``.

    Attributes:
        series: Target time series as a list of floats.
        exog: Optional exogenous series (must match ``series`` length when given).
        goal: Analysis goal — ``"univariate"``, ``"exogenous"``, or ``"comparison"``.
        max_lag: Maximum lag to evaluate.
        n_surrogates: Number of surrogates for significance estimation.
        random_state: Seed for deterministic execution.
    """

    model_config = ConfigDict(frozen=True)

    series: list[float]
    exog: list[float] | None = None
    goal: str = "univariate"  # "univariate" | "exogenous"
    max_lag: int = 40
    n_surrogates: int = 99
    random_state: int = 42

    @field_validator("series")
    @classmethod
    def series_not_empty(cls, v: list[float]) -> list[float]:
        """Reject empty series at the HTTP boundary."""
        if len(v) == 0:
            raise ValueError("series must not be empty")
        return v

    @field_validator("n_surrogates")
    @classmethod
    def surrogates_min(cls, v: int) -> int:
        """Ensure n_surrogates meets statistical minimum for reliable p-values."""
        if v < 99:
            raise ValueError("n_surrogates must be >= 99 for reliable surrogate significance")
        return v


class ScorerSummary(BaseModel):
    """Summary of one registered scorer.

    Attributes:
        name: Short scorer identifier (e.g. ``"mi"``).
        family: Scorer family (``"nonlinear"``, ``"linear"``, etc.).
        description: One-line description.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    family: str
    description: str


class TriageHTTPResponse(BaseModel):
    """HTTP response body for ``POST /triage``.

    All fields are JSON-safe.  Numpy arrays are excluded; count summaries are
    returned instead.

    Attributes:
        blocked: ``True`` when the readiness gate blocked processing.
        readiness_status: Readiness gate status string (``"clear"``, ``"warning"``,
            or ``"blocked"``).
        readiness_warnings: List of ``{"code": ..., "message": ...}`` dicts.
        route: Compute route selected; ``None`` when blocked.
        compute_surrogates: Whether surrogates were computed; ``None`` when blocked.
        recommendation: Deterministic triage recommendation; ``None`` when blocked.
        forecastability_class: High-level forecastability class; ``None`` when blocked.
        directness_class: Directness class; ``None`` when blocked.
        modeling_regime: Recommended modeling regime; ``None`` when blocked.
        primary_lags: Key lags identified; empty list when blocked or none found.
        n_sig_raw_lags: Count of raw significant lags; ``None`` when blocked.
        n_sig_partial_lags: Count of partial significant lags; ``None`` when blocked.
    """

    model_config = ConfigDict(frozen=True)

    blocked: bool
    readiness_status: str
    readiness_warnings: list[dict[str, str]]
    route: str | None = None
    compute_surrogates: bool | None = None
    recommendation: str | None = None
    forecastability_class: str | None = None
    directness_class: str | None = None
    modeling_regime: str | None = None
    primary_lags: list[int] = []
    n_sig_raw_lags: int | None = None
    n_sig_partial_lags: int | None = None


# ---------------------------------------------------------------------------
# Response builder
# ---------------------------------------------------------------------------


def _build_triage_response(result: TriageResult) -> TriageHTTPResponse:
    """Map a ``TriageResult`` to the HTTP response model.

    Args:
        result: ``TriageResult`` from ``run_triage()``.

    Returns:
        :class:`TriageHTTPResponse` with all JSON-safe fields populated.
    """
    view = present_triage_result(result)

    return TriageHTTPResponse(
        blocked=view.blocked,
        readiness_status=view.readiness_status,
        readiness_warnings=view.readiness_warnings,
        route=view.route,
        compute_surrogates=view.compute_surrogates,
        recommendation=view.recommendation,
        forecastability_class=view.forecastability_class,
        directness_class=view.directness_class,
        modeling_regime=view.modeling_regime,
        primary_lags=view.primary_lags,
        n_sig_raw_lags=view.n_sig_raw_lags if not view.blocked else None,
        n_sig_partial_lags=view.n_sig_partial_lags if not view.blocked else None,
    )


# ---------------------------------------------------------------------------
# FastAPI application (only created when fastapi is installed)
# ---------------------------------------------------------------------------

if not _FASTAPI_AVAILABLE:
    app = None
else:
    app = FastAPI(
        title="Forecastability API",
        description=(
            "Deterministic AMI/pAMI forecastability triage over HTTP. "
            "All scientific computation is performed by the deterministic "
            "``run_triage()`` use case — no LLM involvement."
        ),
        version="0.1.0",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        """Liveness check.

        Returns:
            ``{"status": "ok"}`` when the service is running.
        """
        return {"status": "ok"}

    @app.get("/scorers", response_model=list[ScorerSummary])
    def list_scorers() -> list[ScorerSummary]:
        """List all registered dependence scorers.

        Returns:
            List of :class:`ScorerSummary` objects, one per registered scorer.
        """
        registry = default_registry()
        return [
            ScorerSummary(
                name=info.name,
                family=info.family,
                description=info.description,
            )
            for info in registry.list_scorers()
        ]

    @app.post("/triage", response_model=TriageHTTPResponse)
    def triage(body: TriageHTTPRequest) -> TriageHTTPResponse:
        """Run forecastability triage on the provided series.

        Executes the full deterministic pipeline: readiness gate → method
        routing → AMI/pAMI compute → interpretation → recommendation.

        Args:
            body: JSON request body conforming to :class:`TriageHTTPRequest`.

        Returns:
            :class:`TriageHTTPResponse` with analysis results.

        Raises:
            HTTPException(422): When ``goal`` is not a valid
                :class:`~forecastability.triage.models.AnalysisGoal`
                (accepted values: ``"univariate"``, ``"exogenous"``).
        """
        try:
            goal = AnalysisGoal(body.goal)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Invalid goal '{body.goal}'. Valid values: {[g.value for g in AnalysisGoal]}"
                ),
            ) from exc

        request = TriageRequest(
            series=np.asarray(body.series, dtype=np.float64),
            exog=(np.asarray(body.exog, dtype=np.float64) if body.exog is not None else None),
            goal=goal,
            max_lag=body.max_lag,
            n_surrogates=body.n_surrogates,
            random_state=body.random_state,
        )

        result = run_triage(request)
        return _build_triage_response(result)

    @app.get("/triage/stream")
    def triage_stream(
        series: str,
        goal: str = "univariate",
        max_lag: int = 40,
        n_surrogates: int = 99,
        random_state: int = 42,
    ) -> StreamingResponse:
        """Stream triage progress as Server-Sent Events (SSE).

        Runs the complete deterministic triage pipeline in a background thread
        and streams stage lifecycle events as SSE ``data:`` lines.  The stream
        ends with ``data: {"event_type": "done"}``.

        Only available when ``triage_enable_streaming=true`` in settings.

        Args:
            series: JSON-encoded list of floats, e.g. ``[0.1, -0.5, 0.3]``.
            goal: ``"univariate"`` or ``"exogenous"``.
            max_lag: Maximum lag to evaluate.
            n_surrogates: Number of surrogates for significance bands.
            random_state: Seed for determinism.

        Returns:
            ``text/event-stream`` response with SSE events.

        Raises:
            HTTPException(503): When streaming is disabled in settings.
            HTTPException(422): When ``series`` is not valid JSON.
        """
        import json as _json

        settings = InfraSettings()
        if not settings.triage_enable_streaming:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Streaming is disabled.  Set triage_enable_streaming=true "
                    "in .env or environment to enable."
                ),
            )

        try:
            parsed: list[float] = _json.loads(series)
        except _json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid JSON in 'series' query parameter: {exc}",
            ) from exc

        try:
            goal_enum = AnalysisGoal(goal)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid goal '{goal}'. Valid values: {[g.value for g in AnalysisGoal]}",
            ) from exc

        from forecastability.adapters.event_emitter import StreamingEventEmitter

        try:
            request = TriageRequest(
                series=np.asarray(parsed, dtype=np.float64),
                goal=goal_enum,
                max_lag=max_lag,
                n_surrogates=n_surrogates,
                random_state=random_state,
            )
        except (ValueError, ValidationError) as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid triage parameters: {exc}",
            ) from exc

        emitter = StreamingEventEmitter()

        def _run_in_background() -> None:
            try:
                run_triage(request, event_emitter=emitter)
            finally:
                emitter.close()

        thread = threading.Thread(target=_run_in_background, daemon=True)
        thread.start()

        return StreamingResponse(
            emitter.sse_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
