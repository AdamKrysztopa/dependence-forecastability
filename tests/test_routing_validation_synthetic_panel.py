"""Tests for the phase-0 synthetic routing-validation archetype panel."""

from __future__ import annotations

import hashlib

import numpy as np

from forecastability.utils.synthetic import (
    ExpectedFamilyMetadata,
    generate_routing_validation_archetypes,
)


def _digest_first32(series: np.ndarray) -> str:
    first = np.asarray(series[:32], dtype=np.float64)
    return hashlib.sha256(first.tobytes()).hexdigest()


_STABLE_FIRST32_DIGESTS: dict[str, str] = {
    "white_noise": "0bd0cf25abf854961fd834d249d71b1e896c4f13b44bc106526b19c3f15719b4",
    "ar1": "87303bf0123cad6bdde7cc9d3cee96ab03b174047c29c4201b379d592a671272",
    "weak_seasonal_near_threshold": (
        "f368c7a4ff4da917bd8eea08110772f7dca445fb3ebe89e561f2b21032e87a88"
    ),
    "nonlinear_mixed": "f5d0d98a995a39c755b5152bec54b892427165dd9c673f49a73f55109e40d67e",
    "structural_break": "297e35093acf84791b835fba806055422301b510e2e07006908b6b885a82f54e",
    "mediated_low_directness": ("8a41240ff0ef078406904df914d5587bce09141b33158d687d46a72a7300474f"),
    "exogenous_driven": "e6e9f9af3755e1a8f12dbd32422213b11924d57a3bb2849641100d0770bf5a8d",
    "low_directness_high_penalty": (
        "3036277312ad75de7e5cb576f2902055c4780a214d8807833bcbea487888e045"
    ),
}

_FLOAT_REGRESSION_FIRST32: dict[str, np.ndarray] = {
    "seasonal": np.array(
        [
            0.5060869565129978,
            0.5358067988740985,
            0.9803888760018692,
            1.3977618381248624,
            1.1545107813032278,
            0.7026347786556932,
            -0.13270970430225548,
            -0.8566057427939522,
            -0.7343662901167946,
            -1.179185828342098,
            -0.5764932008597625,
            -0.4260609431822291,
            -0.26085302308209507,
            0.5937038419944061,
            1.1142385699660002,
            1.0621320406984778,
            0.5921262195029614,
            0.5918151498855859,
            0.1249505966524585,
            -0.21149941840824432,
            -0.6133133558537174,
            -1.3178901295386853,
            -1.0402453784554748,
            -0.28800040521633496,
            -0.5941875107294913,
            0.7720300838438289,
            0.5722179428671895,
            0.8523785246404484,
            1.371194380771644,
            0.4774309892605878,
            -0.10565770077833536,
            -0.4015054138879778,
        ],
        dtype=np.float64,
    ),
    "long_memory": np.array(
        [
            -0.8638735430281241,
            0.757361723289665,
            -0.05363748810634581,
            1.123507846900335,
            0.14198203364550296,
            -1.196736289650434,
            0.37684488094212154,
            -0.8958284259803183,
            -0.05629614964978497,
            0.8506303712192461,
            0.6655851244218142,
            0.3263870365584842,
            -1.1544786211544706,
            -0.48175133905265094,
            -1.1705023190365338,
            0.7862132137492678,
            0.40366401078263225,
            0.7474322644705138,
            1.1239995032856176,
            0.5785495631630129,
            -0.3705990420180222,
            -0.2466827487390262,
            -0.30019368809891056,
            -0.9470010204818033,
            -0.30600800558868024,
            -1.196681002641367,
            -0.44438455222842527,
            -0.7418164716605623,
            -0.526801617871915,
            1.9747791109787372,
            -0.2869372435143253,
            0.7099857705236456,
        ],
        dtype=np.float64,
    ),
}


def test_routing_validation_archetype_panel_has_expected_cases() -> None:
    """Phase-0 synthetic panel must expose all ten canonical archetypes."""
    panel = generate_routing_validation_archetypes(n=128, seed=42)
    assert set(panel.keys()) == {
        "white_noise",
        "ar1",
        "seasonal",
        "weak_seasonal_near_threshold",
        "nonlinear_mixed",
        "structural_break",
        "long_memory",
        "mediated_low_directness",
        "exogenous_driven",
        "low_directness_high_penalty",
    }


def test_routing_validation_archetypes_return_typed_metadata() -> None:
    """Every panel row must return (series, ExpectedFamilyMetadata)."""
    panel = generate_routing_validation_archetypes(n=96, seed=42)

    for series, metadata in panel.values():
        assert isinstance(series, np.ndarray)
        assert isinstance(metadata, ExpectedFamilyMetadata)
        assert len(series) == 96
        assert metadata.expected_primary_families


def test_routing_validation_archetype_panel_is_deterministic_by_seed() -> None:
    """Panel outputs must be deterministic for identical seed and n."""
    first = generate_routing_validation_archetypes(n=128, seed=7)
    second = generate_routing_validation_archetypes(n=128, seed=7)

    for key in first:
        first_series, first_meta = first[key]
        second_series, second_meta = second[key]
        assert np.array_equal(first_series, second_series)
        assert first_meta == second_meta


def test_routing_validation_archetype_first32_fingerprints() -> None:
    """Freeze first-32 samples while tolerating platform-level float drift.

    Exact byte digests remain appropriate for the byte-stable archetypes. The
    seasonal and long-memory generators include transcendental or reduction
    steps that can move by a few ulps across platforms, so those two cases use
    tight float64 regression checks instead.
    """
    panel = generate_routing_validation_archetypes(n=128, seed=42)

    for key, expected_digest in _STABLE_FIRST32_DIGESTS.items():
        assert _digest_first32(panel[key][0]) == expected_digest

    for key, expected_values in _FLOAT_REGRESSION_FIRST32.items():
        observed = np.asarray(panel[key][0][:32], dtype=np.float64)
        np.testing.assert_allclose(observed, expected_values, rtol=1e-12, atol=1e-12)
