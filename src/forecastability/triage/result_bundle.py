"""Persisted triage result bundles with provenance hashing (backlog #17)."""

from __future__ import annotations

import hashlib
import json
import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Literal, Self, TypeAlias

import numpy as np
import pydantic
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from forecastability.triage.models import AnalysisGoal, TriageResult

MetadataValue: TypeAlias = str | int | float | bool


class TriageBundleWarning(BaseModel):
    """Warning entry persisted in a triage result bundle."""

    model_config = ConfigDict(frozen=True)

    code: str
    message: str


class TriageInputMetadata(BaseModel):
    """Input metadata captured for bundle auditability.

    Attributes:
        run_id: Optional caller-provided execution identifier.
        series_name: Optional human-friendly target series name.
        goal: Analysis goal used for triage.
        series_length: Number of target observations.
        exog_length: Number of exogenous observations when provided.
        metadata: Optional additional key/value metadata.
    """

    model_config = ConfigDict(frozen=True)

    run_id: str | None = None
    series_name: str | None = None
    goal: AnalysisGoal
    series_length: int
    exog_length: int | None = None
    metadata: dict[str, MetadataValue] = Field(default_factory=dict)


class TriageConfigSnapshot(BaseModel):
    """Configuration snapshot captured from the triage request and route plan."""

    model_config = ConfigDict(frozen=True)

    max_lag: int
    n_surrogates: int
    random_state: int
    route: str | None = None
    compute_surrogates: bool | None = None
    assumptions: list[str] = Field(default_factory=list)


class TriageVersions(BaseModel):
    """Version metadata captured for reproducibility across environments."""

    model_config = ConfigDict(frozen=True)

    forecastability: str
    python: str
    numpy: str
    pydantic: str
    scikit_learn: str


class TriageNumericOutputs(BaseModel):
    """Numeric outputs persisted from triage execution."""

    model_config = ConfigDict(frozen=True)

    raw_curve: list[float] = Field(default_factory=list)
    partial_curve: list[float] = Field(default_factory=list)
    sig_raw_lags: list[int] = Field(default_factory=list)
    sig_partial_lags: list[int] = Field(default_factory=list)
    raw_auc: float | None = None
    partial_auc: float | None = None
    raw_peak_lag: int | None = None
    raw_peak_value: float | None = None
    partial_peak_lag: int | None = None
    partial_peak_value: float | None = None
    directness_ratio: float | None = None


class TriageBundleProvenance(BaseModel):
    """Provenance metadata with content and input checksums."""

    model_config = ConfigDict(frozen=True)

    hash_algorithm: Literal["sha256"] = "sha256"
    input_series_sha256: str
    exog_series_sha256: str | None = None
    content_sha256: str


class TriageResultBundle(BaseModel):
    """Persistable, replay-safe triage result bundle.

    The bundle is additive relative to :class:`~forecastability.triage.models.TriageResult`
    and preserves backward compatibility for existing triage APIs.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    input_metadata: TriageInputMetadata
    config_snapshot: TriageConfigSnapshot
    versions: TriageVersions
    numeric_outputs: TriageNumericOutputs
    recommendation: str | None = None
    narration: str | None = None
    warnings: list[TriageBundleWarning] = Field(default_factory=list)
    provenance: TriageBundleProvenance

    @classmethod
    def from_json_file(cls, path: Path) -> Self:
        """Load and validate a bundle from ``path``.

        Args:
            path: Path to a JSON payload created by :meth:`to_json_file`.

        Returns:
            Validated bundle instance.

        Raises:
            ValueError: If the file cannot be read or payload validation fails.
        """
        try:
            payload = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError(f"Failed reading {path}: {exc}") from exc

        try:
            return cls.model_validate_json(payload)
        except ValidationError as exc:
            raise ValueError(f"Invalid {cls.__name__} JSON in {path}: {exc}") from exc

    def to_json_file(self, path: Path, *, exclude_none: bool = False) -> None:
        """Write the bundle as pretty JSON.

        Args:
            path: Output path for the JSON payload.
            exclude_none: Whether to omit ``None`` fields.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            self.model_dump_json(indent=2, exclude_none=exclude_none),
            encoding="utf-8",
        )

    def compute_content_hash(self) -> str:
        """Compute the stable content hash for this bundle.

        The hash is calculated over the full JSON payload with
        ``provenance.content_sha256`` blanked out.

        Returns:
            Lowercase SHA-256 hex digest.
        """
        contentless_provenance = self.provenance.model_copy(update={"content_sha256": ""})
        normalized_bundle = self.model_copy(update={"provenance": contentless_provenance})
        payload: object = normalized_bundle.model_dump(mode="json")
        return _sha256_for_payload(payload)

    def with_content_hash(self) -> Self:
        """Return a copy with ``provenance.content_sha256`` recalculated."""
        content_hash = self.compute_content_hash()
        updated_provenance = self.provenance.model_copy(update={"content_sha256": content_hash})
        return self.model_copy(update={"provenance": updated_provenance})

    def verify_content_hash(self) -> bool:
        """Verify that the persisted content hash matches the bundle payload."""
        return self.provenance.content_sha256 == self.compute_content_hash()


def build_triage_result_bundle(
    result: TriageResult,
    *,
    run_id: str | None = None,
    series_name: str | None = None,
    metadata: dict[str, MetadataValue] | None = None,
    include_narration: bool = True,
) -> TriageResultBundle:
    """Build a persisted bundle from a ``TriageResult``.

    Args:
        result: Deterministic triage result.
        run_id: Optional execution identifier for audit logs.
        series_name: Optional human-friendly series name.
        metadata: Optional extra metadata captured under ``input_metadata``.
        include_narration: Whether to include ``result.narrative`` in the bundle.

    Returns:
        A validated bundle with populated provenance checksums and content hash.
    """
    request = result.request
    method_plan = result.method_plan

    input_metadata = TriageInputMetadata(
        run_id=run_id,
        series_name=series_name,
        goal=request.goal,
        series_length=int(request.series.size),
        exog_length=int(request.exog.size) if request.exog is not None else None,
        metadata={} if metadata is None else dict(metadata),
    )
    config_snapshot = TriageConfigSnapshot(
        max_lag=request.max_lag,
        n_surrogates=request.n_surrogates,
        random_state=request.random_state,
        route=method_plan.route if method_plan is not None else None,
        compute_surrogates=method_plan.compute_surrogates if method_plan is not None else None,
        assumptions=[] if method_plan is None else list(method_plan.assumptions),
    )
    versions = _capture_versions()
    numeric_outputs = _extract_numeric_outputs(result)

    provenance = TriageBundleProvenance(
        input_series_sha256=_array_sha256(request.series),
        exog_series_sha256=_array_sha256(request.exog) if request.exog is not None else None,
        content_sha256="",
    )
    warnings = [
        TriageBundleWarning(code=warning.code, message=warning.message)
        for warning in result.readiness.warnings
    ]

    bundle = TriageResultBundle(
        input_metadata=input_metadata,
        config_snapshot=config_snapshot,
        versions=versions,
        numeric_outputs=numeric_outputs,
        recommendation=result.recommendation,
        narration=result.narrative if include_narration else None,
        warnings=warnings,
        provenance=provenance,
    )
    return bundle.with_content_hash()


def _capture_versions() -> TriageVersions:
    return TriageVersions(
        forecastability=_safe_package_version("forecastability"),
        python=(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"),
        numpy=np.__version__,
        pydantic=pydantic.__version__,
        scikit_learn=_safe_package_version("scikit-learn"),
    )


def _safe_package_version(distribution_name: str) -> str:
    try:
        return package_version(distribution_name)
    except PackageNotFoundError:
        return "unknown"


def _extract_numeric_outputs(result: TriageResult) -> TriageNumericOutputs:
    analyze_result = result.analyze_result
    if analyze_result is None:
        return TriageNumericOutputs(
            directness_ratio=(
                float(result.interpretation.diagnostics.directness_ratio)
                if result.interpretation is not None
                else None
            )
        )

    raw_curve = np.asarray(analyze_result.raw, dtype=float)
    partial_curve = np.asarray(analyze_result.partial, dtype=float)
    raw_peak_lag, raw_peak_value = _peak(raw_curve)
    partial_peak_lag, partial_peak_value = _peak(partial_curve)

    return TriageNumericOutputs(
        raw_curve=[float(value) for value in raw_curve.tolist()],
        partial_curve=[float(value) for value in partial_curve.tolist()],
        sig_raw_lags=[int(value) for value in analyze_result.sig_raw_lags.tolist()],
        sig_partial_lags=[int(value) for value in analyze_result.sig_partial_lags.tolist()],
        raw_auc=_auc(raw_curve),
        partial_auc=_auc(partial_curve),
        raw_peak_lag=raw_peak_lag,
        raw_peak_value=raw_peak_value,
        partial_peak_lag=partial_peak_lag,
        partial_peak_value=partial_peak_value,
        directness_ratio=(
            float(result.interpretation.diagnostics.directness_ratio)
            if result.interpretation is not None
            else None
        ),
    )


def _auc(curve: np.ndarray) -> float | None:
    if curve.size == 0:
        return None
    return float(np.trapezoid(curve, dx=1.0))


def _peak(curve: np.ndarray) -> tuple[int | None, float | None]:
    if curve.size == 0:
        return None, None
    idx = int(np.argmax(curve))
    return idx + 1, float(curve[idx])


def _array_sha256(values: np.ndarray) -> str:
    normalized = np.ascontiguousarray(values, dtype=np.float64)
    digest = hashlib.sha256()
    digest.update(str(normalized.shape).encode("ascii"))
    digest.update(normalized.tobytes(order="C"))
    return digest.hexdigest()


def _sha256_for_payload(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
