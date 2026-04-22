<!-- type: explanation -->
# Lagged-Exogenous Triage

**Introduced in:** v0.3.2
**Related plan:** [v0.3.2 Lagged-Exogenous Triage: Ultimate Release Plan](../plan/v0_3_2_lagged_exogenous_triage_ultimate_plan.md)

This document explains the role taxonomy, method semantics, sparse selection
algorithm, and deliberate out-of-scope choices that underpin the
`run_lagged_exogenous_triage()` surface introduced in v0.3.2.

---

## 1. The core split: multivariate vs covariant-informative

For a target series $Y_t$ and a candidate exogenous series $X_t$, there are
two qualitatively different questions a practitioner may be asking:

| Question | Formal quantity | Lag domain |
| --- | --- | --- |
| Does $X$ co-move with $Y$ at the **same time step**? | $I(X_t\,;\,Y_t)$ | $k = 0$ only |
| Does the **past** of $X$ carry usable predictive information about the **future** of $Y$? | $I(X_{t-k}\,;\,Y_t)$ for $k \ge 1$ | $k \ge 1$ |

The v0.3.0 covariant methods all start from $k = 1$ and silently drop any
$k = 0$ structure. v0.3.2 makes this split explicit with a typed role field on
every emitted row.

### 1.1. `lag_role` — the per-row chronological role

Every `LaggedExogProfileRow` and `LaggedExogSelectionRow` carries a
`lag_role` field:

| `lag_role` | Condition | Interpretation |
| --- | --- | --- |
| `"instant"` | $k = 0$ | Contemporaneous association — structural / multivariate |
| `"predictive"` | $k \ge 1$ | Fixed-lag predictive association — covariant-informative |

### 1.2. `tensor_role` — eligibility for a forecasting tensor

The `tensor_role` field states whether the lag may legitimately enter a
lagged-exogenous tensor used for ordinary forecasting:

| `tensor_role` | Meaning |
| --- | --- |
| `"diagnostic"` | Useful for understanding the system; **not** eligible as a tensor feature |
| `"predictive"` | Eligible to enter a lagged-exogenous tensor for ordinary forecasting |
| `"known_future"` | Eligible at $k = 0$ via explicit `known_future_drivers` opt-in |

By default, every $k = 0$ row gets `tensor_role = "diagnostic"`.
The `"known_future"` value is only assigned when the user explicitly opts in
via `known_future_drivers={"driver_name": True}`.

> [!IMPORTANT]
> A `selected_for_tensor=True` flag at $k = 0$ is impossible by default.
> It requires an explicit `known_future_drivers` opt-in at the use-case layer.
> This is not a library limitation — it is an intentional chronological-causality
> guard.

---

## 2. Methods

### 2.1. Standard cross-correlation (linear baseline)

For each $k \in \{0, 1, \dots, K_{\max}\}$:

$$\hat{\rho}_k(X, Y) = \frac{\sum_{t} (X_{t-k} - \bar{X})(Y_t - \bar{Y})}{\sqrt{\sum_{t}(X_{t-k} - \bar{X})^2 \sum_{t}(Y_t - \bar{Y})^2}}$$

Properties:

- Cheap linear baseline; sign is retained (no premature absolute-value collapse)
- Covers $k = 0$, giving the contemporaneous correlation as a diagnostic reference
- **Cannot detect symmetric nonlinear couplings** — a quadratic driver with near-zero Pearson correlation can be a strong predictive feature; always cross-check with `cross_ami`
- Significance field stays `None`; `significance_source = "not_computed"`

### 2.2. Extended `cross_ami` lag profile

For each $k \in \{0, 1, \dots, K_{\max}\}$:

$$\widehat{I}_k(X, Y) = \widehat{I}(X_{t-k}\,;\,Y_t)$$

estimated with the same kNN mutual-information estimator used throughout
the covariant surface. The v0.3.0 `compute_exog_raw_curve` emitted only
$k \in \{1, \dots, K_{\max}\}$. v0.3.2 adds the $k = 0$ row so that the
multivariate diagnostic is visible alongside the predictive profile.

When surrogate significance bands are available (phase-randomised surrogates),
they extend to $k = 0$ so the strength of the instantaneous coupling can
be assessed against the noise floor.

### 2.3. Shipped `cross_pami` — semantics unchanged

The v0.3.0 `cross_pami` curve remains `target_only` conditioned and covers
$k \in \{1, \dots, K_{\max}\}$ only. Its semantics are not relabelled in
v0.3.2. The `lagged_exog_conditioning` tag for this method stays `target_only`.

### 2.4. Conditioning-scope crosswalk (post-v0.3.2)

| Method | Lag domain | `lag_role` | `tensor_role` | `lagged_exog_conditioning` |
| --- | --- | --- | --- | --- |
| Standard cross-correlation (`xcorr`) | `0..max_lag` | `instant` at $k=0$, `predictive` otherwise | `diagnostic` at $k=0$, `predictive` otherwise | `none` |
| `cross_ami` (extended profile) | `0..max_lag` | `instant` at $k=0$, `predictive` otherwise | `diagnostic` at $k=0$, `predictive` otherwise | `none` |
| Shipped `cross_pami` | `1..max_lag` | `predictive` | `predictive` | `target_only` (unchanged) |
| Sparse lag selector (`xami_sparse`) | `1..max_lag` | `predictive` | `predictive` | `target_only` |
| Transfer Entropy (existing) | `1..max_lag` | `predictive` | `predictive` | `target_only` |
| PCMCI+ / PCMCI-AMI (existing) | `0..max_lag` | inherits from PCMCI link lag | inherits | `full_mci` |
| Known-future opt-in | `0` only | `instant` | `known_future` (via opt-in) | `none` |

---

## 3. Sparse lag selection (`xami_sparse`)

### 3.1. Algorithm

Given the dense profile $\widehat{I}_k$ for $k \in \{1, \dots, K_{\max}\}$,
the sparse selector emits a subset $\mathcal{S}(X, Y) \subseteq \{1, \dots, K_{\max}\}$:

1. Start with $\mathcal{S} \leftarrow \emptyset$.
2. While there exists $k^\dagger \notin \mathcal{S}$ with partialled score
   $\tilde{I}_{k^\dagger}(X, Y \mid \{X_{t-k'}: k' \in \mathcal{S}\}) \ge \tau_{\text{select}}$,
   add $k^\dagger$ to $\mathcal{S}$, capped at `max_selected_per_driver`.
3. Emit each candidate $k$ as a `LaggedExogSelectionRow` with
   `selected_for_tensor=True` if and only if $k \in \mathcal{S}$.

The strongest candidate $k^\star = \arg\max_k \widehat{I}_k$ is always
evaluated first.

### 3.2. Positioning

`xami_sparse` is a **triage layer** — it cheaply prunes redundant lags to reduce
the feature tensor. It does **not** condition on the driver's own autohistory.
That stronger conditioning is the job of `pcmci_ami` (`full_mci`) from v0.3.0.
Any new selector that goes further (PMIME-style, PC-stable with driver
autohistory) must be introduced under a **new method label** so that the
shipped `cross_pami` and `xami_sparse` semantics are not silently extended.

### 3.3. Key guarantees

- **At least one row per `(target, driver)` pair** is emitted by the selector.
- **`selected_for_tensor=True` is impossible at $k=0$** unless the driver
  appears in `known_future_drivers`.
- The selector emits `LaggedExogSelectionRow` objects independently from
  plot artifacts; the sparse map is a typed Python output first.

---

## 4. Known-future opt-in

A "known-future" exogenous covariate is one whose $k=0$ value is legitimately
observed **before** $Y_t$ must be predicted: calendar features, holidays,
regulator-set tariffs, planned promotional events. Such features may be selected
at $k=0$, but only via:

```python
bundle = run_lagged_exogenous_triage(
    target,
    drivers,
    target_name="target",
    max_lag=6,
    n_surrogates=99,
    random_state=42,
    known_future_drivers={"holiday_flag": True},
)
```

Without this opt-in, every $k=0$ row for `"holiday_flag"` will have
`selected_for_tensor=False` and `tensor_role="diagnostic"`. With the opt-in,
those rows flip to `tensor_role="known_future"` and the selector may choose
`selected_for_tensor=True` at $k=0$ for that driver only.

The `known_future_drivers` contract is honored at the **use-case layer**
(`run_lagged_exogenous_triage`). The selector service itself is pure and does
not read it.

---

## 5. Significance handling

Wherever phase-randomised surrogate bands already exist (via
`significance_service`), the lagged-exogenous flow reuses them — including at
$k = 0$ once the lag-range extension is in place.

When a method genuinely lacks a surrogate path (standard cross-correlation),
the significance field stays explicitly `None` and the row metadata records
`significance_source = "not_computed"`. No synthetic p-values are invented.

---

## 6. DTW is intentionally out of scope

DTW (Dynamic Time Warping), FastDTW, and ShapeDTW solve **elastic-alignment
similarity**: they search for the alignment $\pi$ that minimises a
path-cumulated distance between two time series. They do not:

- produce a fixed-lag predictive feature set
- respect the chronological causality required by forecasting tensors
- output a lag map that is directly consumable by ordinary regression or
  neural forecasting models

They remain out of scope for lagged-exogenous triage until a separate plan
justifies a constrained forecasting-causal use. Any elastic-alignment result
would need a new surface, a new method label, and an explicit
chronological-causality guard before it could be admitted to a forecasting
tensor.

---

## 7. Cross-links

- [Conditioning scope and covariant role assignment](covariant_role_assignment.md)
- [Covariant summary table](covariant_summary_table.md)
- [v0.3.2 release plan](../plan/v0_3_2_lagged_exogenous_triage_ultimate_plan.md)
- [Walkthrough notebook](../../notebooks/walkthroughs/03_lagged_exogenous_triage_showcase.ipynb)
- [Public API reference](../public_api.md)
