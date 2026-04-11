<!-- type: reference -->
# Should Have

These items are important and high-value, but they do not outrank paper-baseline parity or the core extension studies.

## 1. Frequency-wise extension report

Goal:
- Add a compact reporting layer that summarizes extension findings by frequency regime.

Acceptance criteria:
- Produces a report section or artifact per frequency group.
- Separates forecastability findings from exploitability findings.
- Makes AMI baseline and pAMI extension conclusions easy to compare within each frequency.

## 2. Extension ablation pack

Goal:
- Provide a reproducible study bundle for testing how extension conclusions change with lag cap, surrogate count, and scorer choice.

Acceptance criteria:
- Includes one reproducible configuration surface for ablations.
- Reports which conclusions are invariant and which are tuning-sensitive.
- Keeps benchmark comparisons frequency-aware rather than pooled into one global claim.

## 3. SOLID Refactor (Compatibility-Preserving)

Goal:
- Improve separation of concerns, reduce class and module responsibility overload, and prepare clean internal seams for later agent integration — **without** breaking the current public API or notebooks.

Full specification: [docs/plan/solid_refactor_backlog.md](solid_refactor_backlog.md)  
Frozen interface contract: [docs/plan/solid_refactor_contract.md](solid_refactor_contract.md)

Tickets:

- **SOLID-01** — Freeze the public compatibility contract
- **SOLID-02** — Add compatibility tests before changing internals
- **SOLID-03** — Turn `ForecastabilityAnalyzer` into a façade
- **SOLID-04** — Extract explicit analyzer state
- **SOLID-05** — Isolate scorer-registry dependency
- **SOLID-06** — Split exogenous analysis logic from core univariate logic
- **SOLID-07** — Refactor pipeline entry points into internal use cases
- **SOLID-08** — Remove filesystem side effects from config validation
- **SOLID-09** — Separate domain models from reporting assembly
- **SOLID-10** — Add notebook smoke contract
- **SOLID-11** — Align `docs/plan` with the new SOLID track
- **SOLID-12** — Prepare agent-ready seams, but do not add agents yet

Verification gates (all must pass before any ticket is closed):

```bash
uv run pytest -q -ra
uv run ruff check .
uv run ty check
```

Hard constraints:
- Public exports in `src/forecastability/__init__.py` must remain backward compatible.
- Notebook files must not be modified.
- No agent framework code is introduced in this phase.
