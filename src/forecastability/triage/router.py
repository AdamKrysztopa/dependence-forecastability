"""Method router: deterministic compute-path selection for triage requests."""

from __future__ import annotations

from forecastability.triage.models import (
    AnalysisGoal,
    MethodPlan,
    ReadinessReport,
    ReadinessStatus,
    TriageRequest,
)

_SIG_FEASIBILITY_CODE = "SIGNIFICANCE_FEASIBILITY"


def plan_method(request: TriageRequest, readiness: ReadinessReport) -> MethodPlan:
    """Select the compute path for a triage request.

    Raises:
        ValueError: If ``readiness.status`` is ``blocked``.

    Args:
        request: Inbound triage request.
        readiness: Readiness gate outcome for the same request.

    Returns:
        MethodPlan: Selected route with compute flags and rationale.
    """
    if readiness.status == ReadinessStatus.blocked:
        raise ValueError("Cannot plan method for blocked request")

    sig_infeasible = any(w.code == _SIG_FEASIBILITY_CODE for w in readiness.warnings)
    is_exog = request.goal == AnalysisGoal.exogenous or request.exog is not None
    is_comparison = request.goal == AnalysisGoal.comparison

    if is_exog:
        return MethodPlan(
            route="exogenous",
            compute_surrogates=not sig_infeasible,
            assumptions=[
                "Exogenous series is available and length-matched.",
                "Cross-MI captures directional predictive information.",
            ],
            rationale=(
                "Exogenous goal or a non-None exog array was detected. "
                "Computing raw and partial cross-MI curves. "
                + (
                    "Significance estimation skipped (series too short)."
                    if sig_infeasible
                    else "Surrogate significance bands will be computed."
                )
            ),
        )

    if is_comparison:
        return MethodPlan(
            route="comparison",
            compute_surrogates=not sig_infeasible,
            assumptions=[
                "A reference series is available for comparison.",
                "Both series share a common time index.",
            ],
            rationale=(
                "Comparison goal was requested. "
                "AMI and pAMI will be computed for both series side-by-side. "
                + (
                    "Significance estimation skipped (series too short)."
                    if sig_infeasible
                    else "Surrogate significance bands will be computed."
                )
            ),
        )

    if sig_infeasible:
        return MethodPlan(
            route="univariate_no_significance",
            compute_surrogates=False,
            assumptions=[
                "Series length is insufficient for stable surrogate bands.",
                "AMI and pAMI curves will be reported without significance thresholds.",
            ],
            rationale=(
                "Series length < 200 makes surrogate significance bands unreliable. "
                "Returning raw AMI / pAMI curves only."
            ),
        )

    return MethodPlan(
        route="univariate_with_significance",
        compute_surrogates=True,
        assumptions=[
            "Series is long enough for stable surrogate significance estimation.",
            "Phase-randomised FFT surrogates preserve the linear autocorrelation structure.",
        ],
        rationale=(
            "Standard univariate AMI / pAMI analysis with surrogate significance bands. "
            f"n_surrogates={request.n_surrogates}, random_state={request.random_state}."
        ),
    )
