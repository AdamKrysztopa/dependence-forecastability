"""Triage orchestration use case (AGT-007, AGT-013, AGT-014)."""

from __future__ import annotations

import time
import warnings
from collections.abc import Callable
from typing import Any

from forecastability.pipeline.analyzer import (
    AnalyzeResult,
    ForecastabilityAnalyzer,
    ForecastabilityAnalyzerExog,
)
from forecastability.ports import CheckpointPort, EventEmitterPort
from forecastability.reporting.interpretation import interpret_canonical_result
from forecastability.services.complexity_band_service import build_complexity_band
from forecastability.services.forecastability_profile_service import build_forecastability_profile
from forecastability.services.theoretical_limit_diagnostics_service import (
    build_theoretical_limit_diagnostics,
)
from forecastability.triage.complexity_band import ComplexityBandResult
from forecastability.triage.events import (
    TriageError,
    TriageStageCompleted,
    TriageStageStarted,
)
from forecastability.triage.forecastability_profile import ForecastabilityProfile
from forecastability.triage.models import (
    AnalysisGoal,
    MethodPlan,
    ReadinessReport,
    ReadinessStatus,
    TriageRequest,
    TriageResult,
)
from forecastability.triage.readiness import assess_readiness
from forecastability.triage.router import plan_method
from forecastability.triage.theoretical_limit_diagnostics import TheoreticalLimitDiagnostics
from forecastability.utils.types import CanonicalExampleResult, MetricCurve


def _run_compute(request: TriageRequest, method_plan: MethodPlan) -> AnalyzeResult:
    """Dispatch compute to the appropriate analyzer based on ``method_plan.route``.

    Args:
        request: Inbound triage request.
        method_plan: Selected compute path from the method router.

    Returns:
        :class:`AnalyzeResult` from the chosen analyzer.

    Raises:
        NotImplementedError: When route is ``"comparison"``.
        ValueError: When route is unrecognised.
    """
    route = method_plan.route

    if route not in {"univariate_with_significance", "univariate_no_significance", "exogenous"}:
        raise ValueError(f"Unknown route: {route}")

    if route == "exogenous":
        analyzer_exog = ForecastabilityAnalyzerExog(
            n_surrogates=request.n_surrogates,
            random_state=request.random_state,
        )
        return analyzer_exog.analyze(
            request.series,
            request.max_lag,
            exog=request.exog,
            compute_surrogates=method_plan.compute_surrogates,
        )

    compute_surrogates = route == "univariate_with_significance"
    analyzer = ForecastabilityAnalyzer(
        n_surrogates=request.n_surrogates,
        random_state=request.random_state,
    )
    return analyzer.analyze(
        request.series,
        request.max_lag,
        compute_surrogates=compute_surrogates,
    )


def _serialize_readiness(report: ReadinessReport) -> dict[str, Any]:
    return {
        "status": report.status.value,
        "warnings": [{"code": w.code, "message": w.message} for w in report.warnings],
    }


def _serialize_method_plan(plan: MethodPlan) -> dict[str, Any]:
    return {
        "route": plan.route,
        "compute_surrogates": plan.compute_surrogates,
        "assumptions": plan.assumptions,
        "rationale": plan.rationale,
    }


class _StageTimer:
    """Context manager that measures wall-clock time and emits lifecycle events.

    Args:
        stage: Stage name for event labels.
        emitter: :class:`~forecastability.ports.EventEmitterPort` or ``None``.
        timing: Mutable dict where ``{stage: duration_ms}`` is recorded, or
            ``None`` to skip timing collection entirely.
        summary_fn: Callable returning a one-line summary string after success.
    """

    def __init__(
        self,
        stage: str,
        emitter: EventEmitterPort | None,
        timing: dict[str, float] | None,
        summary_fn: Callable[[], str] = lambda: "",
    ) -> None:
        self._stage = stage
        self._emitter = emitter
        self._timing = timing
        self._summary_fn = summary_fn
        self._start: float = 0.0

    def __enter__(self) -> _StageTimer:
        self._start = time.perf_counter()
        if self._emitter is not None:
            self._emitter.emit(TriageStageStarted(stage=self._stage))
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        duration_ms = (time.perf_counter() - self._start) * 1_000
        if self._timing is not None:
            self._timing[self._stage] = duration_ms
        if self._emitter is None:
            return
        if exc_type is not None:
            self._emitter.emit(TriageError(stage=self._stage, error=str(exc_val)))
        else:
            self._emitter.emit(
                TriageStageCompleted(
                    stage=self._stage,
                    duration_ms=duration_ms,
                    result_summary=self._summary_fn(),
                )
            )


def run_triage(
    request: TriageRequest,
    *,
    readiness_gate: Callable[[TriageRequest], ReadinessReport] = assess_readiness,
    router: Callable[[TriageRequest, ReadinessReport], MethodPlan] = plan_method,
    event_emitter: EventEmitterPort | None = None,
    checkpoint: CheckpointPort | None = None,
    checkpoint_key: str = "default",
) -> TriageResult:
    """Orchestrate the full triage pipeline for a forecastability request.

    Pipeline steps:

    1. **Readiness gate** — validates series length, lag feasibility, and
       significance feasibility.  Returns immediately with ``blocked=True`` when
       the gate reports :attr:`ReadinessStatus.blocked`.
    2. **Method routing** — selects the compute path and surrogate settings.
    3. **Compute** — runs the appropriate analyzer (univariate or exogenous).
    4. **Interpretation** — maps MI curves to a forecastability class and
       modeling regime.

    .. note:: Checkpoint semantics (AGT-023)

        Checkpoints implement **orchestration-state replay**, not full-artifact
        resume.  Each stage saves the orchestration state (readiness report and
        method plan as JSON-serialisable dicts) but *not* the full numpy arrays
        from the compute stage.  Resuming will re-execute compute from scratch;
        only readiness and routing stages can be skipped.  This is by design:
        numpy arrays are large and not JSON-safe.  If you need full-artifact
        resume, persist the ``AnalyzeResult`` separately and reconstruct it
        before calling ``run_triage()``.

    Args:
        request: Inbound triage request containing the series, optional exog,
            and analysis parameters.
        readiness_gate: Callable that returns a :class:`ReadinessReport`.
            Defaults to :func:`assess_readiness`; injectable for testing.
        router: Callable that returns a :class:`MethodPlan` given a request and
            readiness report.  Defaults to :func:`plan_method`; injectable for
            testing.
        event_emitter: Optional :class:`~forecastability.ports.EventEmitterPort`
            that receives lifecycle events and timing data (AGT-013).  Accepts
            any object with an ``emit`` method; ``None`` disables event emission.
        checkpoint: Optional :class:`~forecastability.ports.CheckpointPort` for
            durable execution (AGT-014).  When provided the function saves
            partial state after each stage and resumes from the last committed
            stage if ``checkpoint_key`` already has saved state.
        checkpoint_key: Unique identifier for the current run's checkpoint.
            Defaults to ``"default"``; supply a stable, per-run ID (e.g. a UUID)
            to avoid collisions when multiple runs share the same checkpoint
            store.  Using ``"default"`` in a multi-run context is a common
            mistake — a :class:`UserWarning` is emitted when ``checkpoint`` is
            not ``None`` and the key is ``"default"``.

    Returns:
        :class:`TriageResult` with all sub-results populated, or a short-circuit
        result with ``blocked=True`` when the readiness gate blocks processing.
        The ``timing`` field contains per-stage wall-clock durations in
        milliseconds when ``event_emitter`` is provided.
    """
    timing: dict[str, float] | None = {} if event_emitter is not None else None

    # AGT-023: warn when caller uses the default checkpoint key in a multi-run
    # context, as it risks overwriting another run's partial state.
    if checkpoint is not None and checkpoint_key == "default":
        warnings.warn(
            "run_triage(): checkpoint_key='default' is shared across runs.  "
            "Supply a unique per-run key (e.g. a UUID) to avoid checkpoint "
            "collisions.  Checkpoints implement replay-only semantics: only "
            "readiness and routing stages can be skipped; compute always re-runs.",
            UserWarning,
            stacklevel=2,
        )

    # --- resume from checkpoint if available ---
    resumed_stage: str | None = None

    if checkpoint is not None:
        ckpt = checkpoint.load_checkpoint(checkpoint_key)
        if ckpt is not None:
            resumed_stage = ckpt.get("stage")

    # ------------------------------------------------------------------ #
    # Stage 1: readiness                                                  #
    # ------------------------------------------------------------------ #
    readiness: ReadinessReport

    if resumed_stage in {"routing", "compute", "interpretation"}:
        assert checkpoint is not None
        ckpt = checkpoint.load_checkpoint(checkpoint_key)
        assert ckpt is not None
        data = ckpt["data"]
        from forecastability.triage.models import ReadinessWarning  # local import avoids cycle

        readiness = ReadinessReport(
            status=data["readiness"]["status"],
            warnings=[
                ReadinessWarning(code=w["code"], message=w["message"])
                for w in data["readiness"]["warnings"]
            ],
        )
    else:
        with _StageTimer(
            "readiness",
            event_emitter,
            timing,
            summary_fn=lambda: (
                f"status={readiness.status.value}" if "readiness" in dir() else "evaluating"
            ),
        ):
            readiness = readiness_gate(request)

        if checkpoint is not None:
            checkpoint.save_checkpoint(
                checkpoint_key,
                "readiness",
                {"readiness": _serialize_readiness(readiness)},
            )

    if readiness.status == ReadinessStatus.blocked:
        return TriageResult(
            request=request,
            readiness=readiness,
            blocked=True,
            timing=timing if timing else None,
        )

    # ------------------------------------------------------------------ #
    # Stage 2: routing                                                    #
    # ------------------------------------------------------------------ #
    method_plan: MethodPlan

    if resumed_stage in {"compute", "interpretation"}:
        assert checkpoint is not None
        ckpt = checkpoint.load_checkpoint(checkpoint_key)
        assert ckpt is not None
        data = ckpt["data"]
        method_plan = MethodPlan(**data["method_plan"])
    else:
        with _StageTimer(
            "routing",
            event_emitter,
            timing,
            summary_fn=lambda: f"route={method_plan.route}",
        ):
            method_plan = router(request, readiness)

        if checkpoint is not None:
            checkpoint.save_checkpoint(
                checkpoint_key,
                "routing",
                {
                    "readiness": _serialize_readiness(readiness),
                    "method_plan": _serialize_method_plan(method_plan),
                },
            )

    # ------------------------------------------------------------------ #
    # Stage 3: compute                                                    #
    # ------------------------------------------------------------------ #
    analyze_result: AnalyzeResult

    with _StageTimer(
        "compute",
        event_emitter,
        timing,
        summary_fn=lambda: (
            f"method={analyze_result.method} raw_mean={analyze_result.raw.mean():.4f}"
        ),
    ):
        analyze_result = _run_compute(request, method_plan)

    if checkpoint is not None:
        checkpoint.save_checkpoint(
            checkpoint_key,
            "compute",
            {
                "readiness": _serialize_readiness(readiness),
                "method_plan": _serialize_method_plan(method_plan),
                # numpy arrays are not JSON-serialisable; store summary only
                "compute_summary": {
                    "method": analyze_result.method,
                    "recommendation": analyze_result.recommendation,
                    "n_raw_lags": int(analyze_result.raw.size),
                },
            },
        )

    # ------------------------------------------------------------------ #
    # Stage 4: interpretation                                             #
    # ------------------------------------------------------------------ #
    # Preserve the semantic contract: None = "surrogates not computed";
    # an empty array = "computed, none significant" (W1 — statistician review).
    ami_sig = None if not method_plan.compute_surrogates else analyze_result.sig_raw_lags
    pami_sig = None if not method_plan.compute_surrogates else analyze_result.sig_partial_lags

    canonical = CanonicalExampleResult(
        series_name="triage",
        series=request.series,
        ami=MetricCurve(values=analyze_result.raw, significant_lags=ami_sig),
        pami=MetricCurve(values=analyze_result.partial, significant_lags=pami_sig),
    )

    with _StageTimer(
        "interpretation",
        event_emitter,
        timing,
        summary_fn=lambda: f"class={interpretation.forecastability_class}",
    ):
        is_exogenous = request.goal == AnalysisGoal.exogenous or request.exog is not None
        interpretation = interpret_canonical_result(
            canonical,
            is_exogenous=is_exogenous,
        )

    recommendation = analyze_result.recommendation

    if checkpoint is not None:
        checkpoint.save_checkpoint(
            checkpoint_key,
            "interpretation",
            {
                "readiness": _serialize_readiness(readiness),
                "method_plan": _serialize_method_plan(method_plan),
                "compute_summary": {
                    "method": analyze_result.method,
                    "recommendation": analyze_result.recommendation,
                    "n_raw_lags": int(analyze_result.raw.size),
                },
                "interpretation_summary": {
                    "forecastability_class": interpretation.forecastability_class,
                    "directness_class": interpretation.directness_class,
                },
            },
        )

    # ------------------------------------------------------------------ #
    # Stage 5: forecastability profile                                    #
    # ------------------------------------------------------------------ #
    forecastability_profile: ForecastabilityProfile | None = None
    if analyze_result is not None:
        # sig_raw_lags in AnalyzeResult are 1-based lag numbers;
        # build_forecastability_profile expects 0-based array indices.
        sig_lags_0based = (
            (analyze_result.sig_raw_lags - 1) if method_plan.compute_surrogates else None
        )
        forecastability_profile = build_forecastability_profile(
            analyze_result.raw,
            sig_raw_lags=sig_lags_0based,
        )

    # ------------------------------------------------------------------ #
    # Stage 6: information-theoretic limit diagnostics                    #
    # ------------------------------------------------------------------ #
    # Guard: ceiling semantics are only valid when the metric IS mutual
    # information.  If routing is extended to non-MI methods in future,
    # interpreting their raw curves as an MI ceiling would be wrong.
    theoretical_limit_diagnostics: TheoreticalLimitDiagnostics | None = None
    if analyze_result is not None and analyze_result.method == "mi":
        theoretical_limit_diagnostics = build_theoretical_limit_diagnostics(
            analyze_result.raw,
        )

    # ------------------------------------------------------------------ #
    # Stage 7: entropy-based complexity triage (F6)                      #
    # ------------------------------------------------------------------ #
    complexity_band: ComplexityBandResult | None = None
    complexity_band = build_complexity_band(request.series)

    # ------------------------------------------------------------------ #
    # Stage 8: largest Lyapunov exponent (F5, experimental)              #
    # ------------------------------------------------------------------ #
    from forecastability.triage.lyapunov import LargestLyapunovExponentResult

    largest_lyapunov_exponent: LargestLyapunovExponentResult | None = None
    try:
        from forecastability.services.lyapunov_service import build_largest_lyapunov_exponent

        largest_lyapunov_exponent = build_largest_lyapunov_exponent(request.series)
    except Exception:
        pass  # experimental — never crashes triage

    return TriageResult(
        request=request,
        readiness=readiness,
        method_plan=method_plan,
        analyze_result=analyze_result,
        interpretation=interpretation,
        recommendation=recommendation,
        blocked=False,
        timing=timing if timing else None,
        forecastability_profile=forecastability_profile,
        theoretical_limit_diagnostics=theoretical_limit_diagnostics,
        complexity_band=complexity_band,
        largest_lyapunov_exponent=largest_lyapunov_exponent,
    )
