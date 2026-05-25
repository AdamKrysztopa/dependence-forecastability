"""PerfBudgetReport — frozen result for PBE-F* performance budget tests (RVH-F15)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PerfBudgetReport(BaseModel):
    """Result record for one PBE-F* performance budget assertion.

    Used by tests/test_perf_budget_*.py to capture and compare timing.
    """

    model_config = ConfigDict(frozen=True)

    pbe_tag: str = Field(description="PBE-F* tag, e.g. 'PBE-F24'.")
    budget_seconds: float = Field(description="Wall-clock budget from tests/perf_budgets.yml.")
    measured_seconds: float = Field(description="Actual wall-clock time measured in this run.")
    passed: bool = Field(description="True if measured_seconds <= budget_seconds.")
    headroom_factor: float = Field(
        description="budget_seconds / measured_seconds. >= 1.5 means CI-safe."
    )
    description: str = Field(description="Human-readable description of what was measured.")
