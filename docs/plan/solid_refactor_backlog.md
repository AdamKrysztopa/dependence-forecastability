# SOLID Refactor Backlog

## Purpose

This backlog defines a **compatibility-preserving SOLID refactor** for the repository.

The goal is to improve separation of concerns, reduce class and module responsibility overload, and prepare clean internal seams for later agent integration **without** breaking the current public API or notebooks.

## Hard Constraints

1. Do **not** rename or remove public exports from `src/forecastability/__init__.py`.
2. Do **not** change existing public class names, public function names, or public method signatures.
3. Do **not** edit notebook files.
4. Preserve behavior covered by tests, especially:
   - unknown scorer raises `KeyError`
   - `n_surrogates` must remain `>= 99`
   - exogenous analyzers require matching target/exog lengths
   - legacy AMI/pAMI methods reject exogenous input where tests expect that
   - rolling-origin diagnostics remain train-only
   - forecast scoring remains holdout-only
5. Use additive refactoring: introduce internal services, use-cases, ports, and adapters, then delegate current façade classes and functions to them.
6. Follow project style and keep functions small, typed, and low-complexity.
7. Avoid wide rewrites. No “clean slate” redesign in this phase.

## Global Definition of Done

A ticket is done only if all of the following pass:

```bash
uv run pytest -q -ra
uv run ruff check .
uv run ty check
```

In addition:

- notebooks remain unchanged in git diff
- public imports remain backward compatible
- existing behavior remains unchanged from the caller perspective

---

## Epic

**EPIC-SOLID-REF-01 — SOLID refactor without breaking notebooks or public API**

### Global implementation brief for Copilot/Codex

```text
Refactor the repository toward SOLID principles without changing the public API.

Hard constraints:
- Do not rename or remove public exports from src/forecastability/__init__.py.
- Do not change existing public class names, public function names, or method signatures.
- Do not edit notebook files.
- Preserve behavior covered by tests, especially:
  - unknown scorer raises KeyError
  - n_surrogates must remain >= 99
  - exogenous analyzers require matching target/exog lengths
  - legacy AMI/pAMI methods reject exogenous input where tests expect that
  - rolling-origin diagnostics remain train-only
  - forecast scoring remains holdout-only
- Use additive refactoring: introduce internal services/use-cases/adapters and delegate current façade classes/functions to them.
- Follow project style and keep functions small.

Done means:
- Existing tests pass.
- New compatibility tests pass.
- uv run pytest -q -ra passes
- uv run ruff check . passes
- uv run ty check passes
- Notebooks remain unchanged in git diff
```

---

## Ticket Backlog

### SOLID-01 — Freeze the public compatibility contract

**Story points:** 2  
**Depends on:** none

#### Goal

Create an explicit contract for what must not break during the refactor.

#### Scope

- Add `docs/plan/solid_refactor_contract.md`
- Define protected surface:
  - `ForecastabilityAnalyzer`
  - `ForecastabilityAnalyzerExog`
  - package-root exports in `src/forecastability/__init__.py`
  - `run_rolling_origin_evaluation`
  - `run_exogenous_rolling_origin_evaluation`
  - notebook import usage
- State clearly that internals may change, public behavior may not

#### Acceptance criteria

- New contract doc exists
- It references the current repo planning model under `docs/plan`
- It includes the verification gates from `acceptance_criteria.md`

#### Copilot/Codex prompt

```text
Create docs/plan/solid_refactor_contract.md for this repository.

The document must:
- define which public interfaces are frozen during the refactor
- state that notebooks must remain unchanged
- state that src/forecastability/__init__.py exports are part of the compatibility contract
- include the current verification commands:
  uv run pytest -q -ra
  uv run ruff check .
  uv run ty check
- align with the existing MoSCoW planning style in docs/plan

Do not change code yet.
```

---

### SOLID-02 — Add compatibility tests before changing internals

**Story points:** 3  
**Depends on:** SOLID-01

#### Goal

Create guardrails so the refactor cannot silently break external usage.

#### Scope

- Add `tests/test_public_api_contract.py`
- Add `tests/test_notebook_contract.py`
- Verify:
  - root-package imports still resolve
  - analyzer classes can be instantiated with current constructor style
  - main pipeline functions still import and execute minimal paths
  - notebook-facing import surface is intact

#### Acceptance criteria

- Tests fail if package-root exports disappear
- Tests fail if analyzer signatures or pipeline entry points are broken
- No production behavior changes

#### Copilot/Codex prompt

```text
Add compatibility tests before any refactor.

Create:
- tests/test_public_api_contract.py
- tests/test_notebook_contract.py

Requirements:
- Verify public imports from forecastability still resolve.
- Verify ForecastabilityAnalyzer and ForecastabilityAnalyzerExog can still be instantiated.
- Verify run_rolling_origin_evaluation and run_exogenous_rolling_origin_evaluation still import.
- Keep tests lightweight and deterministic.
- Do not change existing tests.
```

---

### SOLID-03 — Turn `ForecastabilityAnalyzer` into a façade

**Story points:** 8  
**Depends on:** SOLID-02

#### Goal

Split responsibilities without changing the public class.

#### Scope

Create internal services:

- `src/forecastability/services/raw_curve_service.py`
- `src/forecastability/services/partial_curve_service.py`
- `src/forecastability/services/significance_service.py`
- `src/forecastability/services/recommendation_service.py`
- `src/forecastability/services/plot_service.py`

Refactor `ForecastabilityAnalyzer` so it:

- validates inputs
- delegates to services
- stores minimal orchestration state
- returns the same outputs as before

#### Acceptance criteria

- No public signature changes
- Existing analyzer tests pass unchanged
- Unknown scorer still raises `KeyError`
- `n_surrogates < 99` still raises `ValueError`

#### Copilot/Codex prompt

```text
Refactor src/forecastability/analyzer.py so ForecastabilityAnalyzer becomes a façade.

Create internal service modules:
- raw_curve_service.py
- partial_curve_service.py
- significance_service.py
- recommendation_service.py
- plot_service.py

Rules:
- Do not change public method signatures.
- Do not change class names.
- Preserve existing behavior covered by tests.
- Keep analyzer as orchestrator only.
- Move computational logic into services.
- Keep functions small and typed.

Run tests after the refactor and stop only when behavior is unchanged.
```

---

### SOLID-04 — Extract explicit analyzer state

**Story points:** 5  
**Depends on:** SOLID-03

#### Goal

Separate mutable state from behavior.

#### Scope

- Add `src/forecastability/state.py`
- Introduce `AnalyzerState`
- Move cached arrays, bands, labels, and intermediate artifacts into the state object
- Keep plotting and `analyze()` behavior unchanged

#### Acceptance criteria

- State is explicit and private
- Analyzer methods still work exactly as before
- No notebook-facing behavior changes

#### Copilot/Codex prompt

```text
Introduce an explicit internal AnalyzerState object.

Tasks:
- Add src/forecastability/state.py
- Move mutable cached fields out of ForecastabilityAnalyzer into AnalyzerState
- Keep the public API untouched
- Ensure plot/analyze methods still work with no external changes
- Avoid changing tests unless only additive tests are needed
```

---

### SOLID-05 — Isolate scorer-registry dependency

**Story points:** 5  
**Depends on:** SOLID-03

#### Goal

Apply dependency inversion around dependence scorers.

#### Scope

- Make services depend on a registry abstraction rather than on analyzer internals
- Preserve default scorer behavior
- Preserve custom scorer extensibility

#### Acceptance criteria

- Existing scorer-based analyzer tests still pass
- Unknown scorer still raises `KeyError`
- No public registry usage changes for callers

#### Copilot/Codex prompt

```text
Refactor scorer usage so internal services depend on a scorer registry abstraction.

Requirements:
- Preserve current external scorer behavior
- Preserve custom scorer extensibility
- Do not rename public scorer-related imports
- Keep unknown scorer behavior unchanged
- Prefer dependency injection internally
```

---

### SOLID-06 — Split exogenous analysis logic from core univariate logic

**Story points:** 5  
**Depends on:** SOLID-03, SOLID-05

#### Goal

Make exogenous analysis a clean specialization instead of mixed logic.

#### Scope

Create:

- `src/forecastability/services/exog_raw_curve_service.py`
- `src/forecastability/services/exog_partial_curve_service.py`

Refactor `ForecastabilityAnalyzerExog` to delegate to those services.

#### Acceptance criteria

- Matching-shape validation remains intact
- Legacy AMI/pAMI methods still reject exogenous input where tests expect that
- Exogenous rolling-origin behavior remains unchanged

#### Copilot/Codex prompt

```text
Refactor exogenous analysis into dedicated services.

Tasks:
- Create exog_raw_curve_service.py
- Create exog_partial_curve_service.py
- Make ForecastabilityAnalyzerExog delegate to those services
- Preserve current validation behavior:
  - target/exog lengths must match
  - legacy AMI/pAMI pathways reject exogenous input where existing tests expect that
- Do not change public signatures
```

---

### SOLID-07 — Refactor pipeline entry points into internal use cases

**Story points:** 8  
**Depends on:** SOLID-03, SOLID-06

#### Goal

Keep public pipeline functions, but move orchestration into use-case modules.

#### Scope

Create:

- `src/forecastability/use_cases/run_rolling_origin_evaluation.py`
- `src/forecastability/use_cases/run_exogenous_rolling_origin_evaluation.py`

Leave `pipeline.py` as a thin compatibility wrapper.

#### Acceptance criteria

- Public pipeline function signatures stay unchanged
- Tests asserting `train_only_diagnostics == 1` and `holdout_only_scoring == 1` still pass
- `n_surrogates` defaults remain compatible

#### Copilot/Codex prompt

```text
Refactor pipeline orchestration into internal use-case modules.

Create:
- src/forecastability/use_cases/run_rolling_origin_evaluation.py
- src/forecastability/use_cases/run_exogenous_rolling_origin_evaluation.py

Keep:
- public functions in src/forecastability/pipeline.py
- existing signatures unchanged

Preserve:
- train-only diagnostics semantics
- holdout-only scoring semantics
- n_surrogates compatibility
```

---

### SOLID-08 — Remove filesystem side effects from config validation

**Story points:** 3  
**Depends on:** SOLID-02

#### Goal

Separate pure config validation from runtime side effects.

#### Scope

- Add a bootstrap helper, for example `src/forecastability/bootstrap/output_dirs.py`
- Move directory creation there
- Keep current config model interface stable
- Introduce compatibility shim if needed

#### Acceptance criteria

- Callers can still construct `OutputConfig` as before
- Directory creation is performed by dedicated runtime code, not by config validation
- No behavior regressions in code paths that rely on output directories

#### Copilot/Codex prompt

```text
Refactor OutputConfig so configuration stays pure and directory creation moves into runtime bootstrap code.

Tasks:
- Create a bootstrap/helper module for output directory preparation
- Keep OutputConfig externally compatible
- Remove directory.mkdir side effects from validation logic
- Preserve behavior for callers that rely on prepared output paths
```

---

### SOLID-09 — Separate domain models from reporting assembly

**Story points:** 5  
**Depends on:** SOLID-07

#### Goal

Keep payload and report construction out of domain-facing models and pipeline wrappers.

#### Scope

Create:

- `src/forecastability/assemblers/summary_assembler.py`
- `src/forecastability/assemblers/report_payload_assembler.py`

Move transformation logic there, but preserve existing model constructors or classmethods as thin wrappers if they are public.

#### Acceptance criteria

- Reporting payload shape stays stable
- Models become thinner
- No notebook-facing changes

#### Copilot/Codex prompt

```text
Extract reporting and payload assembly into dedicated assembler modules.

Create:
- summary_assembler.py
- report_payload_assembler.py

Rules:
- Keep current external payload behavior stable
- Prefer thin wrappers on existing public model/classmethod entry points
- Do not redesign outputs in this ticket
```

---

### SOLID-10 — Add notebook smoke contract

**Story points:** 3  
**Depends on:** SOLID-02, SOLID-07

#### Goal

Make “notebooks unchanged” measurable.

#### Scope

- Add `scripts/check_notebook_contract.py`
- Verify:
  - notebook files still exist
  - notebook-facing imports resolve
  - minimal representative calls run
- Do not modify notebooks

#### Acceptance criteria

- Script exits non-zero if notebook contract is broken
- Notebook files remain unchanged in git diff

#### Copilot/Codex prompt

```text
Add a notebook smoke-contract script.

Create:
- scripts/check_notebook_contract.py

The script should:
- verify notebooks exist
- verify notebook-facing imports resolve
- execute minimal representative import/use checks
- fail clearly if the compatibility contract is broken

Do not edit notebook content.
```

---

### SOLID-11 — Align `docs/plan` with the new SOLID track

**Story points:** 2  
**Depends on:** SOLID-01

#### Goal

Make the refactor visible in the repo planning surface.

#### Scope

- Add SOLID refactor items into `must_have.md` or `should_have.md`
- Keep MoSCoW structure intact

#### Acceptance criteria

- Planning docs clearly show that this is a compatibility-preserving refactor track
- Plan docs remain consistent with the existing planning policy

#### Copilot/Codex prompt

```text
Update docs/plan to include a SOLID refactor track.

Requirements:
- Respect current MoSCoW structure
- Keep this positioned as an internal, compatibility-preserving refactor
- Do not remove existing baseline-preservation language
- Add concise, actionable backlog entries
```

---

### SOLID-12 — Prepare agent-ready seams, but do not add agents yet

**Story points:** 5  
**Depends on:** SOLID-07, SOLID-09

#### Goal

Make the next agent phase easy without coupling this ticket set to a framework.

#### Scope

Create:

- `src/forecastability/ports/`
- `src/forecastability/use_cases/requests.py`
- `src/forecastability/use_cases/responses.py`

Define stable internal seams for:

- analyze-one-series
- rolling-origin benchmark
- exogenous benchmark
- report payload generation

#### Acceptance criteria

- New internal seams exist
- No agent framework dependency is added
- Public API remains unchanged

#### Copilot/Codex prompt

```text
Prepare internal agent-ready seams without introducing any agent framework.

Create internal request/response models and ports for:
- analyze one series
- run rolling-origin benchmark
- run exogenous benchmark
- generate report payload

Constraints:
- no public API changes
- no PydanticAI/LangGraph/MCP framework code yet
- this is preparation only
```

---

## Recommended Delivery Order

1. SOLID-01  
2. SOLID-02  
3. SOLID-03  
4. SOLID-04  
5. SOLID-05  
6. SOLID-06  
7. SOLID-07  
8. SOLID-08  
9. SOLID-09  
10. SOLID-10  
11. SOLID-11  
12. SOLID-12

---

## Execution Notes for Copilot/Codex

- Use **one ticket per branch**
- Use **one ticket per PR**
- Keep diffs narrow
- Run verification after every ticket
- Never combine public API preservation work with broad cleanup or style-only rewrites
- Favor additive delegation over moving public entry points
- Do not “improve” notebook code in this phase

---

## Tools and MCPs Worth Using

### Must-have

- **Filesystem / Workspace MCP**  
  Best for controlled multi-file refactors.

- **Git MCP**  
  Important for small commits, diff inspection, and quick rollback.

- **Terminal MCP**  
  Needed for `uv`, `pytest`, `ruff`, `ty`, and smoke scripts.

- **Search / ripgrep MCP**  
  Very useful for tracking public imports, notebook references, and service extraction boundaries.

### High-value extras

- **GitHub MCP**  
  Useful if you want to open issues, track ticket execution, or prepare PR drafts.

- **Python execution MCP**  
  Useful for minimal runtime checks and import-smoke validation.

- **Docs / Markdown MCP**  
  Helpful for updating `docs/plan` consistently.

### Optional

- **Notebook / Jupyter MCP**  
  Use only for smoke validation. Do not use it to rewrite notebooks in this phase.

### Avoid

- autonomous full-repo rewrite modes
- broad rename/move actions without test gating
- notebook-rewriting automation in this phase

---

## Suggested Agent Workflow

For each ticket:

1. read the related files
2. apply only the changes needed for that ticket
3. run tests and static checks
4. stop if compatibility breaks
5. commit only once the ticket meets all acceptance criteria

Recommended command sequence:

```bash
uv run pytest -q -ra
uv run ruff check .
uv run ty check
```

---

## Final Recommendation

This refactor should be treated as **internal architecture hardening**.

Do not redesign the user-facing API yet.  
Do not clean up notebooks yet.  
Do not add agents yet.

First, make the internal architecture stable, explicit, and modular.  
Then add agents on top of those cleaned seams.
