"""Reusable curve-plotting helper."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np


def _plot_curve(
    ax: plt.Axes,
    values: np.ndarray,
    bands: tuple[np.ndarray, np.ndarray] | None,
    *,
    color: str,
    label: str,
) -> None:
    """Plot a single dependence curve with optional significance bands.

    Args:
        ax: Matplotlib axes to draw on.
        values: 1-D curve values.
        bands: Optional ``(lower, upper)`` surrogate band arrays.
        color: Line/fill colour character or name.
        label: Legend label for the curve.
    """
    lags = np.arange(1, values.size + 1)
    ax.plot(lags, values, f"{color}-", lw=2, label=label)
    if bands is not None:
        ax.fill_between(lags, bands[0], bands[1], color=color, alpha=0.15, label="95% band")
    ax.axhline(0.0, color="k", lw=0.5)
    ax.set_xlabel("Lag")
    ax.legend()
    ax.grid(alpha=0.3)
