"""Minimal sanity tests for Phase 0 lagged-exogenous typed models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from forecastability.utils.types import (
    LaggedExogBundle,
    LaggedExogProfileRow,
    LaggedExogSelectionRow,
)


def test_lagged_exog_models_are_frozen() -> None:
    """Phase 0 lagged exogenous models should be immutable."""
    assert LaggedExogProfileRow.model_config.get("frozen") is True
    assert LaggedExogSelectionRow.model_config.get("frozen") is True
    assert LaggedExogBundle.model_config.get("frozen") is True


def _make_profile_row(**kwargs: object) -> LaggedExogProfileRow:
    """Build a minimal valid LaggedExogProfileRow with overridable fields."""
    defaults: dict[str, object] = {
        "target": "target",
        "driver": "driver",
        "lag": 0,
        "lag_role": "instant",
        "tensor_role": "diagnostic",
    }
    defaults.update(kwargs)
    return LaggedExogProfileRow(**defaults)  # type: ignore[arg-type]


def test_lagged_exog_bundle_round_trip_json() -> None:
    """Lagged-exogenous bundle should serialize and round-trip cleanly."""
    profile_row = _make_profile_row()
    selection_row = LaggedExogSelectionRow(
        target="target",
        driver="driver",
        lag=1,
        selected_for_tensor=True,
        selector_name="xami_sparse",
        score=0.42,
    )
    bundle = LaggedExogBundle(
        target_name="target",
        driver_names=["driver"],
        max_lag=4,
        profile_rows=[profile_row],
        selected_lags=[selection_row],
    )

    dumped = bundle.model_dump_json()
    restored = LaggedExogBundle.model_validate_json(dumped)

    assert restored == bundle


def test_frozen_models_raise_on_field_assignment() -> None:
    """Frozen models must raise at runtime when a field is assigned."""
    row = _make_profile_row()
    with pytest.raises(ValidationError):
        row.lag = 99

    sel = LaggedExogSelectionRow(
        target="t",
        driver="d",
        lag=1,
        selected_for_tensor=False,
        selector_name="xcorr_top_k",
    )
    with pytest.raises(ValidationError):
        sel.lag = 99

    bundle = LaggedExogBundle(
        target_name="t",
        driver_names=["d"],
        max_lag=3,
        profile_rows=[],
        selected_lags=[],
    )
    with pytest.raises(ValidationError):
        bundle.max_lag = 0


def test_frozen_model_container_mutability() -> None:
    """Document Pydantic frozen semantics: field reassignment is blocked but
    mutable containers (list, dict) inside frozen models remain mutable.

    This is expected Pydantic v2 behavior.  Phase 0 keeps list fields to
    preserve additive compatibility; deep immutability is out of scope.
    """
    bundle = LaggedExogBundle(
        target_name="t",
        driver_names=["d1"],
        max_lag=3,
        profile_rows=[],
        selected_lags=[],
    )
    # Reassigning the field itself is blocked.
    with pytest.raises(ValidationError):
        bundle.driver_names = ["d2"]

    # But mutating the list in-place is still possible (documented Pydantic behavior).
    bundle.driver_names.append("d2")
    assert "d2" in bundle.driver_names


def test_significance_consistency_validator_valid_cases() -> None:
    """Validator should pass for consistent significance / significance_source pairs."""
    # not_computed + None is valid
    row = _make_profile_row(significance=None, significance_source="not_computed")
    assert row.significance is None

    # non-not_computed + non-empty string is valid
    row2 = _make_profile_row(
        significance="p<0.05",
        significance_source="phase_surrogate_xami",
    )
    assert row2.significance == "p<0.05"


def test_significance_consistency_validator_rejects_mismatches() -> None:
    """Validator must reject inconsistent significance / significance_source pairs."""
    # not_computed but significance provided
    with pytest.raises(ValidationError, match="significance must be None"):
        _make_profile_row(significance="p<0.05", significance_source="not_computed")

    # computed source but significance is None
    with pytest.raises(ValidationError, match="non-None"):
        _make_profile_row(significance=None, significance_source="phase_surrogate_xcorr")

    # computed source but significance is empty string
    with pytest.raises(ValidationError, match="non-None"):
        _make_profile_row(significance="", significance_source="phase_surrogate_xami")
