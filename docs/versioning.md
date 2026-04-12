<!-- type: reference -->
# Versioning and Stability

## Semantic Versioning policy

This project follows Semantic Versioning: `MAJOR.MINOR.PATCH`.

- **MAJOR**: backward-incompatible changes to public behavior or interfaces.
- **MINOR**: backward-compatible feature additions or capability expansions.
- **PATCH**: backward-compatible fixes and clarifications.

> [!NOTE]
> While versions are below `1.0.0`, some breaking changes may occur in MINOR releases.
> Any such change still requires explicit migration notes.

## Stability levels

- **stable**: compatibility is expected across MINOR and PATCH releases.
- **beta**: intended for use, but interfaces may still evolve.
- **experimental**: no compatibility guarantee; rapid iteration expected.

## Current stability classification

| Surface | Stability | Notes |
|---|---|---|
| Domain APIs (`src/forecastability/**`) | stable | Core AMI/pAMI, validation, interpretation, and pipeline contracts are heavily tested and treated as compatibility-sensitive. |
| CLI (`forecastability triage`, `forecastability list-scorers`) | beta | User-facing commands are usable, but options/output details may still be refined. |
| HTTP API (FastAPI + SSE adapters) | beta | Endpoint and stream payload details may evolve as transport adapters mature. |
| MCP server tools | experimental | Tool names and request/response payloads may change during integration hardening. |
| Agent layer (PydanticAI adapters) | experimental | Optional narration layer; provider-facing behavior and response schema may change. |

## Upgrade notes and migration requirements

- Every release must include a release entry in `CHANGELOG.md`.
- Any breaking change must include a `Migration notes` subsection in that release entry.
- Migration notes must state:
  - what changed,
  - who is affected,
  - required code or config updates,
  - any compatibility bridge or fallback path.
- If no user action is required, explicitly state: `No migration required`.
