"""Deterministic interpretation logic for AMI/pAMI outputs."""

from __future__ import annotations

import numpy as np

from forecastability.aggregation import summarize_canonical_result
from forecastability.types import CanonicalExampleResult, Diagnostics, InterpretationResult


def _forecastability_class(peak_ami: float) -> str:
    """Classify forecastability from the global AMI peak.

    The peak AMI value (maximum over all lags) is the most direct
    measure of whether *any* predictive structure exists.  For AR(1) the
    peak at lag 1 is 0.38 nats — clearly exploitable; for white noise it is
    ~0.02 nats — indistinguishable from estimation noise.

    Thresholds calibrated on canonical examples
    (WN ≈0.02, AR(1)≈0.38, Logistic/Sine/Hénon ≥1.1):
    """
    if peak_ami > 0.15:
        return "high"
    if peak_ami > 0.05:
        return "medium"
    return "low"


def _directness_class(directness_ratio: float, n_sig_ami: int, n_sig_pami: int) -> str:
    """Classify the directness of pAMI relative to AMI.

    Args:
        directness_ratio: auc_pami / auc_ami.
        n_sig_ami: Number of significant AMI lags.
        n_sig_pami: Number of significant pAMI lags.

    Returns:
        One of ``"arch_suspected"``, ``"high"``, ``"medium"``, or ``"low"``.

        ``"arch_suspected"`` is returned when ``directness_ratio > 1.0``.  pAMI
        cannot exceed AMI in expectation, so any ratio above 1.0 indicates that
        the linear-residual estimator has been amplified by ARCH-type volatility
        clustering or other violations of the conditioning assumptions.  Interpret
        with caution; see ``docs/theory/foundations.md`` for the full explanation.
    """
    if directness_ratio > 1.0:
        return "arch_suspected"
    if directness_ratio >= 0.5:
        return "high"
    if directness_ratio >= 0.2:
        return "medium"
    return "low"


def interpret_canonical_result(
    result: CanonicalExampleResult,
    *,
    best_smape: float | None = None,
) -> InterpretationResult:
    """Interpret AMI and pAMI behavior using Patterns A-E."""
    summary = summarize_canonical_result(result)

    # Global AMI peak — the single strongest lag-specific dependence signal.
    peak_ami = float(np.max(result.ami.values)) if result.ami.values.size > 0 else 0.0
    directness_ratio = summary.directness_ratio
    n_sig_ami = summary.n_sig_ami
    n_sig_pami = summary.n_sig_pami

    forecastability_class = _forecastability_class(peak_ami)
    directness_class = _directness_class(directness_ratio, n_sig_ami, n_sig_pami)

    # Primary lags: prefer surrogate-derived significant lags; fall back to top
    # pAMI peaks above the series mean when surrogates were skipped (skip_bands=True).
    if result.pami.significant_lags is not None and len(result.pami.significant_lags) > 0:
        primary_lags: list[int] = result.pami.significant_lags.tolist()[:5]
    else:
        pami_vals = result.pami.values
        threshold = float(np.mean(pami_vals)) if pami_vals.size > 0 else 0.0
        above = np.where(pami_vals > threshold)[0]  # 0-indexed → convert to 1-based below
        if len(above) > 0:
            top_idx = above[np.argsort(-pami_vals[above])][:5]
            primary_lags = sorted((top_idx + 1).tolist())
        else:
            primary_lags = []

    seasonal_period = int(result.metadata.get("seasonal_period", 0))
    has_seasonal_peak = bool(
        seasonal_period > 0
        and result.pami.values.size >= seasonal_period
        and result.pami.values[seasonal_period - 1] > np.percentile(result.pami.values, 75)
    )

    # Pattern A — high forecastability, direct memory
    if forecastability_class == "high" and directness_class in {"high", "arch_suspected"}:
        modeling_regime = "rich_models_with_structured_memory"
        narrative = (
            "Strong total dependence remains largely direct after conditioning. "
            "Richer structured models (deep AR, nonlinear, LSTM) are justified."
        )
    # Pattern B — high forecastability, mediated memory
    elif forecastability_class == "high":
        modeling_regime = "compact_structured_models"
        narrative = (
            "Strong total dependence, but much of the long-lag structure is mediated by "
            "shorter lags. Compact lag or state-space/seasonal designs are preferred."
        )
    # Pattern A+ — medium forecastability, high directness (e.g. chaotic attractors)
    elif forecastability_class == "medium" and directness_class in {"high", "arch_suspected"}:
        modeling_regime = "nonlinear_direct_models"
        narrative = (
            "Moderate total dependence with high directness — memory is direct and not "
            "mediated through intermediate lags. Short-lag AR or nonlinear models "
            "(NNAR, SETAR) capture this structure well."
        )
    # Pattern C — medium forecastability, seasonal peak in pAMI
    elif forecastability_class == "medium" and has_seasonal_peak:
        modeling_regime = "seasonal_or_compact_autoregression"
        narrative = (
            "Moderate dependence with a seasonal directness peak. "
            "Seasonal models or compact autoregression (SARIMA, ETS) are preferred."
        )
    # Pattern C′ — medium forecastability, low directness (e.g. periodic/sine series)
    elif forecastability_class == "medium" and directness_class == "low":
        modeling_regime = "seasonal_decomposition"
        narrative = (
            "Moderate total AMI but low direct pAMI: the predictive signal is predominantly "
            "periodic or seasonal and mediated through the cycle, not per-horizon direct. "
            "Seasonal decomposition (STL, SARIMA, Fourier) is the preferred approach."
        )
    # Pattern C″ — medium forecastability, medium directness
    elif forecastability_class == "medium":
        modeling_regime = "seasonal_or_regularized_models"
        narrative = (
            "Moderate dependence with selective direct lags. "
            "Regularized AR or seasonal models are typically sufficient."
        )
    # Pattern D′ — low forecastability, medium/high directness (e.g. AR(1))
    # Guard: if the first-lag pAMI is negligible, the high directness ratio is
    # unreliable (ratio of two near-zero quantities) and the series should be
    # treated as baseline rather than "compact AR".
    elif forecastability_class == "low" and directness_class in {
        "medium",
        "high",
        "arch_suspected",
    }:
        _short_lag_pami = float(np.max(result.pami.values[: min(3, result.pami.values.size)]))
        if _short_lag_pami < 0.05:
            modeling_regime = "baseline_or_robust_decision_design"
            narrative = (
                "Both total and direct dependence are near the noise floor — "
                "the high directness ratio reflects the instability of dividing two "
                "small quantities, not genuine structure. "
                "Baseline methods (mean, drift, naive) are likely sufficient."
            )
        else:
            modeling_regime = "compact_autoregression"
            narrative = (
                "Low total dependence, but the exploitable signal is direct and "
                "concentrated in short lags (lag 1–3). A compact AR(1)–AR(3) model "
                "captures it; deeper lags and richer architectures are unlikely to "
                "improve over naive."
            )
    # Pattern D — low forecastability, low directness (e.g. white noise)
    else:
        modeling_regime = "baseline_or_robust_decision_design"
        narrative = (
            "Both total and direct dependence are weak — near the noise floor. "
            "Baseline methods (mean, drift, naive) are likely sufficient."
        )

    exploitability_mismatch = False
    mismatch_reasons: list[str] = []
    if best_smape is not None and forecastability_class == "high" and best_smape > 25.0:
        exploitability_mismatch = True
        mismatch_reasons = [
            "model class cannot exploit dependence",
            "nonstationarity",
            "insufficient sample",
            "instability across origins",
        ]
        narrative = (
            f"{narrative} High dependence with high error indicates exploitability mismatch "
            f"({', '.join(mismatch_reasons)})."
        )  # Pattern E

    diagnostics = Diagnostics(
        peak_ami_first_5=peak_ami,
        directness_ratio=directness_ratio,
        n_sig_ami=n_sig_ami,
        n_sig_pami=n_sig_pami,
        exploitability_mismatch=int(exploitability_mismatch),
        best_smape=float(best_smape) if best_smape is not None else -1.0,
    )

    return InterpretationResult(
        forecastability_class=forecastability_class,
        directness_class=directness_class,
        primary_lags=primary_lags,
        modeling_regime=modeling_regime,
        narrative=narrative,
        diagnostics=diagnostics,
    )
