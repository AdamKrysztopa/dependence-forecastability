"""Pydantic models for script-level JSON payload I/O."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, ValidationError

from forecastability.reporting.interpretation import interpret_canonical_result
from forecastability.utils.aggregation import summarize_canonical_result
from forecastability.utils.types import (
    CanonicalExampleResult,
    CanonicalSummary,
    InterpretationResult,
)


class _JsonFileModel(BaseModel):
    """Mixin for reading/writing model payloads from/to JSON files."""

    @classmethod
    def from_json_file(cls, path: Path) -> Self:
        """Load and validate one JSON payload from *path*."""
        try:
            payload = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError(f"Failed reading {path}: {exc}") from exc

        try:
            return cls.model_validate_json(payload)
        except ValidationError as exc:
            raise ValueError(f"Invalid {cls.__name__} JSON in {path}: {exc}") from exc

    def to_json_file(self, path: Path, *, exclude_none: bool = False) -> None:
        """Write payload as pretty JSON to *path*."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            self.model_dump_json(indent=2, exclude_none=exclude_none),
            encoding="utf-8",
        )


class CanonicalSummaryPayload(_JsonFileModel):
    """Subset of summary metrics consumed by report scripts."""

    model_config = ConfigDict(extra="ignore")

    n_sig_ami: int
    n_sig_pami: int
    ami_significance_status: Literal["computed", "not computed"] = "computed"
    pami_significance_status: Literal["computed", "not computed"] = "computed"
    directness_ratio: float
    auc_ami: float
    auc_pami: float
    peak_lag_ami: int
    peak_lag_pami: int


class CanonicalInterpretationPayload(_JsonFileModel):
    """Canonical interpretation fields consumed by reporting flows."""

    model_config = ConfigDict(extra="ignore")

    forecastability_class: str
    directness_class: str
    modeling_regime: str
    primary_lags: list[int]
    narrative: str | None = None


class CanonicalPayload(_JsonFileModel):
    """Canonical per-series payload."""

    model_config = ConfigDict(extra="ignore")

    series_name: str
    summary: CanonicalSummaryPayload
    interpretation: CanonicalInterpretationPayload

    @classmethod
    def from_summary_and_interpretation(
        cls,
        *,
        series_name: str,
        summary: CanonicalSummary,
        interpretation: InterpretationResult,
        include_narrative: bool,
    ) -> Self:
        """Build payload from canonical summary + interpretation objects."""
        return cls(
            series_name=series_name,
            summary=CanonicalSummaryPayload.model_validate(summary.model_dump()),
            interpretation=CanonicalInterpretationPayload(
                forecastability_class=interpretation.forecastability_class,
                directness_class=interpretation.directness_class,
                modeling_regime=interpretation.modeling_regime,
                primary_lags=interpretation.primary_lags,
                narrative=interpretation.narrative if include_narrative else None,
            ),
        )

    @classmethod
    def from_result(
        cls,
        result: CanonicalExampleResult,
        *,
        include_narrative: bool = True,
    ) -> Self:
        """Build payload from canonical result object."""
        summary = summarize_canonical_result(result)
        interpretation = interpret_canonical_result(result)
        return cls.from_summary_and_interpretation(
            series_name=result.series_name,
            summary=summary,
            interpretation=interpretation,
            include_narrative=include_narrative,
        )


class CanonicalSummaryBundle(_JsonFileModel):
    """Bundle written to ``canonical_examples_summary.json``."""

    model_config = ConfigDict(extra="forbid")

    examples: list[CanonicalPayload]


class ExogCaseRecord(_JsonFileModel):
    """JSON payload emitted by ``scripts/run_exog_analysis.py``."""

    model_config = ConfigDict(extra="forbid")

    case_name: str
    description: str
    method: str
    max_lag: int
    recommendation: str
    n_sig_raw_lags: int
    n_sig_partial_lags: int
    sig_raw_lags: list[int]
    sig_partial_lags: list[int]
    mean_raw_20: float
    mode: str
    target_name: str
    exog_name: str
    n_target: int
    n_exog: int
    raw_curve: list[float]
    partial_curve: list[float]
    auc_raw: float
    auc_partial: float
    peak_raw_lag: int
    peak_raw_value: float
    peak_partial_lag: int
    peak_partial_value: float
    mean_partial_20: float
    directness_ratio: float
    recommended_lags: list[int]
    compute_surrogates: bool

    @classmethod
    def from_fields(cls, **kwargs: Any) -> Self:
        """Factory for script assembly code."""
        return cls.model_validate(kwargs)
