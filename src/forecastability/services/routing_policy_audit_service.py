"""Policy audit service for routing recommendation validation (plan v0.3.3 §2.2–2.4).

This module implements the four-outcome predicate (pass / fail / abstain / downgrade),
the normalised threshold-distance metric, and the deterministic rule-stability score
used by the v0.3.3 routing validation surface.

The module exposes three public functions:
- ``compute_rule_stability`` — corner-plus-center grid stability score (§2.4)
- ``build_routing_threshold_vector`` — helper to derive threshold_vector from the policy
- ``audit_routing_case`` — single-case four-outcome predicate (§2.2)
"""

from __future__ import annotations

import itertools
from collections.abc import Callable
from typing import TYPE_CHECKING

from forecastability.services.routing_policy_service import (
    RoutingPolicyConfig,
    route_fingerprint,
)
from forecastability.utils.types import (
    ForecastabilityFingerprint,
    RoutingPolicyAuditConfig,
    RoutingRecommendation,
    RoutingValidationCase,
    RoutingValidationOutcome,
    RoutingValidationSourceKind,
)

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Internal coordinate-to-attribute mapping
# ---------------------------------------------------------------------------

# Maps threshold_vector key → ForecastabilityFingerprint attribute name.
# Keys with a common fingerprint attribute (e.g. two thresholds on information_mass)
# share the same attribute value but have distinct threshold_vector keys so the
# dict can hold them without collisions.
_THRESHOLD_TO_FINGERPRINT_ATTR: dict[str, str] = {
    "information_mass_low_max": "information_mass",
    "information_mass_high_min": "information_mass",
    "nonlinear_share": "nonlinear_share",
    "directness_ratio": "directness_ratio",
}

# Fingerprint coordinate names perturbed during the stability analysis.
# These are the continuous scalar fields that drive the routing arm selection.
# Categorical fields (information_structure) are held fixed during perturbation.
_STABILITY_COORDINATES = ("information_mass", "nonlinear_share", "directness_ratio")


def _get_fingerprint_value(
    fingerprint: ForecastabilityFingerprint,
    threshold_key: str,
) -> float:
    """Extract the fingerprint coordinate value for a named threshold key.

    Resolves via ``_THRESHOLD_TO_FINGERPRINT_ATTR`` first; falls back to
    direct attribute lookup on the fingerprint; raises ``ValueError`` if
    neither resolves.

    Args:
        fingerprint: Forecastability fingerprint instance.
        threshold_key: Key from the threshold_vector dict.

    Returns:
        The corresponding scalar float value from the fingerprint.

    Raises:
        ValueError: When the threshold_key cannot be resolved to a fingerprint
            attribute.
    """
    attr = _THRESHOLD_TO_FINGERPRINT_ATTR.get(threshold_key)
    if attr is not None:
        value = getattr(fingerprint, attr, None)
    else:
        value = getattr(fingerprint, threshold_key, None)
    if value is None:
        raise ValueError(
            f"Cannot resolve threshold key '{threshold_key}' to a fingerprint attribute. "
            f"Known keys: {sorted(_THRESHOLD_TO_FINGERPRINT_ATTR)}"
        )
    return float(value)


def _compute_threshold_margin(
    fingerprint: ForecastabilityFingerprint,
    threshold_vector: dict[str, float],
    *,
    config: RoutingPolicyAuditConfig,
) -> float:
    """Compute the normalised threshold margin d_theta(f) per plan §2.3.

    For each (threshold_key, threshold_value) pair in threshold_vector, computes
    the absolute normalised signed difference:
        |f_i - theta_i| / s_i
    where s_i = config.coordinate_scales.get(threshold_key, 1.0).

    Returns the minimum over all active thresholds.

    Args:
        fingerprint: Forecastability fingerprint instance.
        threshold_vector: Mapping from threshold name to threshold value.
        config: Audit configuration providing per-coordinate scales.

    Returns:
        Minimum normalised absolute signed threshold distance. Returns ``inf``
        if threshold_vector is empty.
    """
    if not threshold_vector:
        return float("inf")
    distances: list[float] = []
    for key, theta in threshold_vector.items():
        scale = config.coordinate_scales.get(key, 1.0)
        f_i = _get_fingerprint_value(fingerprint, key)
        distances.append(abs(f_i - theta) / scale)
    return min(distances)


def _extract_stability_coordinates(
    fingerprint: ForecastabilityFingerprint,
) -> dict[str, float]:
    """Extract the scalar routing coordinates from a fingerprint for stability analysis.

    Returns only the continuous scalar fields used in routing arm selection.
    Categorical fields (information_structure) are not included because they are
    not perturbed in the L-infinity stability grid.

    Args:
        fingerprint: Forecastability fingerprint instance.

    Returns:
        Dict mapping coordinate name to value, sorted alphabetically to guarantee
        deterministic grid construction.
    """
    coords: dict[str, float] = {
        "information_mass": fingerprint.information_mass,
        "nonlinear_share": fingerprint.nonlinear_share,
    }
    if fingerprint.directness_ratio is not None:
        coords["directness_ratio"] = fingerprint.directness_ratio
    return dict(sorted(coords.items()))


def _make_routing_callable(
    base_fingerprint: ForecastabilityFingerprint,
    *,
    routing_config: RoutingPolicyConfig | None = None,
) -> Callable[[dict[str, float]], list[str]]:
    """Build a routing callable that applies coordinate overrides to a base fingerprint.

    The returned callable takes a modified coordinate dict, creates a new
    ForecastabilityFingerprint with the overridden scalar fields, and returns
    the primary family labels emitted by ``route_fingerprint``.  All non-scalar
    fields (information_structure, informative_horizons, signal_to_noise,
    information_horizon, metadata) are preserved from the base fingerprint.

    Args:
        base_fingerprint: The original fingerprint to use as the template.
        routing_config: Optional routing policy config; defaults to
            ``RoutingPolicyConfig()``.

    Returns:
        Callable mapping coordinate dict → list of primary family label strings.
    """
    resolved_config = routing_config if routing_config is not None else RoutingPolicyConfig()

    def _callable(coords: dict[str, float]) -> list[str]:
        modified = base_fingerprint.model_copy(update=coords)
        recommendation = route_fingerprint(modified, config=resolved_config)
        return [str(f) for f in recommendation.primary_families]

    return _callable


def compute_rule_stability(
    fingerprint_coordinates: dict[str, float],
    *,
    routing_callable: Callable[[dict[str, float]], list[str]],
    delta: float,
) -> float:
    """Deterministic rule-stability score per plan v0.3.3 §2.4.

    Discretises the L-infinity ball of radius ``delta`` around the fingerprint
    coordinates onto the **corner-plus-center** grid (size 2^K + 1), evaluates
    ``routing_callable`` at each grid point, and returns the fraction of grid
    points whose primary family set matches the centre's primary family set.

    Keys in ``fingerprint_coordinates`` are sorted before constructing the grid
    so the score is invariant to upstream dict insertion order.

    Args:
        fingerprint_coordinates: Mapping from fingerprint attribute name to value.
            Must be non-empty.
        routing_callable: Function that takes a coordinate dict and returns the
            list of primary family label strings. Injected to keep the subroutine
            testable in isolation; the production default at the audit-service
            boundary binds it to ``route_fingerprint``.
        delta: L-infinity perturbation radius in normalised coordinate space.
            Must be > 0.

    Returns:
        Fraction of grid points (including centre) whose primary families match
        the centre's primary families. Range [0.0, 1.0].

    Raises:
        ValueError: If ``delta`` <= 0.
    """
    if delta <= 0.0:
        raise ValueError(f"delta must be > 0, got {delta}")

    # Sort keys for deterministic grid construction (plan §2.4 note)
    sorted_keys = sorted(fingerprint_coordinates.keys())
    k = len(sorted_keys)

    # Build corner-plus-center grid: center point + 2^K corner points (1 + 2^K total)
    grid_points: list[dict[str, float]] = [dict(fingerprint_coordinates)]  # center first
    for signs in itertools.product((-1, 1), repeat=k):
        perturbed = dict(fingerprint_coordinates)
        for key, sign in zip(sorted_keys, signs, strict=True):
            perturbed[key] = fingerprint_coordinates[key] + sign * delta
        grid_points.append(perturbed)

    # Evaluate all grid points in a single pass; centre is grid_points[0]
    families_per_point = [frozenset(routing_callable(point)) for point in grid_points]
    centre_families = families_per_point[0]

    matching = sum(1 for families in families_per_point if families == centre_families)
    return matching / len(grid_points)


def build_routing_threshold_vector(
    fingerprint: ForecastabilityFingerprint,
    *,
    routing_config: RoutingPolicyConfig | None = None,
) -> dict[str, float]:
    """Build the standard threshold vector from the routing policy configuration.

    Constructs the threshold_vector dict used by ``audit_routing_case`` to
    compute the normalised threshold margin.  Each active routing threshold
    gets a distinct key so that duplicate fingerprint coordinates (e.g.
    information_mass appears at both ``low_mass_max`` and ``high_mass_min``)
    are both represented.

    Args:
        fingerprint: Forecastability fingerprint instance; used to determine
            whether the optional ``directness_ratio`` threshold is active.
        routing_config: Optional routing policy config; defaults to
            ``RoutingPolicyConfig()``.

    Returns:
        Dict with keys matching ``_THRESHOLD_TO_FINGERPRINT_ATTR``.
    """
    config = routing_config if routing_config is not None else RoutingPolicyConfig()
    vector: dict[str, float] = {
        "information_mass_low_max": config.low_mass_max,
        "information_mass_high_min": config.high_mass_min,
        "nonlinear_share": config.high_nonlinear_share_min,
    }
    if fingerprint.directness_ratio is not None:
        vector["directness_ratio"] = config.high_directness_min
    return vector


def _extract_penalty_count(recommendation: RoutingRecommendation) -> int:
    """Sum the individual penalty scores stored in the recommendation's metadata.

    The 0.3.1 routing service stores four integer penalty keys in
    ``recommendation.metadata``.  Their sum is the fingerprint_penalty_count
    carried through to ``RoutingValidationCase``.

    Args:
        recommendation: Routing recommendation from ``route_fingerprint``.

    Returns:
        Non-negative integer penalty total.
    """
    penalty_keys = (
        "threshold_margin_penalty",
        "taxonomy_uncertainty_penalty",
        "signal_conflict_penalty",
        "low_signal_quality_penalty",
    )
    total = 0
    for key in penalty_keys:
        value = recommendation.metadata.get(key, 0)
        total += int(value)
    return total


def _determine_outcome(
    *,
    observed_primary_families: list[str],
    expected_primary_families: list[str],
    threshold_margin: float,
    rule_stability: float,
    config: RoutingPolicyAuditConfig,
) -> RoutingValidationOutcome:
    """Apply the four-outcome predicate from plan v0.3.3 §2.2.

    Evaluated in the order: abstain → pass → downgrade → fail.

    Args:
        observed_primary_families: Primary families from the routing recommendation.
        expected_primary_families: Ground-truth expected families for this case.
        threshold_margin: Normalised threshold margin d_theta(f) per §2.3.
        rule_stability: Rule-stability score S(f,r;delta) per §2.4.
        config: Audit config providing tau_margin and tau_stable thresholds.

    Returns:
        One of ``"abstain"``, ``"pass"``, ``"downgrade"``, ``"fail"``.
    """
    # §2.2 predicate evaluated top-to-bottom
    if not observed_primary_families:
        return "abstain"

    intersection = frozenset(expected_primary_families) & frozenset(observed_primary_families)
    family_match = bool(intersection)

    if family_match:
        if threshold_margin >= config.tau_margin and rule_stability >= config.tau_stable:
            return "pass"
        return "downgrade"

    return "fail"


def audit_routing_case(
    *,
    case_name: str,
    source_kind: RoutingValidationSourceKind,
    expected_primary_families: list[str],
    fingerprint: ForecastabilityFingerprint,
    recommendation: RoutingRecommendation,
    threshold_vector: dict[str, float],
    config: RoutingPolicyAuditConfig = RoutingPolicyAuditConfig(),
    routing_config: RoutingPolicyConfig | None = None,
    notes: list[str] | None = None,
    metadata: dict[str, str | int | float] | None = None,
) -> RoutingValidationCase:
    """Evaluate a single routing recommendation against an expected-family case.

    Implements the four-outcome predicate from plan v0.3.3 §2.2 and the
    normalised threshold-distance metric from §2.3.  The rule-stability score
    is computed via ``compute_rule_stability`` (see V3_4-F03a) using the
    corner-plus-center grid defined in §2.4.

    Args:
        case_name: Stable machine-readable case identifier.
        source_kind: ``"synthetic"`` or ``"real"``.
        expected_primary_families: Non-empty list of family labels acceptable for
            this case.  A ``ValueError`` is raised if the list is empty.
        fingerprint: Forecastability fingerprint for the series.
        recommendation: Routing recommendation produced by ``route_fingerprint``.
        threshold_vector: Mapping from threshold name to threshold value used to
            compute d_theta(f).  Use ``build_routing_threshold_vector`` to
            derive this from the routing policy config.
        config: Audit scalars (tau_margin, tau_stable, perturbation_radius …).
            Defaults to the v0.3.3 conservative defaults.
        routing_config: Routing policy config used by the internal routing callable
            during stability analysis.  Defaults to ``RoutingPolicyConfig()``.
        notes: Optional free-text notes attached to the case.
        metadata: Optional key/value annotations for provenance.

    Returns:
        A frozen ``RoutingValidationCase`` with the four-outcome label,
        calibrated confidence label, threshold margin, and rule-stability score.

    Raises:
        ValueError: If ``expected_primary_families`` is empty.
    """
    if not expected_primary_families:
        raise ValueError(
            "expected_primary_families must be non-empty for case '{case_name}'"
        )

    observed = [str(f) for f in recommendation.primary_families]

    # Threshold margin (§2.3)
    threshold_margin = _compute_threshold_margin(
        fingerprint,
        threshold_vector,
        config=config,
    )

    # Rule-stability score (§2.4)
    fingerprint_coordinates = _extract_stability_coordinates(fingerprint)
    routing_callable = _make_routing_callable(fingerprint, routing_config=routing_config)
    rule_stability = compute_rule_stability(
        fingerprint_coordinates,
        routing_callable=routing_callable,
        delta=config.perturbation_radius,
    )

    # Four-outcome label (§2.2)
    outcome = _determine_outcome(
        observed_primary_families=observed,
        expected_primary_families=expected_primary_families,
        threshold_margin=threshold_margin,
        rule_stability=rule_stability,
        config=config,
    )

    penalty_count = _extract_penalty_count(recommendation)

    return RoutingValidationCase(
        case_name=case_name,
        source_kind=source_kind,
        expected_primary_families=expected_primary_families,
        observed_primary_families=observed,
        outcome=outcome,
        confidence_label=recommendation.confidence_label,
        threshold_margin=threshold_margin,
        rule_stability=rule_stability,
        fingerprint_penalty_count=penalty_count,
        notes=notes or [],
        metadata=metadata or {},
    )


__all__ = [
    "audit_routing_case",
    "build_routing_threshold_vector",
    "compute_rule_stability",
]
