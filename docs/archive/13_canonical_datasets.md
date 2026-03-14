# 13. Canonical Datasets

- [x] Implement canonical interpretive examples exactly as named:
  - [ ] sine wave
  - [ ] AirPassengers
  - [ ] Hénon map
  - [ ] simulated stock returns
- [x] Use these datasets only for interpretive analysis.
- [x] Do not use canonical datasets in benchmark model comparison.

```python
from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.datasets import get_rdataset


def generate_sine_wave(
    *,
    n_samples: int = 400,
    cycles: float = 12.0,
    noise_std: float = 0.05,
    random_state: int = 42,
) -> np.ndarray:
    """Generate a noisy sine wave."""
    rng = np.random.default_rng(random_state)
    x = np.linspace(0.0, 2.0 * np.pi * cycles, n_samples)
    return np.sin(x) + rng.normal(0.0, noise_std, size=n_samples)


def load_air_passengers() -> np.ndarray:
    """Load the AirPassengers dataset."""
    data = get_rdataset("AirPassengers").data
    return data["value"].to_numpy(dtype=float)


def generate_henon_map(
    *,
    n_samples: int = 500,
    a: float = 1.4,
    b: float = 0.3,
    discard: int = 100,
) -> np.ndarray:
    """Generate Hénon map x-component."""
    total = n_samples + discard
    x = np.zeros(total, dtype=float)
    y = np.zeros(total, dtype=float)
    x[0] = 0.1
    y[0] = 0.3

    for t in range(total - 1):
        x[t + 1] = 1.0 - a * x[t] ** 2 + y[t]
        y[t + 1] = b * x[t]

    return x[discard:]


def generate_simulated_stock_returns(
    *,
    n_samples: int = 500,
    mean: float = 0.0,
    std: float = 0.01,
    random_state: int = 42,
) -> np.ndarray:
    """Generate weakly dependent stock-like returns."""
    rng = np.random.default_rng(random_state)
    return rng.normal(mean, std, size=n_samples)
```
