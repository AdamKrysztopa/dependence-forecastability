<!-- type: reference -->
# Plan Acceptance Criteria

This file defines the shared done criteria for plan documents. A roadmap item is complete only when the statements below remain true.

## Product center of gravity

- The repository is a deterministic forecastability triage toolkit first. The primary path remains deterministic `run_triage()` / `run_batch_triage()`-style execution, not notebook logic, agents, or transports.
- Numeric outputs remain authoritative only when produced by deterministic code in `src/forecastability/`.
- Notebooks are consumers, walkthroughs, or analysis surfaces. They must not become the implementation source of truth.

## Architecture discipline

- Runtime changes preserve explicit hexagonal boundaries: adapters at the edge, use cases for orchestration, and the scientific core isolated from transport and presentation concerns.
- Responsibilities stay SOLID-sized: core scientific models do not absorb I/O, plotting, transport, persistence, narration, or notebook orchestration without a strong reason.
- Stable facades may be kept for compatibility, but new coupling from core/domain code into notebooks, agents, MCPs, or other adapter concerns is not acceptable.
- CLI, API, MCP, and agent layers remain outer surfaces over the same deterministic triage truth. They may transport or narrate results, but they do not recompute or override scientific outputs.

## Scientific invariants

- AMI/pAMI remain horizon-specific.
- Readiness and routing remain statistical gatekeepers. Invalid, misaligned, lag-infeasible, or significance-infeasible requests must be surfaced before deep compute rather than hidden by convenience layers.
- In rolling-origin evaluation, AMI/pAMI remain train-window only.
- Forecast scoring remains post-origin only.
- Surrogate workflows enforce `n_surrogates >= 99`.
- Significance handling preserves the distinction between "bands not computed" and "computed, but nothing is significant".
- `directness_ratio > 1.0` remains a warning or anomaly boundary, not positive evidence.
- Integrals use `np.trapezoid`, not `np.trapz`.
- Project extensions remain explicitly distinguished from paper-aligned claims. pAMI, agent layers, and other extensions must not be described as paper-native guarantees or causality proofs.

## Surface tiers and experimental scope

- Every affected surface is classified clearly as stable, beta, or experimental.
- Agent and MCP layers are optional outer surfaces. They must not become the required primary user path.
- Experimental diagnostics and live-LLM behaviors are explicitly gated and labeled so they cannot be confused with stable defaults.
- Experimental diagnostics must not silently become default evidence, automated ranking signals, or policy-driving outputs.

## Verification gates

- `uv run pytest -q -ra`
- `uv run ruff check .`
- `uv run ty check`
