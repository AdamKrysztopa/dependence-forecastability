"""Deprecated shim — multi-series comparison reporting.

.. deprecated:: 0.5.0
    Import from ``forecastability.domain.models.comparison_report`` (data models)
    or ``forecastability.reporting.comparison_report_plots`` (rendering + coordinator)
    instead.  This shim re-exports all public symbols from both new locations.
    See ``docs/migration/v0.4.x_to_v0.5.0.md``.
"""

from __future__ import annotations

import warnings as _warnings
from importlib import import_module
from typing import Any

from forecastability.domain.models.comparison_report import (  # noqa: F401, F403
    HORIZON_DROPOFF_TABLE_COLUMNS,
    RECOMMENDATION_TABLE_COLUMNS,
    SERIES_COMPARISON_TABLE_COLUMNS,
    ComparisonArtifactPaths,
    ComparisonSummary,
    HorizonDropoffRow,
    MultiSeriesComparisonReport,
    SeriesComparisonRow,
    SeriesRecommendationRow,
    _build_dropoff_rows,
    _build_recommendation_table,
    _build_series_row,
    _build_summary,
    _compute_auc,
    _compute_dropoff_index,
    _compute_significance_coverage,
    _deserves_deeper_modeling,
    _normalized_curve,
    _priority_score,
    _recommendation_rationale,
)

# Rendering helpers live in the reporting layer. They are resolved lazily so
# this deprecated shim holds no static import edge into the reporting layer
# (hexagonal boundary; v0.5.0). Remove this shim in v0.6.0.
_REPORTING_EXPORTS = frozenset(
    {
        "_build_recommendation_markdown_table",
        "_plot_auc",
        "_plot_directness_ratio",
        "_plot_horizon_dropoff",
        "_plot_significance_coverage",
        "_render_report_markdown",
        "_save_no_data_plot",
        "build_multi_series_comparison_report",
        "write_multi_series_comparison_artifacts",
    }
)


def __getattr__(name: str) -> Any:
    """Resolve relocated reporting renderers from the reporting layer lazily."""
    if name in _REPORTING_EXPORTS:
        module = import_module("forecastability.reporting.comparison_report_plots")
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


_warnings.warn(
    "forecastability.triage.comparison_report is deprecated in v0.5.0; "
    "import from forecastability.domain.models.comparison_report or "
    "forecastability.reporting.comparison_report_plots instead. "
    "See docs/migration/v0.4.x_to_v0.5.0.md.",
    DeprecationWarning,
    stacklevel=2,
)
