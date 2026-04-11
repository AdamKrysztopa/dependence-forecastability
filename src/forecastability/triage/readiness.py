"""Readiness gate for triage requests."""

from __future__ import annotations

import numpy as np

from forecastability.triage.models import (
    AnalysisGoal,
    ReadinessReport,
    ReadinessStatus,
    ReadinessWarning,
    TriageRequest,
)
from forecastability.validation import validate_time_series


def assess_readiness(request: TriageRequest) -> ReadinessReport:
    """Assess whether a triage request is ready for analysis.

    Runs a sequence of feasibility checks and returns a :class:`ReadinessReport`
    describing any problems found.  A ``blocked`` status means the analysis
    cannot proceed; ``warning`` means it can proceed with caveats; ``clear``
    means no issues were detected.

    Args:
        request: Inbound triage request to evaluate.

    Returns:
        ReadinessReport: Readiness gate outcome.
    """
    warnings: list[ReadinessWarning] = []
    block_codes: set[str] = set()

    # --- 1. Basic time-series validation ---
    try:
        validate_time_series(request.series, min_length=10)
    except ValueError as exc:
        return ReadinessReport(
            status=ReadinessStatus.blocked,
            warnings=[ReadinessWarning(code="VALIDATION_ERROR", message=str(exc))],
        )

    n = len(request.series)

    # --- 2. Lag feasibility ---
    # pAMI requires min_length = max_lag + min_pairs_pami + 1 = max_lag + 51.
    # Threshold 200 ≈ 4 × default max_lag (40), ensuring sufficient FFT resolution
    # for phase-randomised surrogates. Reduce only if max_lag is materially smaller.
    if request.max_lag >= n - 50:
        warnings.append(
            ReadinessWarning(
                code="LAG_FEASIBILITY",
                message=(
                    f"max_lag ({request.max_lag}) requires at least "
                    f"{request.max_lag + 51} observations for pAMI "
                    f"(min_pairs=50), but series has {n}. "
                    "Analysis is blocked."
                ),
            )
        )
        block_codes.add("LAG_FEASIBILITY")
    elif request.max_lag > n // 2:
        warnings.append(
            ReadinessWarning(
                code="LAG_FEASIBILITY",
                message=(
                    f"max_lag ({request.max_lag}) exceeds half the series "
                    f"length ({n // 2}). MI estimates at high lags are based "
                    "on progressively fewer pairs and will be unreliable."
                ),
            )
        )

    # --- 3. Significance feasibility ---
    # n=200 ≈ 4 × default max_lag (40); FFT-surrogate tests need sufficient
    # frequency resolution for reliable p-values at the 5% level.
    if n < 200:
        warnings.append(
            ReadinessWarning(
                code="SIGNIFICANCE_FEASIBILITY",
                message=(
                    f"Series length ({n}) < 200. Surrogate significance bands "
                    "may be unstable; interpret p-values with caution."
                ),
            )
        )

    # --- 4. Near-constant variance ---
    # Use std/IQR as scale-free measure — valid for zero-mean processes.
    # For a Gaussian, std/IQR ≈ 0.74; near-constant series approach 0.
    _std = float(np.std(request.series))
    _iqr = float(np.percentile(request.series, 75) - np.percentile(request.series, 25))
    if _std > 1e-6 and _iqr > 1e-10 and (_std / _iqr) < 0.10:
        warnings.append(
            ReadinessWarning(
                code="NEAR_CONSTANT",
                message=(
                    f"IQR-normalised std ({_std / _iqr:.4f}) < 0.10 — series has "
                    "very low dynamic range. kNN MI estimates will be unreliable."
                ),
            )
        )

    # --- 5. Exogenous goal requires exog series ---
    if request.goal == AnalysisGoal.exogenous and request.exog is None:
        warnings.append(
            ReadinessWarning(
                code="MISSING_EXOG",
                message=(
                    "goal='exogenous' was requested but no exogenous series "
                    "was provided (exog=None). Analysis is blocked."
                ),
            )
        )
        block_codes.add("MISSING_EXOG")

    # --- 6. Goal/exog mismatch ---
    if request.exog is not None and request.goal == AnalysisGoal.univariate:
        warnings.append(
            ReadinessWarning(
                code="GOAL_EXOG_MISMATCH",
                message=(
                    "goal='univariate' but a non-None exog was provided. "
                    "Routing will use the exogenous path. Set goal='exogenous' "
                    "explicitly to suppress this warning."
                ),
            )
        )

    # --- 7. Exogenous length mismatch ---
    if request.exog is not None and len(request.exog) != n:
        warnings.append(
            ReadinessWarning(
                code="EXOG_LENGTH_MISMATCH",
                message=(
                    f"Exogenous series length ({len(request.exog)}) does not "
                    f"match target series length ({n})."
                ),
            )
        )
        block_codes.add("EXOG_LENGTH_MISMATCH")

    # --- Determine overall status ---
    if block_codes:
        status = ReadinessStatus.blocked
    elif warnings:
        status = ReadinessStatus.warning
    else:
        status = ReadinessStatus.clear

    return ReadinessReport(status=status, warnings=warnings)
