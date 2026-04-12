<!-- type: reference -->
# Must Have

These items are non-negotiable for the current project direction.

## 1. pAMI robustness study ✅

**Status: Complete.**

Goal:
- Quantify how stable pAMI conclusions are under estimator/backend and sample-size stress.

Implementation:
- `src/forecastability/robustness.py` — backend comparison and sample-size stress functions
- `scripts/run_robustness_study.py` — runner script
- `configs/robustness_study.yaml` — configuration
- `tests/test_robustness.py` — test coverage

Acceptance criteria (all met):
- Compares at least two pAMI estimation settings or backends on the same benchmark subset.
- Reports when lag rankings and `directness_ratio` are stable versus unstable.
- Treats `directness_ratio > 1.0` as a warning condition, not a scientific conclusion.
- Documents any data-regime exclusions needed for valid comparison.
