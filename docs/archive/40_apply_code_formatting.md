# 40. Apply Code Formatting and Minor Fixes (P3)

> **Priority**: P3 — quick, no dependencies.

## Problem

`ruff format --check .` reports 2 files need reformatting:

```
Would reformat: src/forecastability/cmi.py
Would reformat: src/forecastability/datasets.py
```

This is a one-command fix.

## What to do

- [ ] Run `ruff format`
- [ ] Verify no regressions

## Execution

```bash
# Format the two files
uv run ruff format src/forecastability/cmi.py src/forecastability/datasets.py

# Verify formatting is now clean
uv run ruff format --check .

# Verify lint still passes
uv run ruff check .

# Verify tests still pass
uv run pytest -q
```

## Verification

- [ ] `uv run ruff format --check .` reports "All files already formatted"
- [ ] `uv run ruff check .` reports "All checks passed!"
- [ ] `uv run pytest -q` reports all tests pass
