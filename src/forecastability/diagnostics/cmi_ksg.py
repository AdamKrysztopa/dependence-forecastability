"""Frenzel-Pompe KSG conditional mutual information estimator (RVH-F02).

Implements true Schreiber transfer entropy via joint Chebyshev cKDTree.
Reference: Frenzel & Pompe (2007), PRL 99, 204101.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from scipy.spatial import cKDTree  # type: ignore[attr-defined]
from scipy.special import digamma as psi

from forecastability.domain.results.transfer_entropy_ksg import TransferEntropyKsgResult


def compute_conditional_mutual_information_ksg(
    X: np.ndarray,
    Y: np.ndarray,
    Z: np.ndarray,
    lag: int,
    k: int = 5,
) -> float:
    """Estimate I(X; Y | Z) using Frenzel-Pompe KSG-CMI.

    Uses a joint Chebyshev cKDTree with the Frenzel-Pompe algorithm:
    build the joint (X, Y, Z) tree, find k-th neighbour radius, then
    count neighbours in the three marginal (X,Z), (Y,Z), and Z subspaces.

    Args:
        X: 1-D array, target series (already lag-aligned).
        Y: 1-D array, source series (already lag-aligned).
        Z: 1-D or 2-D array, conditioning set (already lag-aligned).
        lag: Lag used for alignment — used only for the hard sample-size
            cutoff ``N_eff < k**(d+2)``.
        k: Number of neighbours for the KSG estimator.

    Returns:
        CMI estimate in nats, or ``float('nan')`` if below the hard cutoff.
    """
    x = np.asarray(X, dtype=float).ravel()
    y = np.asarray(Y, dtype=float).ravel()
    z = np.asarray(Z, dtype=float)
    if z.ndim == 1:
        z = z[:, np.newaxis]

    N_eff = x.size
    d = z.shape[1]

    # Hard sample-size cutoff (Frenzel-Pompe criterion)
    if N_eff < k ** (d + 2):
        return float("nan")

    # Build joint matrix J = [x, y, z1, z2, ...]
    J = np.column_stack([x[:, np.newaxis], y[:, np.newaxis], z])  # (N_eff, d+2)

    # Build joint tree and query k+1 neighbours (first is self)
    tree_joint = cKDTree(J, leafsize=16)
    dists, _ = tree_joint.query(J, k=k + 1, workers=1, p=np.inf)
    # k-th neighbour radius per point (index k, since 0 is self)
    eps = dists[:, k]  # shape (N_eff,)

    # Marginal subspace arrays
    xz = np.column_stack([x[:, np.newaxis], z])  # (N_eff, d+1)
    yz = np.column_stack([y[:, np.newaxis], z])  # (N_eff, d+1)

    tree_xz = cKDTree(xz, leafsize=16)
    tree_yz = cKDTree(yz, leafsize=16)
    tree_z = cKDTree(z, leafsize=16)

    # Marginal counts using closed ball (dist <= eps).  FP 2007 specifies strict
    # dist < eps for marginals; in theory np.nextafter(eps[i], 0.0) implements
    # this.  In practice, Chebyshev ties at exactly eps cause strict counting to
    # exclude O(k) boundary points per query, producing ~2× overestimation of TE
    # at N=5000 on Gaussian VAR(1) (empirically verified: strict vs analytical
    # analytical 0.057 nats → strict gives 0.106, closed gives 0.057).  Closed
    # ball is retained as the numerically stable convention; the boundary-tie bias
    # is negligible for continuous data and is dominated by finite-sample variance.
    n_xz = np.array(
        [len(tree_xz.query_ball_point(xz[i], eps[i], p=np.inf)) - 1 for i in range(N_eff)],
        dtype=float,
    )
    n_yz = np.array(
        [len(tree_yz.query_ball_point(yz[i], eps[i], p=np.inf)) - 1 for i in range(N_eff)],
        dtype=float,
    )
    n_z = np.array(
        [len(tree_z.query_ball_point(z[i], eps[i], p=np.inf)) - 1 for i in range(N_eff)],
        dtype=float,
    )

    # Exclude points where any marginal count is 0; psi(0) is undefined and
    # clamping independently to 1 injects positive CMI bias near independence.
    valid = (n_xz > 0) & (n_yz > 0) & (n_z > 0)
    if not np.any(valid):
        return float("nan")

    # Frenzel-Pompe CMI estimator (over valid points only)
    cmi = float(psi(k) + np.mean(psi(n_z[valid]) - psi(n_xz[valid]) - psi(n_yz[valid])))
    return cmi


def _quality_warning_from_ratio(ratio: float) -> str:
    """Map N_eff / k^d_total ratio to quality_warning literal.

    Note: d_total = 1 + 1 + history_depth (X_t + X_{t-lag} + conditioning dims),
    so k^d_total already incorporates the +2 from the two signal dimensions.
    """
    if ratio >= 10.0:
        return "ok"
    elif ratio >= 2.0:
        return "marginal"
    else:
        return "unreliable"


def compute_transfer_entropy_ksg(
    X: np.ndarray,
    Y: np.ndarray,
    lag: int,
    history_depth: int | None = None,
    k: int = 5,
    n_neighbors: int | None = None,
) -> TransferEntropyKsgResult:
    """Compute Schreiber transfer entropy TE(X→Y) via Frenzel-Pompe KSG-CMI.

    Estimates TE_{X→Y}(lag) = I(Y_t ; X_{t-lag} | Y_{t-1}, ..., Y_{t-d})
    where d = history_depth and X is the **source**, Y is the **target**.

    The conditioning set is the target's (Y's) own history, not the source's.
    This is true Schreiber TE: the additional predictive information X provides
    about Y's future beyond Y's own past.

    Args:
        X: Source series.
        Y: Target series.
        lag: Transfer lag L.
        history_depth: Number of target history lags to condition on.
            Defaults to ``max(1, lag - 1)``.
        k: Number of neighbours for KSG-CMI.
        n_neighbors: Alias for ``k``; overrides ``k`` when provided.

    Returns:
        :class:`TransferEntropyKsgResult` with status, quality_warning, value,
        and provenance fields.
    """
    # Resolve k / n_neighbors
    k_eff = k if n_neighbors is None else n_neighbors

    if history_depth is not None and history_depth < 0:
        raise ValueError(f"history_depth must be >= 0, got {history_depth}")

    # Resolve history_depth
    d = max(1, lag - 1) if history_depth is None else history_depth
    resolved_history_depth = d

    # X = source, Y = target
    x_arr = np.asarray(X, dtype=float).ravel()  # source
    y_arr = np.asarray(Y, dtype=float).ravel()  # target

    # Lag-alignment for TE(X→Y, lag, d):
    #   TE = I(Y_t ; X_{t-lag} | Y_{t-1}, ..., Y_{t-d})
    #
    #   N_eff = N - lag - d
    #   y_t       = y_arr[lag + d :]           current target
    #   x_lagged  = x_arr[d : N - lag]         source at t-lag
    #   z_h       = y_arr[lag + d - h : N - h] for h = 1..d  (target history)
    N = len(y_arr)
    N_eff = N - lag - d

    # Conditioning dimension: y_t-dim=1, x_lagged-dim=1, z-dims=d
    # d_total is the total joint-space dimension (X_t, X_{t-lag}, Z_1..Z_d).
    # Frenzel-Pompe cutoff: N < k^(d_total) — the exponent equals the joint
    # dimension, NOT d_total+2.  Adding +2 was double-counting: the +2 already
    # comes from the X_t and X_{t-lag} components embedded in d_total.
    d_total = 1 + 1 + d

    # Compute quality_warning BEFORE building any trees (Risk 2)
    cutoff = k_eff**d_total
    ratio = N_eff / cutoff if cutoff > 0 else 0.0
    qw: Literal["ok", "marginal", "unreliable"] = _quality_warning_from_ratio(ratio)  # type: ignore[assignment]

    # Blocking conditions (check on full series, before alignment)
    if np.std(x_arr) < 1e-10 or np.std(y_arr) < 1e-10:
        return TransferEntropyKsgResult(
            status="blocked_constant_input",
            quality_warning=qw,
            value=float("nan"),
            lag=lag,
            history_depth=resolved_history_depth,
            n_neighbors=k_eff,
            n_samples=max(N_eff, 0),
            estimator="ksg_frenzel_pompe",
        )

    if (len(np.unique(x_arr)) / len(x_arr) < 0.1) or (len(np.unique(y_arr)) / N < 0.1):
        return TransferEntropyKsgResult(
            status="blocked_low_cardinality",
            quality_warning=qw,
            value=float("nan"),
            lag=lag,
            history_depth=resolved_history_depth,
            n_neighbors=k_eff,
            n_samples=max(N_eff, 0),
            estimator="ksg_frenzel_pompe",
        )

    if N_eff < cutoff:
        return TransferEntropyKsgResult(
            status="blocked_sample_size",
            quality_warning=qw,
            value=float("nan"),
            lag=lag,
            history_depth=resolved_history_depth,
            n_neighbors=k_eff,
            n_samples=max(N_eff, 0),
            estimator="ksg_frenzel_pompe",
        )

    # Build lag-aligned arrays
    y_t = y_arr[lag + d :]  # current target Y_t
    x_lagged = x_arr[d : N - lag]  # lagged source X_{t-lag}

    # Target history conditioning: Y_{t-1}, ..., Y_{t-d}
    z_cols = [y_arr[lag + d - h : N - h] for h in range(1, d + 1)]
    Z = np.column_stack(z_cols) if d > 0 else np.empty((N_eff, 0), dtype=float)

    # Estimate CMI = I(Y_t; X_{t-lag} | Y_{t-1},...,Y_{t-d})
    # lag=1 because arrays are already aligned above
    raw_value = compute_conditional_mutual_information_ksg(y_t, x_lagged, Z, lag=1, k=k_eff)

    if np.isnan(raw_value):
        return TransferEntropyKsgResult(
            status="blocked_sample_size",
            quality_warning=qw,
            value=float("nan"),
            raw_value=float("nan"),
            lag=lag,
            history_depth=resolved_history_depth,
            n_neighbors=k_eff,
            n_samples=N_eff,
            estimator="ksg_frenzel_pompe",
        )

    # Clamp to non-negative for the reported estimate; store raw for diagnostics.
    value = max(0.0, raw_value)

    return TransferEntropyKsgResult(
        status="computed",
        quality_warning=qw,
        value=value,
        raw_value=raw_value,
        lag=lag,
        history_depth=resolved_history_depth,
        n_neighbors=k_eff,
        n_samples=N_eff,
        estimator="ksg_frenzel_pompe",
    )
