"""Triage orchestration use case (AGT-007)."""

from __future__ import annotations

from collections.abc import Callable

from forecastability.analyzer import (
    AnalyzeResult,
    ForecastabilityAnalyzer,
    ForecastabilityAnalyzerExog,
)
from forecastability.interpretation import interpret_canonical_result
from forecastability.triage.models import (
    MethodPlan,
    ReadinessReport,
    ReadinessStatus,
    TriageRequest,
    TriageResult,
)
from forecastability.triage.readiness import assess_readiness
from forecastability.triage.router import plan_method
from forecastability.types import CanonicalExampleResult, MetricCurve


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

    if route == "comparison":
        raise NotImplementedError("comparison route is not yet implemented (AGT-017)")

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


def run_triage(
    request: TriageRequest,
    *,
    readiness_gate: Callable[[TriageRequest], ReadinessReport] = assess_readiness,
    router: Callable[[TriageRequest, ReadinessReport], MethodPlan] = plan_method,
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

    Args:
        request: Inbound triage request containing the series, optional exog,
            and analysis parameters.
        readiness_gate: Callable that returns a :class:`ReadinessReport`.
            Defaults to :func:`assess_readiness`; injectable for testing.
        router: Callable that returns a :class:`MethodPlan` given a request and
            readiness report.  Defaults to :func:`plan_method`; injectable for
            testing.

    Returns:
        :class:`TriageResult` with all sub-results populated, or a short-circuit
        result with ``blocked=True`` when the readiness gate blocks processing.
    """
    readiness = readiness_gate(request)

    if readiness.status == ReadinessStatus.blocked:
        return TriageResult(
            request=request,
            readiness=readiness,
            blocked=True,
        )

    method_plan = router(request, readiness)
    analyze_result = _run_compute(request, method_plan)

    # Preserve the semantic contract: None = "surrogates not computed";
    # an empty array = "computed, none significant" (W1 — statistician review).
    # AnalyzeResult does not carry the raw band arrays, so lower_band/upper_band
    # in MetricCurve remain None even when surrogates were run (W2 — accepted
    # limitation of the current AnalyzeResult schema; does not affect interpretation).
    ami_sig = None if not method_plan.compute_surrogates else analyze_result.sig_raw_lags
    pami_sig = None if not method_plan.compute_surrogates else analyze_result.sig_partial_lags

    canonical = CanonicalExampleResult(
        series_name="triage",
        series=request.series,
        ami=MetricCurve(values=analyze_result.raw, significant_lags=ami_sig),
        pami=MetricCurve(values=analyze_result.partial, significant_lags=pami_sig),
    )

    interpretation = interpret_canonical_result(canonical)
    recommendation = analyze_result.recommendation

    return TriageResult(
        request=request,
        readiness=readiness,
        method_plan=method_plan,
        analyze_result=analyze_result,
        interpretation=interpretation,
        recommendation=recommendation,
        blocked=False,
    )
