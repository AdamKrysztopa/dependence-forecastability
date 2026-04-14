"""Canonical and helper datasets."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# Classic monthly totals from Jan 1949 to Dec 1960.
_AIR_PASSENGERS = np.array(
    [
        112,
        118,
        132,
        129,
        121,
        135,
        148,
        148,
        136,
        119,
        104,
        118,
        115,
        126,
        141,
        135,
        125,
        149,
        170,
        170,
        158,
        133,
        114,
        140,
        145,
        150,
        178,
        163,
        172,
        178,
        199,
        199,
        184,
        162,
        146,
        166,
        171,
        180,
        193,
        181,
        183,
        218,
        230,
        242,
        209,
        191,
        172,
        194,
        196,
        196,
        236,
        235,
        229,
        243,
        264,
        272,
        237,
        211,
        180,
        201,
        204,
        188,
        235,
        227,
        234,
        264,
        302,
        293,
        259,
        229,
        203,
        229,
        242,
        233,
        267,
        269,
        270,
        315,
        364,
        347,
        312,
        274,
        237,
        278,
        284,
        277,
        317,
        313,
        318,
        374,
        413,
        405,
        355,
        306,
        271,
        306,
        315,
        301,
        356,
        348,
        355,
        422,
        465,
        467,
        404,
        347,
        305,
        336,
        340,
        318,
        362,
        348,
        363,
        435,
        491,
        505,
        404,
        359,
        310,
        337,
        360,
        342,
        406,
        396,
        420,
        472,
        548,
        559,
        463,
        407,
        362,
        405,
        417,
        391,
        419,
        461,
        472,
        535,
        622,
        606,
        508,
        461,
        390,
        432,
    ],
    dtype=float,
)


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
    """Return the classic AirPassengers series."""
    return _AIR_PASSENGERS.copy()


def generate_henon_map(
    *,
    n_samples: int = 500,
    a: float = 1.4,
    b: float = 0.3,
    discard: int = 100,
) -> np.ndarray:
    """Generate Henon map x-component."""
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


def generate_ar1(
    *,
    n_samples: int = 500,
    phi: float = 0.8,
    random_state: int = 42,
) -> np.ndarray:
    """Generate a stationary AR(1) process: x_t = φ·x_{t-1} + ε_t.

    For |φ| < 1 the process is stationary and forecastable at every horizon.
    The closed-form AMI is AMI(h) = -½·log(1 - φ^{2h}).
    """
    if abs(phi) >= 1.0:
        raise ValueError("phi must satisfy |phi| < 1 for stationarity")
    rng = np.random.default_rng(random_state)
    x = np.zeros(n_samples, dtype=float)
    for t in range(1, n_samples):
        x[t] = phi * x[t - 1] + rng.normal(0.0, 1.0)
    return x


def generate_white_noise(
    *,
    n_samples: int = 500,
    random_state: int = 42,
) -> np.ndarray:
    """Generate Gaussian white noise (IID, zero forecastability)."""
    rng = np.random.default_rng(random_state)
    return rng.normal(0.0, 1.0, size=n_samples)


def ar1_theoretical_ami(phi: float, max_lag: int) -> np.ndarray:
    """Closed-form AMI for stationary Gaussian AR(1).

    AMI(h) = -½·log(1 - φ^{2h}) for |φ| < 1.
    """
    horizons = np.arange(1, max_lag + 1)
    return -0.5 * np.log(1.0 - phi ** (2 * horizons))


def m4_seasonal_period(frequency: str) -> int:
    """Map M4 frequency to seasonal period."""
    mapping = {
        "Yearly": 1,
        "Quarterly": 4,
        "Monthly": 12,
        "Weekly": 52,
        "Daily": 7,
        "Hourly": 24,
    }
    if frequency not in mapping:
        raise ValueError(f"Unsupported M4 frequency: {frequency}")
    return mapping[frequency]


def load_m4_subset(
    *,
    frequency: str,
    n_series: int,
    cache_dir: Path = Path("data/raw/m4"),
    random_state: int = 42,
    allow_mock: bool = False,
) -> list[tuple[str, str, int, np.ndarray]]:
    """Load deterministic M4 subset from local cache.

    Cached file format: ``{frequency}.csv`` with columns
    ``unique_id``, ``timestamp``, ``y``.
    """
    if n_series < 1:
        raise ValueError("n_series must be >= 1")

    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{frequency}.csv"
    if not path.exists():
        if not allow_mock:
            raise FileNotFoundError(
                f"Missing cached M4 file: {path}. Place a local subset file or use allow_mock=True."
            )
        rng = np.random.default_rng(random_state)
        ids = [f"{frequency[:1]}{idx:04d}" for idx in range(max(40, n_series))]
        rows: list[dict[str, str | int | float]] = []
        length = 180 if frequency == "Monthly" else 120
        for uid in ids:
            base = rng.normal(0.0, 0.8, size=length)
            seasonal = 1.2 * np.sin(
                2.0
                * np.pi
                * np.arange(length)
                / max(
                    m4_seasonal_period(frequency),
                    2,
                )
            )
            series = np.cumsum(base) * 0.05 + seasonal
            for t, value in enumerate(series):
                rows.append({"unique_id": uid, "timestamp": int(t), "y": float(value)})
        pd.DataFrame(rows).to_csv(path, index=False)

    frame = pd.read_csv(path)
    required = {"unique_id", "timestamp", "y"}
    if not required.issubset(frame.columns):
        raise ValueError(f"M4 cache file missing required columns: {sorted(required)}")

    rng = np.random.default_rng(random_state)
    ids = frame["unique_id"].drop_duplicates().to_numpy()
    if ids.size < n_series:
        raise ValueError(f"Requested {n_series} series but cache has only {ids.size}")
    selected = rng.choice(ids, size=n_series, replace=False)

    out: list[tuple[str, str, int, np.ndarray]] = []
    seasonal_period = m4_seasonal_period(frequency)
    for uid in selected:
        values = (
            frame[frame["unique_id"] == uid].sort_values("timestamp")["y"].astype(float).to_numpy()
        )
        out.append((str(uid), frequency.lower(), seasonal_period, values))
    return out


def load_bitcoin_returns(
    *,
    data_dir: Path = Path("data/raw/canonical"),
) -> np.ndarray:
    """Load daily Bitcoin log-return series from cache."""
    path = data_dir / "bitcoin_returns.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Bitcoin returns not found at {path}. Run scripts/download_data.py first."
        )
    return pd.read_csv(path)["y"].astype(float).to_numpy()


def load_gold_returns(
    *,
    data_dir: Path = Path("data/raw/canonical"),
) -> np.ndarray:
    """Load daily Gold futures log-return series from cache."""
    path = data_dir / "gold_returns.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Gold returns not found at {path}. Run scripts/download_data.py first."
        )
    return pd.read_csv(path)["y"].astype(float).to_numpy()


def load_crude_oil_returns(
    *,
    data_dir: Path = Path("data/raw/canonical"),
) -> np.ndarray:
    """Load daily Crude Oil futures log-return series from cache."""
    path = data_dir / "crude_oil_returns.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Crude oil returns not found at {path}. Run scripts/download_data.py first."
        )
    return pd.read_csv(path)["y"].astype(float).to_numpy()


def load_aapl_returns(
    *,
    data_dir: Path = Path("data/raw/canonical"),
) -> np.ndarray:
    """Load daily Apple (AAPL) log-return series from cache."""
    path = data_dir / "aapl_returns.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"AAPL returns not found at {path}. Run scripts/download_data.py first."
        )
    return pd.read_csv(path)["y"].astype(float).to_numpy()
