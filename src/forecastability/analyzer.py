"""Method-independent class API for forecastability analysis.

Supports AMI/pAMI (backward compatible) and an extensible scorer registry
for MI, Pearson, Spearman, Kendall, and distance correlation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import matplotlib.pyplot as plt
import numpy as np

from forecastability.metrics import (
    compute_ami,
    compute_pami_linear_residual,
)
from forecastability.scorers import (
    DependenceScorer,
    ScorerInfo,
    default_registry,
)

# ---------------------------------------------------------------------------
# Service imports — thin wrappers kept here for backward-compat internal calls
# ---------------------------------------------------------------------------
from forecastability.services.partial_curve_service import (
    compute_partial_curve as _compute_partial_curve,
)
from forecastability.services.plot_service import _plot_curve
from forecastability.services.raw_curve_service import (
    compute_raw_curve as _compute_raw_curve,
)
from forecastability.services.recommendation_service import (
    _triage_recommendation,
    _validate_exog_for_target,
)
from forecastability.services.significance_service import (
    compute_significance_bands_generic,
)
from forecastability.state import AnalyzerState
from forecastability.surrogates import compute_significance_bands
from forecastability.validation import validate_time_series


@dataclass(slots=True)
class AnalyzeResult:
    """Container returned by :meth:`ForecastabilityAnalyzer.analyze`.

    Attributes:
        raw: Raw dependence curve (AMI when method is ``"mi"``).
        partial: Partial dependence curve (pAMI when method is ``"mi"``).
        sig_raw_lags: Lag indices where raw exceeds the upper surrogate band.
        sig_partial_lags: Lag indices where partial exceeds the upper band.
        recommendation: Human-readable triage recommendation.
        method: Name of the scorer used.
    """

    raw: np.ndarray
    partial: np.ndarray
    sig_raw_lags: np.ndarray
    sig_partial_lags: np.ndarray
    recommendation: str
    method: str


class ForecastabilityAnalyzer:
    """Method-independent forecastability analyzer with scorer registry.

    Backward compatible: the ``compute_ami`` / ``compute_pami`` methods
    still delegate to *metrics.py*.  New generic entry-points
    ``compute_raw`` / ``compute_partial`` use the scorer registry.
    """

    def __init__(
        self,
        n_surrogates: int = 99,
        random_state: int = 42,
        *,
        method: str = "mi",
    ) -> None:
        if n_surrogates < 99:
            raise ValueError("n_surrogates must be >= 99")
        self.n_surrogates = n_surrogates
        self.random_state = random_state
        self._registry = default_registry()
        self._state = AnalyzerState(method=method)

    # ------------------------------------------------------------------
    # State proxy properties
    # ------------------------------------------------------------------

    @property
    def ts(self) -> np.ndarray | None:
        """Cached target series."""
        return self._state.ts

    @ts.setter
    def ts(self, value: np.ndarray | None) -> None:
        self._state.ts = value

    @property
    def _method(self) -> str:
        """Last scorer method used."""
        return self._state.method

    @_method.setter
    def _method(self, value: str) -> None:
        self._state.method = value

    # ------------------------------------------------------------------
    # Scorer registry helpers
    # ------------------------------------------------------------------

    def list_scorers(self) -> list[ScorerInfo]:
        """Return all registered scorers.

        Returns:
            List of :class:`ScorerInfo` objects.
        """
        return self._registry.list_scorers()

    def register_scorer(
        self,
        name: str,
        scorer: DependenceScorer,
        *,
        family: Literal["nonlinear", "linear", "rank", "bounded_nonlinear"],
        description: str,
    ) -> None:
        """Register a custom dependence scorer.

        Args:
            name: Unique scorer name.
            scorer: Callable matching :class:`DependenceScorer`.
            family: Scorer family for triage thresholds.
            description: One-line description.
        """
        self._registry.register(name, scorer, family=family, description=description)

    # ------------------------------------------------------------------
    # Legacy AMI / pAMI methods (delegate to metrics.py)
    # ------------------------------------------------------------------

    def compute_ami(self, ts: np.ndarray, max_lag: int = 100) -> np.ndarray:
        """Compute AMI curve and cache it."""
        self.ts = validate_time_series(ts, min_length=max_lag + 31)
        self._state.ami = compute_ami(
            self.ts,
            max_lag=max_lag,
            n_neighbors=8,
            min_pairs=30,
            random_state=self.random_state,
        )
        return self._state.ami

    def compute_pami(self, ts: np.ndarray, max_lag: int = 50) -> np.ndarray:
        """Compute pAMI curve and cache it."""
        self.ts = validate_time_series(ts, min_length=max_lag + 51)
        self._state.pami = compute_pami_linear_residual(
            self.ts,
            max_lag=max_lag,
            n_neighbors=8,
            min_pairs=50,
            random_state=self.random_state,
        )
        return self._state.pami

    # ------------------------------------------------------------------
    # Generic scorer methods
    # ------------------------------------------------------------------

    def compute_raw(
        self,
        ts: np.ndarray,
        max_lag: int = 100,
        *,
        method: str = "mi",
        min_pairs: int = 30,
    ) -> np.ndarray:
        """Compute raw per-horizon dependence using a named scorer.

        Args:
            ts: Univariate time series.
            max_lag: Maximum forecast horizon.
            method: Scorer name from the registry.
            min_pairs: Minimum sample pairs per horizon.

        Returns:
            1-D array of shape ``(max_lag,)`` with dependence at each lag.
        """
        info = self._registry.get(method)
        arr = validate_time_series(ts, min_length=max_lag + min_pairs + 1)
        self.ts = arr
        self._method = method
        self._state.raw = _compute_raw_curve(
            arr, max_lag, info.scorer, min_pairs=min_pairs, random_state=self.random_state
        )
        return self._state.raw

    def compute_partial(
        self,
        ts: np.ndarray,
        max_lag: int = 50,
        *,
        method: str = "mi",
        min_pairs: int = 50,
    ) -> np.ndarray:
        """Compute partial (residualized) per-horizon dependence.

        Args:
            ts: Univariate time series.
            max_lag: Maximum forecast horizon.
            method: Scorer name from the registry.
            min_pairs: Minimum sample pairs per horizon.

        Returns:
            1-D array of shape ``(max_lag,)`` with partial dependence at each lag.
        """
        info = self._registry.get(method)
        arr = validate_time_series(ts, min_length=max_lag + min_pairs + 1)
        self.ts = arr
        self._method = method
        self._state.partial = _compute_partial_curve(
            arr, max_lag, info.scorer, min_pairs=min_pairs, random_state=self.random_state
        )
        return self._state.partial

    # ------------------------------------------------------------------
    # Significance bands
    # ------------------------------------------------------------------

    def compute_significance(
        self, which: str = "ami", max_lag: int | None = None, *, n_jobs: int = -1
    ) -> tuple[np.ndarray, np.ndarray]:
        """Compute surrogate significance bands for AMI or pAMI.

        Args:
            which: ``"ami"`` or ``"pami"`` for legacy mode.
            max_lag: Number of lags; inferred from cached curves if ``None``.
            n_jobs: Parallel workers for surrogate evaluation.  ``-1`` = all CPUs.

        Returns:
            ``(lower_band, upper_band)`` arrays.
        """
        if self.ts is None:
            raise ValueError("No series cached. Call compute_ami/compute_pami first.")
        if which not in {"ami", "pami"}:
            raise ValueError("which must be one of {'ami', 'pami'}")

        metric_name = "ami" if which == "ami" else "pami_linear_residual"
        if max_lag is None:
            max_lag = self._infer_max_lag(which)

        bands = compute_significance_bands(
            self.ts,
            metric_name=metric_name,
            max_lag=max_lag,
            n_surrogates=self.n_surrogates,
            alpha=0.05,
            n_neighbors=8,
            random_state=self.random_state,
            n_jobs=n_jobs,
        )
        if which == "ami":
            self._state.ami_bands = bands
        else:
            self._state.pami_bands = bands
        return bands

    def compute_significance_generic(
        self,
        which: str,
        max_lag: int,
        *,
        method: str = "mi",
        min_pairs: int = 30,
        n_jobs: int = -1,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Compute surrogate significance bands for any scorer.

        Note: Phase surrogates preserve linear autocorrelation structure.
        For linear/rank scorers (Pearson, Spearman, Kendall), the surrogate
        null hypothesis is "linear Gaussian process", so the test has near-zero
        power for detecting linear dependence. Significance should be interpreted
        as evidence of *nonlinear* excess only for these scorers.

        Uses :class:`~concurrent.futures.ThreadPoolExecutor` for parallelism
        (scorer callables may not be picklable, so processes cannot be used here;
        sklearn's kNN estimator partially releases the GIL).

        Args:
            which: ``"raw"`` or ``"partial"``.
            max_lag: Number of lags.
            method: Scorer name from the registry.
            min_pairs: Minimum sample pairs per horizon.
            n_jobs: Thread-pool workers.  ``-1`` = all CPUs.  ``1`` = serial.

        Returns:
            ``(lower_band, upper_band)`` arrays.
        """
        if self.ts is None:
            raise ValueError("No series cached. Call compute_raw/compute_partial first.")
        if which not in {"raw", "partial"}:
            raise ValueError("which must be one of {'raw', 'partial'}")

        info = self._registry.get(method)
        bands = compute_significance_bands_generic(
            self.ts,
            self.n_surrogates,
            self.random_state,
            max_lag,
            info,
            which,
            min_pairs=min_pairs,
            n_jobs=n_jobs,
        )
        if which == "raw":
            self._state.raw_bands = bands
        else:
            self._state.partial_bands = bands
        return bands

    # ------------------------------------------------------------------
    # High-level analyze
    # ------------------------------------------------------------------

    def analyze(
        self,
        ts: np.ndarray,
        max_lag: int = 100,
        target_horizon: int | None = None,
        *,
        method: str = "mi",
        compute_surrogates: bool = False,
    ) -> AnalyzeResult:
        """Run end-to-end forecastability analysis.

        Phase-surrogate significance bands are a **project extension** not present
        in the original paper.  They are therefore **opt-in** (``compute_surrogates=False``
        by default) to avoid the expensive 99× repeated MI computation.  Set
        ``compute_surrogates=True`` when you need significance-band overlay on plots.

        Args:
            ts: Univariate time series.
            max_lag: Maximum lag for the raw curve.
            target_horizon: Reserved for prototype compatibility.
            method: Scorer name from the registry.
            compute_surrogates: When ``True``, compute phase-surrogate significance
                bands (slow — 99 surrogate evaluations).  Default ``False``.

        Returns:
            :class:`AnalyzeResult` with raw and partial curves, significant lags
            (empty when ``compute_surrogates=False``), and a recommendation string.
        """
        del target_horizon
        self._method = method
        partial_lag = max(1, max_lag // 2)

        if method == "mi":
            return self._analyze_legacy(
                ts, max_lag, partial_lag, compute_surrogates=compute_surrogates
            )

        return self._analyze_generic(
            ts, max_lag, partial_lag, method=method, compute_surrogates=compute_surrogates
        )

    # ------------------------------------------------------------------
    # Plot
    # ------------------------------------------------------------------

    def plot(self, *, method: str | None = None, show: bool = True) -> plt.Figure:
        """Plot raw and partial curves with cached significance bands.

        Args:
            method: Label to show in titles (inferred from last ``analyze`` call
                if ``None``).
            show: If ``True``, call ``plt.show()``.

        Returns:
            The matplotlib :class:`~matplotlib.figure.Figure`.
        """
        label = (method or self._method).upper()

        raw, partial = self._resolve_curves_for_plot()
        raw_bands = self._state.raw_bands or self._state.ami_bands
        partial_bands = self._state.partial_bands or self._state.pami_bands

        fig, axs = plt.subplots(2, 1, figsize=(11, 8))
        _plot_curve(axs[0], raw, raw_bands, color="b", label=f"Raw {label}(h)")
        axs[0].set_title(f"Raw dependence ({label}) + significance")
        _plot_curve(axs[1], partial, partial_bands, color="r", label=f"Partial {label}(h)")
        axs[1].set_title(f"Partial dependence ({label}) + significance")

        plt.tight_layout()
        if show:
            plt.show()
        return fig

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _infer_max_lag(self, which: str) -> int:
        """Infer max_lag from cached curves."""
        if which == "ami" and self._state.ami is not None:
            return int(self._state.ami.size)
        if which == "pami" and self._state.pami is not None:
            return int(self._state.pami.size)
        raise ValueError("max_lag is required when the selected metric has not been computed yet.")

    def _analyze_legacy(
        self, ts: np.ndarray, max_lag: int, partial_lag: int, *, compute_surrogates: bool
    ) -> AnalyzeResult:
        """Legacy AMI+pAMI analysis pipeline."""
        self.compute_ami(ts, max_lag=max_lag)
        self.compute_pami(ts, max_lag=partial_lag)

        assert self._state.ami is not None  # noqa: S101
        assert self._state.pami is not None  # noqa: S101

        if compute_surrogates:
            self.compute_significance("ami", max_lag=max_lag)
            self.compute_significance("pami", max_lag=partial_lag)
            assert self._state.ami_bands is not None  # noqa: S101
            assert self._state.pami_bands is not None  # noqa: S101
            sig_raw = np.where(self._state.ami > self._state.ami_bands[1])[0] + 1
            sig_partial = np.where(self._state.pami > self._state.pami_bands[1])[0] + 1
        else:
            sig_raw = np.array([], dtype=int)
            sig_partial = np.array([], dtype=int)

        rec = _triage_recommendation(self._state.ami, family="nonlinear")
        return AnalyzeResult(
            raw=self._state.ami.copy(),
            partial=self._state.pami.copy(),
            sig_raw_lags=sig_raw,
            sig_partial_lags=sig_partial,
            recommendation=rec,
            method="mi",
        )

    def _analyze_generic(
        self,
        ts: np.ndarray,
        max_lag: int,
        partial_lag: int,
        *,
        method: str,
        compute_surrogates: bool,
    ) -> AnalyzeResult:
        """Generic analysis pipeline using the scorer registry."""
        info = self._registry.get(method)
        self.compute_raw(ts, max_lag, method=method)
        self.compute_partial(ts, partial_lag, method=method)

        assert self._state.raw is not None  # noqa: S101
        assert self._state.partial is not None  # noqa: S101

        if compute_surrogates:
            self.compute_significance_generic("raw", max_lag, method=method)
            self.compute_significance_generic("partial", partial_lag, method=method)
            assert self._state.raw_bands is not None  # noqa: S101
            assert self._state.partial_bands is not None  # noqa: S101
            sig_raw = np.where(self._state.raw > self._state.raw_bands[1])[0] + 1
            sig_partial = np.where(self._state.partial > self._state.partial_bands[1])[0] + 1
        else:
            sig_raw = np.array([], dtype=int)
            sig_partial = np.array([], dtype=int)

        rec = _triage_recommendation(self._state.raw, family=info.family)
        return AnalyzeResult(
            raw=self._state.raw.copy(),
            partial=self._state.partial.copy(),
            sig_raw_lags=sig_raw,
            sig_partial_lags=sig_partial,
            recommendation=rec,
            method=method,
        )

    def _resolve_curves_for_plot(self) -> tuple[np.ndarray, np.ndarray]:
        """Return (raw, partial) curves from whichever cache is populated."""
        raw = self._state.raw if self._state.raw is not None else self._state.ami
        partial = self._state.partial if self._state.partial is not None else self._state.pami
        if raw is None or partial is None:
            raise ValueError("No cached curves. Run analyze or compute methods first.")
        return raw, partial


class ForecastabilityAnalyzerExog(ForecastabilityAnalyzer):
    """Forecastability analyzer with optional exogenous (CCF-style) support.

    Behavior:
    - ``exog=None``: same as :class:`ForecastabilityAnalyzer` (ACF-style).
    - ``exog=...``: cross dependence from ``exog_t`` to ``target_(t+h)``.
      Partial mode residualizes only the target future against target
      intermediate lags, keeping exogenous predictors untouched.
    """

    def __init__(
        self,
        n_surrogates: int = 99,
        random_state: int = 42,
        *,
        method: str = "mi",
    ) -> None:
        super().__init__(n_surrogates=n_surrogates, random_state=random_state, method=method)

    # ------------------------------------------------------------------
    # State proxy property for exog
    # ------------------------------------------------------------------

    @property
    def exog(self) -> np.ndarray | None:
        """Cached exogenous series."""
        return self._state.exog

    @exog.setter
    def exog(self, value: np.ndarray | None) -> None:
        self._state.exog = value

    def compute_ami(
        self, ts: np.ndarray, max_lag: int = 100, *, exog: np.ndarray | None = None
    ) -> np.ndarray:
        """Legacy AMI path; exogenous input is unsupported by design."""
        if exog is not None:
            raise ValueError(
                "Legacy compute_ami does not support exogenous variables. "
                "Use compute_raw(method='mi', exog=...) instead."
            )
        return super().compute_ami(ts, max_lag=max_lag)

    def compute_pami(
        self, ts: np.ndarray, max_lag: int = 50, *, exog: np.ndarray | None = None
    ) -> np.ndarray:
        """Legacy pAMI path; exogenous input is unsupported by design."""
        if exog is not None:
            raise ValueError(
                "Legacy compute_pami does not support exogenous variables. "
                "Use compute_partial(method='mi', exog=...) instead."
            )
        return super().compute_pami(ts, max_lag=max_lag)

    def compute_raw(
        self,
        ts: np.ndarray,
        max_lag: int = 100,
        *,
        method: str = "mi",
        min_pairs: int = 30,
        exog: np.ndarray | None = None,
    ) -> np.ndarray:
        """Compute raw dependence curve in auto- or cross-dependence mode."""
        info = self._registry.get(method)
        arr = validate_time_series(ts, min_length=max_lag + min_pairs + 1)
        validated_exog = _validate_exog_for_target(exog, target=arr)

        self.ts = arr
        self.exog = validated_exog
        self._method = method
        self._state.raw = _compute_raw_curve(
            arr,
            max_lag,
            info.scorer,
            exog=validated_exog,
            min_pairs=min_pairs,
            random_state=self.random_state,
        )
        return self._state.raw

    def compute_partial(
        self,
        ts: np.ndarray,
        max_lag: int = 50,
        *,
        method: str = "mi",
        min_pairs: int = 50,
        exog: np.ndarray | None = None,
    ) -> np.ndarray:
        """Compute partial dependence curve in auto- or cross-dependence mode."""
        info = self._registry.get(method)
        arr = validate_time_series(ts, min_length=max_lag + min_pairs + 1)
        validated_exog = _validate_exog_for_target(exog, target=arr)

        self.ts = arr
        self.exog = validated_exog
        self._method = method
        self._state.partial = _compute_partial_curve(
            arr,
            max_lag,
            info.scorer,
            exog=validated_exog,
            min_pairs=min_pairs,
            random_state=self.random_state,
        )
        return self._state.partial

    def compute_significance(
        self,
        which: str = "ami",
        max_lag: int | None = None,
        *,
        n_jobs: int = -1,
        exog: np.ndarray | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Legacy significance path; exogenous input is unsupported by design."""
        if exog is not None:
            raise ValueError(
                "Legacy compute_significance does not support exogenous variables. "
                "Use compute_significance_generic(which=..., exog=...) instead."
            )
        return super().compute_significance(which=which, max_lag=max_lag, n_jobs=n_jobs)

    def compute_significance_generic(
        self,
        which: str,
        max_lag: int,
        *,
        method: str = "mi",
        min_pairs: int = 30,
        exog: np.ndarray | None = None,
        n_jobs: int = -1,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Compute surrogate significance bands for auto or cross dependence.

        Uses :class:`~concurrent.futures.ThreadPoolExecutor` for parallelism.
        """
        if self.ts is None:
            raise ValueError("No series cached. Call compute_raw/compute_partial first.")
        if which not in {"raw", "partial"}:
            raise ValueError("which must be one of {'raw', 'partial'}")

        if exog is not None:
            self.exog = _validate_exog_for_target(exog, target=self.ts)
        elif self.exog is not None and self.exog.size != self.ts.size:
            raise ValueError("Cached exogenous series length must match cached target length.")

        info = self._registry.get(method)
        bands = compute_significance_bands_generic(
            self.ts,
            self.n_surrogates,
            self.random_state,
            max_lag,
            info,
            which,
            exog=self.exog,
            min_pairs=min_pairs,
            n_jobs=n_jobs,
        )
        if which == "raw":
            self._state.raw_bands = bands
        else:
            self._state.partial_bands = bands
        return bands

    def analyze(
        self,
        ts: np.ndarray,
        max_lag: int = 100,
        target_horizon: int | None = None,
        *,
        method: str = "mi",
        exog: np.ndarray | None = None,
        compute_surrogates: bool = False,
    ) -> AnalyzeResult:
        """Run end-to-end analysis in auto or cross mode.

        Phase-surrogate significance bands are **opt-in** (``compute_surrogates=False``
        by default) — see :meth:`ForecastabilityAnalyzer.analyze` for rationale.

        Args:
            ts: Univariate time series.
            max_lag: Maximum lag for the raw curve.
            target_horizon: Reserved for prototype compatibility.
            method: Scorer name from the registry.
            exog: Optional exogenous series (CCF-style cross mode).
            compute_surrogates: Compute phase-surrogate significance bands.
                Default ``False``.

        Returns:
            :class:`AnalyzeResult` with raw and partial curves, significant lags
            (empty when ``compute_surrogates=False``), and a recommendation string.
        """
        del target_horizon
        self._method = method
        self.exog = exog
        partial_lag = max(1, max_lag // 2)

        if method == "mi" and exog is None:
            return self._analyze_legacy(
                ts, max_lag, partial_lag, compute_surrogates=compute_surrogates
            )

        return self._analyze_generic_exog(
            ts,
            max_lag,
            partial_lag,
            method=method,
            exog=exog,
            compute_surrogates=compute_surrogates,
        )

    def plot(self, *, method: str | None = None, show: bool = True) -> plt.Figure:
        """Plot raw and partial curves, labeling cross mode when exog is set."""
        label = (method or self._method).upper()
        is_cross = self.exog is not None
        if is_cross:
            label = f"Cross-{label}"

        raw, partial = self._resolve_curves_for_plot()
        raw_bands = self._state.raw_bands or self._state.ami_bands
        partial_bands = self._state.partial_bands or self._state.pami_bands

        fig, axs = plt.subplots(2, 1, figsize=(11, 8))
        _plot_curve(axs[0], raw, raw_bands, color="b", label=f"Raw {label}(h)")
        axs[0].set_title(f"Raw {'cross-' if is_cross else ''}dependence ({label}) + significance")
        _plot_curve(axs[1], partial, partial_bands, color="r", label=f"Partial {label}(h)")
        axs[1].set_title(
            f"Partial {'cross-' if is_cross else ''}dependence ({label}) + significance"
        )

        plt.tight_layout()
        if show:
            plt.show()
        return fig

    def _analyze_generic_exog(
        self,
        ts: np.ndarray,
        max_lag: int,
        partial_lag: int,
        *,
        method: str,
        exog: np.ndarray | None,
        compute_surrogates: bool,
    ) -> AnalyzeResult:
        """Generic analysis pipeline with optional exogenous series."""
        info = self._registry.get(method)
        self.compute_raw(ts, max_lag, method=method, exog=exog)
        self.compute_partial(ts, partial_lag, method=method, exog=exog)

        assert self._state.raw is not None  # noqa: S101
        assert self._state.partial is not None  # noqa: S101

        if compute_surrogates:
            self.compute_significance_generic("raw", max_lag, method=method, exog=exog)
            self.compute_significance_generic("partial", partial_lag, method=method, exog=exog)
            assert self._state.raw_bands is not None  # noqa: S101
            assert self._state.partial_bands is not None  # noqa: S101
            sig_raw = np.where(self._state.raw > self._state.raw_bands[1])[0] + 1
            sig_partial = np.where(self._state.partial > self._state.partial_bands[1])[0] + 1
        else:
            sig_raw = np.array([], dtype=int)
            sig_partial = np.array([], dtype=int)

        rec = _triage_recommendation(self._state.raw, family=info.family, is_cross=exog is not None)
        return AnalyzeResult(
            raw=self._state.raw.copy(),
            partial=self._state.partial.copy(),
            sig_raw_lags=sig_raw,
            sig_partial_lags=sig_partial,
            recommendation=rec,
            method=method,
        )


# _compute_raw_curve, _compute_partial_curve, _plot_curve, _triage_recommendation,
# _TRIAGE_THRESHOLDS, and _validate_exog_for_target are imported at the top of this
# module from the services package and remain accessible here for backward compat.
