<!-- type: reference -->
# Versioning And Stability

_Last verified for release 0.2.0 consolidation on 2026-04-14._

Use this page with [public_api.md](public_api.md) when deciding whether a change is compatible, beta-surface churn, or intentionally experimental.

## Semantic Versioning Policy

The project follows `MAJOR.MINOR.PATCH` versioning.

- `MAJOR` is for deliberate backward-incompatible changes to the supported public surface.
- `MINOR` is for backward-compatible capability additions and contract-safe expansions.
- `PATCH` is for backward-compatible fixes, corrections, and documentation-only clarifications.

> [!NOTE]
> While published versions remain below `1.0.0`, the project still expects explicit migration notes for any intentional breaking change. Pre-1.0 does not waive documentation or upgrade discipline.

## Release Sources Of Truth

Different files answer different questions.

| Source | What it answers |
| --- | --- |
| [../pyproject.toml](../pyproject.toml) | Package metadata for built artifacts |
| [../src/forecastability/__init__.py](../src/forecastability/__init__.py) | In-repo package version string and stable re-export surface |
| [../CHANGELOG.md](../CHANGELOG.md) | Shipped release history and migration notes |
| [releases/](releases/) | Version-specific release notes when present |
| [plan/](plan/) | In-flight planning only; not a statement about what is already shipped |

> [!IMPORTANT]
> Planning docs may describe work that is underway on the repository branch. For shipped behavior, defer to tagged releases, built metadata, and the changelog.

## Stability Levels

| Level | Meaning |
| --- | --- |
| `stable` | Compatibility-sensitive surface. Breaking changes require explicit migration handling. |
| `beta` | Intended for real use, but command options, payload details, or ergonomics may still evolve. |
| `experimental` | No compatibility guarantee. Use only with version pinning and local validation. |

## Current Stability Classification

| Surface | Stability | Notes |
| --- | --- | --- |
| `forecastability` facade | `stable` | Top-level package imports documented in [public_api.md](public_api.md) |
| `forecastability.triage` facade | `stable` | Advanced triage namespace for batch models, events, readiness, and bundles |
| Analyzer facade (`ForecastabilityAnalyzer`, `ForecastabilityAnalyzerExog`, `AnalyzeResult`) | `stable` | Public analyzer contract used by package consumers and examples |
| Stable Pydantic config and result models re-exported from `forecastability` | `stable` | Field names are compatibility-sensitive |
| AMI, pAMI, scorer registry, and validation re-exports | `stable` | Use top-level imports rather than internal modules |
| CLI command `forecastability` | `beta` | `triage`, `triage-batch`, and `list-scorers` are usable, but flags and rendering details may evolve |
| HTTP API at `forecastability.adapters.api:app` | `beta` | Endpoint set is established, but transport-level payload details may still evolve |
| Dashboard command `forecastability-dashboard` | `beta` | Lightweight browser surface over deterministic adapters |
| MCP server | `experimental` | Tool names and request/response shapes may change |
| Agent and narration adapters | `experimental` | Optional narration surfaces over deterministic outputs |
| Largest Lyapunov exponent diagnostics | `experimental` | Project extension; excluded from automated triage decisions |
| Repo scripts under `scripts/` | Repo workflow, not package API | Maintainer-facing workflow surface, not semver-stable import API |
| Checked-in notebooks under `notebooks/` | Learning and analysis surface, not package API | Notebook filenames are maintained, but not all cells are part of a stable contract |
| Checked-in artifacts under `outputs/` | Reference artifacts, not package API | Useful examples, but not guaranteed to be freshly regenerated for every working tree |

## Compatibility Rules

- Public imports documented in [public_api.md](public_api.md) are compatibility-sensitive.
- Stable Pydantic model field names are part of the contract.
- Additive optional fields are compatible.
- Removing fields, renaming fields, changing meanings, or changing runtime entry points is breaking.
- Moving internal implementation modules is not breaking if the documented public facades still work.

## Migration Note Requirements

Every release entry in [../CHANGELOG.md](../CHANGELOG.md) must include either migration notes or an explicit statement that no migration is required.

Migration notes should state:

1. What changed.
2. Which users or integrations are affected.
3. Which import, command, config, or payload updates are required.
4. Whether a compatibility bridge exists and when it will be removed.
