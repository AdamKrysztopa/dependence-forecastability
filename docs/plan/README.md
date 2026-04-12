<!-- type: reference -->
# Plan Docs

`docs/plan/` uses explicit MoSCoW prioritization for paper-baseline preservation plus project extensions.

Baseline framing, invariants, and mathematical definitions still live in the main documentation set:
- [README.md](../../README.md)
- [docs/theory/foundations.md](../theory/foundations.md)

## Active planning surface

| File | Purpose | Status |
|---|---|---|
| [dependence_forecastability_progress.md](dependence_forecastability_progress.md) | Branch-level tracker for dependence-forecastability backlog delivery status and commit mapping | Active |
| [acceptance_criteria.md](acceptance_criteria.md) | Done criteria shared by all roadmap items | Active |
| [must_have.md](must_have.md) | Non-negotiable baseline parity and highest-priority extensions | ✅ Complete |
| [should_have.md](should_have.md) | Important improvements with clear value but not blocking parity | ✅ Complete |
| [could_have.md](could_have.md) | Optional extensions worth doing after higher-priority work | Open |
| [wont_have.md](wont_have.md) | Explicit exclusions for the current phase | Active |

## Planning policy

- `Must Have` includes the requirement to preserve all paper functionality from arXiv:2601.10006.
- Lower priority files cover only extensions or packaging/reporting improvements beyond the paper baseline.
- Historical completed items do not stay in the plan unless they define an ongoing non-negotiable requirement.
- `dependence_forecastability_detailed_backlog.md` remains the source backlog and is intentionally retained until P1-P3 implementation is complete.
