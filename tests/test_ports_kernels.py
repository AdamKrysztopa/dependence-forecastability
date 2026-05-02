"""Tests for forecastability.ports.kernels — Protocol conformance and loader (PBE-F15)."""

from __future__ import annotations

import numpy as np
import pydantic
import pytest

from forecastability.ports.kernels import (
    KernelProvider,
    KernelProviderError,
    KernelProviderMetadata,
    Ksg2ProfileKernel,
    LagDesignKernel,
    LinearResidualizeKernel,
    PhaseSurrogateKernel,
    load_kernel_provider,
)

# ---------------------------------------------------------------------------
# Minimal conforming implementations for Protocol structural checks
# ---------------------------------------------------------------------------


class _GoodPhaseSurrogate:
    def phase_surrogates(
        self,
        arr: np.ndarray,
        *,
        n_surrogates: int,
        random_state: int,
    ) -> np.ndarray:
        return np.zeros((n_surrogates, arr.size))


class _GoodLagDesign:
    def lag_design(
        self,
        series: np.ndarray,
        lag: int,
    ) -> np.ndarray:
        return np.zeros((series.size - lag, lag))


class _GoodLinearResidualize:
    def linear_residualize(
        self,
        z: np.ndarray,
        y: np.ndarray,
        *,
        fit_intercept: bool,
    ) -> np.ndarray:
        return np.zeros_like(y)


class _GoodKsg2Profile:
    def ksg2_profile(
        self,
        series: np.ndarray,
        k_list: list[int],
        max_horizon: int,
        jitter_seed: int,
    ) -> np.ndarray:
        return np.zeros(max_horizon)


class _GoodKernelProvider:
    """Full conforming KernelProvider implementation."""

    @property
    def metadata(self) -> KernelProviderMetadata:
        return KernelProviderMetadata(
            name="test-provider",
            version="0.0.1",
            deterministic=True,
        )

    def peak_memory_model_bytes(
        self,
        *,
        n_surrogates: int,
        max_lag: int,
        n_drivers: int,
        n_workers: int,
    ) -> int:
        return 0

    def phase_surrogates(
        self,
        arr: np.ndarray,
        *,
        n_surrogates: int,
        random_state: int,
    ) -> np.ndarray:
        return np.zeros((n_surrogates, arr.size))

    def lag_design(
        self,
        series: np.ndarray,
        lag: int,
    ) -> np.ndarray:
        return np.zeros((series.size - lag, lag))

    def linear_residualize(
        self,
        z: np.ndarray,
        y: np.ndarray,
        *,
        fit_intercept: bool,
    ) -> np.ndarray:
        return np.zeros_like(y)

    def ksg2_profile(
        self,
        series: np.ndarray,
        k_list: list[int],
        max_horizon: int,
        jitter_seed: int,
    ) -> np.ndarray:
        return np.zeros(max_horizon)


class _NonDeterministicProvider(_GoodKernelProvider):
    @property
    def metadata(self) -> KernelProviderMetadata:
        return KernelProviderMetadata(
            name="non-det-provider",
            version="0.0.1",
            deterministic=False,
        )


class _MissingMethodProvider:
    """Has ``metadata`` but missing all kernel methods — not a KernelProvider."""

    @property
    def metadata(self) -> KernelProviderMetadata:
        return KernelProviderMetadata(
            name="bad-provider",
            version="0.0.1",
            deterministic=True,
        )


class _EmptyClass:
    """Has no relevant attributes at all."""


# ---------------------------------------------------------------------------
# Individual kernel Protocol isinstance checks
# ---------------------------------------------------------------------------


def test_phase_surrogate_kernel_isinstance() -> None:
    assert isinstance(_GoodPhaseSurrogate(), PhaseSurrogateKernel)


def test_lag_design_kernel_isinstance() -> None:
    assert isinstance(_GoodLagDesign(), LagDesignKernel)


def test_linear_residualize_kernel_isinstance() -> None:
    assert isinstance(_GoodLinearResidualize(), LinearResidualizeKernel)


def test_ksg2_profile_kernel_isinstance() -> None:
    assert isinstance(_GoodKsg2Profile(), Ksg2ProfileKernel)


def test_empty_class_is_not_phase_surrogate_kernel() -> None:
    assert not isinstance(_EmptyClass(), PhaseSurrogateKernel)


def test_empty_class_is_not_lag_design_kernel() -> None:
    assert not isinstance(_EmptyClass(), LagDesignKernel)


def test_empty_class_is_not_linear_residualize_kernel() -> None:
    assert not isinstance(_EmptyClass(), LinearResidualizeKernel)


def test_empty_class_is_not_ksg2_profile_kernel() -> None:
    assert not isinstance(_EmptyClass(), Ksg2ProfileKernel)


# ---------------------------------------------------------------------------
# KernelProvider composite Protocol isinstance checks
# ---------------------------------------------------------------------------


def test_good_kernel_provider_isinstance() -> None:
    assert isinstance(_GoodKernelProvider(), KernelProvider)


def test_missing_method_provider_is_not_kernel_provider() -> None:
    """Provider with only metadata and no kernel methods is non-conforming."""
    assert not isinstance(_MissingMethodProvider(), KernelProvider)


def test_empty_class_is_not_kernel_provider() -> None:
    assert not isinstance(_EmptyClass(), KernelProvider)


def test_good_kernel_provider_satisfies_individual_kernel_protocols() -> None:
    """A KernelProvider conformer also satisfies each individual kernel Protocol."""
    impl = _GoodKernelProvider()
    assert isinstance(impl, PhaseSurrogateKernel)
    assert isinstance(impl, LagDesignKernel)
    assert isinstance(impl, LinearResidualizeKernel)
    assert isinstance(impl, Ksg2ProfileKernel)


# ---------------------------------------------------------------------------
# KernelProviderMetadata model
# ---------------------------------------------------------------------------


def test_metadata_fields() -> None:
    meta = KernelProviderMetadata(name="accel", version="0.1.2", deterministic=True)
    assert meta.name == "accel"
    assert meta.version == "0.1.2"
    assert meta.deterministic is True


def test_metadata_is_frozen() -> None:
    meta = KernelProviderMetadata(name="x", version="1.0.0", deterministic=True)
    with pytest.raises((TypeError, ValueError, pydantic.ValidationError)):
        meta.name = "y"


def test_metadata_deterministic_false_is_valid_model() -> None:
    """The Pydantic model itself accepts deterministic=False; the loader rejects it."""
    meta = KernelProviderMetadata(name="x", version="1.0.0", deterministic=False)
    assert meta.deterministic is False


# ---------------------------------------------------------------------------
# load_kernel_provider: no entry points → returns None
# ---------------------------------------------------------------------------


def test_load_returns_none_when_no_entry_points(monkeypatch: pytest.MonkeyPatch) -> None:
    import forecastability.ports.kernels as kernels_mod

    monkeypatch.setattr(kernels_mod, "entry_points", lambda **_: [])
    result = load_kernel_provider()
    assert result is None


# ---------------------------------------------------------------------------
# load_kernel_provider: conforming deterministic provider → returned
# ---------------------------------------------------------------------------


def test_load_returns_conforming_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    import forecastability.ports.kernels as kernels_mod

    provider_instance = _GoodKernelProvider()

    class _FakeEP:
        name = "good"

        def load(self) -> _GoodKernelProvider:
            return provider_instance

    monkeypatch.setattr(kernels_mod, "entry_points", lambda **_: [_FakeEP()])
    result = load_kernel_provider()
    assert result is provider_instance


def test_load_accepts_factory_callable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Entry point may be a factory callable that is called to produce the provider."""
    import forecastability.ports.kernels as kernels_mod

    class _FakeEP:
        name = "factory"

        def load(self) -> type[_GoodKernelProvider]:
            return _GoodKernelProvider

    monkeypatch.setattr(kernels_mod, "entry_points", lambda **_: [_FakeEP()])
    result = load_kernel_provider()
    assert isinstance(result, _GoodKernelProvider)


# ---------------------------------------------------------------------------
# load_kernel_provider: non-conforming provider → KernelProviderError
# ---------------------------------------------------------------------------


def test_load_raises_for_non_conforming_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import forecastability.ports.kernels as kernels_mod

    class _FakeEP:
        name = "bad"

        def load(self) -> _MissingMethodProvider:
            return _MissingMethodProvider()

    monkeypatch.setattr(kernels_mod, "entry_points", lambda **_: [_FakeEP()])
    with pytest.raises(KernelProviderError, match="does not conform"):
        load_kernel_provider()


# ---------------------------------------------------------------------------
# load_kernel_provider: non-deterministic provider → KernelProviderError
# ---------------------------------------------------------------------------


def test_load_raises_for_non_deterministic_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import forecastability.ports.kernels as kernels_mod

    class _FakeEP:
        name = "non-det"

        def load(self) -> _NonDeterministicProvider:
            return _NonDeterministicProvider()

    monkeypatch.setattr(kernels_mod, "entry_points", lambda **_: [_FakeEP()])
    with pytest.raises(KernelProviderError, match="deterministic=False"):
        load_kernel_provider()


# ---------------------------------------------------------------------------
# load_kernel_provider: entry point load failure → KernelProviderError
# ---------------------------------------------------------------------------


def test_load_raises_on_entry_point_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import forecastability.ports.kernels as kernels_mod

    class _FakeEP:
        name = "broken"

        def load(self) -> None:
            raise ImportError("no module named accel")

    monkeypatch.setattr(kernels_mod, "entry_points", lambda **_: [_FakeEP()])
    with pytest.raises(KernelProviderError, match="Failed to load"):
        load_kernel_provider()


def test_load_raises_on_entry_point_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import forecastability.ports.kernels as kernels_mod

    class _FakeEP:
        name = "crash"

        def load(self) -> None:
            raise RuntimeError("plugin initialization failed")

    monkeypatch.setattr(kernels_mod, "entry_points", lambda **_: [_FakeEP()])
    with pytest.raises(KernelProviderError, match="Failed to load"):
        load_kernel_provider()


# ---------------------------------------------------------------------------
# KernelProviderError is a RuntimeError subclass
# ---------------------------------------------------------------------------


def test_kernel_provider_error_is_runtime_error() -> None:
    err = KernelProviderError("test")
    assert isinstance(err, RuntimeError)


# ---------------------------------------------------------------------------
# Imports from forecastability.ports re-export kernel symbols
# ---------------------------------------------------------------------------


def test_kernel_symbols_importable_from_ports() -> None:
    from forecastability.ports import (  # noqa: F401  (smoke import)
        KernelProvider,
        KernelProviderError,
        KernelProviderMetadata,
        Ksg2ProfileKernel,
        LagDesignKernel,
        LinearResidualizeKernel,
        PhaseSurrogateKernel,
        load_kernel_provider,
    )
