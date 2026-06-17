# Architecture review — `dependence-forecastability` (v0.5.0)

- Date: 2026-06-17
- Mode: Refactoring review of existing code (arch-crew:decide-architecture)
- Scope: `src/forecastability/` import structure and layering. Math correctness,
  performance, and release tooling are out of scope (owned by other reviews).

## Current shape

- **Structure:** Hexagonal / ports-and-adapters — *intended*, **partially realized**.
  The ring folders exist (`domain/`, `ports/`, `services/`, `use_cases/`, `api/`,
  `adapters/`) but ~19k LOC of computational code still lives in pre-migration flat
  packages (`diagnostics` 4.5k, `reporting` 3.7k, `utils` 3.2k, `triage` 1.7k,
  `metrics` 1.4k, `pipeline` 1.3k, `kernels` 0.3k) that are cyclically coupled to the
  rings.
- **Topology:** Single installable Python package — modular monolith / library.
  Optionally exposed as a service via a transport adapter (FastAPI + MCP). *No*
  microservices, event bus, or CQRS — correctly so.
- **Data:** Pipe-and-Filter (`pipeline/`) — staged ingest → transform → score →
  report, with rolling-origin evaluation. Right-sized for a scientific compute path.
- **UI / Presentation:** CLI (`forecastability`), a matplotlib dashboard, and an
  optional MCP server. No web front-end; MVC/MVVM *n/a*.
- **Overlays:** LLM-agent adapter (`adapters/agents`, optional extra). The public-API
  facade + deprecation shim is effectively a **Strangler-Fig** over the v0.4.x surface.

## Findings

### 1. The hexagonal migration is half-done — ring layers and legacy packages form import cycles
The folder taxonomy is hexagonal, but the **dependency graph is bidirectional**, so the
guarantee hexagonal buys you (test the core in isolation, swap an adapter without
touching the domain) is not actually realized.

- Inner rings reach **outward** into legacy packages:
  - `domain/models/triage.py:16` → `forecastability.triage.extended_forecastability`
  - `domain/models/comparison_report.py:20` → `forecastability.triage.batch_models`
  - `ports/__init__.py:14,26,27` → `metrics`, `triage`, `utils`
- Legacy packages reach **inward** at the same time, closing cycles:
  - `triage` → `domain` (x14), `diagnostics` → `services` (x15) / `use_cases` (x7),
    `pipeline` → `services` (x6), `utils` → `domain` (x3).
- Net effect: `services ↔ triage`, `services ↔ diagnostics`, `services ↔ metrics`,
  `domain ↔ triage`, `domain ↔ utils`, `use_cases ↔ pipeline` are all mutual-import
  cycles. This is a tangled monolith wearing hex-shaped folders.

· **Impact (real pain):** you cannot import `domain` without dragging in `triage`,
which drags in `services`/`adapters`; the core is not independently testable, and
"which layer owns this?" has no honest answer for ~19k LOC.
· **Move:** finish the Strangler-Fig migration one cycle at a time — pull pure compute
(`metrics`, `kernels`, diagnostic math) inward behind `ports`; the orchestration in
`triage`/`pipeline` becomes `use_cases`; legacy packages shrink to empty.
(`catalog #p-rings`, Strangler Fig)
· **First step:** break the worst edge — move `ExtendedForecastabilityAnalysisResult`
and `BatchSummaryRow` into `domain/models/`, then invert `triage` to import them from
`domain`. That removes the `domain → triage` cycle mechanically, with no math change.
· **Cost:** churn across import sites; do it incrementally so CI stays green per cycle.

### 2. The architecture-boundary test gives false assurance
`tests/test_architecture_boundaries.py` enforces only that `domain`/`ports` avoid
*external* infra (`sklearn`, `scipy`, `matplotlib`, …). It is blind to **first-party**
outward imports, so `domain → triage` and `ports → metrics/triage/utils` pass CI today.
The green check actively masks finding #1.

· **Impact:** the one guardrail meant to protect the hex boundary cannot see the
boundary's actual breaches.
· **Move:** add a rule that `domain`/`ports` may import only `domain`/`ports` among
first-party packages (plus numpy/pandas/pydantic), and a cycle-detection assertion over
the layer graph. (`catalog #p-rings` review cue)
· **First step:** add `triage`, `utils`, `metrics`, `pipeline`, `reporting`,
`diagnostics` to a first-party forbidden set for `domain`/`ports`, marked `xfail`
(strict) until #1's first step lands — so the test documents the debt and flips to
passing as the migration completes.
· **Cost:** one test; goes red immediately (by design).

### 3. `utils/` is a dumping ground that participates in the cycles
At 3.2k LOC, `utils/` imports `domain`, `pipeline`, and `reporting`, and is imported by
five other packages. A "utils" that imports domain and reporting is not utilities — it
is hidden domain/orchestration code mislabeled as a leaf.

· **Impact:** it is the hub of several cycles, so it blocks isolating any layer.
· **Move:** split into (a) a true leaf shared-kernel (pure types/math helpers, *zero*
first-party imports) and (b) domain-aware pieces relocated into `domain`/`services`.
· **First step:** identify the no-first-party-import subset of `utils` and freeze it as
the leaf; everything that imports `domain`/`reporting` is the relocation backlog.
· **Cost:** moderate; pairs naturally with #1.

## Leave alone

- **Public-surface discipline is exemplary — do not touch.** The thin
  `forecastability/__init__.py` re-export shim, the frozen `api/__init__.py` (~25 named
  exports, semver-guarded), the lazy `_legacy/` `DeprecationWarning` shim, and the
  migration guide are textbook Strangler-Fig facade work. This is the part holding the
  half-migrated internals together cleanly for users.
- **Topology.** A single library / modular monolith is exactly right. There is no
  forcing function for microservices, an event bus, CQRS, or a saga here — resist all of
  them. The optional FastAPI/MCP transport and the LLM agent live correctly as edge
  adapters behind optional extras.
- **Pipe-and-Filter data flow** (`pipeline/` + rolling-origin) is appropriate for staged
  scientific compute; keep it.
- **Frozen Pydantic result types at the boundaries** match the repo's stated invariant
  and need no change.

## Bottom line

The architecture is **well-conceived and right-sized for what this is** — a scientific
triage library with a disciplined public contract. There is exactly one structural debt
worth paying down: the hexagonal migration is unfinished, leaving the ring layers and the
legacy flat packages in mutual-import cycles that a blind boundary test hides. The fix is
not a redesign — it is completing the Strangler-Fig migration cycle-by-cycle (#1), backed
by a boundary test that can actually see first-party leaks (#2), starting with the
`utils/` hub (#3). Everything else should be left as-is.
