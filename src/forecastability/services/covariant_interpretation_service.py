"""Deterministic interpretation service for covariant analysis bundles (V3-F09).

Maps a :class:`CovariantAnalysisBundle` to a
:class:`CovariantInterpretationResult` using explicit, ordered role-assignment
rules.  Also provides a pure hallucination verifier for narrative text
produced by LLM adapters downstream.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import get_args

from forecastability.utils.types import (
    CovariantAnalysisBundle,
    CovariantDriverRole,
    CovariantInterpretationResult,
    CovariantMethodConditioning,
    CovariantRoleTag,
    CovariantSummaryRow,
)

_PCMCI_NONLINEAR_WARNING = (
    "PCMCI+ parcorr is blind to nonlinear coupling; rely on cross_ami/te/gcmi "
    "for nonlinear drivers."
)
_TARGET_ONLY_CONDITIONING_WARNING = (
    "transfer_entropy and pCrossAMI are conditioned on target history only; "
    "they do not condition on other drivers."
)
_DEFAULT_CONDITIONING_DISCLAIMER = (
    "Bundle conditioning scope: CrossMI and GCMI rows are unconditioned pairwise "
    "signals (`none`); pCrossAMI and TE rows are `target_only`; only PCMCI+ and "
    "PCMCI-AMI are `full_mci`. See section 5A in "
    "docs/plan/v0_3_0_covariant_informative_ultimate_plan.md."
)

_ALLOWED_ROLE_TAGS: frozenset[str] = frozenset(get_args(CovariantRoleTag))

# Role-assignment thresholds (statistician-approved defaults).
STRONG_MI_NUMERIC = 0.10
NOISE_AMI_CEIL = 0.03
NONLINEAR_AMI_MIN = 0.03
GCMI_NOISE_FLOOR = 0.01
MEDIATION_RATIO = 0.30
CONTEMP_LAG = 0


def _driver_rows(bundle: CovariantAnalysisBundle, driver: str) -> list[CovariantSummaryRow]:
    return [row for row in bundle.summary_table if row.driver == driver]


def _safe_max(values: Iterable[float | None]) -> float:
    collected = [v for v in values if v is not None]
    return max(collected) if collected else 0.0


def _best_lag_by_cross_ami(rows: list[CovariantSummaryRow]) -> int | None:
    ami_rows = [r for r in rows if r.cross_ami is not None]
    if not ami_rows:
        return None
    best = max(ami_rows, key=lambda r: (r.cross_ami if r.cross_ami is not None else -1.0, -r.lag))
    return best.lag


def _parents_for_target(
    parents_map: dict[str, list[tuple[str, int]]], target: str
) -> list[tuple[str, int]]:
    return list(parents_map.get(target, []))


def _pcmci_plus_parents(bundle: CovariantAnalysisBundle) -> list[tuple[str, int]]:
    if bundle.pcmci_graph is None:
        return []
    return _parents_for_target(bundle.pcmci_graph.parents, bundle.target_name)


def _pcmci_ami_parents(bundle: CovariantAnalysisBundle) -> list[tuple[str, int]]:
    if bundle.pcmci_ami_result is None:
        return []
    return _parents_for_target(bundle.pcmci_ami_result.causal_graph.parents, bundle.target_name)


def _row_conditioning(rows: list[CovariantSummaryRow]) -> CovariantMethodConditioning:
    """Return the shared per-row conditioning (all rows share the same instance)."""
    if rows:
        return rows[0].lagged_exog_conditioning
    return CovariantMethodConditioning()


def _driver_warnings(conditioning: CovariantMethodConditioning) -> list[str]:
    warnings: list[str] = []
    if conditioning.transfer_entropy == "target_only" or conditioning.cross_pami == "target_only":
        warnings.append(_TARGET_ONLY_CONDITIONING_WARNING)
    return warnings


def _classify_driver(
    *,
    bundle: CovariantAnalysisBundle,
    driver: str,
    strong_mi_threshold: float,
    noise_ami_ceil: float,
    nonlinear_ami_min: float,
    gcmi_noise_floor: float,
    mediation_ratio: float,
    significance_label: str,
) -> CovariantDriverRole:
    rows = _driver_rows(bundle, driver)
    max_ami = _safe_max(r.cross_ami for r in rows)
    max_gcmi = _safe_max(r.gcmi for r in rows)
    max_te = _safe_max(r.transfer_entropy for r in rows)
    max_pami = _safe_max(r.cross_pami for r in rows)
    sig_count = sum(1 for r in rows if r.significance == significance_label)
    any_sig = sig_count > 0
    has_causal = bundle.pcmci_graph is not None or bundle.pcmci_ami_result is not None
    gcmi_strong = max_gcmi >= strong_mi_threshold
    te_strong = max_te >= strong_mi_threshold
    ami_strong = max_ami >= strong_mi_threshold
    best_lag = _best_lag_by_cross_ami(rows)

    pcmci_parents = _pcmci_plus_parents(bundle)
    pcmci_ami_parents = _pcmci_ami_parents(bundle)
    driver_pcmci_lags = [lag for (src, lag) in pcmci_parents if src == driver]
    driver_pcmci_ami_lags = [lag for (src, lag) in pcmci_ami_parents if src == driver]
    is_pcmci_lagged_parent = any(lag >= 1 for lag in driver_pcmci_lags)
    is_pcmci_ami_parent = bool(driver_pcmci_ami_lags)
    is_pcmci_parent = is_pcmci_lagged_parent
    is_contemp_pcmci_parent = bool(driver_pcmci_lags) and all(
        lag == CONTEMP_LAG for lag in driver_pcmci_lags
    )

    other_lagged_parent_exists = any(
        src != driver and lag >= 1 for (src, lag) in list(pcmci_parents) + list(pcmci_ami_parents)
    )

    methods_supporting: list[str] = []
    methods_missing: list[str] = []
    if ami_strong:
        methods_supporting.append("cross_ami")
    else:
        methods_missing.append("cross_ami")
    if gcmi_strong:
        methods_supporting.append("gcmi")
    else:
        methods_missing.append("gcmi")
    if te_strong:
        methods_supporting.append("transfer_entropy")
    else:
        methods_missing.append("transfer_entropy")
    if is_pcmci_lagged_parent or is_contemp_pcmci_parent:
        methods_supporting.append("pcmci")
    elif bundle.pcmci_graph is not None:
        methods_missing.append("pcmci")
    if is_pcmci_ami_parent:
        methods_supporting.append("pcmci_ami")
    elif bundle.pcmci_ami_result is not None:
        methods_missing.append("pcmci_ami")

    evidence = [
        f"max_cross_ami={max_ami:.4f}",
        f"max_gcmi={max_gcmi:.4f}",
        f"max_transfer_entropy={max_te:.4f}",
        f"max_cross_pami={max_pami:.4f}",
        f"pcmci_lagged_parent={is_pcmci_lagged_parent}",
        f"pcmci_ami_parent={is_pcmci_ami_parent}",
        f"best_lag={best_lag}",
    ]

    role = _assign_role(
        max_ami=max_ami,
        max_gcmi=max_gcmi,
        max_te=max_te,
        max_pami=max_pami,
        any_sig=any_sig,
        sig_count=sig_count,
        has_causal=has_causal,
        is_pcmci_parent=is_pcmci_parent,
        is_pcmci_ami_parent=is_pcmci_ami_parent,
        is_contemp_pcmci_parent=is_contemp_pcmci_parent,
        other_lagged_parent_exists=other_lagged_parent_exists,
        strong_mi_threshold=strong_mi_threshold,
        noise_ami_ceil=noise_ami_ceil,
        nonlinear_ami_min=nonlinear_ami_min,
        gcmi_noise_floor=gcmi_noise_floor,
        mediation_ratio=mediation_ratio,
    )

    conditioning = _row_conditioning(rows)
    warnings = _driver_warnings(conditioning)
    if role == "inconclusive":
        warnings.append(
            "Evidence exists but does not match any canonical covariant pattern; review manually."
        )

    return CovariantDriverRole(
        driver=driver,
        role=role,
        best_lag=best_lag,
        evidence=evidence,
        methods_supporting=methods_supporting,
        methods_missing=methods_missing,
        conditioning=conditioning,
        warnings=warnings,
    )


def _assign_role(
    *,
    max_ami: float,
    max_gcmi: float,
    max_te: float,
    max_pami: float,
    any_sig: bool,
    sig_count: int,
    has_causal: bool,
    is_pcmci_parent: bool,
    is_pcmci_ami_parent: bool,
    is_contemp_pcmci_parent: bool,
    other_lagged_parent_exists: bool,
    strong_mi_threshold: float,
    noise_ami_ceil: float,
    nonlinear_ami_min: float,
    gcmi_noise_floor: float,
    mediation_ratio: float,
) -> CovariantRoleTag:
    """First-match role assignment per statistician-approved rules."""
    # Rule 1: noise_or_weak. A surrogate-significant row (any_sig) blocks this
    # classification even when all effect-size thresholds are sub-threshold:
    # such rows must fall through to `inconclusive` rather than be swallowed.
    if (
        max_ami < noise_ami_ceil
        and max_gcmi < strong_mi_threshold
        and max_te < strong_mi_threshold
        and not is_pcmci_parent
        and not is_pcmci_ami_parent
        and not is_contemp_pcmci_parent
        and not any_sig
    ):
        return "noise_or_weak"
    # Rule 2: direct_driver.
    if is_pcmci_parent or is_pcmci_ami_parent:
        return "direct_driver"
    # Rule 3: contemporaneous.
    if is_contemp_pcmci_parent:
        return "contemporaneous"
    # Rule 4: nonlinear_driver. Require multi-lag surrogate support
    # (>= 2 significant lags) so a single chance-significant row at max_lag=5
    # cannot trigger the role; this is a Bonferroni-style guard against the
    # per-lag false-positive rate of the phase-randomised surrogate test.
    if max_ami >= nonlinear_ami_min and max_gcmi < gcmi_noise_floor and sig_count >= 2:
        return "nonlinear_driver"
    # Rule 5: redundant.
    if (
        max_ami >= strong_mi_threshold
        and max_gcmi >= strong_mi_threshold
        and other_lagged_parent_exists
    ):
        return "redundant"
    # Rule 6: mediated_driver. Mediation is a causal claim; cross_pami alone
    # (conditioned on target history only) cannot establish it. Require:
    # 1. has_causal: a causal method ran (bundle-level gate)
    # 2. any_sig: surrogate test confirms the AMI signal is real for this
    #    driver (driver-specific gate; V3-AI-03). Without any_sig the
    #    ratio max_pami / max_ami could be < 0.30 purely because both values
    #    are sub-noise, not because mediation suppressed the partial.
    # Without both conditions, fall through to `inconclusive`.
    if (
        has_causal
        and any_sig
        and max_ami >= strong_mi_threshold
        and max_ami > 0
        and (max_pami / max_ami) < mediation_ratio
    ):
        return "mediated_driver"
    # Rule 7: inconclusive fallback.
    return "inconclusive"


def _derive_forecastability_class(
    *,
    roles: list[CovariantDriverRole],
) -> tuple[str, list[str]]:
    # A driver earning the `direct_driver` or `nonlinear_driver` role has already
    # cleared the strong-MI / significance gates inside the role rules, so the
    # role itself is the authoritative strength certificate.
    strong_roles = {"direct_driver", "nonlinear_driver"}
    primary_drivers = [entry.driver for entry in roles if entry.role in strong_roles]
    if primary_drivers:
        return "high", primary_drivers
    if roles and all(entry.role == "noise_or_weak" for entry in roles):
        return "low", []
    return "medium", []


def _derive_directness_class(roles: list[CovariantDriverRole]) -> str:
    non_noise = [entry for entry in roles if entry.role != "noise_or_weak"]
    if not non_noise:
        return "low"
    direct_like = sum(
        1 for entry in non_noise if entry.role in {"direct_driver", "contemporaneous"}
    )
    mediated_like = sum(1 for entry in non_noise if entry.role in {"mediated_driver", "redundant"})
    total = len(non_noise)
    if direct_like > total / 2:
        return "high"
    if mediated_like > total / 2:
        return "low"
    if direct_like == mediated_like and direct_like > 0:
        return "mixed"
    return "medium"


_MODELING_REGIMES: dict[tuple[str, str], str] = {
    ("high", "high"): "high+high -> deep structured exogenous models",
    ("high", "medium"): "high+medium -> structured exogenous models with caveats",
    ("high", "low"): "high+low -> compact models w/ mediated drivers",
    ("high", "mixed"): "high+mixed -> hybrid structured + compact exogenous models",
    ("medium", "high"): "medium+high -> regularised structured models",
    ("medium", "medium"): "medium+medium -> seasonal or regularised AR",
    ("medium", "low"): "medium+low -> compact baselines with exogenous review",
    ("medium", "mixed"): "medium+mixed -> seasonal AR with exogenous triage",
    ("low", "high"): "low -> baseline",
    ("low", "medium"): "low -> baseline",
    ("low", "low"): "low -> baseline",
    ("low", "mixed"): "low -> baseline",
}


def _resolve_conditioning_disclaimer(bundle: CovariantAnalysisBundle) -> str:
    meta = bundle.metadata
    for key in ("conditioning_disclaimer", "conditioning_scope_disclaimer"):
        value = meta.get(key)
        if isinstance(value, str) and value:
            return value
    return _DEFAULT_CONDITIONING_DISCLAIMER


def interpret_covariant_bundle(
    bundle: CovariantAnalysisBundle,
    *,
    strong_mi_threshold: float = STRONG_MI_NUMERIC,
    noise_ami_ceil: float = NOISE_AMI_CEIL,
    nonlinear_ami_min: float = NONLINEAR_AMI_MIN,
    gcmi_noise_floor: float = GCMI_NOISE_FLOOR,
    mediation_ratio: float = MEDIATION_RATIO,
    significance_label: str = "above_band",
) -> CovariantInterpretationResult:
    """Derive a deterministic interpretation from a covariant analysis bundle.

    Args:
        bundle: Covariant analysis output from ``run_covariant_analysis``.
        strong_mi_threshold: Minimum MI/GCMI/TE value treated as "strong".
        noise_ami_ceil: AMI ceiling below which a driver is noise candidate.
        nonlinear_ami_min: Minimum AMI for the nonlinear-driver rule.
        gcmi_noise_floor: GCMI floor below which the nonlinear-driver rule applies.
        mediation_ratio: Maximum ``max_pami / max_ami`` ratio for mediation.
        significance_label: Summary-row ``significance`` value treated as sig.

    Returns:
        Immutable :class:`CovariantInterpretationResult` with driver roles,
        forecastability / directness classes, and a modeling-regime tag.
    """
    roles = [
        _classify_driver(
            bundle=bundle,
            driver=driver,
            strong_mi_threshold=strong_mi_threshold,
            noise_ami_ceil=noise_ami_ceil,
            nonlinear_ami_min=nonlinear_ami_min,
            gcmi_noise_floor=gcmi_noise_floor,
            mediation_ratio=mediation_ratio,
            significance_label=significance_label,
        )
        for driver in bundle.driver_names
    ]
    forecastability_class, primary_drivers = _derive_forecastability_class(roles=roles)
    directness_class = _derive_directness_class(roles)
    modeling_regime = _MODELING_REGIMES.get(
        (forecastability_class, directness_class),
        f"{forecastability_class}+{directness_class} -> review manually",
    )
    warnings: list[str] = []
    if bundle.pcmci_graph is not None:
        warnings.append(_PCMCI_NONLINEAR_WARNING)
    return CovariantInterpretationResult(
        target=bundle.target_name,
        driver_roles=roles,
        forecastability_class=forecastability_class,  # type: ignore[arg-type]
        directness_class=directness_class,  # type: ignore[arg-type]
        primary_drivers=primary_drivers,
        modeling_regime=modeling_regime,
        conditioning_disclaimer=_resolve_conditioning_disclaimer(bundle),
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Hallucination verifier
# ---------------------------------------------------------------------------


_NUMERIC_RE = re.compile(r"\d+\.\d+")
_ROLE_TAG_RE = re.compile(r"[a-z_]+")


def _extract_numeric_literals(text: str) -> set[str]:
    return set(_NUMERIC_RE.findall(text))


def verify_narrative_against_bundle(
    narrative: str,
    interpretation: CovariantInterpretationResult,
    *,
    allowed_role_tags: frozenset[str] | None = None,
) -> list[str]:
    """Return a list of hallucination-violation messages for a narrative.

    An empty list means the narrative is consistent with the deterministic
    interpretation.

    Args:
        narrative: Free-form LLM narrative.
        interpretation: Deterministic interpretation produced upstream.
        allowed_role_tags: Override for the permitted role-tag vocabulary.

    Returns:
        List of human-readable violation strings; empty when consistent.
    """
    if not narrative:
        return []

    role_vocab = allowed_role_tags if allowed_role_tags is not None else _ALLOWED_ROLE_TAGS
    known_drivers = {entry.driver for entry in interpretation.driver_roles}
    violations: list[str] = []

    tokens = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", narrative))
    driver_like = {tok for tok in tokens if tok.startswith("driver_")}
    for token in sorted(driver_like - known_drivers):
        violations.append(f"Unknown driver mentioned in narrative: '{token}'.")

    snake_tokens = {tok for tok in tokens if "_" in tok and tok.islower()}
    fabricated_role_like = {
        tok
        for tok in snake_tokens
        if tok.endswith("_driver") or tok in {"redundant", "contemporaneous", "inconclusive"}
    }
    for token in sorted(fabricated_role_like - role_vocab):
        if token not in known_drivers:
            violations.append(f"Fabricated role tag in narrative: '{token}'.")

    deterministic_numbers = _extract_numeric_literals(str(interpretation.model_dump()))
    narrative_numbers = _extract_numeric_literals(narrative)
    stray = sorted(narrative_numbers - deterministic_numbers)
    for literal in stray:
        violations.append(
            f"Stray numeric literal in narrative not in deterministic evidence: '{literal}'."
        )

    return violations
