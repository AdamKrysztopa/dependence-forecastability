<!-- type: reference -->
# Plan Docs

Baseline framing, invariants, and mathematical definitions still live in the main documentation set:
- [README.md](../../README.md)
- [docs/theory/foundations.md](../theory/foundations.md)

## Active planning surface

| File | Purpose | Status |
|---|---|---|
| **[development_plan.md](development_plan.md)** | **Phased development plan for the triage extension epic** | **Active** |
| [acceptance_criteria.md](acceptance_criteria.md) | Done criteria shared by all roadmap items | Active |

## Source epic

The math-grounded feature backlog that feeds the development plan:
- [`not_planed/triage_extension_epic_math_grounded.md`](not_planed/triage_extension_epic_math_grounded.md)

## Planning policy

- The development plan uses **phased dependency-aware ordering** instead of MoSCoW priority buckets.
- Each phase ends with a verification gate before the next begins.
- High-risk estimators ship behind explicit experimental flags.
- All paper functionality from arXiv:2601.10006 is preserved as a non-negotiable baseline.
- Extensions do not weaken or replace the paper-aligned workflow.
