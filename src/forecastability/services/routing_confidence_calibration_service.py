"""Confidence calibration service for routing recommendations (plan v0.3.3 §2.5).

Computes the deterministic ``confidence_label`` from three signals:

1. The existing fingerprint penalty count ``p`` (from the 0.3.1 routing service).
2. The normalised threshold margin ``d_theta(f)`` (from §2.3).
3. The rule-stability score ``S(f, r; delta)`` (from §2.4).

The decision table is evaluated top-to-bottom; the first matching row wins.
The ``abstain`` label is new in 0.3.3 and is reserved for cases where the
routing service emits zero primary families.
"""

from __future__ import annotations

from forecastability.utils.types import RoutingConfidenceLabel, RoutingPolicyAuditConfig


def calibrate_confidence_label(
    *,
    fingerprint_penalty_count: int,
    threshold_margin: float,
    rule_stability: float,
    primary_families: list[str],
    config: RoutingPolicyAuditConfig = RoutingPolicyAuditConfig(),
) -> RoutingConfidenceLabel:
    """Return the calibrated confidence label per plan v0.3.3 §2.5.

    The decision table is evaluated top-to-bottom; the first matching row wins:

    | Condition                                                              | label    |
    |------------------------------------------------------------------------|----------|
    | primary_families is empty                                              | abstain  |
    | p == 0 and margin >= tau_margin and stability >= tau_stable_high       | high     |
    | p <= 1 and margin >= tau_margin_medium and stability >= tau_stable_med | medium   |
    | otherwise                                                              | low      |

    The ``abstain`` label is new in v0.3.3 and is only emitted when the routing
    recommendation carries no primary families.  The three original labels
    (``high``, ``medium``, ``low``) retain their 0.3.1 meaning.

    Args:
        fingerprint_penalty_count: Total penalty count from the 0.3.1 routing
            service (sum of threshold_margin_penalty, taxonomy_uncertainty_penalty,
            signal_conflict_penalty, and low_signal_quality_penalty).
        threshold_margin: Normalised threshold margin d_theta(f) per §2.3.
            Smaller values indicate the fingerprint sits closer to a routing
            boundary.
        rule_stability: Rule-stability score S(f,r;delta) per §2.4.
            Must be in [0.0, 1.0].
        primary_families: Primary family labels from the routing recommendation.
            An empty list triggers the ``abstain`` label regardless of other
            inputs.
        config: Audit scalars (tau_margin, tau_stable_high, tau_stable_medium …).
            Defaults to the v0.3.3 conservative defaults.

    Returns:
        One of ``Literal["high", "medium", "low", "abstain"]``.
    """
    if not primary_families:
        return "abstain"

    if (
        fingerprint_penalty_count == 0
        and threshold_margin >= config.tau_margin
        and rule_stability >= config.tau_stable_high
    ):
        return "high"

    if (
        fingerprint_penalty_count <= 1
        and threshold_margin >= config.tau_margin_medium
        and rule_stability >= config.tau_stable_medium
    ):
        return "medium"

    return "low"


__all__ = ["calibrate_confidence_label"]
