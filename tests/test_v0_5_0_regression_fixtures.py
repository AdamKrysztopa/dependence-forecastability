"""RVH-F14: Regression fixture tests for v0.5.0.

Verifies that current code reproduces committed fixture values within tight
numerical tolerances:
  - KSG-II: atol=1e-7  (deterministic scipy cKDTree + numpy searchsorted)
  - KSG-I : atol=1e-6  (sklearn has minor float-order variability)

If fixtures are absent the tests skip gracefully. Run
    uv run python scripts/regenerate_v0_5_0_regression_fixtures.py
to generate them, then commit the JSON files.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial import cKDTree  # type: ignore[attr-defined]
from sklearn.feature_selection import mutual_info_regression

from forecastability.kernels.ksg1_sklearn_kernel import Ksg1SklearnKernel
from forecastability.kernels.ksg2_curve_kernel import (
    KSG2CurveKernel,
    _ksg2_single_k_vectorized,
)
from forecastability.utils.datasets import (
    generate_ar1,
    generate_henon_map,
    generate_sine_wave,
    generate_white_noise,
)

_FIXTURES_DIR = Path(__file__).parent.parent / "docs" / "fixtures" / "v0_5_0_regression"
_LAG_RANGE = 10


# ---------------------------------------------------------------------------
# Fixture loader
# ---------------------------------------------------------------------------


def _load_fixture(name: str) -> dict[str, float | int | str | list[float]]:
    """Load a named fixture JSON, skipping gracefully if absent.

    Returns a dict with string keys and typed scalar/list values as stored
    by the regeneration script.  The caller is responsible for narrowing
    individual values to the expected type.
    """
    path = _FIXTURES_DIR / f"{name}_fixture.json"
    if not path.exists():
        pytest.skip(
            f"Fixture not found: {path}. "
            "Run scripts/regenerate_v0_5_0_regression_fixtures.py first."
        )
    with open(path, encoding="utf-8") as f:
        raw: dict[str, float | int | str | list[float]] = json.load(f)
    return raw


# ---------------------------------------------------------------------------
# Series generators (must match regenerate script exactly)
# ---------------------------------------------------------------------------


def _series_for(name: str) -> np.ndarray:
    """Reproduce the series exactly as in the regeneration script."""
    if name == "ar1":
        return generate_ar1(n_samples=500, phi=0.7, random_state=42)
    if name == "white_noise":
        return generate_white_noise(n_samples=500, random_state=42)
    if name == "sine_plus_ar1":
        sine = generate_sine_wave(n_samples=500, cycles=12.0, noise_std=0.05, random_state=42)
        ar1 = generate_ar1(n_samples=500, phi=0.5, random_state=43)
        return sine + 0.3 * ar1
    if name == "henon_map":
        return generate_henon_map(n_samples=500)
    raise ValueError(f"Unknown series name: {name!r}")


# ---------------------------------------------------------------------------
# KSG-II curve regression
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("series_name", ["ar1", "white_noise", "sine_plus_ar1", "henon_map"])
def test_ksg2_curve_matches_fixture(series_name: str) -> None:
    """KSG-II AMI curve reproduces committed fixture values (atol=1e-7)."""
    fixture = _load_fixture(series_name)
    expected = np.array(fixture["ksg2_ami_curve"], dtype=float)

    series = _series_for(series_name)
    kernel = KSG2CurveKernel()
    raw = kernel.estimate_curve(series, lag_range=_LAG_RANGE)
    actual = np.median(raw, axis=1)

    np.testing.assert_allclose(
        actual,
        expected,
        atol=1e-7,
        err_msg=(
            f"KSG-II curve for '{series_name}' diverged from fixture. "
            "If this is an intentional algorithm change, re-run "
            "scripts/regenerate_v0_5_0_regression_fixtures.py and commit."
        ),
    )


# ---------------------------------------------------------------------------
# KSG-I curve regression
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("series_name", ["ar1", "white_noise"])
def test_ksg1_curve_matches_fixture(series_name: str) -> None:
    """KSG-I AMI curve reproduces committed fixture values (atol=1e-6)."""
    fixture = _load_fixture(series_name)
    expected = np.array(fixture["ksg1_ami_curve"], dtype=float)

    series = _series_for(series_name)
    kernel = Ksg1SklearnKernel()
    actual = kernel.estimate_curve(series, lag_range=_LAG_RANGE)

    np.testing.assert_allclose(
        actual,
        expected,
        atol=1e-6,
        err_msg=(
            f"KSG-I curve for '{series_name}' diverged from fixture. "
            "If this is an intentional sklearn version change, re-run "
            "scripts/regenerate_v0_5_0_regression_fixtures.py and commit."
        ),
    )


# ---------------------------------------------------------------------------
# Anisotropic KSG-II vs KSG-I disagreement fixture
# ---------------------------------------------------------------------------


def test_anisotropic_ksg2_ksg1_disagreement_fixture() -> None:
    """KSG-II and KSG-I disagree by > 10% on anisotropic bivariate series.

    Reproduces the 'anisotropic_ar1' fixture and verifies the fixture's stored
    disagreement value, and that the disagreement is > 10% relative to true_mi.
    """
    fixture = _load_fixture("anisotropic_ar1")

    def _f(key: str) -> float:
        """Narrow a fixture value to float."""
        v = fixture[key]
        assert isinstance(v, (int, float)), f"fixture[{key!r}] is not numeric: {v!r}"
        return float(v)

    def _i(key: str) -> int:
        """Narrow a fixture value to int."""
        v = fixture[key]
        assert isinstance(v, (int, float)), f"fixture[{key!r}] is not numeric: {v!r}"
        return int(v)

    true_mi = _f("true_mi")
    stored_mi_ksg2 = _f("mi_ksg2")
    stored_mi_ksg1 = _f("mi_ksg1")

    # Reproduce the same bivariate sample
    N = _i("N")
    rho = _f("rho")
    k = _i("k")
    rng = np.random.default_rng(42)
    Z1 = rng.standard_normal(N)
    Z2 = rng.standard_normal(N)
    X = Z1
    Y = 10.0 * (rho * Z1 + np.sqrt(1.0 - rho**2) * Z2)

    # KSG-II
    joint = np.column_stack([X, Y])
    tree = cKDTree(joint, leafsize=16)
    _, indices = tree.query(joint, k=k + 1, p=np.inf)
    nn_idx = indices[:, 1 : k + 1]
    x_sorted = np.sort(X)
    y_sorted = np.sort(Y)
    mi_ksg2 = float(
        _ksg2_single_k_vectorized(
            X, Y, k=k, neighbor_indices=nn_idx, x_sorted=x_sorted, y_sorted=y_sorted
        )
    )

    # KSG-I
    mi_ksg1 = float(mutual_info_regression(X.reshape(-1, 1), Y, n_neighbors=k, random_state=42)[0])

    # Values match stored fixture (tight tolerance: deterministic RNG)
    assert abs(mi_ksg2 - stored_mi_ksg2) < 1e-7, (
        f"Reproduced KSG-II ({mi_ksg2:.6f}) differs from fixture ({stored_mi_ksg2:.6f})"
    )
    assert abs(mi_ksg1 - stored_mi_ksg1) < 1e-6, (
        f"Reproduced KSG-I ({mi_ksg1:.6f}) differs from fixture ({stored_mi_ksg1:.6f})"
    )

    # Disagreement: at least one estimator is > 10% off from true_mi
    err_ksg2 = abs(mi_ksg2 - true_mi) / true_mi
    err_ksg1 = abs(mi_ksg1 - true_mi) / true_mi
    assert max(err_ksg2, err_ksg1) > 0.10, (
        f"Expected KSG-II vs KSG-I disagreement > 10% on anisotropic data. "
        f"err_ksg2={err_ksg2:.3%}, err_ksg1={err_ksg1:.3%}. "
        "Re-run regenerate script if series parameters changed."
    )
