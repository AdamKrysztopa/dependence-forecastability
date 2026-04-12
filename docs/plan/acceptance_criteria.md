<!-- type: reference -->
# Plan Acceptance Criteria

This file defines what must be true before any roadmap item can be marked complete.

## Baseline preservation

- The repository retains all functionality required to reproduce the paper baseline from arXiv:2601.10006.
- AMI remains horizon-specific.
- Rolling-origin diagnostics remain train-window only.
- Forecast scoring remains post-origin only.
- Surrogate workflows keep `n_surrogates >= 99`.
- Integrals use `np.trapezoid`.

## Extension discipline

- Every new item extends functionality, study coverage, or reporting beyond the paper baseline.
- Documentation states whether the item is paper-native parity or project-only extension.
- Extensions do not weaken or replace the paper-aligned workflow.
- Agent-enabled UX layers and notebook facades reuse the deterministic triage use case; they add convenience, explanation, or transport only.
- New notebooks (e.g. `03_agentic_triage.ipynb`) must route all compute through `run_triage()` and must not duplicate orchestration logic from notebooks 01/02.
- If agent workflows are maintained in both `.github` and `.codex`, the supported role roster and ownership boundaries are documented and aligned.

## Verification gates

- `uv run pytest -q -ra`
- `uv run ruff check .`
- `uv run ty check`
