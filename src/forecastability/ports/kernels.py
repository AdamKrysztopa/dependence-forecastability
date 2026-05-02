"""Kernel-provider Protocols for optional native acceleration (PBE-F15).

Core package exposes these runtime-checkable Protocols so out-of-tree plugins
(e.g. ``dependence-forecastability-accel``) can register curve-level kernel
implementations via the ``forecastability.kernels`` entry-point group.

Pure-Python code remains the default and the authoritative parity oracle.
No Rust, Cython, or native code ships in this package.

Usage
-----
Plugins register a callable or factory via the ``forecastability.kernels``
entry-point group in their distribution's ``pyproject.toml``::

    [project.entry-points."forecastability.kernels"]
    accel = "dependence_forecastability_accel:get_provider"

The core package discovers and validates plugins at import time::

    from forecastability.ports.kernels import load_kernel_provider
    provider = load_kernel_provider()   # None if no plugin installed

Design notes
------------
- The native boundary is **curve-level**, not the scalar ``DependenceScorer``
  callback.  Scalar callbacks cross Python too often and erase most native
  benefit.
- All ``random_state`` parameters are ``int``, never ``numpy.Generator``.
- Plugins must reject ``n_surrogates < 99`` before any allocation.
- The loader rejects providers whose ``metadata.deterministic`` is ``False``.
"""

from __future__ import annotations

from importlib.metadata import entry_points
from typing import Protocol, runtime_checkable

import numpy as np
from pydantic import BaseModel, ConfigDict

__all__ = [
    "KernelProvider",
    "KernelProviderError",
    "KernelProviderMetadata",
    "Ksg2ProfileKernel",
    "LagDesignKernel",
    "LinearResidualizeKernel",
    "PhaseSurrogateKernel",
    "load_kernel_provider",
]

# ---------------------------------------------------------------------------
# Individual kernel Protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class PhaseSurrogateKernel(Protocol):
    """Curve-level phase-surrogate generator.

    Produces ``n_surrogates`` rows of phase-randomised surrogates for ``arr``
    using a fixed seed.  The returned array has shape
    ``(n_surrogates, arr.size)``.

    Keyword-only arguments match the existing
    ``forecastability.diagnostics.surrogates.phase_surrogates`` signature.
    Native implementations must reject ``n_surrogates < 99`` before any
    allocation.
    """

    def phase_surrogates(
        self,
        arr: np.ndarray,
        *,
        n_surrogates: int,
        random_state: int,
    ) -> np.ndarray: ...


@runtime_checkable
class LagDesignKernel(Protocol):
    """Curve-level lagged design-matrix builder.

    Returns a 2-D array of shape ``(n_rows, lag)`` suitable for residual
    regression at a given lag depth.  ``series`` is 1-D; ``lag >= 1``.
    """

    def lag_design(
        self,
        series: np.ndarray,
        lag: int,
    ) -> np.ndarray: ...


@runtime_checkable
class LinearResidualizeKernel(Protocol):
    """Curve-level linear residualizer (OLS).

    Residualizes ``y`` against ``z`` (the design matrix) using ordinary least
    squares, optionally with an intercept.  Returns residuals of shape
    ``(y.shape[0],)``.

    Parity oracle: ``sklearn.linear_model.LinearRegression`` with default
    settings; ``residuals = y - model.predict(z)``.  Native implementations
    must reproduce degenerate matrix behaviour (rank-deficient ``z``) by
    falling back to a minimum-norm solution (equivalent to ``np.linalg.lstsq``
    with ``rcond=None``).
    """

    def linear_residualize(
        self,
        z: np.ndarray,
        y: np.ndarray,
        *,
        fit_intercept: bool,
    ) -> np.ndarray: ...


@runtime_checkable
class Ksg2ProfileKernel(Protocol):
    """Curve-level KSG-II mutual-information profile.

    Returns a 1-D array of shape ``(max_horizon,)`` where index ``h - 1`` is
    the AMI estimate for lag ``h``.  Uses the KSG algorithm-2 digamma identity
    with Chebyshev metric, one-shot jitter, and median over ``k_list``.

    Parity requirements (see §3.7 of the performance plan):

    - ``ε`` via ``searchsorted(side='right', x+ε) - searchsorted(side='left',
      x-ε) - 1`` with self-exclusion at ``[1:k+1]``.
    - KSG-II digamma identity:
      ``ψ(k) - 1/k + ψ(N) - mean(ψ(nx) + ψ(ny))``.
    - One-shot jitter using ``jitter_seed``; ``seed + 1`` offset for phase
      surrogates.
    - Median over ``k_list``; ``NaN`` for invalid/underdetermined horizons.
    - ``SeedSequence(random_state).spawn(n_surrogates)`` for shuffle seeds.
    - ``nanmean`` for shuffle bias; ``nanpercentile(90)`` for ``tau``.
    - ``corrected = max(raw - bias, 0)`` applied only on ``valid_mask``.
    """

    def ksg2_profile(
        self,
        series: np.ndarray,
        k_list: list[int],
        max_horizon: int,
        jitter_seed: int,
    ) -> np.ndarray: ...


# ---------------------------------------------------------------------------
# Composite KernelProvider Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class KernelProvider(Protocol):
    """Composite Protocol for a full optional native kernel provider.

    A conforming plugin must implement all four curve-level kernel methods,
    expose a ``metadata`` property returning :class:`KernelProviderMetadata`,
    and provide ``peak_memory_model_bytes`` so the loader can enforce memory
    budgets.

    The loader (:func:`load_kernel_provider`) validates providers with
    ``isinstance(impl, KernelProvider)`` and rejects non-conforming objects
    and providers whose ``metadata.deterministic`` is ``False``.

    Any conforming ``KernelProvider`` also satisfies each of the four
    individual kernel Protocols (:class:`PhaseSurrogateKernel`,
    :class:`LagDesignKernel`, :class:`LinearResidualizeKernel`,
    :class:`Ksg2ProfileKernel`) structurally.
    """

    @property
    def metadata(self) -> KernelProviderMetadata: ...

    def peak_memory_model_bytes(
        self,
        *,
        n_surrogates: int,
        max_lag: int,
        n_drivers: int,
        n_workers: int,
    ) -> int:
        """Return the declared peak working-set in bytes for the given params.

        The loader may refuse to enable a kernel whose declared envelope
        exceeds a configured memory budget.
        """
        ...

    def phase_surrogates(
        self,
        arr: np.ndarray,
        *,
        n_surrogates: int,
        random_state: int,
    ) -> np.ndarray: ...

    def lag_design(
        self,
        series: np.ndarray,
        lag: int,
    ) -> np.ndarray: ...

    def linear_residualize(
        self,
        z: np.ndarray,
        y: np.ndarray,
        *,
        fit_intercept: bool,
    ) -> np.ndarray: ...

    def ksg2_profile(
        self,
        series: np.ndarray,
        k_list: list[int],
        max_horizon: int,
        jitter_seed: int,
    ) -> np.ndarray: ...


# ---------------------------------------------------------------------------
# Provider metadata model
# ---------------------------------------------------------------------------


class KernelProviderMetadata(BaseModel):
    """Static, serialisable metadata declared by a kernel provider.

    Fields
    ------
    name:
        Short identifier for the provider distribution (e.g.
        ``"dependence-forecastability-accel"``).
    version:
        PEP 440 version string reported by the distribution.
    deterministic:
        ``True`` iff the provider guarantees bit-identical outputs for
        identical inputs and seeds across platforms and worker counts.
        The loader rejects providers whose ``deterministic`` flag is
        ``False``.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    version: str
    deterministic: bool


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


class KernelProviderError(RuntimeError):
    """Raised when a registered kernel provider fails validation."""


def load_kernel_provider() -> KernelProvider | None:
    """Discover and validate the first registered kernel provider.

    Scans the ``forecastability.kernels`` entry-point group for registered
    providers.  Returns ``None`` if no entry points are registered (pure-Python
    fallback remains active).

    Only the first registered entry point is loaded.  If multiple providers
    are registered the selection order is determined by the Python packaging
    environment and is not guaranteed to be stable.

    Parameters
    ----------
    (none)

    Returns
    -------
    KernelProvider | None
        The validated provider, or ``None`` if no plugin is installed.

    Raises
    ------
    KernelProviderError
        If a registered entry point loads successfully but the resulting
        object does not conform to :class:`KernelProvider`, reports
        ``metadata.deterministic=False``, or raises an exception during
        import.
    """
    eps = entry_points(group="forecastability.kernels")
    if not eps:
        return None

    ep = next(iter(eps))
    try:
        factory = ep.load()
        impl: object = factory() if callable(factory) else factory
    except Exception as exc:  # noqa: BLE001
        raise KernelProviderError(
            f"Failed to load kernel provider from entry point {ep.name!r}: {exc}"
        ) from exc

    if not isinstance(impl, KernelProvider):
        raise KernelProviderError(
            f"Kernel provider {ep.name!r} does not conform to the KernelProvider "
            f"Protocol. Got {type(impl)!r}. Ensure the provider implements all of: "
            "metadata, peak_memory_model_bytes, phase_surrogates, lag_design, "
            "linear_residualize, ksg2_profile."
        )

    meta: KernelProviderMetadata = impl.metadata
    if not meta.deterministic:
        raise KernelProviderError(
            f"Kernel provider {ep.name!r} ({meta.name} {meta.version}) "
            "reports deterministic=False and cannot be used. Only deterministic "
            "providers are accepted to preserve forecastability reproducibility."
        )

    return impl
