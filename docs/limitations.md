<!-- type: explanation -->
# Limitations

This page collects the known limitations of the AMI → pAMI Forecastability Analysis
toolkit. Read it before drawing conclusions from the outputs, especially in
short-series or noisy-data settings.

> [!IMPORTANT]
> These limitations are properties of the current implementation and the underlying
> methodology, not defects to be fixed. Understanding them is part of using the
> toolkit correctly.

---

## 1. Finite-sample MI caveats

The kNN mutual information estimator (Kraskov et al., 2004; `n_neighbors=8`) is
asymptotically consistent but has positive bias for finite samples, particularly at
short series lengths and large lag indices.

- **Minimum recommended length.** Approximately $n \geq 3 \times H_{\max}$, where
  $H_{\max}$ is the maximum evaluation horizon. Below this threshold, MI estimates
  are unreliable for lags close to $H_{\max}$.
- **Bias inflation.** Positive MI bias is strongest when the number of nearest
  neighbours $k$ is large relative to the local sample density. Short series with
  high-dimensional lag spaces (F3 at large $k$) are most affected.
- **Surrogate-band availability.** Phase-randomized surrogate significance bands
  require a minimum series length to produce stable quantile estimates. When the
  series is too short, surrogates are not computed and the significance boundary is
  unavailable. This is distinct from "computed, none significant" — the two outcomes
  must not be conflated.

> [!WARNING]
> "Surrogates not computed" means the sample size did not permit reliable band
> estimation. It does not mean nothing is significant.

---

## 2. pAMI is an approximation, not exact conditional MI

pAMI is a **project extension** and is not paper-native. It approximates
$I(X_t; X_{t+h} \mid X_{t+1}, \ldots, X_{t+h-1})$ via linear (or optional RF)
residualisation, not by exact conditional MI estimation.

- **Residualisation is approximate.** The conditioning-out step removes only the
  component of dependence that is linearly predictable from the intermediate lags.
  Nonlinear residual dependence that the linear backend cannot capture remains in
  the AMI but may not be fully removed from pAMI.
- **No causal proof.** pAMI quantifies approximate direct dependence after removing
  mediated paths. It does not prove direct causality or Granger causality.
- **`directness_ratio > 1.0` is an anomaly boundary.** In finite samples with the
  residual approximation, pAMI can slightly exceed AMI. When `directness_ratio > 1.0`
  the system flags `arch_suspected`. This flag is a **warning or anomaly boundary,
  not positive evidence** of any particular architecture.
- **Backend dependence.** Results differ between the linear (default) and RF
  backends. The linear backend is faster and more stable; the RF backend may capture
  more nonlinear residual structure but introduces additional noise for short series.

---

## 3. Surrogate significance assumptions and requirements

Surrogate significance bands are computed from phase-randomized surrogates, which
implies specific assumptions.

- **Stationarity assumption.** Phase randomisation preserves the power spectrum but
  destroys temporal order. It assumes approximate second-order stationarity. Series
  with strong trends or regime changes will produce uninformative surrogate bands.
- **Minimum surrogate count.** At least `n_surrogates = 99` is required for a valid
  two-sided 95% band. Fewer than 99 surrogates are not sufficient and must not be
  used as a significance threshold.
- **Unavailability vs absence.** When surrogates are not computed (sample size too
  short, or `n_surrogates=0` set deliberately), the resulting state is "significance
  not assessed", not "no significant lags found". Always check the
  `surrogates_computed` flag before interpreting significance results.
- **One-sided interpretation.** The upper band is operationally informative for
  detecting non-null dependence. The lower band is usually near zero for MI and is
  not typically operationally useful.

---

## 4. Rolling-origin discipline

In rolling-origin evaluation, the leakage boundary is strict and must be enforced
by the caller.

- **Train-window-only diagnostics.** AMI, pAMI, and all F1–F8 diagnostics are
  computed on the training window up to each rolling origin. No diagnostic touches
  the post-origin holdout.
- **Holdout-only scoring.** Forecast errors and accuracy metrics are computed on the
  post-origin holdout window only.
- **Caller responsibility.** The `run_rolling_origin_evaluation()` function enforces
  this boundary internally. If you compute diagnostics manually outside this
  function, you must enforce the same boundary. Violating it introduces look-ahead
  leakage and invalidates the evaluation.
- **Exogenous workflows.** The same leakage boundary applies to exogenous screening
  (F8): CrossAMI must be computed on the training window only.

> [!CAUTION]
> Look-ahead leakage in rolling-origin evaluation is silent — it produces optimistic
> forecastability scores without any error message. Always verify that diagnostics
> are computed before the origin and scoring after it.

---

## 5. F5 Largest Lyapunov Exponent — experimental

Largest Lyapunov exponent is experimental and excluded from automated triage
decisions.

- **Numerical fragility.** The Rosenstein algorithm and Takens embedding are
  sensitive to noise, non-stationarity, and the choice of embedding parameters
  ($m$, $\tau$, Theiler window, evolution time $s$). Small parameter changes can
  produce meaningfully different $\hat{\lambda}$ values.
- **Sample-size requirement.** Reliable phase-space coverage requires
  $n \gg 10^m$. For the default $m = 3$ this means $n \gg 1000$. Results for
  shorter series are indicative only.
- **Cannot distinguish chaos from noise.** A positive $\hat{\lambda}$ is consistent
  with chaotic dynamics, but stochastic coloured noise and non-stationary processes
  also produce positive estimates. F5 alone cannot distinguish the two cases.
- **Config gate.** F5 must be explicitly enabled via `experimental: true` in the
  config. It does not run in default triage mode.
- **F7 exclusion.** LLE is intentionally excluded from the batch triage ranking
  table (F7) by design.

---

## 6. `directness_ratio > 1.0`

When the pAMI residual approximation produces a pAMI value that numerically exceeds
the corresponding AMI value, `directness_ratio > 1.0`.

- This is an **anomaly boundary, not positive evidence** of direct causal structure
  or particularly strong direct dependence.
- It arises most commonly in noisy series, misspecified linear residual backends,
  or very short series where estimation variance is high.
- The system flags the affected horizon as `arch_suspected`.
- The correct interpretation: treat the ratio as informative only below 1.0; values
  above 1.0 indicate the residual approximation has broken down at that horizon.

---

## 7. Non-goals

These are explicitly outside the scope of this toolkit.

- **pAMI does not prove direct causality.** It quantifies approximate direct
  lag-dependence after a linear conditioning step. No causal inference standard
  (Granger, Pearl, etc.) is claimed or implied.
- **Agent layer does not recompute science.** The PydanticAI agent layer reads
  frozen deterministic payloads (A1–A3) and generates natural-language narration.
  It does not perform any statistical computation or validate the numeric results.
- **Non-uniform production-readiness.** The toolkit is not uniformly production-
  ready. The deterministic core and stable facades are stable; CLI and HTTP API are
  beta; MCP server and agent layer are experimental. Do not assume that a working
  demonstration in one surface implies stability guarantees for all surfaces.
- **MCP and agent layers are narration, not validation.** Any numeric claim in an
  agent response is a restatement of a deterministic result. If the underlying
  `TriageResult` is wrong, the agent narration will be wrong in the same way.

---

## 8. Platform constraints

- **Python 3.11+ required.** The codebase uses 3.11-specific syntax and type
  features. Earlier Python versions are not supported and will produce parse errors.
- **No Windows-specific validation.** Development and CI run on macOS and Linux.
  Windows path handling, line endings, and subprocess behaviour have not been
  systematically tested.
- **Optional extras add transitive dependencies.** The `[agent]` extras (PydanticAI)
  and `[api]` extras (FastAPI + uvicorn) each add transitive packages. In
  constrained environments, install only the extras you need:
  - `pip install forecastability` for core only
  - `pip install forecastability[api]` for HTTP API
  - `pip install forecastability[agent]` for agent layer
- **MCP server dependency.** The MCP server requires additional server-framework
  dependencies. It is not included in the default install.
