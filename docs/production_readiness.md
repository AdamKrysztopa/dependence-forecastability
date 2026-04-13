<!-- type: reference -->
# Production Readiness Contract

This page defines what is ready for production use today, what remains optional,
and what stability guarantees apply to each system zone.

> [!IMPORTANT]
> Deterministic scientific outputs are the source of truth.
> Optional narration layers must not change numeric results.

## Maturity zones

| Zone | Intended use | Stability level | Main risks | Required extras | Expected observability | Testing coverage target |
|---|---|---|---|---|---|---|
| 1) Domain scientific core | Deterministic AMI/pAMI computation, validation, significance bands, interpretation, and recommendation primitives. Includes diagnostic scorers (spectral predictability, permutation entropy, spectral entropy) and diagnostic services (forecastability profile, theoretical limits, predictive-info learning curves, complexity band). | stable | Data-leakage risk if callers bypass train-only diagnostics; misuse on short/sparse/degenerate series; over-interpretation of pAMI as exact conditional MI. | none (core install) | Deterministic outputs for fixed `random_state`; explicit warnings for known reliability constraints (for example readiness limits and unstable regimes). | Target: >=95% core-module coverage with invariant-focused tests (AMI/pAMI shape and bounds, rolling-origin train/test separation, surrogate requirements). |
| 1b) Experimental diagnostics | Largest Lyapunov exponent estimation. Gated behind `experimental: true` in config. | experimental | Numerical instability on short or noisy series; results not included in automated triage decisions. | none (core install) | Deterministic output for fixed `random_state`; diagnostic logs when estimation is unreliable. | Target: basic invariant tests only; not held to Zone 1 coverage bar. |
| 2) Triage application layer | Deterministic orchestration via `run_triage()`: readiness gate -> method routing -> compute -> interpretation -> recommendation. `run_triage()` now produces optional diagnostic fields (F1–F6) when enabled; `run_batch_triage()` includes diagnostic ranking columns for multi-series comparison. | stable | Incorrect goal/config selection; callers ignoring readiness warnings or blocked states; assumptions that recommendation text is a forecast guarantee. | none (core install) | Stage-level lifecycle visibility (readiness, routing, compute, interpretation) and deterministic result payloads suitable for audit trails. | Target: >=90% use-case and triage-policy coverage, including blocked/warning/clear flows and deterministic regression fixtures. |
| 3) Transport adapters | Interface access through CLI, HTTP API (+SSE), and MCP tools for remote or automated consumers. | beta overall (CLI and HTTP API are beta; MCP tools are experimental) | Interface drift across adapter versions; client coupling to presentation details; transport/runtime failures outside scientific core. | `transport` extra for HTTP API and MCP server (CLI remains available without transport extras). | CLI: exit codes + stderr. API: HTTP status + SSE stage events. MCP: structured tool error responses. | Target: >=80% adapter contract coverage with smoke tests for command/API paths and schema-level compatibility checks for payloads/events. |
| 4) LLM narration layer | Optional natural-language explanation of deterministic triage results for human consumption. | experimental | Hallucinated prose if prompts are changed poorly; provider outages/timeouts/rate limits; accidental trust inversion where narrative is treated as authoritative over numbers. | `agent` extra + provider credentials via settings (`.env`). | Narrative and caveat outputs are traceable to deterministic tool results; provider/runtime failures are surfaced as narration failures, not silent numeric changes. | Target: >=70% adapter-level tests using mocked providers and grounding checks that narration never rewrites deterministic numeric fields. |

## Safe default path

For production workflows, use the deterministic path first and keep narration optional:

1. Run deterministic triage with `run_triage()` (or equivalent deterministic CLI/API path).
2. Persist the structured numeric output (`analyze_result`, `interpretation`, `recommendation`) as the decision artifact.
3. Add LLM narration only as a secondary explanation layer for human readability.

> [!TIP]
> If you need one default operating mode, choose deterministic `run_triage()` without narration.

## Failure behavior and non-goals

### CLI path

- Failure behavior:
  - Input/readiness violations fail fast with non-zero exit status and explicit error text.
  - No partial success is assumed when validation fails.
- Non-goals:
  - The CLI is not a long-running orchestrator.
  - The CLI output format is not a frozen integration schema.

### API path

- Failure behavior:
  - Request-shape and validation failures return client-visible errors.
  - Runtime failures surface explicit error responses/events; no silent fallback to fabricated outputs.
- Non-goals:
  - The API is not a transactional job queue.
  - SSE transport does not imply exactly-once event delivery guarantees.

### Agent path

- Failure behavior:
  - Provider/config/runtime failures surface as narration-layer failures.
  - Deterministic numeric outputs remain unchanged; narration may be omitted.
- Non-goals:
  - The agent is not a replacement for deterministic computation.
  - Narrative text is not a source of new numeric evidence.

## Scope boundaries

- This contract governs production-readiness expectations for software surfaces.
- It does not upgrade statistical assumptions: users must still honor sample-size,
  surrogate, and train/test separation constraints documented in theory and architecture docs.

## Related documents

- [versioning.md](versioning.md)
- [architecture.md](architecture.md)
- [theory/foundations.md](theory/foundations.md)
