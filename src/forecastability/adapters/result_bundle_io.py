"""Filesystem I/O adapter for triage result bundles.

Separates persistence concerns from domain models in
:mod:`forecastability.triage.result_bundle`, following hexagonal architecture.
"""

from __future__ import annotations

from pathlib import Path

from forecastability.triage.models import TriageResult
from forecastability.triage.result_bundle import (
    MetadataValue,
    TriageResultBundle,
    build_triage_result_bundle,
)


def save_result_bundle(
    bundle: TriageResultBundle,
    *,
    path: Path,
    exclude_none: bool = False,
) -> None:
    """Persist a triage bundle to disk.

    Args:
        bundle: Validated bundle to write.
        path: Output JSON path.
        exclude_none: Whether to omit ``None`` fields.
    """
    bundle.to_json_file(path, exclude_none=exclude_none)


def load_result_bundle(path: Path) -> TriageResultBundle:
    """Load a triage bundle from disk.

    Args:
        path: Path to a JSON payload created by :func:`save_result_bundle`.

    Returns:
        Validated bundle instance.
    """
    return TriageResultBundle.from_json_file(path)


def save_triage_result_bundle(
    result: TriageResult,
    *,
    path: Path,
    run_id: str | None = None,
    series_name: str | None = None,
    metadata: dict[str, MetadataValue] | None = None,
    include_narration: bool = True,
    exclude_none: bool = False,
) -> TriageResultBundle:
    """Build and persist a triage bundle in one call.

    Args:
        result: Deterministic triage result.
        path: Output JSON path.
        run_id: Optional execution identifier for audit logs.
        series_name: Optional human-friendly series name.
        metadata: Optional additional metadata attached to the bundle.
        include_narration: Whether to include optional narration.
        exclude_none: Whether to omit ``None`` values in the written JSON.

    Returns:
        The bundle that was written to ``path``.
    """
    bundle = build_triage_result_bundle(
        result,
        run_id=run_id,
        series_name=series_name,
        metadata=metadata,
        include_narration=include_narration,
    )
    bundle.to_json_file(path, exclude_none=exclude_none)
    return bundle
