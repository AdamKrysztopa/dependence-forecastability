"""Linear Gaussian-information baseline derived from autocorrelation."""

from __future__ import annotations

import math

import numpy as np
from pydantic import BaseModel, Field


class LinearInformationPoint(BaseModel, frozen=True):
    """Per-horizon linear-information proxy.

    Attributes:
        horizon: Lag horizon index.
        rho: Pearson autocorrelation at this horizon, or None if undefined.
        gaussian_information: -0.5 * log(1 - rho²), clipped near |rho|=1, or None if undefined.
        valid: False when autocorrelation could not be computed.
        caution: Reason string if the estimate has a known limitation.
    """

    horizon: int
    rho: float | None = None
    gaussian_information: float | None = None
    valid: bool = True
    caution: str | None = None


class LinearInformationCurve(BaseModel, frozen=True):
    """Collection of Gaussian-information points over horizons.

    Attributes:
        points: Horizon-ordered list of LinearInformationPoint.
    """

    points: list[LinearInformationPoint] = Field(default_factory=list)

    def valid_gaussian_values(self) -> list[tuple[int, float]]:
        """Return (horizon, gaussian_information) pairs for valid horizons only."""
        return [
            (p.horizon, p.gaussian_information)
            for p in self.points
            if p.valid and p.gaussian_information is not None
        ]


def _safe_autocorrelation(series: np.ndarray, horizon: int) -> float | None:
    """Compute Pearson autocorrelation for one horizon.

    Args:
        series: One-dimensional numeric series.
        horizon: Positive lag horizon.

    Returns:
        float | None: Correlation value, or None if undefined due to insufficient
            pairs or zero variance.
    """
    if horizon <= 0 or horizon >= len(series):
        return None
    x = series[:-horizon]
    y = series[horizon:]
    if x.size < 3:
        return None
    std_x = float(np.std(x))
    std_y = float(np.std(y))
    if std_x == 0.0 or std_y == 0.0:
        return None
    corr_matrix = np.corrcoef(x, y)
    return float(corr_matrix[0, 1])


def _gaussian_information_from_rho(rho: float, *, epsilon: float) -> float:
    """Map Pearson correlation to the Gaussian-information proxy.

    Implements I_G = -0.5 * log(1 - rho²) with safe clipping near |rho| = 1.

    Args:
        rho: Pearson correlation value.
        epsilon: Numerical floor for clipping: rho_abs is capped at (1 - epsilon).

    Returns:
        float: Gaussian-information value in nats (non-negative).
    """
    rho_abs = min(abs(rho), 1.0 - epsilon)
    return -0.5 * math.log(1.0 - rho_abs * rho_abs)


def compute_linear_information_curve(
    series: np.ndarray,
    *,
    horizons: list[int],
    epsilon: float = 1e-12,
) -> LinearInformationCurve:
    """Compute the Gaussian-information baseline over the provided horizons.

    This function provides a per-horizon linear-information proxy derived from
    Pearson autocorrelation. It is used as a baseline against which AMI excess
    (nonlinear_share) is measured. It does NOT replace AMI computation.

    The Gaussian-information proxy for horizon h is:
        I_G(h) = -0.5 * log(1 - rho(h)²)

    where rho(h) is the Pearson autocorrelation at lag h. Horizons where
    autocorrelation is undefined are excluded conservatively (valid=False)
    rather than imputed.

    Args:
        series: One-dimensional numeric array (float64 or compatible).
        horizons: Positive horizon indices to evaluate.
        epsilon: Numerical clipping constant for safe log computation near |rho|=1.
            Defaults to 1e-12.

    Returns:
        LinearInformationCurve: Horizon-wise baseline values, including validity
            flags and caution strings for undefined or limited estimates.

    Example:
        >>> import numpy as np
        >>> rng = np.random.default_rng(42)
        >>> series = rng.normal(0, 1, 200)
        >>> curve = compute_linear_information_curve(series, horizons=[1, 2, 3])
        >>> len(curve.points)
        3
    """
    arr = np.asarray(series, dtype=np.float64)
    points: list[LinearInformationPoint] = []
    for horizon in horizons:
        rho = _safe_autocorrelation(arr, horizon)
        if rho is None:
            points.append(
                LinearInformationPoint(
                    horizon=horizon,
                    rho=None,
                    gaussian_information=None,
                    valid=False,
                    caution="undefined_autocorrelation",
                )
            )
            continue
        if not math.isfinite(rho):
            points.append(
                LinearInformationPoint(
                    horizon=horizon,
                    rho=rho,
                    gaussian_information=None,
                    valid=False,
                    caution="non_finite_autocorrelation",
                )
            )
            continue
        gi = _gaussian_information_from_rho(rho, epsilon=epsilon)
        points.append(
            LinearInformationPoint(
                horizon=horizon,
                rho=rho,
                gaussian_information=gi,
                valid=True,
                caution=None,
            )
        )
    return LinearInformationCurve(points=points)
