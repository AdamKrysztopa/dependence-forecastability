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

## Verification gates

- `uv run pytest -q -ra`
- `uv run ruff check .`
- `uv run ty check`
