"""Focused tests for lagged-exogenous plotting helpers (V3_2-F08)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from forecastability import (
    LaggedExogBundle,
    generate_lagged_exog_panel,
    run_lagged_exogenous_triage,
)
from forecastability.adapters.rendering.lagged_exog_plots import (
    build_lagged_exog_profile_figure,
    save_lagged_exog_profile_figure,
    save_lagged_exog_selection_heatmap,
)


def _build_bundle() -> LaggedExogBundle:
    panel = generate_lagged_exog_panel(n=900, seed=42)
    target = panel["target"].to_numpy()
    drivers = {
        "direct_lag2": panel["direct_lag2"].to_numpy(),
        "instant_only": panel["instant_only"].to_numpy(),
    }
    return run_lagged_exogenous_triage(
        target,
        drivers,
        target_name="target",
        max_lag=4,
        n_surrogates=99,
        random_state=42,
    )


def test_profile_figure_separates_lag_zero_and_highlights_selected_predictive_lags() -> None:
    """Profile plot should separate lag=0 and mark selected predictive lags."""
    bundle = _build_bundle()

    fig = build_lagged_exog_profile_figure(bundle, driver_order=["direct_lag2", "instant_only"])

    first_axis = fig.axes[0]
    has_lag_zero_separator = False
    for line in first_axis.lines:
        xdata = np.asarray(line.get_xdata(), dtype=float)
        if xdata.size == 2 and np.allclose(xdata, np.array([0.5, 0.5], dtype=float)):
            has_lag_zero_separator = True
            break
    assert has_lag_zero_separator

    selected_predictive = {
        row.lag
        for row in bundle.selected_lags
        if row.driver == "direct_lag2" and row.selected_for_tensor and row.lag >= 1
    }
    assert selected_predictive

    scatter_x_values: list[float] = []
    for collection in first_axis.collections:
        offsets = np.asarray(collection.get_offsets(), dtype=float)
        if offsets.size == 0:
            continue
        if offsets.ndim == 1:
            scatter_x_values.append(float(offsets[0]))
            continue
        scatter_x_values.extend(float(value) for value in offsets[:, 0].tolist())

    assert any(
        any(np.isclose(x_value, float(lag)) for x_value in scatter_x_values)
        for lag in selected_predictive
    )

    plt.close(fig)


def test_plot_helpers_save_profile_and_selection_figures(tmp_path: Path) -> None:
    """Plot helpers should write non-empty profile and selection figures."""
    bundle = _build_bundle()

    profile_path = tmp_path / "lagged_exog_profiles.png"
    selection_path = tmp_path / "lagged_exog_selected_lags.png"

    save_lagged_exog_profile_figure(bundle, output_path=profile_path)
    save_lagged_exog_selection_heatmap(bundle, output_path=selection_path)

    assert profile_path.exists()
    assert profile_path.stat().st_size > 0
    assert selection_path.exists()
    assert selection_path.stat().st_size > 0
