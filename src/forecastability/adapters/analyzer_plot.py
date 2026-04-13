"""Plotting adapter for ForecastabilityAnalyzer results."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from forecastability.adapters.plot_service import _plot_curve


def plot_analyzer(
    raw: np.ndarray,
    partial: np.ndarray,
    *,
    raw_bands: tuple[np.ndarray, np.ndarray] | None = None,
    partial_bands: tuple[np.ndarray, np.ndarray] | None = None,
    method: str = "MI",
    is_cross: bool = False,
    show: bool = True,
) -> Any:
    """Plot raw and partial dependence curves with optional significance bands.

    Args:
        raw: Raw dependence curve values.
        partial: Partial dependence curve values.
        raw_bands: Optional (lower, upper) surrogate bands for raw curve.
        partial_bands: Optional (lower, upper) surrogate bands for partial curve.
        method: Scorer label for titles.
        is_cross: When ``True``, prefix titles with "cross-".
        show: If True, call plt.show().

    Returns:
        The matplotlib Figure.
    """
    label = method.upper()
    if is_cross:
        label = f"Cross-{label}"
    cross_prefix = "cross-" if is_cross else ""
    fig, axs = plt.subplots(2, 1, figsize=(11, 8))
    _plot_curve(axs[0], raw, raw_bands, color="b", label=f"Raw {label}(h)")
    axs[0].set_title(f"Raw {cross_prefix}dependence ({label}) + significance")
    _plot_curve(axs[1], partial, partial_bands, color="r", label=f"Partial {label}(h)")
    axs[1].set_title(f"Partial {cross_prefix}dependence ({label}) + significance")
    plt.tight_layout()
    if show:
        plt.show()
    return fig
