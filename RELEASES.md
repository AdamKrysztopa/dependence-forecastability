# Release Index

This file cross-references **core** releases and **sibling** follow-up status
so the full v0.4.0+ product history is visible in one place.

> **Two repos, one product.** The [`dependence-forecastability`][core] package
> ships the deterministic triage toolkit. The [`forecastability-examples`][sibling]
> sibling hosts tutorials, walkthroughs, and framework-integration notebooks.
> Core releases remain authoritative for the framework-agnostic package. When a
> sibling follow-up is not yet tagged, the table marks that side as planned.

[core]: https://github.com/AdamKrysztopa/dependence-forecastability
[sibling]: https://github.com/AdamKrysztopa/forecastability-examples

---

## Release table

| Core tag | Sibling tag | Core highlights | Sibling highlights |
| --- | --- | --- | --- |
| `v0.4.3` | *(planned)* `v0.4.3` | Lag-Aware ModMRMR sparse covariate-lag selection; `run_lag_aware_mod_mrmr()`, fast and Catt showcase scripts, theory/code/public API/recipe/README updates, and release-surface hardening | Richer walkthrough notebooks remain a sibling-repo follow-up in `forecastability-examples`; no core notebook additions are required for this release |
| `v0.4.2` | *(planned)* `v0.4.2` | AMI-first forecastability structure expansion; extended fingerprint, extended routing, and spectral/ordinal/classical/memory diagnostics | Extended walkthrough refresh and showcase updates for the expanded fingerprint remain a sibling-repo follow-up |
| `v0.4.1` | — | Performance hardening, benchmark visibility, and fast-screening controls | — |
| `v0.4.0` | `v0.4.0` | Library-first slim release; `notebooks/` removed; causal-rivers extensions promoted | Notebook migration complete; 12 walkthroughs, 6 triage walkthroughs, 1 recipe notebook; EX-NB-01–05 |
| `v0.3.6` | — | Release-truth and docs-integrity automation | — |
| `v0.3.5` | — | Documentation quality hardening; redirect-stub cleanup; recipe page for forecast-prep hand-off | — |
| `v0.3.4` | — | `ForecastPrepContract` public API; `build_forecast_prep_contract`; `docs/recipes/forecast_prep_to_external_frameworks.md` | — |
| `v0.3.3` | — | Routing validation hardening; benchmark calibration; regression fixtures | — |
| `v0.3.2` | — | Lagged-exogenous triage (`run_lagged_exogenous_triage`) | — |

---

## How cross-repo releases are coordinated

See [EX-REL-01 in the v0.4.0 plan](docs/plan/implemented/v0_4_0_examples_repo_split_ultimate_plan.md)
for the two-repo release dance. In brief:

1. Core publishes a release candidate to TestPyPI.
2. Sibling pre-flight matrix (`source ∈ {testpypi, git}`) runs against the RC.
3. On acceptance-gate green, core tags and publishes to PyPI.
4. Sibling updates its `dependence-forecastability` pin, tags a matching release,
   and the cross-repo CI handshake (EX-CPL-01) posts a confirmation comment on
   the core release page.

The [shared GitHub Project](https://github.com/orgs/AdamKrysztopa/projects)
tracks issues and PRs across both repos under the current release milestone.
