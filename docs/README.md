<!-- type: reference -->
# Documentation

Navigation hub for the AMI → pAMI Forecastability Analysis documentation.

## Quickstart

Task-oriented first-run entry points.

| Document | Description |
|---|---|
| [quickstart.md](quickstart.md) | Laddered quickstart: 60s CLI, 5m notebook, 10m Python API, 15m HTTP API, plus optional agent and MCP routes using one shared signal |

## Results

Decision-focused evidence summary.

| Document | Description |
|---|---|
| [results_summary.md](results_summary.md) | Compact evidence-first summary of univariate AMI/pAMI, exogenous screening, and triage workflow findings, with explicit limitations |

## Operational Guidance

Practical guides for choosing components and mapping diagnostics to industrial decisions.

| Document | Description |
|---|---|
| [why_use_this.md](why_use_this.md) | Component comparison matrix for AMI, pAMI, directness ratio, exogenous analysis, triage, and optional narration |
| [use_cases_industrial.md](use_cases_industrial.md) | Manufacturing/reliability/PdM scenario matrix with recommended path, outputs, and next decisions |

## Theory

Conceptual background and mathematical foundations.

| Document | Description |
|---|---|
| [theory/README.md](theory/README.md) | Theory guide scope and paper references |
| [theory/foundations.md](theory/foundations.md) | AMI and pAMI definitions, significance logic, rolling-origin invariants |
| [theory/interpretation_patterns.md](theory/interpretation_patterns.md) | Pattern A–E classification logic for agentic narration |

## Architecture

| Document | Description |
|---|---|
| [architecture.md](architecture.md) | Hexagonal architecture guide, SOLID principles, layer boundaries, enforcement |

## Project Policy

| Document | Description |
|---|---|
| [versioning.md](versioning.md) | Semantic versioning policy, stability levels, and migration-note requirements |
| [production_readiness.md](production_readiness.md) | Production maturity zones, safe default deterministic path, and failure/non-goal contract for CLI/API/agent surfaces |

## Code Reference

API documentation and module maps.

| Document | Description |
|---|---|
| [code/README.md](code/README.md) | Code reference overview |
| [code/module_map.md](code/module_map.md) | Module-by-module public symbol reference |
| [code/exog_analyzer.md](code/exog_analyzer.md) | `ForecastabilityAnalyzerExog` user manual (synthetic data) |
| [code/exog_analyzer_real_data.md](code/exog_analyzer_real_data.md) | `ForecastabilityAnalyzerExog` user manual (real-world data) |
| [code/exog_benchmark_workflow.md](code/exog_benchmark_workflow.md) | Fixed exogenous benchmark slice workflow |

## Planning

Project roadmap and acceptance criteria (MoSCoW framework).

| Document | Description |
|---|---|
| [plan/README.md](plan/README.md) | Planning surface overview |
| [plan/acceptance_criteria.md](plan/acceptance_criteria.md) | Done criteria for all roadmap items |
| [plan/must_have.md](plan/must_have.md) | Non-negotiable items (✅ complete) |
| [plan/should_have.md](plan/should_have.md) | High-value improvements (✅ complete) |
| [plan/could_have.md](plan/could_have.md) | Optional extensions (open) |
| [plan/wont_have.md](plan/wont_have.md) | Explicit exclusions |

## Archive

Historical completed development documentation from the build-out phase.
These files are reference-only and not part of the active roadmap.

Located in [archive/](archive/) — 27 documents covering repository setup, core types, config objects, validation, datasets, pipeline design, rolling-origin evaluation, models, reporting, and more.
