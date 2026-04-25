<!-- type: reference -->
# Documentation Coverage Matrix

This matrix maps maintained repository surfaces to their primary documentation owners.

_Last verified for release 0.2.0 consolidation on 2026-04-14._

## Active Coverage

| Repo surface | Source of truth | Primary doc | Secondary docs | Status |
| --- | --- | --- | --- | --- |
| Package facade | `src/forecastability/__init__.py` | [../public_api.md](../public_api.md) | [../../README.md](../../README.md), [../reference/versioning.md](../reference/versioning.md) | Active |
| Advanced triage facade | `src/forecastability/triage/__init__.py` | [../public_api.md](../public_api.md) | [../code/module_map.md](../code/module_map.md) | Active |
| Source layout | `src/forecastability/` | [../code/module_map.md](../code/module_map.md) | [../explanation/architecture.md](../explanation/architecture.md) | Active |
| CLI | `src/forecastability/adapters/cli.py`, `pyproject.toml` | [../../README.md](../../README.md) | [../explanation/surface_guide.md](../explanation/surface_guide.md), [../quickstart.md](../quickstart.md) | Active |
| Dashboard | `src/forecastability/adapters/dashboard.py`, `pyproject.toml` | [../../README.md](../../README.md) | [../explanation/surface_guide.md](../explanation/surface_guide.md) | Active |
| HTTP API | `src/forecastability/adapters/api.py` | [../reference/api_contract.md](../reference/api_contract.md) | [../../README.md](../../README.md), [../explanation/surface_guide.md](../explanation/surface_guide.md) | Active |
| Maintainer scripts | `scripts/` | [developer_guide.md](developer_guide.md) | [../../README.md](../../README.md), [../README.md](../README.md) | Active |
| Config roles | `configs/` | [developer_guide.md](developer_guide.md) | [../../README.md](../../README.md) | Active |
| Notebook path | `notebooks/walkthroughs/`, `notebooks/triage/` | [../notebooks/README.md](../notebooks/README.md) | [../../README.md](../../README.md), [../README.md](../README.md) | Active |
| Artifact surfaces | `outputs/json/`, `outputs/tables/`, `outputs/reports/` | [developer_guide.md](developer_guide.md) | [../../README.md](../../README.md), [../README.md](../README.md) | Active |
| Stability policy | `pyproject.toml`, facade docs, runtime entry points | [../reference/versioning.md](../reference/versioning.md) | [../public_api.md](../public_api.md) | Active |
| Architecture narrative | `src/forecastability/` and architecture tests | [../explanation/architecture.md](../explanation/architecture.md) | [../code/module_map.md](../code/module_map.md) | Active |

## Archived Or De-emphasized Coverage

| Archived surface | Reason | Current replacement |
| --- | --- | --- |
| Legacy notebook narrative pages under `docs/notebooks/` | Duplicated live notebooks and obscured the canonical learning path | [../notebooks/README.md](../notebooks/README.md) and the live notebooks |
| `docs/archive/theory/interpretation_patterns.md` | Checklist-style theory page that overstated project heuristics as active theory documentation | [wording_policy.md](wording_policy.md), [../explanation/limitations.md](../explanation/limitations.md), and active interpretation surfaces |
| Planning material in `docs/plan/` | Useful for release tracking, but not part of the primary docs path | [../README.md](../README.md) for active docs, `docs/plan/` for planning only |

## Maintenance Rule

If a repository surface is user-facing and lacks a clear primary doc owner in this table, add one before expanding the public docs path.
