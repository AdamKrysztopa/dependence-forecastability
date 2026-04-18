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
