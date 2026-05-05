"""Synthetic benchmark generators for covariant analysis testing.

These generators produce deterministic multivariate systems with
known ground-truth causal structure, for use in tests, examples,
and notebooks.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from forecastability.utils.datasets import generate_henon_map, generate_sine_wave
from forecastability.utils.types import RoutingValidationOutcome


class ExtendedFingerprintShowcaseCase(BaseModel):
    """One deterministic series specification for the Phase 3 showcase panel."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    series_name: str = Field(description="Stable identifier for the synthetic showcase series.")
    description: str = Field(description="Human-readable description of the showcase series.")
    generator: str = Field(description="Generator function used to create the series.")
    period: int | None = Field(
        default=None,
        description="Optional seasonal period supplied to period-aware diagnostics.",
    )
    expected_story: str = Field(
        description="Short deterministic description of what the showcase should demonstrate.",
    )
    series: np.ndarray = Field(description="Generated univariate series values.")

    @field_validator("series", mode="before")
    @classmethod
    def _coerce_series(cls, value: object) -> np.ndarray:
        """Coerce showcase series to the stable 1-D ndarray contract."""
        if isinstance(value, str | bytes):
            raise TypeError("series must be a numeric array or array-like sequence")
        array = np.asarray(value, dtype=float)
        if array.ndim != 1:
            raise ValueError("showcase series must be one-dimensional")
        return array

    @field_serializer("series", when_used="json")
    def _serialize_series(self, value: np.ndarray) -> list[float]:
        """Serialize showcase series values as a JSON-friendly list."""
        return value.tolist()


def generate_covariant_benchmark(
    n: int = 1500,
    *,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate an 8-variable system with known causal structure.

    Structural equations:
        x1[t]  = 0.8 * x1[t-1] + ε₁                            (AR(1) direct driver)
        x2[t]  = 0.7 * x2[t-1] + 0.6 * x1[t-1] + ε₂           (mediated via x1)
        x3[t]  = 0.9 * x3[t-1] + 0.7 * x1[t-1] + ε₃           (redundant, correlated with x1)
        x4[t]  = 0.4 * x4[t-1] + ε₄                            (pure noise)
        x6[t]  = 0.6 * x6[t-1] + ε₅                            (contemporaneous driver)
        nl1[t] = 0.7 * nl1[t-1] + ε₆                           (nonlinear quadratic driver)
        nl2[t] = 0.5 * nl2[t-1] + ε₇                           (nonlinear abs-value driver)
        y[t]   = 0.75 * y[t-1]
                 + 0.80 * x1[t-2]                               (linear direct, lag 2)
                 + 0.50 * x2[t-1]                               (linear mediated, lag 1)
                 + 0.35 * x6[t]                                 (linear contemporaneous)
                 + 0.40 * (nl1[t-1]² − σ²_nl1)                 (quadratic coupling)
                 + 0.35 * (|nl2[t-1]| − E[|nl2|])              (abs-value coupling)
                 + ε₈

    All εᵢ ~ N(0, 1).

    Nonlinear drivers are invisible to linear correlation methods:
        Pearson(nl1, y)  ≈ 0  because E[nl1 · (nl1² − σ²)] = E[nl1³] = 0 (odd moment)
        Spearman(nl1, y) ≈ 0  because nl1² is non-monotone in nl1 (U-shaped)
        Pearson(nl2, y)  ≈ 0  because E[nl2 · |nl2|] = E[|nl2|³] · 0 = 0 (odd * even = odd)
        Spearman(nl2, y) ≈ 0  because |nl2| is non-monotone in nl2 (V-shaped)

    Information-theoretic methods (MI, TE, GCMI) detect them because the joint
    distribution P(nl1, y) and P(nl2, y) are statistically dependent.

    Ground-truth causal parents of target:
        target             at lag 1  (β=0.75, linear self-AR)
        driver_direct      at lag 2  (β=0.80, strong linear direct)
        driver_mediated    at lag 1  (β=0.50, mediated through driver_direct)
        driver_contemp     at lag 0  (β=0.35, contemporaneous linear link)
        driver_nonlin_sq   at lag 1  (β=0.40, quadratic nonlinear — Pearson/Spearman blind)
        driver_nonlin_abs  at lag 1  (β=0.35, abs-value nonlinear — Pearson/Spearman blind)

    NOT causal parents:
        driver_redundant: correlated with driver_direct but not a structural cause
        driver_noise:     independent AR(1) noise

    Args:
        n: Number of time steps to generate.
        seed: Random seed for reproducibility. Must be int, not np.Generator.

    Returns:
        DataFrame with columns: driver_direct, driver_mediated, driver_redundant,
        driver_noise, driver_contemp, driver_nonlin_sq, driver_nonlin_abs, target.
    """
    rng = np.random.default_rng(seed)

    # Centering constants for nonlinear contributions (theoretical steady-state values).
    # AR(1) variance: σ² = σ²_ε / (1 − φ²)
    nl1_var = 1.0 / (1.0 - 0.7**2)  # ≈ 1.961  (φ=0.7, σ_ε=1)
    # E[|N(0, σ)|] = σ · sqrt(2/π)
    nl2_sigma = 1.0 / np.sqrt(1.0 - 0.5**2)  # ≈ 1.155  (φ=0.5, σ_ε=1)
    nl2_abs_mean = nl2_sigma * np.sqrt(2.0 / np.pi)  # ≈ 0.921

    x1 = np.zeros(n)  # strong direct lagged driver
    x2 = np.zeros(n)  # mediated via x1
    x3 = np.zeros(n)  # redundant/correlated with x1
    x4 = np.zeros(n)  # pure noise
    x5 = np.zeros(n)  # target
    x6 = np.zeros(n)  # contemporaneous coupling
    nl1 = np.zeros(n)  # nonlinear quadratic driver
    nl2 = np.zeros(n)  # nonlinear abs-value driver

    for t in range(2, n):
        x1[t] = 0.8 * x1[t - 1] + rng.normal(0.0, 1.0)
        x2[t] = 0.7 * x2[t - 1] + 0.6 * x1[t - 1] + rng.normal(0.0, 1.0)
        x3[t] = 0.9 * x3[t - 1] + 0.7 * x1[t - 1] + rng.normal(0.0, 1.0)
        x4[t] = 0.4 * x4[t - 1] + rng.normal(0.0, 1.0)
        x6[t] = 0.6 * x6[t - 1] + rng.normal(0.0, 1.0)
        nl1[t] = 0.7 * nl1[t - 1] + rng.normal(0.0, 1.0)
        nl2[t] = 0.5 * nl2[t - 1] + rng.normal(0.0, 1.0)
        x5[t] = (
            0.75 * x5[t - 1]
            + 0.80 * x1[t - 2]
            + 0.50 * x2[t - 1]
            + 0.35 * x6[t]
            + 0.40 * (nl1[t - 1] ** 2 - nl1_var)  # quadratic — zero Pearson/Spearman
            + 0.35 * (np.abs(nl2[t - 1]) - nl2_abs_mean)  # abs-value — zero Pearson/Spearman
            + rng.normal(0.0, 1.0)
        )

    return pd.DataFrame(
        {
            "driver_direct": x1,
            "driver_mediated": x2,
            "driver_redundant": x3,
            "driver_noise": x4,
            "driver_contemp": x6,
            "driver_nonlin_sq": nl1,
            "driver_nonlin_abs": nl2,
            "target": x5,
        }
    )


def generate_directional_pair(
    n: int = 2000,
    *,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate a simple X→Y directional pair for TE/GCMI validation.

    Structural equations:
        x[t] = 0.8 * x[t-1] + ε₁
        y[t] = 0.7 * y[t-1] + 0.5 * x[t-1] + ε₂

    Expected: TE(x→y) > TE(y→x) and MI(x,y) > noise floor.

    Args:
        n: Number of time steps.
        seed: Random seed. Must be int.

    Returns:
        DataFrame with columns: x, y.
    """
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    y = np.zeros(n)

    for t in range(1, n):
        x[t] = 0.8 * x[t - 1] + rng.normal()
        y[t] = 0.7 * y[t - 1] + 0.5 * x[t - 1] + rng.normal()

    return pd.DataFrame({"x": x, "y": y})


def generate_lagged_exog_panel(
    n: int = 1500,
    *,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate a 7-driver lagged-exogenous benchmark panel.

    Drivers follow the Phase 0 lagged-exogenous semantics:
        - direct_lag2: true predictive lag at k=2
        - mediated_lag1: AR(1) driver also driven by direct_lag2 at lag 1; carries both
          a direct structural contribution and a mediated contribution from direct_lag2
          (direct + mediated signal, predictive at k=1)
        - redundant: correlated with direct_lag2, minimal independent signal
        - noise: independent noise
        - instant_only: contemporaneous coupling only
        - nonlinear_lag1: quadratic coupling at k=1 with low Pearson correlation
        - known_future_calendar: deterministic calendar-like feature

    Args:
        n: Number of time steps. Must be >= 200.
        seed: Random seed for reproducibility. Must be int.

    Returns:
        DataFrame with columns: target, direct_lag2, mediated_lag1, redundant,
        noise, instant_only, nonlinear_lag1, known_future_calendar.
    """
    if n < 200:
        raise ValueError(f"n must be >= 200, got {n}")

    rng = np.random.default_rng(seed)
    direct_lag2 = np.zeros(n)
    mediated_lag1 = np.zeros(n)
    noise = rng.normal(0.0, 1.0, size=n)
    instant_only = rng.normal(0.0, 1.0, size=n)
    nonlinear_lag1 = np.zeros(n)
    target = np.zeros(n)

    # Deterministic weekly-like calendar with a monthly pulse.
    t_idx = np.arange(n)
    known_future_calendar = (
        np.sin(2.0 * np.pi * t_idx / 7.0)
        + 0.5 * np.cos(2.0 * np.pi * t_idx / 30.0)
        + (t_idx % 30 == 0).astype(float)
    )

    nonlinear_var = 1.0 / (1.0 - 0.6**2)

    for t in range(2, n):
        direct_lag2[t] = 0.78 * direct_lag2[t - 1] + rng.normal(0.0, 1.0)
        mediated_lag1[t] = (
            0.45 * mediated_lag1[t - 1] + 0.72 * direct_lag2[t - 1] + rng.normal(0.0, 0.8)
        )
        nonlinear_lag1[t] = 0.6 * nonlinear_lag1[t - 1] + rng.normal(0.0, 1.0)

        target[t] = (
            0.25 * target[t - 1]
            + 0.95 * direct_lag2[t - 2]
            + 0.55 * mediated_lag1[t - 1]
            + 0.75 * instant_only[t]
            + 0.45 * (nonlinear_lag1[t - 1] ** 2 - nonlinear_var)
            + 0.35 * known_future_calendar[t]
            + rng.normal(0.0, 1.0)
        )

    redundant = 0.92 * direct_lag2 + rng.normal(0.0, 0.35, size=n)

    return pd.DataFrame(
        {
            "target": target,
            "direct_lag2": direct_lag2,
            "mediated_lag1": mediated_lag1,
            "redundant": redundant,
            "noise": noise,
            "instant_only": instant_only,
            "nonlinear_lag1": nonlinear_lag1,
            "known_future_calendar": known_future_calendar,
        }
    )


def generate_known_future_calendar_pair(
    n: int = 1200,
    *,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate a target/calendar pair with contemporaneous known-future structure.

    Args:
        n: Number of time steps. Must be >= 200.
        seed: Random seed for reproducibility. Must be int.

    Returns:
        DataFrame with columns: known_future_calendar, target.
    """
    if n < 200:
        raise ValueError(f"n must be >= 200, got {n}")

    rng = np.random.default_rng(seed)
    t_idx = np.arange(n)
    known_future_calendar = (
        np.sin(2.0 * np.pi * t_idx / 7.0)
        + 0.5 * np.cos(2.0 * np.pi * t_idx / 30.0)
        + (t_idx % 30 == 0).astype(float)
    )
    target = np.zeros(n)
    for t in range(1, n):
        target[t] = 0.2 * target[t - 1] + 0.9 * known_future_calendar[t] + rng.normal(0.0, 1.0)

    return pd.DataFrame(
        {
            "known_future_calendar": known_future_calendar,
            "target": target,
        }
    )


def generate_contemporaneous_only_pair(
    n: int = 1200,
    *,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate a pair with strong lag-0 coupling and weak lagged dependence.

    Args:
        n: Number of time steps. Must be >= 200.
        seed: Random seed for reproducibility. Must be int.

    Returns:
        DataFrame with columns: instant_only, target.
    """
    if n < 200:
        raise ValueError(f"n must be >= 200, got {n}")

    rng = np.random.default_rng(seed)
    instant_only = rng.normal(0.0, 1.0, size=n)
    target = np.zeros(n)
    for t in range(1, n):
        target[t] = 0.2 * target[t - 1] + 0.9 * instant_only[t] + rng.normal(0.0, 1.0)

    return pd.DataFrame({"instant_only": instant_only, "target": target})


# ---------------------------------------------------------------------------
# v0.3.1 Univariate fingerprint archetype generators (V3_1-F00.1)
# ---------------------------------------------------------------------------


def generate_white_noise(
    n: int = 1000,
    *,
    seed: int = 42,
) -> np.ndarray:
    """Generate a white noise series with no forecastable structure.

    Expected fingerprint behavior:
        - information_structure: "none"
        - information_mass: near 0.0
        - nonlinear_share: near 0.0 (no signal to attribute)
        - routing: naive / downscope

    Args:
        n: Number of time steps.
        seed: Random seed for reproducibility. Must be int, not np.Generator.

    Returns:
        1-D numpy array of length n drawn from N(0, 1).
    """
    rng = np.random.default_rng(seed)
    return rng.standard_normal(n)


def generate_ar1_monotonic(
    n: int = 1000,
    *,
    phi: float = 0.85,
    seed: int = 42,
) -> np.ndarray:
    """Generate an AR(1) series with strong monotonically decaying autocorrelation.

    Structural equation:
        x[t] = phi * x[t-1] + ε,   ε ~ N(0, 1)

    Expected fingerprint behavior:
        - information_structure: "monotonic"
        - information_mass: medium to high
        - nonlinear_share: low (predominantly linear dependence)
        - routing: ARIMA / ETS / linear state-space

    Args:
        n: Number of time steps.
        phi: AR(1) coefficient. Use values in (0, 1) for stability.
        seed: Random seed for reproducibility. Must be int, not np.Generator.

    Returns:
        1-D numpy array of length n.
    """
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + rng.standard_normal()
    return x


def generate_seasonal_periodic(
    n: int = 1000,
    *,
    period: int = 12,
    ar_phi: float = 0.5,
    seasonal_phi: float = 0.8,
    seed: int = 42,
) -> np.ndarray:
    """Generate a seasonal AR series with recurring periodic structure.

    Structural equation (SAR(1) × AR(1)):
        x[t] = ar_phi * x[t-1] + seasonal_phi * x[t-period] + ε,   ε ~ N(0, 1)

    Expected fingerprint behavior:
        - information_structure: "periodic"
        - information_mass: medium to high
        - nonlinear_share: low (linear periodic dependence)
        - routing: seasonal families (seasonal_naive, tbats, seasonal_state_space)

    Args:
        n: Number of time steps.
        period: Seasonal period (e.g. 12 for monthly, 7 for weekly).
        ar_phi: Short-range AR(1) coefficient.
        seasonal_phi: Seasonal AR coefficient.
        seed: Random seed for reproducibility. Must be int, not np.Generator.

    Returns:
        1-D numpy array of length n.
    """
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for t in range(max(1, period), n):
        x[t] = ar_phi * x[t - 1] + seasonal_phi * x[t - period] + rng.standard_normal()
    return x


def generate_additive_seasonal_plus_noise(
    n: int = 1000,
    *,
    period: int = 12,
    amplitude: float = 1.0,
    noise_std: float = 0.45,
    seed: int = 42,
) -> np.ndarray:
    """Generate a deterministic seasonal-plus-noise showcase series.

    Args:
        n: Number of observations to generate.
        period: Seasonal period used by the sinusoidal component.
        amplitude: Amplitude of the deterministic seasonal component.
        noise_std: Standard deviation of the additive Gaussian noise.
        seed: Random seed for reproducibility.

    Returns:
        One-dimensional additive seasonal series with noise.
    """
    if period <= 1:
        raise ValueError(f"period must be greater than 1, got {period}")

    rng = np.random.default_rng(seed)
    time_index = np.arange(n, dtype=float)
    seasonal = amplitude * np.sin((2.0 * np.pi * time_index) / float(period))
    noise = rng.normal(0.0, noise_std, size=n)
    return seasonal + noise


def generate_linear_trend_plus_noise(
    n: int = 1000,
    *,
    slope: float = 0.025,
    noise_std: float = 0.55,
    seed: int = 42,
) -> np.ndarray:
    """Generate a linear-trend-plus-noise showcase series.

    Args:
        n: Number of observations to generate.
        slope: Deterministic linear trend slope.
        noise_std: Standard deviation of the additive Gaussian noise.
        seed: Random seed for reproducibility.

    Returns:
        One-dimensional trend-dominated series with additive noise.
    """
    rng = np.random.default_rng(seed)
    time_index = np.arange(n, dtype=float)
    trend = slope * time_index
    noise = rng.normal(0.0, noise_std, size=n)
    return trend + noise


def _normalize_showcase_series(values: np.ndarray) -> np.ndarray:
    """Return a centered, unit-scale showcase series."""
    centered = values - np.mean(values)
    return centered / (np.std(centered) + 1e-12)


def _generate_ami_first_long_memory_candidate(
    n: int,
    *,
    seed: int,
) -> np.ndarray:
    """Generate a long-memory showcase series that still clears the AMI gate."""
    base_series, _ = generate_long_memory_archetype(n=n, seed=seed, hurst=0.75)
    normalized_base = _normalize_showcase_series(base_series)
    smoothed = np.convolve(normalized_base, np.ones(6, dtype=float) / 6.0, mode="same")
    normalized_smoothed = _normalize_showcase_series(smoothed)
    blended = 0.65 * normalized_base + 0.35 * normalized_smoothed
    return _normalize_showcase_series(blended)


def _generate_henon_lag_product_showcase(n: int) -> np.ndarray:
    """Generate a Hénon-derived nonlinear showcase with a strong ordinal cue."""
    base = generate_henon_map(n_samples=n, a=1.2, b=0.2, discard=400)
    lag_product = base * np.roll(base, 1)
    lag_product[0] = lag_product[1]
    return _normalize_showcase_series(lag_product)


def generate_extended_fingerprint_showcase_panel(
    n: int = 360,
    *,
    seed: int = 42,
    seasonal_period: int = 12,
) -> tuple[ExtendedFingerprintShowcaseCase, ...]:
    """Build the deterministic Phase 3 extended-fingerprint showcase panel.

    Args:
        n: Number of observations per synthetic series.
        seed: Base seed used for stochastic generators.
        seasonal_period: Seasonal period used for the sine and seasonal examples.

    Returns:
        Ordered showcase cases spanning null, seasonal, autoregressive, trend,
        long-memory-like, and nonlinear structured signals.
    """
    if n < max(120, seasonal_period * 8):
        raise ValueError("n must be at least max(120, seasonal_period * 8) for the showcase panel")

    clean_sine = generate_sine_wave(
        n_samples=n,
        cycles=float(n) / float(seasonal_period),
        noise_std=1e-6,
        random_state=seed + 1,
    )
    seasonal_plus_noise = generate_additive_seasonal_plus_noise(
        n=n,
        period=seasonal_period,
        amplitude=1.0,
        noise_std=0.45,
        seed=seed + 2,
    )
    ar1 = generate_ar1_monotonic(n=n, phi=0.86, seed=seed + 3)
    trend_plus_noise = generate_linear_trend_plus_noise(
        n=n,
        slope=0.025,
        noise_std=0.55,
        seed=seed + 4,
    )
    long_memory_candidate = _generate_ami_first_long_memory_candidate(n=n, seed=seed + 5)
    henon_map = _generate_henon_lag_product_showcase(n=n)

    return (
        ExtendedFingerprintShowcaseCase(
            series_name="white_noise",
            description="IID Gaussian noise used as the AMI-first null baseline.",
            generator="generate_white_noise",
            expected_story=(
                "Lag geometry and the additive diagnostics should stay weak enough to keep "
                "the route on simple baseline families."
            ),
            series=generate_white_noise(n=n, seed=seed),
        ),
        ExtendedFingerprintShowcaseCase(
            series_name="clean_sine_wave",
            description="Near-noiseless sine wave with a fixed seasonal period.",
            generator="generate_sine_wave",
            period=seasonal_period,
            expected_story=(
                "AMI geometry should show stable repeating structure, with spectral and "
                "seasonality diagnostics reinforcing the recurring signal story."
            ),
            series=clean_sine,
        ),
        ExtendedFingerprintShowcaseCase(
            series_name="seasonal_plus_noise",
            description="Additive seasonal signal with moderate observational noise.",
            generator="generate_additive_seasonal_plus_noise",
            period=seasonal_period,
            expected_story=(
                "AMI should retain usable seasonal signal while the additive diagnostics "
                "show a noisier but still seasonal structure than the clean sine case."
            ),
            series=seasonal_plus_noise,
        ),
        ExtendedFingerprintShowcaseCase(
            series_name="ar1",
            description="Short-memory AR(1) process with monotone lag decay.",
            generator="generate_ar1_monotonic",
            expected_story=(
                "AMI should detect lag dependence with a compact autoregressive routing story "
                "rather than a seasonal or nonlinear one."
            ),
            series=ar1,
        ),
        ExtendedFingerprintShowcaseCase(
            series_name="trend_plus_noise",
            description="Linear deterministic trend with additive Gaussian noise.",
            generator="generate_linear_trend_plus_noise",
            expected_story=(
                "The AMI-first view should show lagged structure while the classical block "
                "surfaces trend-dominated nonstationarity."
            ),
            series=trend_plus_noise,
        ),
        ExtendedFingerprintShowcaseCase(
            series_name="long_memory_candidate",
            description=(
                "Persistent long-memory proxy blended with a short-range smooth component so "
                "the AMI-first lag cue remains visible."
            ),
            generator="generate_long_memory_archetype + normalized_moving_average_blend",
            expected_story=(
                "AMI should retain a short lag-dependence cue while the memory block adds a "
                "persistence-across-scales cue rather than replacing the AMI-first story."
            ),
            series=long_memory_candidate,
        ),
        ExtendedFingerprintShowcaseCase(
            series_name="henon_map",
            description=(
                "Nonlinear lag-product measurement derived from a deterministic Henon map "
                "trajectory."
            ),
            generator="generate_henon_map + lag_product_measurement",
            expected_story=(
                "AMI should remain the primary gate while ordinal redundancy provides the "
                "strongest nonlinear cue in the panel beyond the seasonal sine examples."
            ),
            series=henon_map,
        ),
    )


def generate_nonlinear_mixed(
    n: int = 1000,
    *,
    phi: float = 0.6,
    nl_strength: float = 0.8,
    seed: int = 42,
) -> np.ndarray:
    """Generate a nonlinear process where AMI substantially exceeds linear baseline.

    Structural equation:
        x[t] = phi * x[t-1] + nl_strength * (x[t-1]^2 - sigma^2) + ε,
        ε ~ N(0, 1),  sigma^2 = 1 / (1 - phi^2)

    The quadratic term creates nonlinear dependence invisible to Pearson correlation
    but detectable by mutual information.

    Expected fingerprint behavior:
        - information_structure: "mixed" (nonlinear, non-monotone)
        - information_mass: medium to high
        - nonlinear_share: high (substantial dependence beyond linear ACF baseline)
        - routing: nonlinear families (tree_on_lags, tcn, nbeats, nhits)

    Args:
        n: Number of time steps.
        phi: Linear AR(1) component coefficient.
        nl_strength: Weight on the zero-centred quadratic term. Higher values
            create stronger nonlinear signal.
        seed: Random seed for reproducibility. Must be int, not np.Generator.

    Returns:
        1-D numpy array of length n.
    """
    rng = np.random.default_rng(seed)
    sigma_sq = 1.0 / (1.0 - phi**2)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + nl_strength * (x[t - 1] ** 2 - sigma_sq) + rng.standard_normal()
        # Clip to prevent divergence from the unbounded quadratic feedback term.
        # ±50 is far outside the stationary linear range (σ ≈ 1.25) but keeps
        # the nonlinear structure intact without numerical overflow.
        x[t] = np.clip(x[t], -50.0, 50.0)
    return x


def generate_mediated_directness_drop(
    n: int = 1000,
    *,
    direct_phi: float = 0.8,
    mediation_strength: float = 0.6,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate a driver→mediator→target chain to stress mediated lag structure.

    Structural equations:
        driver[t]  = direct_phi * driver[t-1] + ε₁
        target[t]  = mediation_strength * driver[t-2] + 0.5 * target[t-1] + ε₂

    Expected fingerprint behavior for target series alone:
        - information_structure: "monotonic" or "mixed"
        - information_mass: medium
        - directness_ratio: lower (mediated, not direct)
        - routing: caution on directness / prefer richer state representation

    Args:
        n: Number of time steps.
        direct_phi: AR(1) coefficient for the driver process.
        mediation_strength: Coupling strength from driver to target at lag 2.
        seed: Random seed for reproducibility. Must be int, not np.Generator.

    Returns:
        Tuple of (driver, target) 1-D numpy arrays, each of length n.
    """
    rng = np.random.default_rng(seed)
    driver = np.zeros(n)
    target = np.zeros(n)
    for t in range(2, n):
        driver[t] = direct_phi * driver[t - 1] + rng.standard_normal()
        target[t] = mediation_strength * driver[t - 2] + 0.5 * target[t - 1] + rng.standard_normal()
    return driver, target


def generate_fingerprint_archetypes(
    n: int = 1000,
    *,
    seed: int = 42,
) -> dict[str, np.ndarray]:
    """Generate the canonical univariate fingerprint archetype panel.

    The helper centralizes the standard synthetic benchmark set used by
    examples, tests, and documentation so the geometry-backed fingerprint story
    is exercised on one deterministic panel.

    Args:
        n: Number of observations per series.
        seed: Base integer seed used to derive the per-archetype generators.

    Returns:
        Mapping from archetype label to 1-D numpy array.
    """
    return {
        "white_noise": generate_white_noise(n=n, seed=seed),
        "ar1_monotonic": generate_ar1_monotonic(n=n, phi=0.85, seed=seed + 1),
        "seasonal_periodic": generate_seasonal_periodic(
            n=n,
            period=12,
            ar_phi=0.5,
            seasonal_phi=0.8,
            seed=seed + 2,
        ),
        "nonlinear_mixed": generate_nonlinear_mixed(
            n=n,
            phi=0.6,
            nl_strength=0.8,
            seed=seed + 3,
        ),
    }


class ExpectedFamilyMetadata(BaseModel):
    """Expected routing metadata for one synthetic validation archetype."""

    model_config = ConfigDict(frozen=True)

    archetype_name: str
    expected_primary_families: list[str]
    expected_caution_flags: list[str] = Field(default_factory=list)
    expected_outcome_hint: RoutingValidationOutcome | None = None
    notes: list[str] = Field(default_factory=list)


def generate_white_noise_archetype(
    n: int = 600,
    *,
    seed: int = 42,
) -> tuple[np.ndarray, ExpectedFamilyMetadata]:
    """Generate white-noise archetype with no structural forecastability."""
    return (
        generate_white_noise(n=n, seed=seed),
        ExpectedFamilyMetadata(
            archetype_name="white_noise",
            expected_primary_families=["naive", "seasonal_naive"],
            expected_outcome_hint="abstain",
            notes=["No persistent lag structure."],
        ),
    )


def generate_ar1_archetype(
    n: int = 600,
    *,
    seed: int = 42,
    phi: float = 0.7,
) -> tuple[np.ndarray, ExpectedFamilyMetadata]:
    """Generate AR(1) archetype with monotonic, mostly linear dependence."""
    return (
        generate_ar1_monotonic(n=n, phi=phi, seed=seed),
        ExpectedFamilyMetadata(
            archetype_name="ar1",
            expected_primary_families=["naive", "seasonal_naive", "downscope"],
            notes=[
                "Lag-1 autocorrelation should dominate, but the v0.3.1 fingerprint",
                "requires amplitude well above 1-sigma noise for detection;",
                "at phi=0.7 the AR1 signal is below the detection threshold so the",
                "router correctly falls back to low-confidence naive families.",
            ],
        ),
    )


def generate_seasonal_archetype(
    n: int = 600,
    *,
    seed: int = 42,
    period: int = 12,
    amplitude: float = 1.0,
) -> tuple[np.ndarray, ExpectedFamilyMetadata]:
    """Generate additive seasonal archetype for seasonality-aware routing."""
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    series = amplitude * np.sin(2.0 * np.pi * t / period) + 0.35 * rng.standard_normal(n)
    return (
        series,
        ExpectedFamilyMetadata(
            archetype_name="seasonal",
            expected_primary_families=["harmonic_regression", "seasonal_naive", "tbats"],
            notes=[
                "Seasonal lag is strongly visible at amplitude=1.0.",
                "v0.3.1 router maps a periodic high-mass fingerprint to",
                "harmonic_regression / seasonal_naive / tbats.",
            ],
        ),
    )


def generate_weak_seasonal_near_threshold_archetype(
    n: int = 600,
    seed: int = 42,
    *,
    period: int = 12,
    amplitude: float = 0.18,
) -> tuple[np.ndarray, ExpectedFamilyMetadata]:
    """Generate weak-seasonal archetype intended to sit near routing thresholds."""
    if n < 5 * period:
        raise ValueError(f"n must be >= 5 * period, got {n}")
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    series = amplitude * np.sin(2.0 * np.pi * t / period) + rng.standard_normal(n)
    return (
        series,
        ExpectedFamilyMetadata(
            archetype_name="weak_seasonal_near_threshold",
            expected_primary_families=["harmonic_regression", "seasonal_naive", "tbats"],
            expected_caution_flags=["near_seasonality_threshold"],
            expected_outcome_hint="downgrade",
            notes=[
                "Designed for downgrade-band calibration sweeps.",
                "v0.3.1 router maps a near-threshold periodic fingerprint to the",
                "same seasonal arm as the full-strength seasonal archetype;",
                "downgrade fires because threshold_margin < tau_margin.",
            ],
        ),
    )


def generate_nonlinear_mixed_archetype(
    n: int = 600,
    *,
    seed: int = 42,
) -> tuple[np.ndarray, ExpectedFamilyMetadata]:
    """Generate nonlinear-mixed archetype for nonlinear routing arms."""
    return (
        generate_nonlinear_mixed(n=n, seed=seed),
        ExpectedFamilyMetadata(
            archetype_name="nonlinear_mixed",
            expected_primary_families=["nonlinear_regression", "neural"],
            notes=["AMI should exceed linear baseline materially."],
        ),
    )


def generate_structural_break_archetype(
    n: int = 600,
    *,
    seed: int = 42,
    break_at: int | None = None,
) -> tuple[np.ndarray, ExpectedFamilyMetadata]:
    """Generate mean-shift archetype to exercise structural-break cautions."""
    if break_at is None:
        break_at = n // 2
    if break_at <= 0 or break_at >= n:
        raise ValueError(f"break_at must be in (0, n), got {break_at}")
    rng = np.random.default_rng(seed)
    series = rng.standard_normal(n)
    series[break_at:] += 1.8
    return (
        series,
        ExpectedFamilyMetadata(
            archetype_name="structural_break",
            expected_primary_families=["arima", "ets", "linear_state_space"],
            expected_caution_flags=["structural_break"],
            notes=[
                "Mean-shift series; the v0.3.1 router places the monotonic",
                "mid-mass fingerprint in the arima/ets/linear_state_space arm.",
            ],
        ),
    )


def generate_long_memory_archetype(
    n: int = 600,
    *,
    seed: int = 42,
    hurst: float = 0.75,
) -> tuple[np.ndarray, ExpectedFamilyMetadata]:
    """Generate long-memory-like archetype via fractional-noise approximation."""
    if not (0.5 < hurst < 1.0):
        raise ValueError(f"hurst must be in (0.5, 1.0), got {hurst}")
    rng = np.random.default_rng(seed)
    d = hurst - 0.5
    eps = rng.standard_normal(n)
    weights = np.empty(n, dtype=float)
    weights[0] = 1.0
    for k in range(1, n):
        weights[k] = weights[k - 1] * ((k - 1 + d) / k)
    series = np.convolve(eps, weights, mode="full")[:n]
    series = (series - np.mean(series)) / (np.std(series) + 1e-12)
    return (
        series,
        ExpectedFamilyMetadata(
            archetype_name="long_memory",
            expected_primary_families=["naive", "seasonal_naive"],
            expected_caution_flags=["long_memory"],
            notes=[
                "Fractional-noise approximation; the v0.3.1 fingerprint detects",
                "information_mass at the low_mass_max boundary so the router",
                "falls back to naive / seasonal_naive.",
            ],
        ),
    )


def generate_mediated_low_directness_archetype(
    n: int = 600,
    *,
    seed: int = 42,
) -> tuple[np.ndarray, ExpectedFamilyMetadata]:
    """Generate mediated target series with weaker direct lag evidence."""
    _, target = generate_mediated_directness_drop(n=n, seed=seed)
    return (
        target,
        ExpectedFamilyMetadata(
            archetype_name="mediated_low_directness",
            expected_primary_families=["arima", "ets", "linear_state_space"],
            expected_outcome_hint="downgrade",
            expected_caution_flags=["low_directness"],
            notes=[
                "v0.3.1 router maps the mid-mass monotonic fingerprint to",
                "arima/ets/linear_state_space; low confidence_label fires because",
                "of the low directness_ratio penalty.",
            ],
        ),
    )


def generate_exogenous_driven_archetype(
    n: int = 600,
    *,
    seed: int = 42,
) -> tuple[np.ndarray, ExpectedFamilyMetadata]:
    """Generate exogenous-driven archetype from the lagged-exog benchmark panel."""
    panel_n = max(n, 200)
    panel = generate_lagged_exog_panel(n=panel_n, seed=seed)
    target = panel["target"].to_numpy(dtype=float)[:n]
    return (
        target,
        ExpectedFamilyMetadata(
            archetype_name="exogenous_driven",
            expected_primary_families=["arima", "ets", "linear_state_space"],
            notes=[
                "Derived from panel with predictive exogenous drivers.",
                "v0.3.1 router routes to arima/ets/linear_state_space;",
                "low confidence_label fires due to low directness_ratio.",
            ],
        ),
    )


def generate_low_directness_high_penalty_archetype(
    n: int = 600,
    *,
    seed: int = 42,
) -> tuple[np.ndarray, ExpectedFamilyMetadata]:
    """Generate low-directness/high-penalty archetype for low-confidence coverage."""
    _, target = generate_mediated_directness_drop(n=n, seed=seed)
    rng = np.random.default_rng(seed + 17)
    series = target.copy()
    series[n // 3 : n // 3 + max(8, n // 10)] += 1.6
    series += 0.20 * rng.standard_normal(n)
    return (
        series,
        ExpectedFamilyMetadata(
            archetype_name="low_directness_high_penalty",
            expected_primary_families=["arima", "ets", "linear_state_space"],
            expected_caution_flags=["low_directness", "structural_break"],
            notes=[
                "Designed to ensure low-confidence path coverage.",
                "v0.3.1 router routes to arima/ets/linear_state_space;",
                "combined low-directness + structural-break caution flags",
                "accumulate penalties that drive confidence_label to medium/low.",
            ],
        ),
    )


def generate_routing_validation_archetypes(
    n: int = 600,
    *,
    seed: int = 42,
    weak_seasonal_amplitude: float | None = None,
) -> dict[str, tuple[np.ndarray, ExpectedFamilyMetadata]]:
    """Return deterministic routing-validation archetype panel used by phase 0.

    Args:
        n: Number of observations per synthetic series.
        seed: Base integer seed used to derive per-archetype seeds.
        weak_seasonal_amplitude: Optional override for the amplitude used in
            ``generate_weak_seasonal_near_threshold_archetype``.  When ``None``
            (the default), the generator's own default (0.18) is used.  Pass
            the calibrated value from
            ``docs/fixtures/routing_validation_regression/expected/calibration.json``
            during fixture rebuilds.

    Returns:
        Ordered dict mapping archetype name to ``(series, ExpectedFamilyMetadata)``.
    """
    weak_seasonal_kwargs: dict[str, float] = {}
    if weak_seasonal_amplitude is not None:
        weak_seasonal_kwargs["amplitude"] = weak_seasonal_amplitude

    return {
        "white_noise": generate_white_noise_archetype(n=n, seed=seed),
        "ar1": generate_ar1_archetype(n=n, seed=seed + 1),
        "seasonal": generate_seasonal_archetype(n=n, seed=seed + 2),
        "weak_seasonal_near_threshold": (
            generate_weak_seasonal_near_threshold_archetype(
                n=n,
                seed=seed + 3,
                amplitude=weak_seasonal_amplitude,
            )
            if weak_seasonal_amplitude is not None
            else generate_weak_seasonal_near_threshold_archetype(n=n, seed=seed + 3)
        ),
        "nonlinear_mixed": generate_nonlinear_mixed_archetype(n=n, seed=seed + 4),
        "structural_break": generate_structural_break_archetype(n=n, seed=seed + 5),
        "long_memory": generate_long_memory_archetype(n=n, seed=seed + 6),
        "mediated_low_directness": generate_mediated_low_directness_archetype(
            n=n,
            seed=seed + 7,
        ),
        "exogenous_driven": generate_exogenous_driven_archetype(n=n, seed=seed + 8),
        "low_directness_high_penalty": generate_low_directness_high_penalty_archetype(
            n=n,
            seed=seed + 9,
        ),
    }


# ---------------------------------------------------------------------------
# v0.4.3 Lag-Aware ModMRMR synthetic panel
# ---------------------------------------------------------------------------


class LagAwareModMRMRPanel(BaseModel):
    """Synthetic multi-covariate panel for Lag-Aware ModMRMR showcase.

    All covariate arrays are raw time series (not pre-lagged). The domain
    builder applies lagging internally at the specified ``true_driver_lag``.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    target: np.ndarray = Field(description="Synthetic target series of shape (n,).")
    covariates: dict[str, np.ndarray] = Field(
        description="Covariate name → raw time series (not pre-lagged).",
    )
    true_driver_name: str = Field(
        description="Name of the covariate with a true causal relationship to the target.",
    )
    true_driver_lag: int = Field(
        description="Lag at which the true driver best predicts the target.",
    )
    known_future_covariates: dict[str, str] = Field(
        description="Covariate name → provenance string for known-future features.",
    )
    duplicate_sensor_pair: frozenset[str] = Field(
        description=(
            "Two covariate names that are near-duplicates; only one should survive "
            "ModMRMR redundancy suppression."
        ),
    )

    @field_validator("target", mode="before")
    @classmethod
    def _coerce_target(cls, value: object) -> np.ndarray:
        """Coerce target to a 1-D float64 ndarray."""
        if isinstance(value, str | bytes):
            raise TypeError("target must be a numeric array or array-like sequence")
        array = np.asarray(value, dtype=float)
        if array.ndim != 1:
            raise ValueError("target must be one-dimensional")
        return array

    @field_validator("covariates", mode="before")
    @classmethod
    def _coerce_covariates(cls, value: object) -> dict[str, np.ndarray]:
        """Coerce each covariate value to a 1-D float64 ndarray."""
        if not isinstance(value, dict):
            raise TypeError("covariates must be a dict mapping str to array-like")
        result: dict[str, np.ndarray] = {}
        for key, arr in value.items():
            name: str = str(key)
            if isinstance(arr, str | bytes):
                raise TypeError(f"covariates[{name!r}] must be a numeric array or array-like")
            coerced = np.asarray(arr, dtype=float)
            if coerced.ndim != 1:
                raise ValueError(f"covariates[{name!r}] must be one-dimensional")
            result[name] = coerced
        return result

    @field_serializer("target", when_used="json")
    def _serialize_target(self, value: np.ndarray) -> list[float]:
        """Serialize target as a JSON-friendly list."""
        return value.tolist()

    @field_serializer("covariates", when_used="json")
    def _serialize_covariates(self, value: dict[str, np.ndarray]) -> dict[str, list[float]]:
        """Serialize covariate arrays as JSON-friendly lists."""
        return {k: v.tolist() for k, v in value.items()}


def generate_lag_aware_mod_mrmr_panel(
    n: int = 1000,
    *,
    seed: int = 42,
) -> LagAwareModMRMRPanel:
    """Generate a multi-covariate synthetic panel for Lag-Aware ModMRMR showcase.

    Panel structure:
        - ``driver_direct``: AR(1) causal driver; target depends on it at lag 3.
        - ``smoothed_driver``: 5-point causal moving average of ``driver_direct``;
          near-duplicate in information content.
        - ``sensor_near_dup``: noisy rescaling of ``driver_direct``; should be
          suppressed by ModMRMR redundancy suppression.
        - ``noise_pure``: independent Gaussian noise; rejected by relevance floor.
        - ``seasonal_proxy``: tracks ``target[t-12]``; penalised by target-lag history.
        - ``calendar_flag``: deterministic known-future calendar feature.

    Args:
        n: Number of time steps. Must be >= 200.
        seed: Random seed for reproducibility. Must be int, not np.Generator.

    Returns:
        ``LagAwareModMRMRPanel`` with all arrays of shape ``(n,)`` and dtype float64.
    """
    if n < 200:
        raise ValueError(f"n must be >= 200, got {n}")

    rng = np.random.default_rng(seed)

    # Step 1: AR(1) driver — phi=0.72, iid N(0,1) innovations.
    driver_direct = np.zeros(n, dtype=float)
    for t in range(1, n):
        driver_direct[t] = 0.72 * driver_direct[t - 1] + rng.normal(0.0, 1.0)

    # Step 2: pure noise covariate (generated before target loop to preserve RNG order).
    noise_pure = rng.normal(0.0, 1.0, size=n)

    # Step 3: target — causal lag-3 link to driver_direct, 12-step seasonal, weak AR(1).
    t_idx = np.arange(n, dtype=float)
    seasonal_component = np.sin(2.0 * np.pi * t_idx / 12.0)
    target = np.zeros(n, dtype=float)
    for t in range(3, n):
        target[t] = (
            0.40 * driver_direct[t - 3]
            + 0.30 * seasonal_component[t]
            + 0.35 * target[t - 1]
            + rng.normal(0.0, 1.0)
        )

    # Step 4: seasonal_proxy — tracks target[t-12].
    target_lagged_12 = np.zeros(n, dtype=float)
    target_lagged_12[12:] = target[:n - 12]
    seasonal_proxy = 0.9 * target_lagged_12 + rng.normal(0.0, 0.1, size=n)

    # Step 5: derived covariates.
    # 5a. smoothed_driver — 5-point causal moving average; zero-pad for t < 4.
    smoothed_driver = np.zeros(n, dtype=float)
    for t in range(4, n):
        smoothed_driver[t] = np.mean(driver_direct[t - 4 : t + 1])

    # 5b. sensor_near_dup — noisy rescaling of driver_direct.
    sensor_near_dup = 1.2 * driver_direct + rng.normal(0.0, 0.15, size=n)

    # 5c. calendar_flag — deterministic sinusoidal known-future feature.
    calendar_flag = np.sin(2.0 * np.pi * t_idx / 12.0) + 0.5 * np.cos(2.0 * np.pi * t_idx / 12.0)

    return LagAwareModMRMRPanel(
        target=target,
        covariates={
            "driver_direct": driver_direct,
            "smoothed_driver": smoothed_driver,
            "sensor_near_dup": sensor_near_dup,
            "noise_pure": noise_pure,
            "seasonal_proxy": seasonal_proxy,
            "calendar_flag": calendar_flag,
        },
        true_driver_name="driver_direct",
        true_driver_lag=3,
        known_future_covariates={"calendar_flag": "calendar"},
        duplicate_sensor_pair=frozenset({"driver_direct", "sensor_near_dup"}),
    )
