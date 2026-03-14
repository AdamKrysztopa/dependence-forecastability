# 8. Core Config Objects

- [x] Implement these dataclasses exactly as specified:
  - [ ] `MetricConfig`
  - [ ] `RollingOriginConfig`
  - [ ] `OutputConfig`
- [x] Enforce defaults:
  - [ ] `MetricConfig.n_neighbors = 8`
  - [ ] `RollingOriginConfig.n_origins = 10`
  - [ ] `RollingOriginConfig.horizons = list(range(1, 19))`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class MetricConfig:
    """Configuration for AMI and pAMI estimation.

    Args:
        max_lag: Maximum lag to evaluate.
        n_neighbors: Number of neighbors for kNN MI estimation.
        min_pairs_ami: Minimum valid lagged pairs for AMI.
        min_pairs_pami: Minimum valid lagged pairs for pAMI.
        n_surrogates: Number of surrogates for significance estimation.
        alpha: Significance level.
        random_state: Seed for deterministic execution.
    """

    max_lag: int = 100
    n_neighbors: int = 8
    min_pairs_ami: int = 30
    min_pairs_pami: int = 50
    n_surrogates: int = 99
    alpha: float = 0.05
    random_state: int = 42


@dataclass(slots=True)
class RollingOriginConfig:
    """Configuration for rolling-origin evaluation.

    Args:
        n_origins: Number of rolling origins.
        horizons: Forecast horizons.
        seasonal_period: Seasonal period if known.
    """

    n_origins: int = 10
    horizons: list[int] = field(default_factory=lambda: list(range(1, 19)))
    seasonal_period: int | None = None


@dataclass(slots=True)
class OutputConfig:
    """Output locations for artifacts.

    Args:
        figures_dir: Directory for figures.
        tables_dir: Directory for tables.
        json_dir: Directory for JSON outputs.
        reports_dir: Directory for markdown reports.
    """

    figures_dir: Path
    tables_dir: Path
    json_dir: Path
    reports_dir: Path
```
