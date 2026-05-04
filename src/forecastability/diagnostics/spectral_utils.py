"""Shared deterministic PSD / FFT utilities for Phase 2 scorers (F4, F6)."""

from __future__ import annotations

import numpy as np
from scipy.signal import welch


def compute_normalised_psd(
    series: np.ndarray,
    *,
    nperseg: int | None = None,
    detrend: str | bool = "constant",
) -> tuple[np.ndarray, np.ndarray]:
    """Compute Welch PSD and return normalised frequency weights.

    Uses ``scipy.signal.welch`` for a consistent, bias-reduced estimate.
    The returned ``p`` array sums to 1.0 (probability weights).  Zero
    power is handled by clipping before normalisation.

    Args:
        series: 1-D float array, length >= 8.
        nperseg: Segment length passed to ``scipy.signal.welch``.  Defaults to
            ``min(len(series), 256)``.
        detrend: Detrending applied by welch (``"constant"`` mean-centres,
            ``"linear"`` removes linear trend, ``False`` skips detrending).

    Returns:
        Tuple ``(freqs, p)`` where ``freqs`` is the frequency array and ``p``
        is the normalised power vector (sums to 1.0).

    Raises:
        ValueError: When ``series`` has fewer than 8 samples or is not 1-D.
    """
    if series.ndim != 1 or len(series) < 8:
        raise ValueError(f"series must be 1-D with at least 8 samples; got shape {series.shape}")
    n = len(series)
    seg = nperseg if nperseg is not None else min(n, 256)
    freqs, psd = welch(series, nperseg=seg, detrend=detrend)
    # Clip near-zero to avoid log(0) in entropy computations
    psd = np.clip(psd, a_min=1e-12, a_max=None)
    p = psd / psd.sum()
    return freqs, p


def spectral_entropy(p: np.ndarray, *, base: float = np.e) -> float:
    """Compute spectral entropy from normalised PSD weights.

    H_a = -sum_i p_i * log_a(p_i)

    Args:
        p: Normalised PSD probability vector (sums to 1.0).
        base: Logarithm base (default: natural log, ``base=e``).

    Returns:
        Non-negative entropy value.
    """
    p_safe = np.clip(p, a_min=1e-12, a_max=None)
    h = -np.sum(p_safe * np.log(p_safe))
    if base != np.e:
        h = h / np.log(base)
    return float(h)
