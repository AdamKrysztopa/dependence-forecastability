# 12. Refactor That Implementation Into Package Code

- [x] Refactor baseline prototype into package modules.
- [x] Preserve baseline logic while aligning with project rules.
- [x] Implement:
  - [x] 12.1 `metrics.py`
  - [x] 12.2 `surrogates.py`

## 12.1 `metrics.py`

```python
from __future__ import annotations

import numpy as np
from sklearn.feature_selection import mutual_info_regression
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from forecastability.validation import validate_time_series


def _scale_series(ts: np.ndarray) -> np.ndarray:
    """Standardize a univariate time series.

    Args:
        ts: Input series.

    Returns:
        np.ndarray: Standardized series.
    """
    return StandardScaler().fit_transform(ts.reshape(-1, 1)).ravel()


def compute_ami(
    ts: np.ndarray,
    max_lag: int,
    *,
    n_neighbors: int = 8,
    min_pairs: int = 30,
    random_state: int = 42,
) -> np.ndarray:
    """Compute horizon-specific AMI.

    Args:
        ts: Input time series.
        max_lag: Maximum lag.
        n_neighbors: kNN neighbors.
        min_pairs: Minimum required lagged pairs.
        random_state: Seed.

    Returns:
        np.ndarray: AMI values of shape (max_lag,).
    """
    arr = validate_time_series(ts, min_length=max_lag + min_pairs + 1)
    arr = _scale_series(arr)
    rng = np.random.default_rng(random_state)

    ami = np.zeros(max_lag, dtype=float)
    for h in range(1, max_lag + 1):
        if arr.size - h < min_pairs:
            break
        x = arr[:-h].reshape(-1, 1)
        y = arr[h:]
        ami[h - 1] = mutual_info_regression(
            x,
            y,
            n_neighbors=n_neighbors,
            random_state=rng,
        )[0]
    return ami


def _build_conditioning_matrix(ts: np.ndarray, lag: int) -> np.ndarray:
    """Build conditioning matrix for lags 1..lag-1.

    Args:
        ts: Standardized series.
        lag: Target lag.

    Returns:
        np.ndarray: Conditioning matrix.
    """
    if lag <= 1:
        return np.empty((ts.size - lag, 0))

    cols = [np.roll(ts, k)[lag:] for k in range(1, lag)]
    return np.column_stack(cols)


def compute_pami_linear_residual(
    ts: np.ndarray,
    max_lag: int,
    *,
    n_neighbors: int = 8,
    min_pairs: int = 50,
    random_state: int = 42,
) -> np.ndarray:
    """Compute pAMI via linear residualisation.

    This is an approximate nonlinear partial-dependence measure:
    linear conditioning + nonlinear MI on residuals.

    Args:
        ts: Input time series.
        max_lag: Maximum lag.
        n_neighbors: kNN neighbors.
        min_pairs: Minimum required lagged pairs.
        random_state: Seed.

    Returns:
        np.ndarray: pAMI values.
    """
    arr = validate_time_series(ts, min_length=max_lag + min_pairs + 1)
    arr = _scale_series(arr)
    rng = np.random.default_rng(random_state)

    pami = np.zeros(max_lag, dtype=float)
    for h in range(1, max_lag + 1):
        if arr.size - h < min_pairs:
            break

        z = _build_conditioning_matrix(arr, h)
        past = arr[:-h]
        future = arr[h:]

        if h == 1 or z.shape[1] == 0:
            res_past = past
            res_future = future
        else:
            model_past = LinearRegression()
            model_future = LinearRegression()

            model_past.fit(z, past)
            model_future.fit(z, future)

            res_past = past - model_past.predict(z)
            res_future = future - model_future.predict(z)

        pami[h - 1] = mutual_info_regression(
            res_past.reshape(-1, 1),
            res_future,
            n_neighbors=n_neighbors,
            random_state=rng,
        )[0]

    return pami
```

## 12.2 `surrogates.py`

```python
from __future__ import annotations

import numpy as np
from scipy.fftpack import fft, ifft

from forecastability.metrics import compute_ami, compute_pami_linear_residual
from forecastability.validation import validate_time_series


def phase_surrogates(
    ts: np.ndarray,
    *,
    n_surrogates: int,
    random_state: int = 42,
) -> np.ndarray:
    """Generate phase-randomized surrogates.

    Args:
        ts: Input series.
        n_surrogates: Number of surrogates.
        random_state: Seed.

    Returns:
        np.ndarray: Surrogates with shape (n_surrogates, n_samples).
    """
    arr = validate_time_series(ts, min_length=16)
    rng = np.random.default_rng(random_state)

    surrogates = np.empty((n_surrogates, arr.size), dtype=float)
    fft_ts = fft(arr)

    for i in range(n_surrogates):
        phases = np.exp(1j * rng.uniform(0.0, 2.0 * np.pi, arr.size // 2))
        phases = np.concatenate(
            ([1.0], phases, np.conj(phases[::-1 if arr.size % 2 else -1:0:-1]))
        )
        surrogates[i] = np.real(ifft(fft_ts * phases))

    return surrogates


def compute_significance_bands(
    ts: np.ndarray,
    *,
    metric_name: str,
    max_lag: int,
    n_surrogates: int = 99,
    alpha: float = 0.05,
    n_neighbors: int = 8,
    random_state: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute surrogate significance bands.

    Args:
        ts: Input series.
        metric_name: One of 'ami' or 'pami_linear_residual'.
        max_lag: Maximum lag.
        n_surrogates: Number of surrogates.
        alpha: Significance level.
        n_neighbors: kNN neighbors.
        random_state: Seed.

    Returns:
        tuple[np.ndarray, np.ndarray]: Lower and upper bands.

    Raises:
        ValueError: If metric_name is unsupported.
    """
    surrogates = phase_surrogates(
        ts,
        n_surrogates=n_surrogates,
        random_state=random_state,
    )

    values = []
    for surrogate in surrogates:
        if metric_name == "ami":
            curve = compute_ami(
                surrogate,
                max_lag,
                n_neighbors=n_neighbors,
                random_state=random_state,
            )
        elif metric_name == "pami_linear_residual":
            curve = compute_pami_linear_residual(
                surrogate,
                max_lag,
                n_neighbors=n_neighbors,
                random_state=random_state,
            )
        else:
            raise ValueError(f"Unsupported metric_name: {metric_name}")

        values.append(curve)

    stacked = np.vstack(values)
    lower = np.percentile(stacked, 100.0 * alpha / 2.0, axis=0)
    upper = np.percentile(stacked, 100.0 * (1.0 - alpha / 2.0), axis=0)
    return lower, upper
```
