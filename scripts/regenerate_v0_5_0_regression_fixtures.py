"""Regenerate v0.5.0 regression fixture files.

Run once before committing; the test suite loads the saved fixtures
for bit-identical (or near-identical) replay checks.

Usage:
    uv run python scripts/regenerate_v0_5_0_regression_fixtures.py

Output:
    docs/fixtures/v0_5_0_regression/{name}_fixture.json
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
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
_FORECASTABILITY_VERSION = "0.5.0-dev"


# ---------------------------------------------------------------------------
# Series generators
# ---------------------------------------------------------------------------


def _make_ar1() -> np.ndarray:
    return generate_ar1(n_samples=500, phi=0.7, random_state=42)


def _make_white_noise() -> np.ndarray:
    return generate_white_noise(n_samples=500, random_state=42)


def _make_sine_plus_ar1() -> np.ndarray:
    sine = generate_sine_wave(n_samples=500, cycles=12.0, noise_std=0.05, random_state=42)
    ar1 = generate_ar1(n_samples=500, phi=0.5, random_state=43)
    return sine + 0.3 * ar1


def _make_henon_map() -> np.ndarray:
    return generate_henon_map(n_samples=500)


# ---------------------------------------------------------------------------
# Compute curves
# ---------------------------------------------------------------------------


def _ksg2_curve(series: np.ndarray) -> list[float]:
    """Compute KSG-II AMI curve (median across k_list) for univariate series."""
    kernel = KSG2CurveKernel()
    result = kernel.estimate_curve(series, lag_range=_LAG_RANGE)
    # result shape (H, len(k_list)); median across k_list axis
    return np.median(result, axis=1).tolist()


def _ksg1_curve(series: np.ndarray) -> list[float]:
    """Compute KSG-I AMI curve for univariate series."""
    kernel = Ksg1SklearnKernel()
    result = kernel.estimate_curve(series, lag_range=_LAG_RANGE)
    return result.tolist()


def _save_fixture(name: str, data: dict[str, object]) -> None:
    _FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    path = _FIXTURES_DIR / f"{name}_fixture.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# Univariate series fixtures
# ---------------------------------------------------------------------------


def _build_univariate_fixture(name: str, series: np.ndarray) -> None:
    print(f"Building fixture: {name}")
    ksg2 = _ksg2_curve(series)
    ksg1 = _ksg1_curve(series)
    _save_fixture(
        name,
        {
            "series_name": name,
            "lag_range": _LAG_RANGE,
            "ksg2_ami_curve": ksg2,
            "ksg1_ami_curve": ksg1,
            "generated_with": "regenerate_v0_5_0_regression_fixtures.py",
            "forecastability_version": _FORECASTABILITY_VERSION,
        },
    )


# ---------------------------------------------------------------------------
# Anisotropic bivariate fixture
# ---------------------------------------------------------------------------


def _build_anisotropic_fixture() -> None:
    """Build fixture for bivariate anisotropic pair (X, Y) with sigma_x=1, sigma_y=10, rho=0.5."""
    name = "anisotropic_ar1"
    print(f"Building fixture: {name}")
    N = 500
    rho = 0.5
    rng = np.random.default_rng(42)
    Z1 = rng.standard_normal(N)
    Z2 = rng.standard_normal(N)
    X = Z1  # sigma_x = 1
    Y = 10.0 * (rho * Z1 + np.sqrt(1.0 - rho**2) * Z2)  # sigma_y = 10

    true_mi = -0.5 * float(np.log(1.0 - rho**2))

    # KSG-II
    k = 5
    joint = np.column_stack([X, Y])
    tree = cKDTree(joint, leafsize=16)
    _, indices = tree.query(joint, k=k + 1, p=np.inf)
    nn_idx = indices[:, 1 : k + 1]
    x_sorted = np.sort(X)
    y_sorted = np.sort(Y)
    mi_ksg2 = float(
        _ksg2_single_k_vectorized(
            X,
            Y,
            k=k,
            neighbor_indices=nn_idx,
            x_sorted=x_sorted,
            y_sorted=y_sorted,
        )
    )

    # KSG-I
    mi_ksg1 = float(mutual_info_regression(X.reshape(-1, 1), Y, n_neighbors=k, random_state=42)[0])

    _save_fixture(
        name,
        {
            "series_name": name,
            "description": "bivariate anisotropic: sigma_x=1, sigma_y=10, rho=0.5",
            "N": N,
            "rho": rho,
            "k": k,
            "true_mi": true_mi,
            "mi_ksg2": mi_ksg2,
            "mi_ksg1": mi_ksg1,
            "generated_with": "regenerate_v0_5_0_regression_fixtures.py",
            "forecastability_version": _FORECASTABILITY_VERSION,
        },
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Generate all v0.5.0 regression fixtures."""
    print(f"Writing fixtures to: {_FIXTURES_DIR}")

    _build_univariate_fixture("ar1", _make_ar1())
    _build_univariate_fixture("white_noise", _make_white_noise())
    _build_univariate_fixture("sine_plus_ar1", _make_sine_plus_ar1())
    _build_univariate_fixture("henon_map", _make_henon_map())
    _build_anisotropic_fixture()

    print("Done. Commit the generated fixture files.")


if __name__ == "__main__":
    main()
