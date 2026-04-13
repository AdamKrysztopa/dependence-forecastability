<!-- type: reference -->
# Documentation

A deterministic forecastability triage toolkit with AMI as the paper-aligned foundation and pAMI as a project extension.

CLI, API, notebooks, MCP, and agents are optional access or narration layers around the same deterministic outputs.

---

## Start here

First-time user path: install, run one deterministic triage, read the result.

| Document | Description |
|---|---|
| [quickstart.md](quickstart.md) | Laddered quickstart: 60s CLI, 5m notebook, 10m Python API, 15m HTTP API, plus optional agent and MCP routes using one shared signal |
| [golden_path.md](golden_path.md) | Opinionated path from install to first trustworthy output — the recommended starting point |
| [executive_summary.md](executive_summary.md) | One-page visual summary for non-specialists: problem, AMI/pAMI value, readiness, and next steps |

---

## Learn the methods

Conceptual background and mathematical foundations.

| Document | Description |
|---|---|
| [theory/foundations.md](theory/foundations.md) | AMI and pAMI definitions, significance logic, rolling-origin invariants |
| [theory/forecastability_profile.md](theory/forecastability_profile.md) | Forecastability Profile model, informative horizon set, epsilon resolution, DPI diagnostic |
| [theory/pami_residual_backends.md](theory/pami_residual_backends.md) | Residual backend trade-offs, linear-baseline comparison workflow, and failure modes |
| [theory/interpretation_patterns.md](theory/interpretation_patterns.md) | Pattern A–E classification logic for agentic narration |
| [theory/spectral_predictability.md](theory/spectral_predictability.md) | Spectral predictability score Ω, PSD normalisation, and complementarity with AMI |
| [theory/entropy_based_complexity.md](theory/entropy_based_complexity.md) | Permutation entropy, spectral entropy, complexity band classification |
| [triage_methods/predictive_information_learning_curves.md](triage_methods/predictive_information_learning_curves.md) | EvoRate-style lookback analysis, plateau detection, reliability caveats |
| [triage_methods/largest_lyapunov_exponent.md](triage_methods/largest_lyapunov_exponent.md) | Experimental LLE estimation, delay embedding, sample-size constraints |

### Notebook narratives

Durable narrative pages distilled from the most important notebooks.

| Document | Description |
|---|---|
| [notebooks/README.md](notebooks/README.md) | Notebook taxonomy and walkthrough vs deterministic deep-dive role split |
| [notebooks/canonical_forecastability.md](notebooks/canonical_forecastability.md) | AMI/pAMI notebook: purpose, key figure, key result, takeaways |
| [notebooks/exogenous_analysis.md](notebooks/exogenous_analysis.md) | CrossAMI/pCrossAMI notebook with warning-aware driver-screening outcomes |
| [notebooks/agentic_triage.md](notebooks/agentic_triage.md) | Triage walkthrough surface and deterministic payload/adapter deep dive |

#### Triage extension notebooks

Interactive notebooks in `notebooks/triage/` covering the extended diagnostic pipeline:

| Notebook | Topic |
|---|---|
| `01_forecastability_profile_walkthrough.ipynb` | F1 forecastability profile walkthrough |
| `02_information_limits_and_compression.ipynb` | F2 information-theoretic limits and compression |
| `07_predictive_information_learning_curves.ipynb` | F3 predictive information learning curves |
| `08_spectral_and_entropy_diagnostics.ipynb` | F4/F6 spectral predictability and entropy diagnostics |
| `09_batch_and_exogenous_workbench.ipynb` | F7/F8 batch ranking and exogenous screening |
| `10_agent_ready_triage_interpretation.ipynb` | Deterministic payload/serializer/interpretation deep dive (non-walkthrough) |

---

## Use in practice

Operational guides, scenario maps, and diagnostic reference.

| Document | Description |
|---|---|
| [why_use_this.md](why_use_this.md) | Component comparison matrix for AMI, pAMI, directness ratio, exogenous analysis, triage, and optional narration |
| [use_cases_industrial.md](use_cases_industrial.md) | Manufacturing/reliability/PdM scenario matrix with recommended path, outputs, and next decisions |
| [results_summary.md](results_summary.md) | Evidence-first summary of univariate AMI/pAMI, exogenous screening, and triage workflow findings, with explicit limitations |
| [diagnostics_matrix.md](diagnostics_matrix.md) | Single evaluator-facing index for all F1–F8 diagnostics with stability and caveat columns |
| [surface_guide.md](surface_guide.md) | Explanation of the surface model: deterministic core, CLI/API, MCP/agents, what most users can safely ignore |

### Examples

Self-contained scripts in [`examples/triage/`](../examples/triage/) covering F1–F8, agent adapter integrations, and a runnable live screening-agent example with deterministic fallback.

---

## Policy / release / architecture

Stability, supported surfaces, API contract, and project governance.

| Document | Description |
|---|---|
| [wording_policy.md](wording_policy.md) | Frozen canonical wording lines and banned claims for all docs and surface text |
| [versioning.md](versioning.md) | Semantic versioning policy, stability levels, and migration-note requirements |
| [public_api.md](public_api.md) | Stable import paths, schema stability notes, and what is not in the public API |
| [api_contract.md](api_contract.md) | FastAPI and SSE transport contract: request/response schemas, validation and readiness semantics |
| [architecture.md](architecture.md) | Hexagonal architecture guide, SOLID principles, layer boundaries, enforcement |
| [production_readiness.md](production_readiness.md) | Production maturity zones, safe default deterministic path, and failure/non-goal contract for CLI/API/agent surfaces |
| [agent_layer.md](agent_layer.md) | Deterministic-first contract for optional LLM narration, strict mode behavior, and numeric-grounding checks |
| [observability.md](observability.md) | Operational observability and auditability guide: event payload contract, checkpoint replay boundaries, logging fields |
| [../CHANGELOG.md](../CHANGELOG.md) | Repository release and change history |
| [releases/v0.1.0.md](releases/v0.1.0.md) | Upgrade notes for release `v0.1.0` |

### Code reference

| Document | Description |
|---|---|
| [code/README.md](code/README.md) | Code reference overview |
| [code/module_map.md](code/module_map.md) | Module-by-module public symbol reference |
| [code/exog_analyzer.md](code/exog_analyzer.md) | `ForecastabilityAnalyzerExog` user manual (synthetic data) |
| [code/exog_analyzer_real_data.md](code/exog_analyzer_real_data.md) | `ForecastabilityAnalyzerExog` user manual (real-world data) |
| [code/exog_benchmark_workflow.md](code/exog_benchmark_workflow.md) | Fixed exogenous benchmark slice workflow |

### Planning

| Document | Description |
|---|---|
| [plan/README.md](plan/README.md) | Planning surface overview |
| [plan/development_plan.md](plan/development_plan.md) | Primary development plan: triage extension features F1–F8, stage gates, and delivery status |
| [plan/acceptance_criteria.md](plan/acceptance_criteria.md) | Done criteria for all roadmap items |
| [plan/must_have.md](plan/must_have.md) | Non-negotiable items |
| [plan/should_have.md](plan/should_have.md) | High-value improvements |
| [plan/could_have.md](plan/could_have.md) | Optional extensions |
| [plan/wont_have.md](plan/wont_have.md) | Explicit exclusions |

## Archive

Historical completed development documentation from the build-out phase.
Reference-only; not part of the active roadmap.

Located in [archive/](archive/)
