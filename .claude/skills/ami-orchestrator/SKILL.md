---
name: ami-orchestrator
description: Dispatch the orchestrator subagent for any task in the
  dependence-forecastability (ami) project. Use for every code change, bug fix,
  test run, review, planning, or release — even one-liners. Invoked as
  /ami-orchestrator <task>. Pre-loads pytest -n auto (parallel, never piped),
  active release plan, and all stage-gate constraints so the orchestrator gets
  full project context from the first message.
---

# AMI Orchestrator Dispatcher

Routes tasks through the `orchestrator` subagent with all project constraints
pre-loaded. No boilerplate. No forgotten flags.

## Step 1 — Capture the task

The task is everything after `/ami-orchestrator`, or the user's most recent
message if invoked without args.

## Step 2 — Gather context (run in parallel)

Before dispatching, collect:

- `git branch --show-current`
- `git log --oneline -5`

## Step 3 — Dispatch

Call `Agent` with `subagent_type="orchestrator"` using this prompt template
(fill in the angle-bracket placeholders):

---

**Task**: <USER TASK>

**Project**: dependence-forecastability (`src/forecastability/`)
**Branch**: <CURRENT BRANCH>
**Active plan**: `docs/plan/v0_5_0_review_hardening_ultimate_plan.md`
**Recent commits**:
<GIT LOG ONELINE -5>

---

### Test constraints — propagate to every specialist without exception

| Constraint | Why it matters |
|---|---|
| `uv run pytest -q -ra -n auto` | Parallel workers cut wall-clock time; `-ra` surfaces all non-passing reasons |
| **Never** pipe pytest output — no `\| tail`, `\| grep`, `\| tee`, no `2>&1` redirect | Piping truncates output and makes the same tests appear to run multiple times (worker output interleaving fools naive grep) |
| Read pytest stdout and exit-code directly | The only reliable signal of pass/fail |
| Lint gate: `uv run ruff check .` | Must be green before any commit |
| Type gate: `uv run ty check` | Must be green before any commit |

---

**Files touched** (if known): <extract from user message, else "derive from task context">
**Risks pre-screened by caller**: <any risks the user mentioned, else "none">

---

Please:
1. Decompose this task into specialist assignments
2. State routing order and stage gates between each step
3. Flag any concerns or blockers before work begins

---

## Behaviour notes

- If the task is ambiguous, ask **one** clarifying question before dispatching.
- "Run tests" with no other context → dispatch `tester` subagent with
  `uv run pytest -q -ra -n auto` and no piping.
- Update the active-plan path when switching to a different release branch
  (check `docs/plan/` for the current plan file).
- Never dispatch orchestrator for read-only investigation that produces no
  edits (that's just regular Claude conversation).
