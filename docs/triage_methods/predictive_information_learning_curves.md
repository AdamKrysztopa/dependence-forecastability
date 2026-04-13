<!-- type: explanation -->

# Predictive Information Learning Curves (F3)

## Overview

F3 answers the question: **"How much lookback history is enough?"** It computes the predictive information between a past block of length $k$ and a one-step-ahead future target for $k = 1, 2, \ldots, K$. The resulting curve is analysed for plateau/convergence to recommend a minimal sufficient lookback.

---

## Definition — Predictive Information / EvoRate

The **EvoRate** at horizon 1 with lookback $k$ is the mutual information between the $k$-dimensional past embedding and the one-step future:

$$
\text{EvoRate}(k) = I\!\left(X_{t-k+1{:}t};\, X_{t+1}\right)
$$

This is the **one-step-ahead special case** of the more general predictive information:

$$
I_{\text{pred}}(k) = I\!\left(\mathbf{X}^{(k)}_t;\, X_{t+1}\right)
$$

where $\mathbf{X}^{(k)}_t = (X_{t-k+1}, \ldots, X_t)$ is the $k$-dimensional delay embedding of the series.

---

## Estimation

For each lookback $k$, the estimator builds:

- **Past matrix** of shape $(n - k,\, k)$: each row $i$ is the window $[x_{i}, x_{i+1}, \ldots, x_{i+k-1}]$.
- **Future vector** of length $n - k$: the scalar $x_{i+k}$ (one step ahead of each window).

$I_{\text{pred}}(k)$ is estimated using `sklearn.feature_selection.mutual_info_regression` with $k$ neighbours set to $n_{\text{nbrs}} = 8$, matching the convention in the broader AMI pipeline.

---

## Lookback Sufficiency and Plateau Detection

As $k$ increases, $I_{\text{pred}}(k)$ is non-decreasing in expectation (more context can only add information). In practice it levels off when the additional past carries negligible new predictive information.

**Marginal gain:**

$$
g(k) = I_{\text{pred}}(k) - I_{\text{pred}}(k-1)
$$

**Plateau condition:** a plateau is declared at position $k^*$ when the relative gain

$$
\frac{g(k)}{I_{\text{pred}}(k-1)} < \tau_{\text{plateau}}
$$

holds for at least $m_{\text{min}}$ consecutive steps, where $\tau_{\text{plateau}} = 0.05$ and $m_{\text{min}} = 2$ by default.

The **recommended lookback** is $k^*$ — the first step of the detected plateau run. If no plateau is found within the evaluated range, the maximum evaluated $k$ is returned as a conservative recommendation.

---

## kNN Curse of Dimensionality Warning

kNN mutual information estimators suffer from the **curse of dimensionality** as the embedding dimension $k$ grows:

- For $k > 5$–$8$, the nearest-neighbour distances in the $k$-dimensional past space become unreliable with typical financial or economic time-series lengths.
- A hard cap of $k_{\max} = 8$ is enforced to limit this effect.
- When $n < 1000$, estimates for $k > 3$ carry elevated estimation variance; a reliability warning is attached to the result.

---

## Important Caveats

- **Finite-sample bias:** The asymptotic log forms for MI are guidance, not finite-sample truths. Estimates are positively biased for small $n$ and large $k$.
- **Stationarity:** The estimator assumes approximate stationarity. Non-stationary series (e.g. random walks) will produce inflated $I_{\text{pred}}(k)$ values that grow with $k$ without plateauing.
- **Not a scorer:** F3 produces a curve and a recommended lookback, not a scalar forecastability score. It must not be used as a standalone triage decision.

---

## Notation Alignment

| Symbol | Meaning |
|---|---|
| $I_{\text{pred}}(k)$ | Predictive information at lookback $k$ |
| $\mathbf{X}^{(k)}_t$ | $k$-dimensional delay embedding at time $t$ |
| $k^*$ | Recommended lookback (plateau onset) |
| $\tau_{\text{plateau}}$ | Relative-gain plateau threshold (default 0.05) |
| $m_{\text{min}}$ | Minimum consecutive steps for plateau (default 2) |
| $n_{\text{nbrs}}$ | kNN neighbours (default 8, matches AMI pipeline) |
