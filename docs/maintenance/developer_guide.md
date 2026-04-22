<!-- type: how-to -->
# Developer Guide

This guide is for contributors maintaining the live repository surfaces rather than only consuming the package.

_Last verified for release 0.2.0 consolidation on 2026-04-14._

## 1. Start From The Real Public Surface

The supported public import roots are:

- `forecastability`
- `forecastability.triage`

The supported runtime entry points are:

- `forecastability`
- `forecastability-dashboard`
- `forecastability.adapters.api:app`

When documentation, examples, or scripts disagree with those surfaces, the code wins and the docs should be updated.

## 2. Know The Current Package Shape

The repository is layered and subpackage-heavy. The main internal packages are:

- `triage/`
- `use_cases/`
- `pipeline/`
- `metrics/`
- `diagnostics/`
- `reporting/`
- `utils/`
- `adapters/`
- `services/`
- `ports/`
- `bootstrap/`

Use [../code/module_map.md](../code/module_map.md) when you need the detailed map.

## 3. Use The Canonical Maintainer Workflows

| Workflow | Command |
| --- | --- |
| Canonical triage artifacts | `uv run python scripts/run_canonical_triage.py` |
| Benchmark panel | `uv run python scripts/run_benchmark_panel.py` |
| Report artifacts | `uv run python scripts/build_report_artifacts.py` |
| Exogenous analysis | `uv run python scripts/run_exog_analysis.py` |

Secondary maintenance utilities:

- `scripts/download_data.py`
- `scripts/check_notebook_contract.py`
- `scripts/rebuild_benchmark_fixture_artifacts.py`
- `scripts/rebuild_diagnostic_regression_fixtures.py`

## 4. Treat Config Files By Current Role

| Config | Current role |
| --- | --- |
| `configs/benchmark_panel.yaml` | Active benchmark workflow |
| `configs/canonical_examples.yaml` | Descriptive reference for canonical examples |
| `configs/interpretation_rules.yaml` | Reference interpretation thresholds |
| `configs/benchmark_exog_panel.yaml` | Secondary exogenous benchmark workflow |
| `configs/exogenous_screening_workbench.yaml` | Secondary screening workbench |
| `configs/robustness_study.yaml` | Secondary robustness workflow |

Do not document a config as a primary entry point unless it is actually wired into the current maintainer workflow.

## 5. Keep The Notebook Path Clean

The maintained notebook path is:

1. `docs/notebooks/README.md`
2. `notebooks/walkthroughs/00_air_passengers_showcase.ipynb`
3. `notebooks/walkthroughs/01_covariant_informative_showcase.ipynb`
4. Remaining walkthrough notebooks
5. Deep-dive notebooks `notebooks/triage/01` to `06`

Legacy narrative pages that duplicate live notebooks should be archived, not kept in the primary docs path.

## 6. Treat Artifacts As Reference Surfaces

The main artifact surfaces are:

- `outputs/json/`
- `outputs/tables/`
- `outputs/reports/`

Checked-in artifacts are useful reference outputs, but maintainers should avoid implying that every checked-in file is freshly regenerated.

## 7. Documentation Maintenance Rules

- Use the live repository as the source of truth.
- Add a Diataxis comment at the top of new or substantially rewritten docs.
- Prefer archiving stale or duplicate docs over leaving them active and misleading.
- Update [../../README.md](../../README.md), [../public_api.md](../public_api.md), [../code/module_map.md](../code/module_map.md), and [../versioning.md](../versioning.md) together when public surfaces move.
- Update [../api_contract.md](../api_contract.md) whenever CLI or API entry points, request shapes, or event semantics change.
- Update [../notebooks/README.md](../notebooks/README.md) whenever the onboarding notebook path changes.

## 8. Statistical Guardrails For Documentation

- Describe AMI as per-horizon.
- Describe pAMI as a linear-residual project extension rather than exact conditional mutual information.
- State surrogate significance as phase-randomized FFT surrogates with at least 99 surrogates and two-sided 95% bands.
- Distinguish skipped significance from computed-but-not-significant results.
- Restrict train-window-only wording to rolling-origin workflows.
- Treat `directness_ratio` and Pattern A to E as project interpretation heuristics, not paper-native theory.

Use [../wording_policy.md](../wording_policy.md) when release-facing wording is involved.

## 9. Keeping Machine-Guidance Surfaces Fresh

The machine-guidance layer consists of the following instruction surfaces:

| File | Audience |
| --- | --- |
| `llms.txt` | Generic LLM consumers |
| `.github/copilot-instructions.md` | GitHub Copilot (repo-wide) |
| `AGENTS.md` | Codex / agent-style tools |
| `.github/instructions/*.instructions.md` | Path-targeted Copilot instructions |

**Update these files whenever any of the following change:**

- The public import surface (`forecastability` / `forecastability.triage`) or its stable exports.
- The triage-first routing rule (description, entry point, or decision logic).
- The canonical entry points: `README.md`, `docs/quickstart.md`, `docs/public_api.md`.

**Verification:** after any instruction surface change, run the LLM visibility evaluation documented in [llm_visibility_eval.md](llm_visibility_eval.md).

> [!NOTE]
> Pass criterion: 4 of 5 benchmark prompts must produce triage-first behavior with no incorrect model-training claims. Fail any prompt that routes directly to model fitting.
