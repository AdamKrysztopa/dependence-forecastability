# Examples, Notebooks, and Improved Agents Plan  
**Companion to:** `development_plan.md`  
**Last reviewed:** 2026-04-13 (N3/N4/N5 notebooks implemented and executed)
**Repo:** `AdamKrysztopa/dependence-forecastability`

---

## Purpose

This document adds the missing execution track for:

1. **Runnable examples**
2. **Notebooks**
3. **Improved agent-facing payloads**
4. **One notebook focused on agent-ready interpretation**

It is intentionally **not** a new scientific roadmap.  
It sits on top of the deterministic development plan and translates new features into:

- reproducible example scripts,
- reviewable notebooks,
- stable agent-ready summaries,
- one lightweight agentic demo path.

The core rule stays unchanged:

- deterministic math lives in domain/application,
- notebooks are demonstration and validation artifacts,
- agent logic consumes stable deterministic payloads,
- no feature-specific agent orchestration explosion.

---

# 1. Design rules

## 1.1 Example rules

Every feature from the main development plan must have:
- [ ] one **minimal synthetic example**
- [ ] one **repo-realistic example**
- [ ] one **saved output artifact** where practical
- [ ] one **README-style usage block**

Examples must be:
- deterministic,
- fast enough for local execution,
- small enough for CI-friendly smoke checks where possible.

## 1.2 Notebook rules

Notebooks are for:
- explaining the method,
- showing result interpretation,
- comparing behaviors across signals,
- helping architect/statistician review.

Notebooks are **not** the source of truth for business logic.

All notebook logic must call library code from `src/`, not duplicate formulas inline except for explanatory markdown cells.

## 1.3 Agent rules

Agents should consume **stable deterministic summaries** only.

Per feature:
- [ ] expose structured payload
- [ ] expose human-readable summary fields
- [ ] expose warning fields
- [ ] expose confidence / reliability notes where relevant

Do **not** build one bespoke agent workflow per feature.

Instead build:
- one shared interpretation adapter,
- one shared notebook demo for agent-style consumption.

---

# 2. Target structure

## 2.1 Examples directory

Recommended structure:

```text
examples/
  triage/
    f1_forecastability_profile_synthetic.py
    f1_forecastability_profile_realistic.py
    f2_information_limits_synthetic.py
    f3_predictive_info_learning_curve.py
    f4_spectral_predictability.py
    f5_lle_experimental.py
    f6_entropy_complexity.py
    f7_batch_ranking.py
    f8_exogenous_screening.py
```

## 2.2 Notebook directory

Recommended structure:

```text
notebooks/
  triage/
    01_forecastability_profile_walkthrough.ipynb
    02_information_limits_and_compression.ipynb
    07_predictive_information_learning_curves.ipynb
    08_spectral_and_entropy_diagnostics.ipynb
    09_batch_and_exogenous_workbench.ipynb
    06_agent_ready_triage_interpretation.ipynb
```

## 2.3 Agent-facing adapter structure

Recommended structure:

```text
src/forecastability/adapters/agents/
  triage_summary_serializer.py
  triage_agent_payload_models.py
  triage_agent_interpretation_adapter.py
```

This keeps agent work in adapter land, not in the deterministic core.

---

# 3. Per-feature examples and notebook plan

## F1 — Forecastability Profile & Informative Horizon Set

### Example scripts
- [x] `examples/triage/f1_forecastability_profile_synthetic.py`
- [x] `examples/triage/f1_forecastability_profile_realistic.py`

### Example requirements
- [ ] seasonal synthetic process with non-monotone profile
- [ ] simple autoregressive process with smoother decay
- [ ] output:
  - horizons
  - profile values
  - informative horizon set
  - recommended horizons

### Notebook
- [ ] `notebooks/triage/01_forecastability_profile_walkthrough.ipynb`

### Notebook sections
- [ ] concept and equation recap
- [ ] how profile differs from a single scalar score
- [ ] non-monotone vs monotone examples
- [ ] interpretation for modeling decisions

### Agent payload additions
- [ ] `profile_peak_horizon`
- [ ] `profile_informative_horizons`
- [ ] `profile_shape_label`
- [ ] `profile_summary`

---

## F2 — Information-Theoretic Limit Diagnostics

### Example scripts
- [x] `examples/triage/f2_information_limits_synthetic.py`

### Example requirements
- [ ] original signal vs compressed/aggregated signal
- [ ] show reduced ceiling after destructive transform
- [ ] explicitly distinguish:
  - theoretical ceiling
  - achieved model performance

### Notebook
- [ ] `notebooks/triage/02_information_limits_and_compression.ipynb`

### Notebook sections
- [ ] theorem intuition
- [ ] ceiling vs realization
- [ ] compression/downsampling warning examples
- [ ] practical interpretation for users

### Agent payload additions
- [ ] `theoretical_ceiling_by_horizon`
- [ ] `ceiling_summary`
- [ ] `compression_warning`
- [ ] `dpi_warning`

---

## F3 — Predictive Information Learning Curves

### Example scripts
- [x] `examples/triage/f3_predictive_info_learning_curve.py`

### Example requirements
- [x] short-memory process
- [x] longer-memory process
- [x] plateau detection
- [x] explicit reliability warning example for small sample size

### Notebook
- [x] `notebooks/triage/07_predictive_information_learning_curves.ipynb`

### Notebook sections
- [x] why “how much history?” differs from “is horizon forecastable?”
- [x] lookback curve construction
- [x] plateau detection
- [x] bias-floor warning and curse-of-dimensionality caveat

### Agent payload additions
- [ ] `recommended_lookback`
- [ ] `plateau_detected`
- [ ] `reliability_warnings`
- [ ] `lookback_summary`

---

## F4 — Spectral Predictability

### Example scripts
- [x] `examples/triage/f4_spectral_predictability.py`

### Example requirements
- [x] white-noise-like signal
- [x] periodic signal
- [x] PSD summary + score
- [x] note on preprocessing assumptions

### Notebook
- [x] merged into `08_spectral_and_entropy_diagnostics.ipynb`

### Agent payload additions
- [ ] `spectral_predictability_score`
- [ ] `spectral_summary`
- [ ] `spectral_reliability_notes`

---

## F5 — Largest Lyapunov Exponent

### Example scripts
- [x] `examples/triage/f5_lle_experimental.py`

### Example requirements
- [x] chaotic toy system
- [x] smoother non-chaotic example
- [x] parameter sensitivity demonstration
- [x] explicit experimental warning in output

### Notebook
- [x] optional section inside `08_spectral_and_entropy_diagnostics.ipynb`
- [ ] or separate appendix notebook only if complexity grows too much

### Agent payload additions
- [ ] `lyapunov_estimate`
- [ ] `lyapunov_warning`
- [ ] `experimental_flag_required`

### Important rule
- [ ] agent adapter must never present LLE as production-stable by default

---

## F6 — Entropy-Based Complexity Triage

### Example scripts
- [x] `examples/triage/f6_entropy_complexity.py`

### Example requirements
- [x] periodic signal
- [x] noisy signal
- [x] structured-irregular signal
- [x] complexity band result

### Notebook
- [x] merged into `08_spectral_and_entropy_diagnostics.ipynb`

### Agent payload additions
- [ ] `permutation_entropy`
- [ ] `spectral_entropy`
- [ ] `complexity_band`
- [ ] `complexity_summary`

---

## F7 — Batch Multi-Signal Ranking

### Example scripts
- [x] `examples/triage/f7_batch_ranking.py`

### Example requirements
- [x] 10+ signals
- [x] ranking output
- [x] show individual diagnostic columns, not only composite rank
- [x] export JSON/CSV example

### Notebook
- [x] `notebooks/triage/09_batch_and_exogenous_workbench.ipynb`

### Agent payload additions
- [ ] `batch_rank`
- [ ] `diagnostic_vector`
- [ ] `ranking_summary`

---

## F8 — Enhanced Exogenous Screening

### Example scripts
- [x] `examples/triage/f8_exogenous_screening.py`

### Example requirements
- [x] strong driver
- [x] weak driver
- [x] redundant driver
- [x] keep/review/reject table

### Notebook
- [x] shared inside `09_batch_and_exogenous_workbench.ipynb`

### Agent payload additions
- [ ] `driver_scores_by_horizon`
- [ ] `redundancy_flags`
- [ ] `driver_recommendations`
- [ ] `screening_summary`

---

# 4. Improved agent layer plan

## 4.1 Goal

The goal is not “AI for everything.”  
The goal is a cleaner adapter that can consume deterministic triage results and produce stable interpretation-ready objects for:

- future agents,
- chat interfaces,
- notebook narration,
- API consumers.

## 4.2 New adapter responsibilities

### A. Serializer
- [ ] convert deterministic result models into compact agent-safe payloads
- [ ] preserve field names and schema version
- [ ] avoid leaking internal implementation details

### B. Interpretation adapter
- [ ] build concise summaries from deterministic outputs
- [ ] keep warnings explicit
- [ ] separate “strong signal” from “experimental / low reliability” outputs

### C. Payload models
- [ ] define Pydantic payload models for:
  - [ ] profile summary
  - [ ] theoretical ceiling summary
  - [ ] lookback summary
  - [ ] complexity summary
  - [ ] batch summary
  - [ ] exogenous summary

## 4.3 Proposed files

- [ ] `src/forecastability/adapters/agents/triage_agent_payload_models.py`
- [ ] `src/forecastability/adapters/agents/triage_summary_serializer.py`
- [ ] `src/forecastability/adapters/agents/triage_agent_interpretation_adapter.py`

## 4.4 Acceptance criteria

- [ ] no agent adapter imports in domain/application layers
- [ ] payloads built only from deterministic result models
- [ ] schema version included
- [ ] experimental methods clearly marked

---

# 5. Agent notebook plan

## Notebook
- [ ] `notebooks/triage/06_agent_ready_triage_interpretation.ipynb`

## Purpose

This notebook demonstrates how a lightweight agent or chat layer should consume deterministic outputs.

It should **not** implement a full conversational framework.  
It should show:

1. deterministic triage execution,
2. payload serialization,
3. summary generation,
4. warning-aware interpretation.

## Required notebook flow

### Section 1 — Run deterministic triage
- [ ] load sample series
- [ ] run `run_triage()`
- [ ] inspect raw result bundle

### Section 2 — Convert to agent-ready payload
- [ ] serialize profile, limits, and any enabled diagnostics
- [ ] show compact payload schema

### Section 3 — Generate interpretation summary
- [ ] summary for human review
- [ ] explicit warning blocks
- [ ] experimental flags if present

### Section 4 — Compare strict deterministic output vs agent-friendly narrative
- [ ] tabular deterministic fields
- [ ] compact narrative paragraph
- [ ] show that no new science is added by the adapter

## Acceptance criteria
- [ ] notebook runs end-to-end
- [ ] no domain logic duplicated in notebook
- [ ] payload schema stable and documented
- [ ] warning and reliability notes preserved

---

# 6. Recommended implementation order

## Step 1
Build examples and notebook for F1 and F2 immediately after Phase 1 feature completion.

## Step 2
After Phase 2:
- add F3/F4/F6 examples,
- add notebooks 03 and 04,
- extend agent payload schema.

## Step 3
After Phase 3:
- add F7/F8 examples,
- add notebook 05,
- add notebook 06 for shared agent-ready interpretation.

## Step 4
Treat F5 as optional in notebook coverage until the experimental implementation stabilizes.

---

# 7. Cross-cutting checklist

## Examples
- [ ] every feature has executable script
- [ ] examples use library code only
- [ ] examples are deterministic

## Notebooks
- [ ] every notebook calls `src/` code
- [ ] notebook markdown includes paper references
- [ ] notebook output illustrates interpretation, not raw coding experimentation

## Agents
- [ ] one shared adapter layer
- [ ] one shared agent-ready notebook
- [ ] no per-feature agent duplication
- [ ] experimental outputs clearly flagged

---

# 8. Final recommendation

This is the right companion plan for the repo:

- examples prove methods are usable,
- notebooks make methods reviewable,
- agent adapters make outputs reusable,
- none of that pollutes the deterministic scientific core.

That keeps the architecture clean while still making the repo much easier to demonstrate, review, and extend.
