<!-- type: explanation -->
# Agentic Triage Notebook: Durable Summary

## Purpose

Document the triage orchestration contract in a durable, test-backed form: deterministic readiness and routing first, optional LLM narration second.

Scope covered:
- run_triage one-entry workflow,
- blocked versus warning versus executable paths,
- deterministic behavior guarantees used by the agent layer.

## Key Figure

```mermaid
flowchart LR
    A["TriageRequest"] --> B["Readiness Gate"]
    B -->|blocked| C["Early return"]
    B -->|warning or clear| D["Method Router"]
    D --> E["AMI/pAMI or CrossAMI/pCrossAMI Compute"]
    E --> F["Interpretation"]
    F --> G["Recommendation"]
    G --> H["Optional agent narration adapter"]
```

Why this figure matters: it separates deterministic scientific outputs from optional narration, which is the core operational contract.

## Key Result

From regression tests:

- [../../tests/test_triage_run.py](../../tests/test_triage_run.py) verifies AR(1) returns high forecastability and white noise returns low forecastability.
- [../../tests/test_triage_regression.py](../../tests/test_triage_regression.py) pins route stability: n = 150 requests follow univariate_no_significance (or exogenous) without surrogate computation.
- [../../tests/test_triage_run.py](../../tests/test_triage_run.py) verifies blocked requests return early with no compute payload.
- [../../tests/test_triage_run.py](../../tests/test_triage_run.py) verifies run_triage never sets narrative, preserving deterministic-first ownership boundaries.

## Takeaways

- Triage outputs are deterministic and regression-tested before any optional narration is applied.
- Readiness gating prevents invalid or leakage-prone requests from entering compute stages.
- Route selection is stable for canonical univariate and exogenous request types.
- Agent narration is an interpretation surface, not a source of numeric truth.

## Notebook For Full Detail

- Full walkthrough: [../../notebooks/03_agentic_triage.ipynb](../../notebooks/03_agentic_triage.ipynb)
