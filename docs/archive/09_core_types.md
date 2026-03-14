# 9. Core Types

- [x] Implement these result containers:
  - [ ] `MetricCurve`
  - [ ] `CanonicalExampleResult`
  - [ ] `ForecastResult`
  - [ ] `SeriesEvaluationResult`
  - [ ] `InterpretationResult`

```python
from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np
import pandas as pd


@dataclass(slots=True)
class MetricCurve:
    """Container for a metric curve and significance bands."""

    values: np.ndarray
    lower_band: np.ndarray | None = None
    upper_band: np.ndarray | None = None
    significant_lags: np.ndarray | None = None


@dataclass(slots=True)
class CanonicalExampleResult:
    """Result for one canonical example."""

    series_name: str
    series: np.ndarray
    ami: MetricCurve
    pami: MetricCurve
    metadata: dict[str, str | int | float] = field(default_factory=dict)


@dataclass(slots=True)
class ForecastResult:
    """Forecast results across horizons."""

    model_name: str
    horizons: list[int]
    smape_by_horizon: dict[int, float]


@dataclass(slots=True)
class SeriesEvaluationResult:
    """Rolling-origin evaluation result for one series."""

    series_id: str
    frequency: str
    ami_by_horizon: dict[int, float]
    pami_by_horizon: dict[int, float]
    forecast_results: list[ForecastResult]
    metadata: dict[str, str | int | float] = field(default_factory=dict)


@dataclass(slots=True)
class InterpretationResult:
    """Interpretation result for one series."""

    forecastability_class: str
    directness_class: str
    primary_lags: list[int]
    modeling_regime: str
    narrative: str
    diagnostics: dict[str, float | int | str]
```
