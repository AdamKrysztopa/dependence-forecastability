"""Routing validation orchestration use case (plan v0.3.3 V3_4-F05).

Orchestrates the full routing validation workflow:
1. Generates or loads the synthetic archetype panel (§6.1).
2. Loads and processes the real-series panel (§6.2) if requested.
3. Runs forecastability fingerprinting on every panel series.
4. Evaluates the four-outcome audit predicate (§2.2) for each case.
5. Assembles and returns a frozen :class:`RoutingValidationBundle`.

The use case does not import any plotting, CLI, or agent module.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from forecastability.services.routing_policy_audit_service import (
    audit_routing_case,
    build_routing_threshold_vector,
)
from forecastability.use_cases.routing_validation_panel import (
    RealPanelCaseEntry,
    RealValidationPanelManifest,
    load_real_panel_manifest,
    load_series_from_entry,
)
from forecastability.use_cases.run_forecastability_fingerprint import (
    run_forecastability_fingerprint,
)
from forecastability.utils.synthetic import (
    ExpectedFamilyMetadata,
    generate_routing_validation_archetypes,
)
from forecastability.utils.types import (
    RoutingPolicyAudit,
    RoutingPolicyAuditConfig,
    RoutingValidationBundle,
    RoutingValidationCase,
)

_logger = logging.getLogger(__name__)

# Maximum lag used for fingerprint computation.
# Derived conservatively from n_per_archetype to ensure adequate data coverage.
_MIN_MAX_LAG = 4
_MAX_MAX_LAG = 24
_N_SURROGATES = 99
_DEFAULT_ROUTING_POLICY_AUDIT_CONFIG = RoutingPolicyAuditConfig()


def _derive_max_lag(n: int) -> int:
    """Derive a safe max_lag from the series length."""
    return min(_MAX_MAX_LAG, max(_MIN_MAX_LAG, n // 20))


def _derive_real_case_max_lag(*, default_max_lag: int, series_length: int) -> int:
    """Clamp real-panel lag depth to the local series length contract."""
    return min(default_max_lag, _derive_max_lag(series_length))


def _is_too_short_error(error: ValueError) -> bool:
    """Return whether a fingerprint failure is the validated too-short guard."""
    return str(error) == "Time series is too short."


def _build_audit(cases: list[RoutingValidationCase]) -> RoutingPolicyAudit:
    """Aggregate per-case outcome counts into a RoutingPolicyAudit.

    Args:
        cases: All evaluated validation cases.

    Returns:
        Frozen ``RoutingPolicyAudit`` with cross-validated counts.
    """
    passed = sum(1 for c in cases if c.outcome == "pass")
    failed = sum(1 for c in cases if c.outcome == "fail")
    downgraded = sum(1 for c in cases if c.outcome == "downgrade")
    abstained = sum(1 for c in cases if c.outcome == "abstain")
    return RoutingPolicyAudit(
        total_cases=len(cases),
        passed_cases=passed,
        failed_cases=failed,
        downgraded_cases=downgraded,
        abstained_cases=abstained,
    )


def _run_synthetic_cases(
    *,
    archetypes: dict[str, tuple[np.ndarray, ExpectedFamilyMetadata]],
    max_lag: int,
    random_state: int,
    config: RoutingPolicyAuditConfig,
) -> list[RoutingValidationCase]:
    """Fingerprint and audit each synthetic archetype.

    Args:
        archetypes: Mapping from archetype name to ``(series, metadata)`` pair.
        max_lag: Maximum lag horizon passed to the fingerprint use case.
        random_state: Reproducibility seed for surrogate generation.
        config: Audit configuration scalars.

    Returns:
        List of frozen ``RoutingValidationCase`` instances in stable iteration order.
    """
    cases: list[RoutingValidationCase] = []
    for archetype_name, (series, meta) in archetypes.items():
        series_arr: np.ndarray = series
        _logger.debug("Fingerprinting synthetic archetype '%s' …", archetype_name)
        bundle = run_forecastability_fingerprint(
            series_arr,
            target_name=archetype_name,
            max_lag=max_lag,
            n_surrogates=_N_SURROGATES,
            random_state=random_state,
        )
        threshold_vector = build_routing_threshold_vector(bundle.fingerprint)
        case = audit_routing_case(
            case_name=archetype_name,
            source_kind="synthetic",
            expected_primary_families=meta.expected_primary_families,
            fingerprint=bundle.fingerprint,
            recommendation=bundle.recommendation,
            threshold_vector=threshold_vector,
            config=config,
            notes=list(meta.notes),
            metadata={"archetype": archetype_name},
        )
        cases.append(case)
    return cases


def _run_real_cases(
    *,
    entries: list[RealPanelCaseEntry],
    repo_root: Path,
    max_lag: int,
    random_state: int,
    config: RoutingPolicyAuditConfig,
) -> list[RoutingValidationCase]:
    """Fingerprint and audit each real-series panel entry.

    Entries whose CSV is absent (source='download' and not yet fetched) are
    skipped with a warning rather than raising. Loaded real-series entries that
    are shorter than the fingerprint minimum are also skipped with a warning so
    the default report path can complete on the bundled clean-checkout panel.

    Args:
        entries: Parsed real panel entries.
        repo_root: Absolute path to the repository root; used to resolve CSV paths.
        max_lag: Maximum lag horizon.
        random_state: Reproducibility seed.
        config: Audit configuration scalars.

    Returns:
        List of frozen ``RoutingValidationCase`` instances for resolved entries.
    """
    cases: list[RoutingValidationCase] = []
    for entry in entries:
        try:
            series = load_series_from_entry(entry, repo_root=repo_root)
        except FileNotFoundError:
            if entry.source != "download":
                raise
            _logger.warning(
                "Real panel CSV absent for case '%s' (source=%s). Skipping. Run '%s' first.",
                entry.name,
                entry.source,
                entry.download_command or "<no download command>",
            )
            continue

        series_max_lag = _derive_real_case_max_lag(
            default_max_lag=max_lag,
            series_length=series.size,
        )
        _logger.debug(
            "Fingerprinting real series '%s' with max_lag=%d …",
            entry.name,
            series_max_lag,
        )
        try:
            bundle = run_forecastability_fingerprint(
                series,
                target_name=entry.name,
                max_lag=series_max_lag,
                n_surrogates=_N_SURROGATES,
                random_state=random_state,
            )
        except ValueError as error:
            if not _is_too_short_error(error):
                raise
            _logger.warning(
                "Real panel series '%s' is too short for fingerprinting "
                "(length=%d, max_lag=%d). Skipping.",
                entry.name,
                series.size,
                series_max_lag,
            )
            continue
        threshold_vector = build_routing_threshold_vector(bundle.fingerprint)
        case = audit_routing_case(
            case_name=entry.name,
            source_kind="real",
            expected_primary_families=list(entry.expected_primary_families),
            fingerprint=bundle.fingerprint,
            recommendation=bundle.recommendation,
            threshold_vector=threshold_vector,
            config=config,
            notes=[f"license={entry.license}"],
            metadata={
                "source": entry.source,
                "license": entry.license,
            },
        )
        cases.append(case)
    return cases


def _resolve_repo_root(real_panel_path: Path) -> Path:
    """Resolve the repository root from a real panel manifest path.

    If the manifest lives at ``<root>/configs/<filename>.yaml``, the repo root
    is two levels above the manifest file. Falls back to the resolved parent
    directory when the path depth is insufficient.

    Args:
        real_panel_path: Path to the YAML manifest (resolved to absolute before use).

    Returns:
        Absolute path to the repository root.
    """
    abs_path = real_panel_path.resolve()
    # Expect: <repo_root>/configs/routing_validation_real_panel.yaml
    if abs_path.parent.name == "configs":
        return abs_path.parent.parent
    # Fallback: one level above the manifest's parent
    return abs_path.parent


def run_routing_validation(
    *,
    synthetic_panel: list[ExpectedFamilyMetadata] | None = None,
    real_panel_path: Path | None = None,
    n_per_archetype: int = 600,
    random_state: int = 42,
    weak_seasonal_amplitude: float | None = None,
    config: RoutingPolicyAuditConfig = _DEFAULT_ROUTING_POLICY_AUDIT_CONFIG,
) -> RoutingValidationBundle:
    """Run routing validation orchestration over the configured panels.

    Defaults to the §6.1 synthetic panel (ten deterministic archetypes) plus
    any real-series panel declared via ``real_panel_path``.  Returns a frozen
    :class:`RoutingValidationBundle` suitable for fixture freezing and report
    rendering.

    The ``config`` argument is validated on construction (Pydantic enforces the
    cross-field ordering invariants from §2.6); no re-validation is performed
    here.

    Args:
        synthetic_panel: Optional list of :class:`ExpectedFamilyMetadata` objects
            that restricts the synthetic panel to the named archetypes.  When
            ``None`` (the default), all ten §6.1 archetypes are run.  Metadata
            for unrecognised archetype names is silently skipped because the
            corresponding generator cannot be located.
        real_panel_path: Optional path to the real-series manifest YAML
            (``configs/routing_validation_real_panel.yaml``).  When ``None``,
            the real panel is not evaluated.  Missing bundled CSVs raise
            :class:`FileNotFoundError`; missing download-on-demand CSVs emit a
            warning and are skipped.
        n_per_archetype: Number of time-series observations generated for each
            synthetic archetype (default 600).  Also controls the ``max_lag``
            used for fingerprint computation via ``max_lag = n // 20``.  Use
            ``n_per_archetype=200`` for smoke/CI runs.
        random_state: Global reproducibility seed (int, not Generator).  Passed
            to ``run_forecastability_fingerprint`` for surrogate generation and
            to the synthetic archetype generators.
        weak_seasonal_amplitude: Optional override for the
            ``weak_seasonal_near_threshold`` synthetic archetype amplitude.
            When ``None``, the generator uses its own default.
        config: Frozen :class:`RoutingPolicyAuditConfig` holding the versioned
            scalars from plan §2.6.  Defaults to the conservative v0.3.3 values.

    Returns:
        Frozen :class:`RoutingValidationBundle` with all evaluated cases, the
        aggregate audit, and the config used.

    Raises:
        ValueError: If both ``synthetic_panel`` resolves to zero archetypes and
            the real panel is not provided or produces zero cases.
    """
    max_lag = _derive_max_lag(n_per_archetype)

    # -----------------------------------------------------------------------
    # 1. Build synthetic archetype panel
    # -----------------------------------------------------------------------
    all_archetypes = generate_routing_validation_archetypes(
        n=n_per_archetype,
        seed=random_state,
        weak_seasonal_amplitude=weak_seasonal_amplitude,
    )

    if synthetic_panel is not None:
        requested_names = {meta.archetype_name for meta in synthetic_panel}
        active_archetypes = {
            name: pair for name, pair in all_archetypes.items() if name in requested_names
        }
        skipped = requested_names - set(active_archetypes)
        if skipped:
            _logger.warning(
                "Unrecognised archetype names in synthetic_panel (no generators found): %s",
                sorted(skipped),
            )
    else:
        active_archetypes = all_archetypes

    # -----------------------------------------------------------------------
    # 2. Load real panel entries
    # -----------------------------------------------------------------------
    real_entries: list[RealPanelCaseEntry] = []
    real_manifest: RealValidationPanelManifest | None = None
    if real_panel_path is not None:
        real_manifest = load_real_panel_manifest(real_panel_path)
        real_entries = list(real_manifest.cases)

    # -----------------------------------------------------------------------
    # 3. Validate panel has at least one potential case
    # -----------------------------------------------------------------------
    if not active_archetypes and not real_entries:
        raise ValueError(
            "run_routing_validation: both panels resolve to zero cases. "
            "Provide synthetic_panel with at least one recognised archetype name "
            "or a real_panel_path with at least one accessible series."
        )

    # -----------------------------------------------------------------------
    # 4. Run fingerprint + audit for each panel
    # -----------------------------------------------------------------------
    cases: list[RoutingValidationCase] = []

    if active_archetypes:
        synthetic_cases = _run_synthetic_cases(
            archetypes=active_archetypes,
            max_lag=max_lag,
            random_state=random_state,
            config=config,
        )
        cases.extend(synthetic_cases)
        _logger.info("Synthetic panel: %d archetype(s) evaluated.", len(synthetic_cases))

    if real_entries:
        repo_root = _resolve_repo_root(real_panel_path)  # type: ignore[arg-type]
        real_cases = _run_real_cases(
            entries=real_entries,
            repo_root=repo_root,
            max_lag=max_lag,
            random_state=random_state,
            config=config,
        )
        cases.extend(real_cases)
        _logger.info("Real panel: %d case(s) evaluated.", len(real_cases))

    if not cases:
        raise ValueError(
            "run_routing_validation: no cases were evaluated successfully. "
            "All synthetic archetypes may have been unrecognised and all real "
            "series may be absent. Check logs for details."
        )

    # -----------------------------------------------------------------------
    # 5. Aggregate audit and return bundle
    # -----------------------------------------------------------------------
    audit = _build_audit(cases)
    metadata: dict[str, str | int | float] = {
        "n_per_archetype": n_per_archetype,
        "random_state": random_state,
        "max_lag": max_lag,
        "n_surrogates": _N_SURROGATES,
    }
    if real_manifest is not None:
        metadata["panel_version"] = real_manifest.panel_version

    return RoutingValidationBundle(
        cases=cases,
        audit=audit,
        config=config,
        metadata=metadata,
    )


__all__ = ["run_routing_validation"]
