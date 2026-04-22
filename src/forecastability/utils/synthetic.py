"""Synthetic benchmark generators for covariant analysis testing.

These generators produce deterministic multivariate systems with
known ground-truth causal structure, for use in tests, examples,
and notebooks.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


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
