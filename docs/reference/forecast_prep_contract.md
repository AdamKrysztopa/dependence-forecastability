<!-- type: reference -->
# Forecast Prep Contract

`ForecastPrepContract` is the neutral, deterministic, additive hand-off boundary
between the forecastability triage toolkit and any downstream model family adapter.
After running univariate triage, covariant analysis, lagged-exogenous triage, and
fingerprint estimation, a user has precise diagnostic answers: which lags carry
information, which covariates are predictive, what seasonality structure exists, and
how confident the routing service is. `ForecastPrepContract` converts those
diagnostic outputs into a single machine-readable object — serialisable via standard
Pydantic `model_dump()` / `model_dump_json()` — that a user can translate into
framework-specific configuration in their own code. The contract is
**framework-agnostic by design**: it never imports `darts`, `mlforecast`,
`statsforecast`, or `nixtla`, and the package ships no framework-specific
export helpers. See [What this is not](#what-this-is-not) and
[docs/recipes/forecast_prep_to_external_frameworks.md](recipes/forecast_prep_to_external_frameworks.md)
for illustrative user-side mappings.

> [!IMPORTANT]
> The `ForecastPrepContract` is a **hand-off boundary, not a model trainer**.
> Every `recommended_*` field is paired with a `confidence_label` and
> `caution_flags` so downstream consumers can make informed, not blind, decisions.
> The repository scope directive at
> [docs/plan/aux_documents/developer_instruction_repo_scope.md](plan/aux_documents/developer_instruction_repo_scope.md)
> forbids first-class framework integrations in the core package.

---

## Imports

```python
# Compact contract + builder + framework-agnostic exporters
from forecastability import (
    ForecastPrepContract,
    build_forecast_prep_contract,
    forecast_prep_contract_to_markdown,
    forecast_prep_contract_to_lag_table,
)

# Rich bundle (typed recommendation rows) — advanced surface
from forecastability.triage import ForecastPrepBundle
```

---

## The three input axes

The input space of any tabular forecasting model is treated as the disjoint union
of three axes:

$$\mathcal{X} = \mathcal{X}_{\text{target-lag}} \sqcup \mathcal{X}_{\text{past-cov}} \sqcup \mathcal{X}_{\text{future-cov}}$$

$\mathcal{X}_{\text{past-cov}}$ and $\mathcal{X}_{\text{future-cov}}$ are disjoint
by construction. A driver column may appear in at most one of them; the builder
enforces this before emitting a contract.

### Axis A — Univariate target lags

**Source:** `TriageResult.summary.primary_lags` and fingerprint structural
candidates.

**Classification rules:**

| Role | Meaning |
|---|---|
| `direct` | Strongest non-seasonal lag; typically lag 1 or the primary AMI peak |
| `seasonal` | Lag matching a detected seasonal period (e.g., lag 12 for monthly data) |
| `secondary` | Corroborating lag with medium confidence; included when `confidence_label` is `medium` or above |
| `excluded` | Lag present in diagnostics but not selected for the downstream hand-off |

**Field names in the contract:**

- `recommended_target_lags: list[int]` — direct and secondary lags selected for hand-off
- `recommended_seasonal_lags: list[int]` — seasonal lags selected for hand-off
- `excluded_target_lags: list[int]` — lags explicitly excluded
- `lag_rationale: list[str]` — human-readable rationale strings, one per selected lag

All values in `recommended_target_lags` and `excluded_target_lags` are strictly
positive integers ($\ge 1$); a field validator enforces this invariant.

### Axis B — Lagged exogenous covariates

**Source:** `LaggedExogBundle.selected_lags` rows with `selected_for_tensor=True`
and `lag >= 1`.

**Field names in the contract:**

- `past_covariates: list[str]` — driver column names selected as past covariates

The sparse lag set $L_{\text{past}}(c)$ for each driver $c$ is carried in the
richer `ForecastPrepBundle.covariate_rows` typed surface
(`CovariateRecommendation.selected_lags`). See
[Past-covariate lag predicate](#past-covariate-lag-predicate) for the formal
definition.

> [!NOTE]
> A driver appearing in `selected_for_tensor=True` rows is **not** known-future
> by default. Past-data informativeness is necessary but not sufficient for
> known-future eligibility. The user owns that contractual claim.

### Axis C — Known-future covariates

Two channels populate `future_covariates`:

1. **User-declared:** column names supplied via `known_future_drivers: dict[str, bool]`
   where the value is `True`.
2. **Auto-generated calendar features:** injected when `add_calendar_features=True`
   (the default). See [Calendar feature naming](#calendar-feature-naming).

**Field names in the contract:**

- `future_covariates: list[str]` — all future-covariate column names (user-declared + calendar)
- `calendar_features: list[str]` — subset of `future_covariates` that were auto-generated; all entries begin with `_calendar__`
- `calendar_locale: str | None` — locale string passed to the `holidays` package; `null` when holiday features are disabled

---

## Calendar feature naming

When `add_calendar_features=True`, the builder injects a deterministically named
set of calendar features derived from the `pandas.DatetimeIndex` of the training
period. The naming scheme `_calendar__<feature>` is **stable across versions**.

| Column name | Type | Source |
|---|---|---|
| `_calendar__dayofweek` | `int8` (0 = Monday) | `index.dayofweek` |
| `_calendar__month` | `int8` (1–12) | `index.month` |
| `_calendar__quarter` | `int8` (1–4) | `index.quarter` |
| `_calendar__is_weekend` | `bool` | `index.dayofweek.isin([5, 6])` |
| `_calendar__is_business_day` | `bool` | `pd.bdate_range`-derived |
| `_calendar__is_holiday` | `bool` | `holidays` package, locale `calendar_locale`; included only when both are set |

> [!NOTE]
> When `calendar_locale` is set but the optional `[calendar]` extra (`holidays>=0.50`)
> is not installed, the builder skips `_calendar__is_holiday` silently and adds
> `"calendar_locale_set_but_holidays_unavailable"` to `caution_flags`. No column
> is missing at the recipe site; the user is informed non-fatally.

Users may rename the columns after receiving the contract. The export helpers
never strip the `_calendar__` prefix.

---

## Known-future eligibility predicate

A covariate column $c$ is eligible for $\mathcal{X}_{\text{future-cov}}$ if and
only if:

$$\text{KnownFuture}(c) \iff \big( c \in K \big) \lor \big( c \in C_{\text{cal}} \land \texttt{add\_calendar\_features} \big)$$

where:

- $K$ — column names from `known_future_drivers` with value `True` (user-declared);
- $C_{\text{cal}} = \{\texttt{\_calendar\_\_dayofweek},\ \texttt{\_calendar\_\_month},\ \texttt{\_calendar\_\_quarter},\ \texttt{\_calendar\_\_is\_weekend},\ \texttt{\_calendar\_\_is\_business\_day},\ \texttt{\_calendar\_\_is\_holiday}\}$
  (last entry is locale-gated).

---

## Past-covariate lag predicate

For each driver $c \in \mathcal{X}_{\text{past-cov}}$, the contract carries a sparse lag set $L_{\text{past}}(c) \subseteq \{1, 2, \ldots, K_{\max}\}$ defined as:

$$L_{\text{past}}(c) = \{k : \exists\, r \in \texttt{LaggedExogBundle.selected\_lags}\ \text{with}\ r.\text{driver}=c,\ r.\text{lag}=k,\ r.\text{selected\_for\_tensor}=\text{True},\ r.\text{lag} \ge 1\}$$

> [!IMPORTANT]
> The `r.lag >= 1` constraint is non-redundant. The `xami_sparse` selector
> (v0.3.2) already enforces `min_lag >= 1`, but the builder defensively
> re-checks this invariant because future selectors registered under different
> `selector_name` literals may relax it. Cross-reference:
> [v0.3.2 plan §2.1](plan/implemented/v0_3_2_lagged_exogenous_triage_ultimate_plan.md).

---

## Future-covariate lag predicate

For each driver $c \in \mathcal{X}_{\text{future-cov}}$, the contract carries a
lag set $L_{\text{future}}(c) \subseteq \{0, 1, \ldots, H-1\}$ where $H$ is the
forecast horizon:

$$L_{\text{future}}(c) = \begin{cases} \{0\} & \text{if } c \in C_{\text{cal}} \\ \{0\} \cup \text{user-supplied lags or default } \{0\} & \text{if } c \in K \end{cases}$$

> [!IMPORTANT]
> `lag = 0` is **only** allowed for columns in $C_{\text{cal}}$ or $K$. Any
> other column appearing with `role = "future"` and a lag of `0` is a contract
> bug; the builder raises `ValueError` before returning. The recipes page repeats
> this invariant for users translating the contract into framework configuration.

---

## Confidence propagation

The contract's `confidence_label` is a direct copy of
`RoutingRecommendation.confidence_label` (v0.3.3). Propagation rules:

| `RoutingRecommendation.confidence_label` | `ForecastPrepContract.confidence_label` | Effect on `recommended_families` |
|---|---|---|
| `high` | `high` | full `recommended_families` from routing |
| `medium` | `medium` | full `recommended_families`, plus baseline families |
| `low` | `low` | only top-1 routing family + baselines |
| `abstain` | `abstain` | `recommended_families` is empty; `baseline_families` only |

When `TriageResult.blocked` is `True`, the contract overrides the routing label
entirely and emits `confidence_label = "abstain"`, regardless of what routing
reported. Blocked triages produce conservative empty contracts with explicit
`caution_flags`.

---

## Schema-evolution policy

The `contract_version` field is a string of the form `"<major>.<minor>.<patch>"`
matching the package version at the time the contract was introduced.

| Change type | Version bump? | Release action |
|---|---|---|
| New optional field added | No | Document in `CHANGELOG.md` under the release entry |
| Existing field renamed or removed | Yes | Bump `contract_version`; add a migration entry in `CHANGELOG.md` |
| Field validator logic tightened | No | Document in `CHANGELOG.md` as a bugfix |

The current value is `"0.3.4"` and will remain so until a breaking field change
is shipped.

---

## JSON example

The following is the serialised form of a `ForecastPrepBundle` for a univariate
triage result (from `docs/fixtures/forecast_prep_regression/expected/contract_univariate.json`).
The `contract` key holds the `ForecastPrepContract`; `lag_table` is produced by
`forecast_prep_contract_to_lag_table`.

```json
{
  "contract": {
    "contract_version": "0.3.4",
    "source_goal": "univariate",
    "blocked": false,
    "readiness_status": "clear",
    "forecastability_class": "high",
    "confidence_label": "high",
    "target_frequency": null,
    "horizon": null,
    "recommended_target_lags": [1, 12],
    "recommended_seasonal_lags": [],
    "excluded_target_lags": [],
    "lag_rationale": [
      "lag 1 is the strongest non-seasonal lag",
      "lag 12 is secondary under current confidence"
    ],
    "candidate_seasonal_periods": [],
    "recommended_families": ["arima", "ets"],
    "baseline_families": ["naive", "seasonal_naive"],
    "past_covariates": [],
    "future_covariates": [],
    "static_features": [],
    "rejected_covariates": [],
    "covariate_notes": [],
    "transformation_hints": [],
    "caution_flags": [],
    "downstream_notes": ["deterministic routing for regression fixture"],
    "calendar_features": [],
    "calendar_locale": null,
    "metadata": {
      "covariate_rows": 0,
      "family_rows": 5,
      "lag_rows": 2
    }
  },
  "lag_table": [
    {
      "axis": "target",
      "driver": "target",
      "lag": 1,
      "rationale": "lag 1 is the strongest non-seasonal lag",
      "role": "direct",
      "selected_for_handoff": true
    },
    {
      "axis": "target",
      "driver": "target",
      "lag": 12,
      "rationale": "lag 12 is secondary under current confidence",
      "role": "direct",
      "selected_for_handoff": true
    }
  ],
  "markdown_length": 882
}
```

---

## Markdown export example

`forecast_prep_contract_to_markdown(contract)` returns a stable, deterministic,
human- and LLM-readable string. The output for the univariate fixture above:

```markdown
# Forecast Prep Contract

## Metadata

- source_goal: univariate
- blocked: False
- readiness_status: clear
- confidence_label: high
- target_frequency: None
- horizon: None
- contract_version: 0.3.4

## Target Lags

**recommended_target_lags:**
- 1
- 12

**recommended_seasonal_lags:**
(none)

**excluded_target_lags:**
(none)

**lag_rationale:**
- lag 1 is the strongest non-seasonal lag
- lag 12 is secondary under current confidence

## Model Families

**recommended_families:**
- arima
- ets

**baseline_families:**
- naive
- seasonal_naive

## Covariates

**past_covariates:**
(none)

**covariate_notes:**
(none)

**future_covariates:**
(none)

**calendar_features:**
(none)

**calendar_locale:** None

**rejected_covariates:**
(none)

## Notes

**caution_flags:**
(none)

**downstream_notes:**
- deterministic routing for regression fixture

**transformation_hints:**
(none)
```

When calendar features are present (e.g., `add_calendar_features=True` with a
covariant contract), `future_covariates` and `calendar_features` sections are
populated with entries such as `_calendar__dayofweek`, `_calendar__month`, etc.

---

## Lag-table export example

`forecast_prep_contract_to_lag_table(contract)` returns a deterministic list of
dicts. Rows are sorted by `(axis_order, driver, lag)` where
`"target" < "past" < "future"`.

**Univariate contract (target lags only):**

| driver | axis | role | lag | selected_for_handoff | rationale |
|---|---|---|---|---|---|
| `target` | `target` | `direct` | 1 | `True` | lag 1 is the strongest non-seasonal lag |
| `target` | `target` | `direct` | 12 | `True` | lag 12 is secondary under current confidence |

**Extended example including past and future covariates:**

| driver | axis | role | lag | selected_for_handoff | rationale |
|---|---|---|---|---|---|
| `target` | `target` | `direct` | 1 | `True` | lag 1 is the strongest non-seasonal lag |
| `target` | `target` | `seasonal` | 12 | `True` | lag 12 matches the detected seasonal period |
| `target` | `target` | `excluded` | 6 | `False` | lag 6 below significance threshold |
| `temperature` | `past` | `past` | 1 | `True` | |
| `_calendar__dayofweek` | `future` | `future` | 0 | `True` | |
| `_calendar__is_weekend` | `future` | `future` | 0 | `True` | |

---

## Framework-agnostic export

Two export helpers are provided. Neither imports any downstream library.

### `forecast_prep_contract_to_markdown`

```python
from forecastability import (
    build_forecast_prep_contract,
    forecast_prep_contract_to_markdown,
)

bundle = build_forecast_prep_contract(triage_result, horizon=12)
md = forecast_prep_contract_to_markdown(bundle.contract)
print(md)
```

### `forecast_prep_contract_to_lag_table`

```python
from forecastability import (
    build_forecast_prep_contract,
    forecast_prep_contract_to_lag_table,
)

bundle = build_forecast_prep_contract(triage_result, horizon=12)
rows = forecast_prep_contract_to_lag_table(bundle.contract)
for row in rows:
    print(row)
```

### JSON and dict export

```python
from forecastability import build_forecast_prep_contract

bundle = build_forecast_prep_contract(triage_result, horizon=12)
contract = bundle.contract

# Dict
data = contract.model_dump()

# JSON string (stable, indented)
json_str = contract.model_dump_json(indent=2)
```

---

## What this is not

- **Does not train or score models.** The contract emits lag recommendations and
  model-family suggestions backed by diagnostic evidence; it does not fit any model.
- **Does not claim optimal hyperparameters.** `recommended_target_lags` and
  `recommended_families` are evidence-based starting points; they are not
  guarantees of forecast accuracy.
- **Does not include framework-specific export helpers.** Framework-specific
  translation is the responsibility of the user. Illustrative recipes are
  at [docs/recipes/forecast_prep_to_external_frameworks.md](recipes/forecast_prep_to_external_frameworks.md).
- **Does not import `darts`, `mlforecast`, `statsforecast`, or `nixtla`.** These
  packages are not runtime, optional-extra, dev, or CI dependencies of the core
  repository.
- **Is not a replacement for downstream forecasting libraries.** It is a
  diagnostic hand-off boundary; model training, validation, and deployment remain
  the responsibility of the downstream framework and the user.

---

## See also

- [docs/recipes/forecast_prep_to_external_frameworks.md](recipes/forecast_prep_to_external_frameworks.md) — illustrative
  mappings to MLForecast, Darts, and Nixtla / StatsForecast
- [docs/public_api.md](public_api.md) — supported import contract
- [docs/quickstart.md](quickstart.md) — end-to-end triage walkthrough
- [docs/plan/aux_documents/developer_instruction_repo_scope.md](plan/aux_documents/developer_instruction_repo_scope.md) — repository scope directive
