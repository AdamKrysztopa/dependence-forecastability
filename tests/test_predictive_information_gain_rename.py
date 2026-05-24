"""Verify that compute_transfer_entropy raises ImportError and PIG rename works."""

from __future__ import annotations

import pytest


def test_compute_transfer_entropy_removed() -> None:
    with pytest.raises(ImportError, match="compute_transfer_entropy was split in v0.5.0"):
        from forecastability.diagnostics import compute_transfer_entropy  # noqa: F401


def test_predictive_information_gain_importable() -> None:
    from forecastability.diagnostics.predictive_information_gain import (
        compute_predictive_information_gain,
    )

    assert callable(compute_predictive_information_gain)


def test_compute_transfer_entropy_ksg_importable() -> None:
    from forecastability.diagnostics.cmi_ksg import compute_transfer_entropy_ksg

    assert callable(compute_transfer_entropy_ksg)
