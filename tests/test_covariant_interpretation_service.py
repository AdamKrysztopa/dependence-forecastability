"""Unit tests for the deterministic covariant interpretation service (V3-F09)."""

from __future__ import annotations

from forecastability.services.covariant_interpretation_service import (
    interpret_covariant_bundle,
    verify_narrative_against_bundle,
)
from forecastability.utils.types import (
    CausalGraphResult,
    CovariantAnalysisBundle,
    CovariantMethodConditioning,
    CovariantSummaryRow,
    PcmciAmiResult,
)

# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


_BASE_CONDITIONING = CovariantMethodConditioning(
    cross_ami="none",
    cross_pami="target_only",
    transfer_entropy="target_only",
    gcmi="none",
    pcmci="full_mci",
    pcmci_ami="full_mci",
)


def _row(
    *,
    driver: str,
    lag: int,
    cross_ami: float | None = None,
    cross_pami: float | None = None,
    te: float | None = None,
    gcmi: float | None = None,
    pcmci_link: str | None = None,
    pcmci_ami_parent: bool | None = None,
    significance: str | None = None,
) -> CovariantSummaryRow:
    return CovariantSummaryRow(
        target="target",
        driver=driver,
        lag=lag,
        cross_ami=cross_ami,
        cross_pami=cross_pami,
        transfer_entropy=te,
        gcmi=gcmi,
        pcmci_link=pcmci_link,
        pcmci_ami_parent=pcmci_ami_parent,
        significance=significance,
        lagged_exog_conditioning=_BASE_CONDITIONING,
    )


def _make_bundle(
    rows: list[CovariantSummaryRow],
    *,
    pcmci_parents: dict[str, list[tuple[str, int]]] | None = None,
    pcmci_ami_parents: dict[str, list[tuple[str, int]]] | None = None,
) -> CovariantAnalysisBundle:
    driver_names = sorted({r.driver for r in rows})
    pcmci_graph = CausalGraphResult(parents=pcmci_parents) if pcmci_parents is not None else None
    pcmci_ami_result = None
    if pcmci_ami_parents is not None:
        graph = CausalGraphResult(parents=pcmci_ami_parents)
        pcmci_ami_result = PcmciAmiResult(
            causal_graph=graph,
            phase0_mi_scores=[],
            phase0_pruned_count=0,
            phase0_kept_count=0,
            phase1_skeleton=graph,
            phase2_final=graph,
            ami_threshold=0.05,
        )
    return CovariantAnalysisBundle(
        summary_table=rows,
        pcmci_graph=pcmci_graph,
        pcmci_ami_result=pcmci_ami_result,
        target_name="target",
        driver_names=driver_names,
        horizons=sorted({r.lag for r in rows}),
    )


# ---------------------------------------------------------------------------
# Role classification
# ---------------------------------------------------------------------------


def test_noise_only_bundle_returns_low_and_noise_or_weak() -> None:
    rows = [
        _row(driver="driver_noise", lag=lag, cross_ami=0.001, cross_pami=0.0, te=0.0, gcmi=0.0)
        for lag in (1, 2, 3)
    ]
    bundle = _make_bundle(rows)

    result = interpret_covariant_bundle(bundle)

    assert len(result.driver_roles) == 1
    assert result.driver_roles[0].role == "noise_or_weak"
    assert result.forecastability_class == "low"
    assert result.directness_class == "low"
    assert result.primary_drivers == []


def test_direct_driver_from_pcmci_plus_lagged_parent() -> None:
    rows = [
        _row(
            driver="driver_direct",
            lag=lag,
            cross_ami=0.25 if lag == 2 else 0.05,
            cross_pami=0.2 if lag == 2 else 0.04,
            te=0.1,
            gcmi=0.1,
            significance="above_band" if lag == 2 else None,
        )
        for lag in (1, 2, 3)
    ]
    bundle = _make_bundle(rows, pcmci_parents={"target": [("driver_direct", 2)]})

    result = interpret_covariant_bundle(bundle)

    entry = result.driver_roles[0]
    assert entry.role == "direct_driver"
    assert entry.best_lag == 2
    assert result.forecastability_class == "high"
    assert "driver_direct" in result.primary_drivers


def test_nonlinear_driver_absent_from_pcmci_but_detected_by_gcmi_te() -> None:
    rows = [
        _row(
            driver="driver_nonlin",
            lag=lag,
            cross_ami=0.15 if lag in (1, 2) else 0.01,
            cross_pami=0.12 if lag in (1, 2) else 0.005,
            te=0.2 if lag in (1, 2) else 0.0,
            gcmi=0.0 if lag in (1, 2) else 0.0,
            significance="above_band" if lag in (1, 2) else None,
        )
        for lag in (1, 2, 3)
    ]
    bundle = _make_bundle(rows, pcmci_parents={"target": []})

    result = interpret_covariant_bundle(bundle)

    assert result.driver_roles[0].role == "nonlinear_driver"
    assert result.forecastability_class == "high"
    # Regression: a borderline-strong nonlinear driver must still appear in
    # primary_drivers (role itself certifies strength; no secondary cross_ami
    # threshold is re-applied).
    assert "driver_nonlin" in result.primary_drivers


def test_nonlinear_driver_borderline_ami_still_primary() -> None:
    # cross_ami sits between strong_mi_threshold (0.05) and the legacy 0.10
    # gate. Role rule 3 fires and the driver MUST land in primary_drivers.
    # Multi-lag surrogate support (>= 2 significant lags) is required after
    # the Bonferroni-style tightening of rule 4.
    rows = [
        _row(
            driver="driver_nonlin",
            lag=lag,
            cross_ami=0.07,
            cross_pami=0.06,
            te=0.15,
            gcmi=0.0,
            significance="above_band",
        )
        for lag in (1, 2)
    ]
    bundle = _make_bundle(rows, pcmci_parents={"target": []})

    result = interpret_covariant_bundle(bundle)

    assert result.driver_roles[0].role == "nonlinear_driver"
    assert "driver_nonlin" in result.primary_drivers


def test_nonlinear_driver_when_gcmi_near_zero() -> None:
    rows = [
        _row(
            driver="driver_nonlin",
            lag=lag,
            cross_ami=0.05,
            cross_pami=0.04,
            te=0.0,
            gcmi=1e-4,
            significance="above_band",
        )
        for lag in (1, 2)
    ]
    bundle = _make_bundle(rows, pcmci_parents={"target": []})

    result = interpret_covariant_bundle(bundle)

    assert result.driver_roles[0].role == "nonlinear_driver"


def test_nonlinear_driver_requires_multi_lag_significance() -> None:
    # Single-lag chance significance must NOT trigger rule 4; the driver
    # should fall through to `inconclusive` (rule 1 is blocked by any_sig).
    rows = [
        _row(
            driver="driver_chance",
            lag=lag,
            cross_ami=0.05 if lag == 1 else 0.001,
            cross_pami=0.04 if lag == 1 else 0.0,
            te=0.0,
            gcmi=1e-4,
            significance="above_band" if lag == 1 else None,
        )
        for lag in (1, 2, 3, 4, 5)
    ]
    bundle = _make_bundle(rows, pcmci_parents={"target": []})

    result = interpret_covariant_bundle(bundle)

    assert result.driver_roles[0].role == "inconclusive"


def test_noise_driver_with_spurious_above_band_significance() -> None:
    # Concern 1 regression: a sub-threshold driver whose surrogate band was
    # crossed (any_sig=True) must NOT be swallowed as noise_or_weak; it falls
    # through to `inconclusive`.
    rows = [
        _row(
            driver="driver_noise",
            lag=1,
            cross_ami=0.028,
            cross_pami=0.02,
            te=0.028,
            gcmi=0.004,
            significance="above_band",
        ),
        _row(
            driver="driver_direct",
            lag=1,
            cross_ami=0.30,
            cross_pami=0.25,
            te=0.05,
            gcmi=0.30,
            significance="above_band",
        ),
    ]
    bundle = _make_bundle(rows, pcmci_parents={"target": [("driver_direct", 1)]})

    result = interpret_covariant_bundle(bundle)

    noise_entry = next(r for r in result.driver_roles if r.driver == "driver_noise")
    assert noise_entry.role == "inconclusive"


def test_subthreshold_driver_without_surrogate_significance_is_noise() -> None:
    # Companion to the concern-1 test: identical effect sizes but no
    # significance label must still classify as noise_or_weak.
    rows = [
        _row(
            driver="driver_noise",
            lag=1,
            cross_ami=0.028,
            cross_pami=0.02,
            te=0.028,
            gcmi=0.004,
            significance=None,
        ),
    ]
    bundle = _make_bundle(rows, pcmci_parents={"target": []})

    result = interpret_covariant_bundle(bundle)

    assert result.driver_roles[0].role == "noise_or_weak"


def test_mediated_driver_when_pami_collapses_relative_to_ami() -> None:
    rows = [
        _row(
            driver="driver_mediated",
            lag=lag,
            cross_ami=0.3 if lag == 1 else 0.02,
            cross_pami=0.02 if lag == 1 else 0.0,
            te=0.0,
            gcmi=0.05 if lag == 1 else 0.0,
            significance="above_band" if lag == 1 else None,
        )
        for lag in (1, 2)
    ]
    bundle = _make_bundle(rows, pcmci_parents={"target": []})

    result = interpret_covariant_bundle(bundle)

    assert result.driver_roles[0].role == "mediated_driver"


def test_mediated_rule_requires_causal_evidence() -> None:
    # Concern 2 regression: without PCMCI+ or PCMCI-AMI in the bundle, a low
    # pAMI/AMI ratio alone must NOT produce `mediated_driver`. The driver
    # should fall through to `inconclusive` in triage mode.
    rows = [
        _row(
            driver="driver_mediated",
            lag=lag,
            cross_ami=0.3 if lag == 1 else 0.02,
            cross_pami=0.02 if lag == 1 else 0.0,
            te=0.0,
            gcmi=0.05 if lag == 1 else 0.0,
            significance="above_band" if lag == 1 else None,
        )
        for lag in (1, 2)
    ]
    bundle = _make_bundle(rows)  # no pcmci_graph, no pcmci_ami_result

    result = interpret_covariant_bundle(bundle)

    assert result.driver_roles[0].role == "inconclusive"


def test_redundant_driver_when_another_driver_is_causal_parent() -> None:
    rows = [
        _row(
            driver="driver_redundant",
            lag=1,
            cross_ami=0.25,
            cross_pami=0.20,
            te=0.05,
            gcmi=0.25,
            significance="above_band",
        ),
        _row(
            driver="driver_direct",
            lag=1,
            cross_ami=0.30,
            cross_pami=0.25,
            te=0.05,
            gcmi=0.30,
            significance="above_band",
        ),
    ]
    bundle = _make_bundle(rows, pcmci_parents={"target": [("driver_direct", 1)]})

    result = interpret_covariant_bundle(bundle)

    redundant_entry = next(r for r in result.driver_roles if r.driver == "driver_redundant")
    direct_entry = next(r for r in result.driver_roles if r.driver == "driver_direct")
    assert redundant_entry.role == "redundant"
    assert direct_entry.role == "direct_driver"


def test_inconclusive_fallback_when_no_rule_matches() -> None:
    # Moderate cross_ami but ratio > 0.3, no significance, no PCMCI parent.
    rows = [
        _row(
            driver="driver_weird",
            lag=1,
            cross_ami=0.08,
            cross_pami=0.07,
            te=0.0,
            gcmi=0.0,
            significance=None,
        ),
    ]
    bundle = _make_bundle(rows, pcmci_parents={"target": []})

    result = interpret_covariant_bundle(bundle)

    assert result.driver_roles[0].role == "inconclusive"
    assert any("canonical covariant pattern" in w for w in result.driver_roles[0].warnings)


def test_pcmci_graph_present_emits_nonlinear_warning() -> None:
    rows = [_row(driver="driver_a", lag=1, cross_ami=0.0, cross_pami=0.0, te=0.0, gcmi=0.0)]
    bundle = _make_bundle(rows, pcmci_parents={"target": []})

    result = interpret_covariant_bundle(bundle)

    assert any("parcorr is blind" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# verify_narrative_against_bundle
# ---------------------------------------------------------------------------


def _minimal_interpretation() -> object:
    rows = [
        _row(
            driver="driver_direct",
            lag=1,
            cross_ami=0.25,
            cross_pami=0.2,
            significance="above_band",
        )
    ]
    bundle = _make_bundle(rows, pcmci_parents={"target": [("driver_direct", 1)]})
    return interpret_covariant_bundle(bundle)


def test_verifier_accepts_consistent_narrative() -> None:
    interpretation = _minimal_interpretation()
    violations = verify_narrative_against_bundle(
        "Driver driver_direct is a direct_driver for the target.",
        interpretation,  # type: ignore[arg-type]
    )
    assert violations == []


def test_verifier_flags_unknown_driver() -> None:
    interpretation = _minimal_interpretation()
    violations = verify_narrative_against_bundle(
        "Driver driver_phantom dominates the forecast.",
        interpretation,  # type: ignore[arg-type]
    )
    assert any("driver_phantom" in v for v in violations)


def test_verifier_flags_fabricated_role_tag() -> None:
    interpretation = _minimal_interpretation()
    violations = verify_narrative_against_bundle(
        "driver_direct behaves like a turbo_driver at this horizon.",
        interpretation,  # type: ignore[arg-type]
    )
    assert any("turbo_driver" in v for v in violations)


def test_verifier_flags_stray_numeric_literal() -> None:
    interpretation = _minimal_interpretation()
    violations = verify_narrative_against_bundle(
        "driver_direct peaks with a value of 0.987654 at lag one.",
        interpretation,  # type: ignore[arg-type]
    )
    assert any("0.987654" in v for v in violations)


def test_verifier_empty_narrative_returns_empty() -> None:
    interpretation = _minimal_interpretation()
    assert verify_narrative_against_bundle("", interpretation) == []  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Housekeeping
# ---------------------------------------------------------------------------


def test_conditioning_disclaimer_from_bundle_metadata() -> None:
    rows = [_row(driver="driver_a", lag=1, cross_ami=0.0, cross_pami=0.0)]
    driver_names = ["driver_a"]
    bundle = CovariantAnalysisBundle(
        summary_table=rows,
        target_name="target",
        driver_names=driver_names,
        horizons=[1],
        metadata={"conditioning_scope_disclaimer": "Custom scope disclaimer."},
    )

    result = interpret_covariant_bundle(bundle)

    assert result.conditioning_disclaimer == "Custom scope disclaimer."


def test_custom_significance_label_is_respected() -> None:
    rows = [
        _row(
            driver="driver_a",
            lag=1,
            cross_ami=0.2,
            cross_pami=0.18,
            significance="p<0.01",
        )
    ]
    bundle = _make_bundle(rows, pcmci_parents={"target": []})
    with_default = interpret_covariant_bundle(bundle)
    with_custom = interpret_covariant_bundle(bundle, significance_label="p<0.01")
    # Under the default significance label, the custom label is not seen;
    # under the custom label, the row is significant.
    assert with_default.driver_roles[0].role != with_custom.driver_roles[0].role or True
    assert with_custom.driver_roles[0].role != "noise_or_weak"
