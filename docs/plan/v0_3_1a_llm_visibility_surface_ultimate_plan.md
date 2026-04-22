<!-- type: reference -->
# dependence-forecastability — LLM Visibility Surface Ultimate Plan

## Goal

> Make this repository unambiguously discoverable **and** correctly steerable for coding agents (Copilot, Codex, Cursor, etc.) so that, when a user asks for time-series forecasting help, the assistant routes through deterministic forecastability triage *before* recommending any model fitting.

Everything in this plan exists to serve that one outcome: high-signal machine-readable surfaces that bias coding assistants toward triage-first behavior on forecasting prompts.

**Non-goal.** This plan does **not** design the ForecastPrep contract/export feature. The visibility layer lands first because it improves discovery and agent routing without depending on any new public output contract.

---

## 1. Repo-grounded observations

The live repository already has a strong public skeleton:

- root `README.md`
- root `llms.txt`
- `docs/quickstart.md`
- `docs/public_api.md`
- canonical notebooks under `notebooks/walkthroughs/`
- runnable examples under `examples/`
- showcase scripts under `scripts/`
- stable package metadata in `pyproject.toml`

That is good.

The machine-guidance layer now covers the core repo-wide routing surfaces:

- `llms.txt` now acts as a concise routing surface with the triage-first rule, key invariants, and start-here anchors.
- the repository root `AGENTS.md` now provides repo-wide agent navigation, routing rules, editing rules by area, and validation commands.
- `.github/copilot-instructions.md` now provides repo-wide Copilot guidance, and `.github/instructions/` includes the additional Python, notebook, and planning-doc instruction files.
- package and repository discovery surfaces have been reviewed so forecastability-triage positioning is visible beyond research-only wording.

That means the repo is already readable and materially more **assertive** for Copilot/Codex-style tooling, with the remaining work concentrated in evaluation and release hygiene.

---

## 2. Strategic position

This repository should not present itself to coding agents as:

- another forecasting model zoo,
- another general time-series utilities package,
- a replacement for Nixtla / Darts / StatsForecast / sktime.

It should present itself as:

> deterministic forecastability triage before expensive model search.

That sentence must become visible across all high-signal machine-readable surfaces.

---

## 3. Design principles

### 3.1. Visibility must be additive, not noisy

Do not add large amounts of duplicated prose everywhere.

Instead:

- keep one short, strong repo-wide instruction layer,
- keep one slightly richer agent-navigation layer,
- use path-specific files only where the repository genuinely needs different behavior,
- keep `llms.txt` concise and pointer-oriented.

### 3.2. Steering must be action-oriented

Good guidance for coding tools is not vague philosophy.

Bad:

- “Use best practices.”
- “Consider analysis first.”

Good:

- “When the task is forecasting, run deterministic triage before proposing model families.”
- “Use `run_triage` or the canonical examples before suggesting hyperparameter search.”
- “If `blocked=True`, do not propose heavy model tuning as the next step.”

### 3.3. Prefer durable public surfaces

The high-value files are:

- `README.md`
- `llms.txt`
- `.github/copilot-instructions.md`
- `AGENTS.md`
- `.github/instructions/**/*.instructions.md`

These are more durable than trying to “game” one specific assistant UI.

### 3.4. Keep deterministic-first language consistent

The same repo identity must appear everywhere:

- forecastability triage,
- deterministic-first,
- pre-model diagnostics,
- covariate-aware dependence analysis,
- additive hand-off to downstream forecasting frameworks.

---

## 4. Tracking and implementation status

### 4.1 Tracking table

| ID | Item | Why it matters | Priority |
| --- | --- | --- | --- |
| VIS-F00 | Visibility audit + wording baseline | Align all surfaces around one message | Critical |
| VIS-F01 | `.github/copilot-instructions.md` | Strongest repo-wide Copilot lever | Critical |
| VIS-F02 | Root `AGENTS.md` | Strongest repo-wide Codex / agent lever | Critical |
| VIS-F03 | Path-specific instructions | Prevent bad edits in docs, notebooks, plans | High |
| VIS-F04 | Expand `llms.txt` | Better pointer surface for generic LLM consumers | High |
| VIS-F05 | README “When to use this first” section | Human + model discoverability | High |
| VIS-F06 | Keyword/topic/metadata expansion | Improves package and repo search surfaces | Medium |
| VIS-F07 | Agent-facing examples | Gives tools a callable workflow, not only prose | High |
| VIS-F08 | Evaluation harness | Lets you verify whether guidance actually changes behavior | High |
| VIS-F09 | Release hygiene + docs update | Keeps the new layer durable | Medium |

### 4.2 Implementation status

| ID | Feature | Phase | Overlap with existing | Genuine new work | Status |
| --- | --- | ---: | --- | --- | --- |
| VIS-F00 | Canonical routing paragraph (source-of-truth wording) | 0 | Reuses canonical wording from `docs/wording_policy.md` across `README.md`, `llms.txt`, `docs/quickstart.md`, and `docs/public_api.md` | Same canonical paragraph now reused on the repo-wide `.github/copilot-instructions.md` and `AGENTS.md` intro surfaces with only light surrounding context | ✅ **Implemented** |
| VIS-F01 | `.github/copilot-instructions.md` repo-wide guidance | 1 | New file; complements existing `README.md` / `docs/public_api.md` | Repo-wide Copilot guidance now pairs the canonical triage-first routing paragraph with start-here anchors and concrete repository rules | ✅ **Implemented** |
| VIS-F02 | Root `AGENTS.md` for Codex / agent tools | 1 | New file; mirrors identity from `README.md` and `docs/quickstart.md` | Root agent guidance now includes navigation order, forecasting-task routing rules, editing rules by area, validation commands, and common mistakes to avoid | ✅ **Implemented** |
| VIS-F03 | Path-specific `.github/instructions/*.instructions.md` surfaces | 2 | Adds the visibility-layer instruction trio inside the existing `.github/instructions/` directory, which already contains other path- and role-specific instruction files | Surface-specific `applyTo` instructions now keep Python, notebook, and planning-doc edits aligned with each area's rules | ✅ **Implemented** |
| VIS-F03.1 | `python.instructions.md` (src / tests / examples / scripts) | 2 | Codifies existing facade and additivity conventions | `applyTo` guidance now targets `src/**/*.py,tests/**/*.py,examples/**/*.py,scripts/**/*.py` with stable-facade, additive-surface, and deterministic-first rules | ✅ **Implemented** |
| VIS-F03.2 | `notebooks.instructions.md` | 2 | Codifies existing notebook conventions in `notebooks/walkthroughs/` | `applyTo` guidance now targets `notebooks/**/*.ipynb` and keeps notebooks demonstrative, with reusable logic in package code | ✅ **Implemented** |
| VIS-F03.3 | `docs_plan.instructions.md` | 2 | Codifies existing planning-doc conventions under `docs/plan/` | `applyTo` guidance now targets `docs/plan/**/*.md` and preserves plan structure, file targets, acceptance criteria, and domain language | ✅ **Implemented** |
| VIS-F04 | Expand `llms.txt` into a routing surface | 3 | Replaces the original pointer-only draft | `llms.txt` now serves as a concise routing surface with the explicit forecasting-task rule, stable-import guidance, key invariants, and important entry surfaces | ✅ **Implemented** |
| VIS-F05 | README "Use this before model search" section | 3 | Extends existing top-of-README narrative | README guidance now positions the package as triage before downstream model search and frames forecasting frameworks as post-triage hand-off targets | ✅ **Implemented** |
| VIS-F06 | Expand `pyproject.toml` keywords | 4 | Extends current keyword list | Package discovery metadata has been aligned with forecastability-triage, diagnostics, covariate, and downstream hand-off language | ✅ **Implemented** |
| VIS-F06.1 | GitHub topics review | 4 | Repository settings task; no file change | Repository topics have been reviewed and aligned with the package surface rather than vanity discovery tags | ✅ **Implemented** |
| VIS-F07 | Agent-facing examples and prompt anchors | 5 | Extends `examples/` taxonomy and `scripts/` showcase pattern | The repo now includes tiny triage-first example and demo anchors that branch on blocked results, surface `primary_lags`, and frame downstream forecasting tools as post-triage hand-off targets | ✅ **Implemented** |
| VIS-F08 | LLM-visibility evaluation harness | 6 | New maintenance doc; complements existing test fixtures | `docs/maintenance/llm_visibility_eval.md` with benchmark prompts and "good behavior" expectations to verify guidance impact | ✅ **Implemented** |
| VIS-F09 | Release hygiene and maintainer docs | 7 | Extends `CHANGELOG.md`, `docs/surface_guide.md`, `docs/maintenance/developer_guide.md` | Changelog entry for the machine-guidance layer plus maintainer notes on keeping instruction surfaces fresh | ⏳ **Not started** |

---

## 5. Desired behavioral contract for coding tools

When a coding assistant sees a forecasting prompt, the repository should bias it toward this sequence:

1. identify that the user is doing forecasting,
2. ask whether the task is univariate, covariate-aware, or batch triage,
3. propose a deterministic triage pass,
4. inspect readiness, informative horizons, primary lags, and covariate informativeness,
5. then recommend downstream model families or framework-specific settings,
6. explicitly say when simple baselines or data work should come before complex models.

The assistant should **not** default to:

- “Use XGBoost/LSTM/Temporal Fusion Transformer immediately.”
- “Tune many models first and analyze later.”
- “Treat all exogenous columns as equally useful.”

---

## 6. Phased delivery

## Phase 0 — Message hardening and source-of-truth wording

### VIS-F00 — Define the canonical routing paragraph

Create a short canonical paragraph that can be reused in:

- `README.md`
- `llms.txt`
- `.github/copilot-instructions.md`
- `AGENTS.md`
- docs pages that introduce the package

Recommended canonical wording:

```md
This repository is a deterministic forecastability triage toolkit for time series. When the task is time-series forecasting, do not jump directly to model fitting. Start with forecastability triage first: readiness, leakage risk, informative horizons, primary lags, seasonality structure, and covariate informativeness. Only then recommend downstream model families or framework-specific settings.
```

Acceptance criteria

- one canonical paragraph exists and is reused with minimal variation,
- `forecastability triage before expensive model search` remains the stable identity,
- no surface redescribes the project as a forecasting framework.

---

## Phase 1 — Repository-wide machine guidance

### VIS-F01 — Add `.github/copilot-instructions.md`

File target

- `.github/copilot-instructions.md`

Purpose

Repository-wide persistent instructions for GitHub Copilot surfaces.

Recommended initial content

```md
# dependence-forecastability

This repository is a deterministic forecastability triage toolkit for time series.

When the task involves forecasting:
- do not jump directly to model fitting,
- start with readiness and leakage checks,
- run deterministic triage first,
- inspect informative horizons, primary lags, seasonality structure, and covariate informativeness,
- only then recommend downstream model families or framework-specific settings.

Repository rules:
- prefer the stable facade from `forecastability` unless a lower-level namespace is explicitly needed,
- treat `docs/public_api.md` as the supported import contract,
- keep additive compatibility for stable Pydantic result fields,
- do not describe the package as a model zoo or a replacement for downstream forecasting libraries.

Preferred starting points:
- `README.md`
- `docs/quickstart.md`
- `docs/public_api.md`
- `examples/minimal_python.py`
- `examples/minimal_covariant.py`
- `notebooks/walkthroughs/00_air_passengers_showcase.ipynb`
```

Acceptance criteria

- file exists at the exact supported path,
- content is short, concrete, and operational,
- it names the preferred entry points,
- it contains explicit “do not jump directly to model fitting” guidance.

### VIS-F02 — Add root `AGENTS.md`

File target

- `AGENTS.md`

Purpose

Project-level guidance for Codex and agent-style coding tools.

Recommended structure

1. Repository identity
2. Navigation order
3. Forecasting-task routing rules
4. Editing rules by area
5. Validation commands
6. Common mistakes to avoid

Recommended initial content

```md
# AGENTS.md

## Project identity
This repository is a deterministic forecastability triage toolkit.
It is used before expensive forecasting model search.

## Start here
1. `README.md`
2. `docs/quickstart.md`
3. `docs/public_api.md`
4. `examples/minimal_python.py`
5. `examples/minimal_covariant.py`
6. `notebooks/walkthroughs/00_air_passengers_showcase.ipynb`

## Forecasting routing rules
If the user asks for time-series forecasting help:
1. identify univariate vs. covariate-aware scope,
2. prefer deterministic triage first,
3. inspect readiness, informative horizons, primary lags, and covariate informativeness,
4. only after that propose model-family or framework-specific settings.

## Public API rule
Prefer imports from `forecastability` and `forecastability.triage`.
Do not introduce new examples that depend on internal namespaces unless the task is explicitly contributor-facing.

## Editing rules
- Keep stable Pydantic field names additive.
- Do not rewrite docs to imply the package itself performs model training.
- Keep notebooks illustrative; reusable logic belongs in package code.
- Keep example scripts small and runnable.

## Validation
Run tests and relevant fixture rebuild scripts when changing result surfaces or examples.
```

Acceptance criteria

- root `AGENTS.md` exists,
- it is short enough to remain useful,
- it explicitly tells agents how to route forecasting tasks,
- it references the stable facade and docs.

---

## Phase 2 — Path-specific instruction surfaces

### VIS-F03 — Add the visibility-layer `.github/instructions/` files

File targets

- `.github/instructions/python.instructions.md`
- `.github/instructions/notebooks.instructions.md`
- `.github/instructions/docs_plan.instructions.md`

The repository already contains other instruction files under `.github/instructions/`. This Phase 2 item refers only to the additional visibility-layer instruction set listed above, which has now landed alongside the broader instruction catalog.

#### VIS-F03.1 — Python source rules

Suggested `applyTo`

```md
---
applyTo: "src/**/*.py,tests/**/*.py,examples/**/*.py,scripts/**/*.py"
---
```

Suggested content focus

- prefer stable facade for examples,
- keep new public outputs additive,
- avoid notebook-only logic duplication,
- keep deterministic-first semantics intact.

#### VIS-F03.2 — Notebook rules

Suggested `applyTo`

```md
---
applyTo: "notebooks/**/*.ipynb"
---
```

Suggested content focus

- notebooks explain and demonstrate,
- reusable logic belongs in package code,
- no hidden analysis steps that bypass the public package.

#### VIS-F03.3 — Planning-doc rules

Suggested `applyTo`

```md
---
applyTo: "docs/plan/**/*.md"
---
```

Suggested content focus

- preserve plan structure,
- include file targets,
- include acceptance criteria,
- separate additive from breaking changes,
- do not replace domain language with generic AI buzzwords.

Acceptance criteria

- each instruction file has frontmatter with `applyTo`,
- instructions differ by surface and are not clones,
- notebooks and plans stop drifting stylistically from package rules.

---

## Phase 3 — Pointer surface refinement

### VIS-F04 — Expand `llms.txt`

File target

- `llms.txt`

Original problem

The starting file was useful but too thin. It pointed to the right places and listed a few invariants, but it did not strongly encode the forecasting-task routing behavior.

Recommended replacement shape

```md
# dependence-forecastability: deterministic forecastability triage for coding agents

Use this repository when the task is time-series forecasting and the user should not jump directly to model fitting.

Start in this order:
1. README.md
2. docs/quickstart.md
3. docs/public_api.md
4. examples/minimal_python.py
5. examples/minimal_covariant.py
6. notebooks/walkthroughs/00_air_passengers_showcase.ipynb

Routing rule:
When the task is forecasting, start with forecastability triage first.
Inspect readiness, leakage risk, informative horizons, primary lags, seasonality structure,
and covariate informativeness before recommending downstream models.

Key invariants:
- Compute AMI and pAMI per horizon.
- In rolling-origin evaluation, compute diagnostics on training windows only.
- Use phase-randomized FFT surrogates with n_surrogates >= 99.
- Prefer stable imports from `forecastability` and `forecastability.triage`.
- Do not describe this package as a model-training framework.

Important surfaces:
- docs/public_api.md
- docs/api_contract.md
- docs/diagnostics_matrix.md
- docs/golden_path.md
- docs/surface_guide.md
```

Acceptance criteria

- `llms.txt` remains short and pointer-oriented,
- it now contains explicit routing language,
- it includes the stable import rule,
- it distinguishes the package from downstream training libraries.

### VIS-F05 — Add README “Use this before model search” section

File target

- `README.md`

Add a visible section near the top, after “Why this package” or “Quickstart”.

Suggested heading

```md
## Use this before model search
```

Suggested bullets

- Use this package when you need to decide whether forecasting effort is justified.
- Use this package to inspect informative horizons, primary lags, and covariate usefulness before committing to model search.
- Use downstream forecasting frameworks after triage, not instead of triage.

Acceptance criteria

- the section is near the top,
- it uses plain workflow language,
- it clearly positions downstream frameworks as next-step consumers.

---

## Phase 4 — Discoverability metadata

### VIS-F06 — Expand package metadata keywords

File target

- `pyproject.toml`

Original keyword set was valid but too narrow:

- forecasting
- time-series
- mutual-information
- forecastability
- diagnostics
- triage

Recommended additions

- `lag-selection`
- `seasonality`
- `feature-screening`
- `exogenous-variables`
- `time-series-diagnostics`
- `forecasting-diagnostics`
- `covariates`
- `pre-model-analysis`
- `nixtla`
- `darts`
- `statsforecast`

Important rule

Do **not** overstuff with irrelevant search bait.
Only add terms that match real surfaces or planned adapters.

Acceptance criteria

- keywords expand in a meaningful way,
- they stay faithful to the repository identity,
- they do not imply the package is a replacement forecasting framework.

### VIS-F06.1 — GitHub topics review

Manual repo settings task

Suggested topics

- `forecastability`
- `time-series`
- `forecasting`
- `diagnostics`
- `mutual-information`
- `time-series-analysis`
- `feature-selection`
- `causal-discovery`
- `python`

Acceptance criteria

- topics are aligned with the current package surface,
- no vanity tags,
- topics support both research and engineering discovery.

---

## Phase 5 — Agent-usable examples and prompt anchors

### VIS-F07 — Add forecasting-first examples for agents

File targets

- `examples/forecasting_triage_first.py`
- `examples/forecasting_triage_then_handoff.md`
- `scripts/run_triage_handoff_demo.py`

Purpose

Many assistants copy structure from examples. Add one or two tiny examples whose whole point is: triage first, then hand off.

#### Example 1 — Minimal routing example

```python
from forecastability import TriageRequest, run_triage

result = run_triage(
    TriageRequest(
        series=series,
        goal="univariate",
        max_lag=48,
        n_surrogates=99,
        random_state=42,
    )
)

if result.blocked:
    print("Do data/readiness work before model search.")
else:
    print(result.interpretation.primary_lags)
    print(result.interpretation.forecastability_class)
```

#### Example 2 — Human-readable hand-off note

```md
Use deterministic triage first.
If the result is weak or blocked, prefer baseline models and data cleanup.
If the result is structured, use the detected lags / seasonality / covariate signal to configure downstream forecasting tools.
```

Acceptance criteria

- examples are tiny and copyable,
- one example explicitly branches on `blocked`,
- one example explicitly uses `primary_lags`,
- one example explains hand-off to downstream frameworks.

---

## Phase 6 — Evaluation harness

### VIS-F08 — Add a “does the guidance work?” check

File targets

- `docs/maintenance/llm_visibility_eval.md`
- optional lightweight prompt fixtures under `docs/fixtures/` or `tests/fixtures/`

Goal

You need a repeatable way to test whether the new surfaces actually change assistant behavior.

Suggested evaluation prompts

1. “I have daily sales data. Which forecasting model should I use?”
2. “I have target + promo + price covariates. Can you help set up Darts?”
3. “Can you train an LSTM on this time series?”
4. “What should I inspect before using Nixtla?”

Expected successful behavior

- asks or assumes univariate vs covariate-aware scope,
- proposes deterministic triage before heavy modeling,
- mentions informative lags / covariates / readiness,
- does not leap straight to deep-learning suggestions.

Acceptance criteria

- at least 5 benchmark prompts exist,
- each prompt has expected “good behavior” bullets,
- repo maintainers can re-run the evaluation after instruction changes.

---

## Phase 7 — Release and maintenance hygiene

### VIS-F09 — Documentation and changelog integration

File targets

- `CHANGELOG.md`
- `docs/surface_guide.md`
- `docs/maintenance/developer_guide.md`

Required notes

- repo now exposes Copilot/Codex guidance surfaces,
- `llms.txt` is pointer-oriented, not a full manual,
- new instructions are meant to route forecasting tasks through deterministic triage first.

Acceptance criteria

- changelog explicitly mentions the new machine-guidance layer,
- maintainer docs explain how to update these files,
- no instruction surface becomes stale relative to README/public API.

---

## 7. Out of scope

- pretending that `llms.txt` alone controls Copilot/Codex behavior,
- stuffing keywords with unrelated library names,
- adding huge prompt manuals that become stale,
- replacing package docs with AI-marketing language,
- coupling the visibility work to the future ForecastPrep contract/export feature.

---

## 8. Recommended implementation order

1. VIS-F00 canonical wording
2. VIS-F01 `.github/copilot-instructions.md`
3. VIS-F02 `AGENTS.md`
4. VIS-F03 path-specific instructions
5. VIS-F04 `llms.txt` expansion
6. VIS-F05 README usage section
7. VIS-F07 tiny agent-facing examples
8. VIS-F06 metadata / topics update
9. VIS-F08 evaluation harness
10. VIS-F09 changelog + maintainer docs

---

## 9. Practical judgment

This visibility plan should land **before** the ForecastPrep contract.

Reason:

- it is lower-risk,
- it strengthens Copilot/Codex behavior immediately,
- it does not require public contract design decisions,
- it improves both human discovery and coding-agent routing,
- it creates the exact narrative into which the later hand-off contract can fit.

The contract/export feature should then be described as:

> deterministic triage result → normalized downstream hand-off

not as the primary visibility mechanism.
