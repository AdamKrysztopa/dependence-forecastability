# dependence-forecastability — Detailed Backlog

_Last reviewed: 2026-04-12_

## Purpose

This backlog is designed to move the repository from a strong research-plus-tooling project into a more clearly **adoptable, production-oriented toolkit**.

The repository already presents a broad and credible scope: AMI, pAMI, exogenous analysis, a scorer registry, a deterministic `run_triage()` pipeline, optional agentic interpretation, CLI, HTTP API with SSE, and MCP integration. The README also states that the code follows a hexagonal architecture with adapters kept out of the core domain. Those are real strengths and worth preserving. citeturn247678view0turn247678view2

The main recommendation is therefore **not** “add more conceptual surface.” It is to improve:
- operational trust,
- packaging and onboarding,
- benchmark evidence,
- product framing,
- and clarity about what is stable versus experimental.

---

## Strategic goals

### Goal A — Make the project easier to trust
The README already claims deterministic triage, strict separation from the paper baseline, and hexagonal architecture. The next step is to make that trust visible through releases, compatibility guarantees, explicit stability boundaries, and reproducible examples. citeturn247678view0turn247678view2

### Goal B — Make the project easier to adopt
The repository currently exposes many strong capabilities at once: AMI, pAMI, exogenous analysis, scorer registry, triage, agent layer, CLI, API, and MCP. That is powerful, but can also feel dense for first-time users. The next step is to improve the first-run path and reduce cognitive load at the top of the repo. citeturn247678view0

### Goal C — Make the project easier to position publicly
The strongest marketable story is no longer only “AMI replication + extension.” It is now closer to: **a production-oriented triage layer for deciding whether and how a signal should be modeled**. That positioning is already implied by `run_triage()`, readiness gating, routing, interpretation, and recommendation. citeturn247678view0

---

## Priority model

- **P0** — should be done before broad public promotion or external adoption push
- **P1** — strong next-step improvements after P0
- **P2** — valuable expansions after the repo is more stable and better packaged
- **P3** — optional or later-stage enhancements

---

# P0 — Trust, packaging, and adoption basics

## 1. Publish a real versioned release story
**Priority:** P0  
**Why:** The repository currently shows tags/branches navigation but no visible release history on the main repo page snapshot used for this review. A toolkit that wants to signal production readiness should expose releases, change tracking, and upgrade confidence. citeturn247678view0

### Actions
- [x] Create `CHANGELOG.md` with semantic sections: Added, Changed, Fixed, Deprecated, Removed.
- [x] Publish `v0.1.0` as the first explicit public release.
- [x] Add a lightweight versioning policy in `README.md` or `docs/versioning.md`.
- [x] Mark features as one of:
  - stable,
  - beta,
  - experimental.
- [x] State whether domain-level interfaces are frozen or only “best effort stable.”
- [x] Add upgrade notes for each release.

### Acceptance criteria
- [x] A user can see current version, past releases, and what changed between them.
- [x] Stability level is explicit for CLI, API, MCP, agent, and domain APIs.
- [x] A breaking change has a documented migration note.

---

## 2. Add a visible production-readiness contract
**Priority:** P0  
**Why:** The README already mentions deterministic triage, adapters separated from domain logic, SSE, MCP, and agentic narration. What is missing is a compact “what exactly is production-ready here?” statement. citeturn247678view0turn247678view2

### Actions
- [x] Create `docs/production_readiness.md`.
- [x] Split the system into explicit maturity zones:
  - domain scientific core,
  - triage application layer,
  - transport adapters,
  - LLM narration layer.
- [x] For each zone, document:
  - intended use,
  - stability level,
  - main risks,
  - required extras,
  - expected observability,
  - testing coverage target.
- [x] Add a “safe default path” recommendation, for example:
  - use deterministic `run_triage()` first,
  - treat LLM narration as optional.
- [x] Add a section on failure behavior and non-goals.

### Acceptance criteria
- [x] A reader can immediately tell what is safe to use in a production workflow today.
- [x] The optional agent layer is clearly separated from deterministic scientific results.
- [x] Failure expectations are documented for API/CLI/agent paths.

---

## 3. Rework the README first screen
**Priority:** P0  
**Why:** The README is strong, but concept-dense. It introduces paper baseline, extensions, architecture, invariants, API, MCP, and agent layer early. New visitors need a narrower first-run message. citeturn247678view0

### Actions
- [x] Reorganize the top of `README.md` into five blocks only:
  1. one-sentence value proposition,
  2. who it is for,
  3. fastest quickstart,
  4. what result the user gets,
  5. where to go next.
- [x] Move deeper theory lower on the page.
- [x] Reduce the number of concepts shown before the first executable example.
- [x] Add one visual architecture summary image or diagram screenshot near the top.
- [x] Add one “common use cases” block:
  - signal triage,
  - lookback/horizon screening,
  - exogenous driver screening,
  - industrial/PdM use cases.

### Acceptance criteria
- [ ] A first-time visitor can understand the project in under 30 seconds.
- [ ] A user can run one working example without reading the full theoretical context.
- [ ] The README no longer feels like a combined whitepaper + product sheet + architecture spec at the very top.

---

## 4. Add an opinionated quickstart ladder
**Priority:** P0  
**Why:** The repo exposes multiple entry points: CLI, API, MCP, notebooks, and optional agent features. A laddered quickstart will reduce choice overload. The README already advertises CLI, API, and MCP, so the adoption path should be just as explicit. citeturn247678view0

### Actions
- [x] Add `docs/quickstart.md` with these paths:
  - 60 seconds: deterministic CLI run,
  - 5 minutes: notebook exploration,
  - 10 minutes: Python API usage,
  - 15 minutes: HTTP API call,
  - optional: agent narration,
  - optional: MCP integration.
- [x] Keep one sample dataset used across all quickstart routes.
- [x] Keep outputs visually consistent across all routes.
- [x] Add expected output snippets.

### Acceptance criteria
- [ ] Users can choose the shortest route for their need.
- [ ] The project no longer requires users to infer the best starting interface.
- [ ] All quickstarts produce aligned outputs for the same input signal.

---

## 5. Add explicit benchmark/result cards
**Priority:** P0  
**Why:** The repo references paper alignment, M4 setup, rolling-origin evaluation, and forecastability-error association, but the public-facing result story should be condensed into one easy-to-scan evidence layer. citeturn247678view0

### Actions
- [x] Create `docs/results_summary.md`.
- [x] Add three compact sections:
  - univariate AMI/pAMI findings,
  - exogenous screening findings,
  - triage workflow findings.
- [x] For each section, include:
  - dataset,
  - evaluation protocol,
  - what decision was improved,
  - what limitation remains.
- [x] Add one compact table with the most decision-relevant outcomes.
- [x] Link notebooks as “deep evidence,” not as the first evidence layer.

### Acceptance criteria
- [ ] A decision-maker can understand the practical benefit without reading notebooks.
- [ ] The repo shows not only what it computes, but why that computation improves workflow quality.
- [ ] Evidence is separated from marketing language.

---

## 6. Improve packaging metadata and install trust
**Priority:** P0  
**Why:** The repo has `pyproject.toml`, uv setup, and Python 3.11 signposting in the README, which is good. The next step is standard distribution polish and installation trust signals. citeturn247678view0turn190201view3

### Actions
- [x] Expand package metadata in `pyproject.toml`:
  - description,
  - keywords,
  - classifiers,
  - project URLs,
  - license metadata,
  - authors/maintainers where desired.
- [x] Decide on PyPI publication and prepare for it.
  - Decision (2026-04-12): publish to PyPI via GitHub OIDC trusted publishing on release publication.
- [x] Add an installation matrix:
  - core,
  - transport,
  - agent,
  - dev.
- [x] Add compatibility notes for Python versions.
- [x] Add badges for CI, version, and docs status.

### Acceptance criteria
- [x] The package looks distribution-ready.
- [x] Installation choices are explicit and low-friction.
- [x] A user knows which extras they need for which workflow.

---

# P1 — Better product framing and stronger public narrative

## 7. Create a “Why use this?” comparison page
**Priority:** P1  
**Why:** The repository offers several layers: AMI, pAMI, directness ratio, CrossAMI/pCrossAMI, triage, and optional narration. A comparison page would make the product structure much easier to understand. citeturn247678view0

### Actions
- [x] Create `docs/why_use_this.md`.
- [x] Add a matrix with rows such as:
  - AMI,
  - pAMI,
  - directness ratio,
  - exogenous analysis,
  - triage,
  - optional narration.
- [x] Columns should include:
  - what question it answers,
  - when to use it,
  - output type,
  - industrial value,
  - caveats.
- [x] Add one “do not use this for…” section.

### Acceptance criteria
- [x] A reader can quickly choose the right component for the right analytical question.
- [x] The repo feels like a coherent toolkit, not a pile of adjacent features.

---

## 8. Add a use-case pack for manufacturing / reliability / PdM
**Priority:** P1  
**Why:** The project is especially well-suited to industrial positioning. The public repo should make that path explicit without overclaiming. The current triage framing already supports this direction. citeturn247678view0

### Actions
- [x] Create `docs/use_cases_industrial.md`.
- [x] Add concise scenarios such as:
  - predictability alarm on rolling windows,
  - horizon-aware maintenance signals,
  - driver screening for exogenous forecasting,
  - signal readiness before model development,
  - post-maintenance regime comparison.
- [x] For each use case, define:
  - input signal type,
  - recommended path,
  - expected output,
  - typical next decision.
- [x] Keep claims operational, not sensational.

### Acceptance criteria
- [x] The repo speaks clearly to manufacturing/reliability users.
- [x] Each use case maps to a real action, not only an analysis artifact.

---

## 9. Turn “agentic” into a carefully framed optional layer
**Priority:** P1  
**Why:** The README already says the PydanticAI agent narrates deterministic numeric results and never invents numbers. That is a good constraint. The next step is to frame it as an optional usability layer, not the center of scientific credibility. citeturn247678view0

### Actions
- [x] Create `docs/agent_layer.md`.
- [x] Document the exact contract:
  - deterministic numbers come first,
  - narration comes second,
  - no free-form recomputation by the LLM.
- [x] Add examples of:
  - deterministic output only,
  - deterministic output plus narration,
  - narration disabled in strict mode.
- [x] Add prompt/testing guidance for numeric grounding.
- [x] Add a disclaimer on where the agent should not be trusted.

### Acceptance criteria
- [x] Users understand that the agent layer is interpretive, not authoritative over the core metrics.
- [x] Public messaging can use “agentic” without reducing trust in the repo.

---

## 10. Add one hardened API contract page
**Priority:** P1  
**Why:** The repo already advertises FastAPI + SSE and MCP. Integration-minded users need concrete request/response contracts and failure behavior. citeturn247678view0turn247678view2

### Actions
- [x] Create `docs/api_contract.md`.
- [x] Document:
  - request schema,
  - response schema,
  - validation errors,
  - readiness-failed example,
  - success example,
  - SSE event sequence,
  - versioning expectations.
- [x] Include one “minimal client integration” example.
- [x] Add API error semantics and status-code philosophy.

### Acceptance criteria
- [x] An engineer can integrate without reverse-engineering the server.
- [x] API behavior is predictable and version-aware.

---

# P1 — Testing and operational assurance

## 11. Add interface-level contract tests
**Priority:** P1  
**Why:** The architecture claims nine narrow protocol interfaces and adapter isolation. Contract tests would make that architecture easier to verify over time. citeturn247678view2

### Actions
- [x] Add tests that verify each adapter honors the relevant protocol contract.
- [x] Add shared fixtures for deterministic triage outputs.
- [x] Add schema-level tests for CLI/API/MCP parity on the same input.
- [x] Add regression tests for event emission ordering.

### Acceptance criteria
- [x] Changing adapters cannot silently drift away from application-layer expectations.
- [x] CLI/API/MCP differences are intentional and test-visible.

---

## 12. Add reproducibility fixtures for benchmark examples
**Priority:** P1  
**Why:** Public confidence grows when benchmark examples are small, fixed, and rerunnable.

### Actions
- [x] Add a tiny benchmark fixture dataset folder for docs/tests.
- [x] Freeze expected outputs for selected examples.
- [x] Add a script that rebuilds summary artifacts from raw benchmark runs and verifies fixture consistency.
- [x] Add a “reproduce the summary table” command.

### Acceptance criteria
- [x] Users can rerun representative examples exactly.
- [x] Docs and benchmark summaries do not drift silently.

---

## 13. Add observability and auditability guidance
**Priority:** P1  
**Why:** Since the repo positions itself toward production orientation, it should explain how to inspect stage progress, failed runs, and analytical provenance. The SSE/event-emitter/checkpoint story is already present conceptually. citeturn247678view0turn247678view2

### Actions
- [x] Create `docs/observability.md`.
- [x] Define standard event payload fields.
- [x] Clarify checkpoint semantics and resumability boundaries.
- [x] Add a minimal audit trail schema for triage runs.
- [x] Recommend logging fields for industrial usage.

### Acceptance criteria
- [x] Users know what to log, what to persist, and how to trace a run.
- [x] Operational debugging is a designed workflow, not an afterthought.

---

# P2 — High-value feature evolution

## 14. Batch dataset / signal screening mode
**Priority:** P2  
**Why:** This is likely the most valuable next product feature. Real users often have many candidate signals or many potential exogenous drivers, not just one. A batch mode would move the repo much closer to practical industrial triage.

### Actions
- [x] Add a batch screening use case that accepts multiple series.
- [x] Rank outputs by:
  - readiness,
  - forecastability profile,
  - directness ratio,
  - exogenous usefulness,
  - recommended next action.
- [x] Add exportable summary tables.
- [x] Add failure isolation so one bad series does not fail the full batch.

### Acceptance criteria
- [x] Users can screen a set of signals, not only one signal at a time.
- [x] Output is easy to sort, compare, and route into downstream model-selection workflows.

---

## 15. Multi-series comparison reports
**Priority:** P2  
**Why:** Once batch mode exists, comparative reporting becomes very useful for selecting model candidates and prioritizing effort.

### Actions
- [x] Add comparison report generation for multiple target series.
- [x] Add standardized tables and plots for:
  - AMI AUC,
  - pAMI AUC,
  - directness ratio,
  - significance coverage,
  - horizon-specific drop-off.
- [x] Add a report summary that recommends which series deserve deeper modeling.

### Acceptance criteria
- [x] Teams can compare many signals consistently.
- [x] Comparative reports are suitable for engineering review meetings.

---

## 16. Exogenous screening workbench
**Priority:** P2  
**Why:** The repo already includes exogenous cross-dependence analysis. The next useful step is a practical driver-screening workbench rather than only pairwise analysis. citeturn247678view0

### Actions
- [x] Support target-plus-many-drivers evaluation.
- [x] Add ranking of candidate drivers by horizon-specific usefulness.
- [x] Add optional pruning heuristics for weak drivers.
- [x] Add lag-window summaries for driver relevance.
- [x] Add a compact recommendation layer: keep / review / reject.

### Acceptance criteria
- [x] Users can use the tool to narrow exogenous candidates before model building.
- [x] The repo gains clear value in multivariate forecasting preparation.

---

## 17. Persisted result artifacts and provenance bundle
**Priority:** P2  
**Why:** For auditability and repeatability, it is useful to persist not only plots or summaries, but also inputs, config, versions, and stage results.

### Actions
- [ ] Define a result bundle format containing:
  - input metadata,
  - config snapshot,
  - versions,
  - numeric outputs,
  - recommendation,
  - optional narration,
  - warnings.
- [ ] Add save/load utilities.
- [ ] Add a provenance checksum or content hash where practical.

### Acceptance criteria
- [ ] A run can be persisted, reloaded, compared, and reviewed later.
- [ ] Reproducibility is improved across teams and environments.

---

# P2 — Documentation and outreach assets

## 18. Convert selected notebooks into durable docs pages
**Priority:** P2  
**Why:** GitHub language distribution often makes notebook-heavy repos look less production-ready at first glance. Converting the most important notebook insights into narrative docs helps rebalance that perception.

### Actions
- [ ] Identify the 3 most important notebooks.
- [ ] Turn each into a docs page with:
  - purpose,
  - key figure,
  - key result,
  - takeaways,
  - link to notebook for full detail.
- [ ] Keep notebooks as evidence, not as the only explanatory medium.

### Acceptance criteria
- [ ] Core insights are available without opening notebooks.
- [ ] The repo looks more like a maintained toolkit and less like a notebook-first experiment.

---

## 19. Create a one-page executive summary
**Priority:** P2  
**Why:** For sharing on LinkedIn, with engineering managers, or with industrial stakeholders, a concise overview is very useful.

### Actions
- [ ] Add `docs/executive_summary.md`.
- [ ] Cover:
  - what problem this solves,
  - what is novel here,
  - why AMI/pAMI triage matters,
  - what is ready today,
  - what comes next.
- [ ] Keep it highly visual and low-jargon.

### Acceptance criteria
- [ ] The project can be shared with non-specialists without sending them into the full README immediately.

---

# P3 — Later expansions

## 20. Optional lightweight dashboard
**Priority:** P3  
**Why:** A dashboard can help demonstrations and internal adoption, but it should come after packaging, contracts, and evidence.

### Actions
- [ ] Prototype a minimal dashboard for single-series and batch triage.
- [ ] Keep it as a thin adapter over existing use cases.
- [ ] Do not let dashboard logic leak into domain or triage code.

### Acceptance criteria
- [ ] The UI is demonstrative and operationally useful without distorting the architecture.

---

## 21. Residual backend expansion for pAMI
**Priority:** P3  
**Why:** This is scientifically interesting, but lower priority than workflow adoption and operational trust.

### Actions
- [ ] Evaluate alternative residualisation backends.
- [ ] Add benchmark comparisons with the current linear residual backend.
- [ ] Document trade-offs and failure modes.

### Acceptance criteria
- [ ] New backends are justified by measurable value, not novelty alone.

---

## 22. More transport adapters only if user demand appears
**Priority:** P3  
**Why:** The project already has CLI, API, and MCP exposure. More transports are unlikely to be the current bottleneck. citeturn247678view0

### Actions
- [ ] Do not add more transports by default.
- [ ] Revisit only if concrete user demand emerges.

### Acceptance criteria
- [ ] Effort remains focused on adoption quality rather than interface sprawl.

---

# Recommended execution order

## Phase 1 — Trust and onboarding
- [ ] Release/versioning story
- [x] Production-readiness page
- [x] README first-screen rewrite
- [x] Quickstart ladder
- [x] Packaging metadata and badges

## Phase 2 — Evidence and contracts
- [x] Results summary page
- [x] API contract page
- [ ] Interface contract tests
- [ ] Reproducibility fixtures
- [x] Observability and auditability guide

## Phase 3 — Productization
- [x] Why-use-this comparison page
- [x] Industrial use-case pack
- [x] Agent-layer framing page
- [ ] Executive summary
- [ ] Selected notebook-to-doc conversions

## Phase 4 — Functional expansion
- [x] Batch dataset/signal screening
- [x] Multi-series comparison reports
- [x] Exogenous screening workbench
- [ ] Persisted provenance bundle

---

# What not to prioritise right now

These are the items I would deliberately postpone:

- [ ] adding more transports,
- [ ] inflating the agent story beyond its optional interpretive role,
- [ ] adding many new scorers before the current ones are better packaged and benchmarked,
- [ ] spending too much time on UI before contracts and reproducibility are solid.

Reason: the repository already has enough conceptual breadth. The current limiting factor is **operational credibility and adoption clarity**, not feature count. That judgment is consistent with the repo’s current surface area: deterministic triage, scorer registry, exogenous analysis, API/SSE, MCP, and optional agent integration are already present. citeturn247678view0turn247678view2

---

# Suggested public positioning after P0/P1

A strong positioning line after the first two phases would be:

> **A production-oriented forecastability triage toolkit for deciding whether, when, and how a signal should be modeled.**

That is stronger than presenting it only as an AMI/pAMI implementation, while still remaining faithful to the current repository structure and capabilities. citeturn247678view0

---

# Sources used for this backlog

This backlog is grounded in the current public repository description, README-visible feature list, architecture description, and package structure visible on GitHub as of 2026-04-12. The most load-bearing facts are:
- the repo presents AMI, pAMI, exogenous analysis, scorer registry, deterministic triage, optional agentic interpretation, CLI, API, and MCP integration, citeturn247678view0
- the project explicitly claims hexagonal architecture with adapters isolated from domain logic via narrow protocol boundaries, citeturn247678view0turn247678view2
- and the scientific framing is currently tied to paper-aligned rolling-origin evaluation and frequency-conditional forecastability triage. citeturn247678view1
