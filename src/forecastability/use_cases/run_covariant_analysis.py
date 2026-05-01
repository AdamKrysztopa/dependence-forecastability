"""Covariant analysis orchestration facade.

This is the top-level entry point for the v0.3.0 covariant bundle. It
coordinates existing pairwise, directional, and causal-discovery services
without introducing new metric math in the use-case layer.
"""

from __future__ import annotations

from typing import cast

import numpy as np

from forecastability.metrics.scorers import DependenceScorer, default_registry
from forecastability.ports import CausalGraphFullPort, CausalGraphPort
from forecastability.services.exog_partial_curve_service import compute_exog_partial_curve
from forecastability.services.exog_raw_curve_service import compute_exog_raw_curve
from forecastability.services.gcmi_service import compute_gcmi_curve
from forecastability.services.pcmci_ami_service import build_pcmci_ami_hybrid
from forecastability.services.pcmci_plus_service import build_pcmci_plus
from forecastability.services.significance_service import compute_significance_bands_generic
from forecastability.services.transfer_entropy_service import compute_transfer_entropy_curve
from forecastability.use_cases.run_lagged_exogenous_triage import (
    run_lagged_exogenous_triage,
)
from forecastability.utils.types import (
    CausalGraphResult,
    CovariantAnalysisBundle,
    CovariantMethodConditioning,
    CovariantSummaryRow,
    GcmiResult,
    LaggedExogBundle,
    LaggedExogConditioningTag,
    PcmciAmiResult,
    TransferEntropyResult,
)
from forecastability.utils.validation import validate_time_series

ALL_METHODS: tuple[str, ...] = (
    "cross_ami",
    "cross_pami",
    "te",
    "gcmi",
    "pcmci",
    "pcmci_ami",
)
_ALL_METHOD_SET = frozenset(ALL_METHODS)
_TARGET_ONLY_METHODS = frozenset({"cross_pami", "te"})
_METHOD_TO_CONDITIONING_FIELD: dict[str, str] = {
    "cross_ami": "cross_ami",
    "cross_pami": "cross_pami",
    "te": "transfer_entropy",
    "gcmi": "gcmi",
    "pcmci": "pcmci",
    "pcmci_ami": "pcmci_ami",
}
_METHOD_TO_CONDITIONING_TAG: dict[str, LaggedExogConditioningTag] = {
    "cross_ami": "none",
    "cross_pami": "target_only",
    "te": "target_only",
    "gcmi": "none",
    "pcmci": "full_mci",
    "pcmci_ami": "full_mci",
}
_CONDITIONING_DISCLAIMER = (
    "Bundle conditioning scope: CrossMI and GCMI rows are unconditioned pairwise "
    "signals (`none`); pCrossAMI and TE rows are `target_only`; only PCMCI+ and "
    "PCMCI-AMI are `full_mci`. See section 5A in "
    "docs/plan/v0_3_0_covariant_informative_ultimate_plan.md."
)
_FORWARD_LINK = "docs/plan/v0_3_2_lagged_exogenous_triage_ultimate_plan.md"


def _resolve_requested_methods(methods: list[str] | None) -> tuple[str, ...]:
    if methods is None:
        return ALL_METHODS

    requested = tuple(dict.fromkeys(methods))
    unknown = sorted(set(requested) - _ALL_METHOD_SET)
    if unknown:
        raise ValueError(f"Unknown methods: {unknown}. Available: {sorted(_ALL_METHOD_SET)}")
    return requested


def _validate_inputs(
    *,
    target: np.ndarray,
    drivers: dict[str, np.ndarray],
    target_name: str,
    max_lag: int,
    alpha: float,
    n_surrogates: int,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    if n_surrogates < 99:
        raise ValueError(f"n_surrogates must be >= 99, got {n_surrogates}")
    if max_lag < 1:
        raise ValueError(f"max_lag must be >= 1, got {max_lag}")
    if not target_name.strip():
        raise ValueError("target_name must be non-empty")
    if not (0.0 < alpha < 1.0):
        raise ValueError("alpha must be in (0, 1)")

    validated_target = validate_time_series(target, min_length=max_lag + 2)
    if len(drivers) == 0:
        raise ValueError("drivers must contain at least one candidate exogenous series")

    validated_drivers: dict[str, np.ndarray] = {}
    for driver_name in sorted(drivers):
        if not driver_name.strip():
            raise ValueError("driver names must be non-empty")
        driver_series = validate_time_series(drivers[driver_name], min_length=max_lag + 2)
        if driver_series.size != validated_target.size:
            raise ValueError(
                "each driver series must exactly match target length: "
                f"{driver_name}={driver_series.size}, target={validated_target.size}"
            )
        validated_drivers[driver_name] = driver_series
    return validated_target, validated_drivers


def _compute_cross_ami_curves(
    *,
    target: np.ndarray,
    drivers: dict[str, np.ndarray],
    max_lag: int,
    random_state: int,
) -> dict[str, np.ndarray]:
    registry = default_registry()
    mi_scorer = cast(DependenceScorer, registry.get("mi").scorer)
    cross_ami_curves: dict[str, np.ndarray] = {}

    for index, (driver_name, driver_series) in enumerate(drivers.items()):
        seed = random_state + index
        cross_ami_curves[driver_name] = compute_exog_raw_curve(
            target,
            driver_series,
            max_lag,
            mi_scorer,
            random_state=seed,
        )
    return cross_ami_curves


def _compute_cross_pami_curves(
    *,
    target: np.ndarray,
    drivers: dict[str, np.ndarray],
    max_lag: int,
    random_state: int,
) -> dict[str, np.ndarray]:
    registry = default_registry()
    mi_scorer = cast(DependenceScorer, registry.get("mi").scorer)
    cross_pami_curves: dict[str, np.ndarray] = {}

    for index, (driver_name, driver_series) in enumerate(drivers.items()):
        seed = random_state + index
        cross_pami_curves[driver_name] = compute_exog_partial_curve(
            target,
            driver_series,
            max_lag,
            mi_scorer,
            random_state=seed,
        )
    return cross_pami_curves


def _compute_te_curves(
    *,
    target: np.ndarray,
    drivers: dict[str, np.ndarray],
    max_lag: int,
    random_state: int,
) -> dict[str, np.ndarray]:
    curves: dict[str, np.ndarray] = {}
    for index, (driver_name, driver_series) in enumerate(drivers.items()):
        curves[driver_name] = compute_transfer_entropy_curve(
            driver_series,
            target,
            max_lag=max_lag,
            random_state=random_state + index,
        )
    return curves


def _compute_gcmi_curves(
    *,
    target: np.ndarray,
    drivers: dict[str, np.ndarray],
    max_lag: int,
) -> dict[str, np.ndarray]:
    return {
        driver_name: compute_gcmi_curve(driver_series, target, max_lag=max_lag)
        for driver_name, driver_series in drivers.items()
    }


def _build_panel(
    *,
    target: np.ndarray,
    drivers: dict[str, np.ndarray],
    target_name: str,
) -> tuple[np.ndarray, list[str]]:
    var_names = [target_name, *drivers.keys()]
    data = np.column_stack([target, *drivers.values()])
    return data, var_names


def _run_pcmci(
    *,
    data: np.ndarray,
    var_names: list[str],
    max_lag: int,
    alpha: float,
    random_state: int,
) -> CausalGraphResult | None:
    try:
        port: CausalGraphPort = build_pcmci_plus(ci_test="parcorr")
    except ImportError:
        return None

    return port.discover(
        data,
        var_names,
        max_lag=max_lag,
        alpha=alpha,
        random_state=random_state,
    )


def _run_pcmci_ami(
    *,
    data: np.ndarray,
    var_names: list[str],
    max_lag: int,
    ami_threshold: float,
    alpha: float,
    random_state: int,
) -> PcmciAmiResult | None:
    try:
        port = build_pcmci_ami_hybrid(ami_threshold=ami_threshold)
    except ImportError:
        return None

    if not isinstance(port, CausalGraphFullPort):
        raise TypeError("build_pcmci_ami_hybrid() returned an object without discover_full()")

    return port.discover_full(
        data,
        var_names,
        max_lag=max_lag,
        alpha=alpha,
        random_state=random_state,
    )


def _parse_link_cell(cell: str) -> dict[int, str]:
    if not cell:
        return {}

    mapping: dict[int, str] = {}
    for chunk in cell.split(","):
        lag_text, link = chunk.split(":", maxsplit=1)
        mapping[int(lag_text)] = link
    return mapping


def _build_link_lookup(
    *,
    graph: CausalGraphResult,
    var_names: list[str],
) -> dict[tuple[str, str, int], str]:
    if graph.link_matrix is None:
        return {}

    lookup: dict[tuple[str, str, int], str] = {}
    for source_index, source_name in enumerate(var_names):
        for target_index, target_name in enumerate(var_names):
            cell = graph.link_matrix[source_index][target_index]
            for lag, link in _parse_link_cell(cell).items():
                lookup[(source_name, target_name, lag)] = link
    return lookup


def _build_conditioning_metadata(active_methods: set[str]) -> CovariantMethodConditioning:
    return CovariantMethodConditioning(
        cross_ami=(
            _METHOD_TO_CONDITIONING_TAG["cross_ami"] if "cross_ami" in active_methods else None
        ),
        cross_pami=(
            _METHOD_TO_CONDITIONING_TAG["cross_pami"] if "cross_pami" in active_methods else None
        ),
        transfer_entropy=(_METHOD_TO_CONDITIONING_TAG["te"] if "te" in active_methods else None),
        gcmi=_METHOD_TO_CONDITIONING_TAG["gcmi"] if "gcmi" in active_methods else None,
        pcmci=_METHOD_TO_CONDITIONING_TAG["pcmci"] if "pcmci" in active_methods else None,
        pcmci_ami=(
            _METHOD_TO_CONDITIONING_TAG["pcmci_ami"] if "pcmci_ami" in active_methods else None
        ),
    )


def _compute_cross_ami_bands(
    *,
    target: np.ndarray,
    drivers: dict[str, np.ndarray],
    max_lag: int,
    n_surrogates: int,
    random_state: int,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Compute phase-surrogate significance bands for cross-AMI per driver.

    Phase-randomises the target series to break the temporal association with
    each driver, then computes the 2.5/97.5 surrogate percentile bands.

    Args:
        target: Validated target series (will be phase-randomised).
        drivers: Validated driver mapping (kept fixed during surrogates).
        max_lag: Maximum lag horizon.
        n_surrogates: Number of phase-randomised surrogates (>= 99).
        random_state: Base random seed.

    Returns:
        Mapping driver_name → (lower_band, upper_band), each of shape (max_lag,).
    """
    registry = default_registry()
    mi_info = registry.get("mi")
    bands: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for index, (driver_name, driver_series) in enumerate(drivers.items()):
        lower, upper = compute_significance_bands_generic(
            target,
            n_surrogates,
            random_state + index,
            max_lag,
            mi_info,
            "raw",
            exog=driver_series,
            min_pairs=30,
            n_jobs=1,
        )
        bands[driver_name] = (lower, upper)
    return bands


def _significance_tag(value: float | None, upper: float | None) -> str | None:
    """Return 'above_band' / 'below_band' / None."""
    if value is None or upper is None:
        return None
    return "above_band" if value > upper else "below_band"


def _interpretation_tag(
    *,
    cross_ami: float | None,
    cross_pami: float | None,
    transfer_entropy: float | None,
    gcmi: float | None,
    pcmci_link: str | None,
    significance: str | None,
    pcmci_ran: bool = False,
) -> str | None:
    """Assign a multi-method evidence tag to a covariant summary row.

    Priority (first match wins):
    1. ``causal_confirmed``          — PCMCI+ confirms a parent link AND cross_ami above band
    2. ``probably_mediated``         — cross_ami significant but pCrossAMI collapses
                                        (directness_ratio < 0.3)
    3. ``directional_informative``   — cross_ami AND transfer_entropy both above a floor
    4. ``pairwise_informative``      — cross_ami alone is significant
    5. ``noise_or_weak``             — no significant dependence found

    The ``probably_mediated`` tag (priority 2) additionally requires
    ``pcmci_ran=True``; without a causal method in the bundle, a low
    directness ratio is insufficient to claim mediation at the row level.

    Returns None when no primary metric is available to classify.
    """
    has_primary = cross_ami is not None or transfer_entropy is not None or gcmi is not None
    if not has_primary:
        return None

    is_sig = significance == "above_band"
    pcmci_confirmed = pcmci_link is not None

    if pcmci_confirmed and is_sig:
        return "causal_confirmed"

    if is_sig and pcmci_ran and cross_ami is not None and cross_pami is not None and cross_ami > 0:
        directness_ratio = cross_pami / cross_ami
        # directness_ratio > 1.0 is a numerical anomaly (pAMI > AMI); skip mediation check
        if 0.0 <= directness_ratio < 0.3:
            return "probably_mediated"

    if is_sig and transfer_entropy is not None and transfer_entropy > 0.01:
        return "directional_informative"

    if is_sig:
        return "pairwise_informative"

    return "noise_or_weak"


def _assign_ranks(rows: list[CovariantSummaryRow]) -> list[CovariantSummaryRow]:
    """Return new rows (frozen model) with rank populated.

    Rank is global across all (driver, lag) pairs, ordered by primary score
    descending. Primary score priority: cross_ami → gcmi → transfer_entropy.
    Ties broken by driver name then lag.

    Args:
        rows: Rows without rank assigned (rank=None).

    Returns:
        New list of rows with rank field populated (1-indexed, 1 = best).
    """

    def _primary(row: CovariantSummaryRow) -> float:
        if row.cross_ami is not None:
            return row.cross_ami
        if row.gcmi is not None:
            return row.gcmi
        if row.transfer_entropy is not None:
            return row.transfer_entropy
        return 0.0

    sorted_rows = sorted(rows, key=lambda r: (-_primary(r), r.driver, r.lag))
    ranked: list[CovariantSummaryRow] = []
    for rank, row in enumerate(sorted_rows, start=1):
        ranked.append(row.model_copy(update={"rank": rank}))
    return ranked


def _build_bundle_metadata(
    *,
    requested_methods: tuple[str, ...],
    active_methods: set[str],
    skipped_optional_methods: set[str],
    n_surrogates: int,
) -> dict[str, str | int | float]:
    metadata: dict[str, str | int | float] = {
        "requested_methods": ",".join(requested_methods),
        "active_methods": ",".join(sorted(active_methods)),
        "requested_n_surrogates": n_surrogates,
    }
    if skipped_optional_methods:
        metadata["skipped_optional_methods"] = ",".join(sorted(skipped_optional_methods))
    if _TARGET_ONLY_METHODS & active_methods:
        metadata["contains_target_only_methods"] = 1
        metadata["conditioning_scope_disclaimer"] = _CONDITIONING_DISCLAIMER
        metadata["conditioning_scope_forward_link"] = _FORWARD_LINK
    return metadata


def run_covariant_analysis(
    target: np.ndarray,
    drivers: dict[str, np.ndarray],
    *,
    target_name: str = "target",
    max_lag: int = 40,
    methods: list[str] | None = None,
    ami_threshold: float = 0.05,
    alpha: float = 0.01,
    n_surrogates: int = 99,
    random_state: int = 42,
    include_lagged_exog_triage: bool = False,
) -> CovariantAnalysisBundle:
    """Run the covariant analysis bundle and assemble a unified summary table.

    Args:
        target: One-dimensional target series.
        drivers: Driver name to one-dimensional series mapping.
        target_name: Human-readable target name for the bundle.
        max_lag: Maximum lag horizon to evaluate.
        methods: Optional subset of method names to run. ``None`` runs all.
        ami_threshold: Phase-0 MI threshold for PCMCI-AMI.
        alpha: Significance threshold for PCMCI-family CI tests.
        n_surrogates: Reserved bundle-level surrogate contract; must be >= 99.
        random_state: Deterministic random seed.
        include_lagged_exog_triage: When ``True``, attach a Phase 2
            lagged-exogenous triage bundle.

    Returns:
        CovariantAnalysisBundle with pairwise, directional, and causal results.

    Raises:
        ValueError: If inputs, methods, or surrogate settings are invalid.
    """
    requested_methods = _resolve_requested_methods(methods)
    requested_method_set = set(requested_methods)
    validated_target, validated_drivers = _validate_inputs(
        target=target,
        drivers=drivers,
        target_name=target_name,
        max_lag=max_lag,
        alpha=alpha,
        n_surrogates=n_surrogates,
    )
    horizons = list(range(1, max_lag + 1))
    active_methods: set[str] = set()
    skipped_optional_methods: set[str] = set()
    cross_ami_curves: dict[str, np.ndarray] = {}
    cross_pami_curves: dict[str, np.ndarray] = {}
    cross_ami_upper_bands: dict[str, np.ndarray] = {}
    te_curves: dict[str, np.ndarray] = {}
    gcmi_curves: dict[str, np.ndarray] = {}
    te_results: list[TransferEntropyResult] = []
    gcmi_results: list[GcmiResult] = []
    pcmci_graph: CausalGraphResult | None = None
    pcmci_ami_result: PcmciAmiResult | None = None
    lagged_exog: LaggedExogBundle | None = None

    if "cross_ami" in requested_method_set:
        cross_ami_curves = _compute_cross_ami_curves(
            target=validated_target,
            drivers=validated_drivers,
            max_lag=max_lag,
            random_state=random_state,
        )
        active_methods.add("cross_ami")
        bands = _compute_cross_ami_bands(
            target=validated_target,
            drivers=validated_drivers,
            max_lag=max_lag,
            n_surrogates=n_surrogates,
            random_state=random_state,
        )
        cross_ami_upper_bands = {name: upper for name, (lower, upper) in bands.items()}

    if "cross_pami" in requested_method_set:
        cross_pami_curves = _compute_cross_pami_curves(
            target=validated_target,
            drivers=validated_drivers,
            max_lag=max_lag,
            random_state=random_state,
        )
        active_methods.add("cross_pami")

    if "te" in requested_method_set:
        te_curves = _compute_te_curves(
            target=validated_target,
            drivers=validated_drivers,
            max_lag=max_lag,
            random_state=random_state,
        )
        active_methods.add("te")

    if "gcmi" in requested_method_set:
        gcmi_curves = _compute_gcmi_curves(
            target=validated_target,
            drivers=validated_drivers,
            max_lag=max_lag,
        )
        active_methods.add("gcmi")

    panel_data, var_names = _build_panel(
        target=validated_target,
        drivers=validated_drivers,
        target_name=target_name,
    )
    if "pcmci" in requested_method_set:
        pcmci_graph = _run_pcmci(
            data=panel_data,
            var_names=var_names,
            max_lag=max_lag,
            alpha=alpha,
            random_state=random_state,
        )
        if pcmci_graph is None:
            skipped_optional_methods.add("pcmci")
        else:
            active_methods.add("pcmci")

    if "pcmci_ami" in requested_method_set:
        pcmci_ami_result = _run_pcmci_ami(
            data=panel_data,
            var_names=var_names,
            max_lag=max_lag,
            ami_threshold=ami_threshold,
            alpha=alpha,
            random_state=random_state,
        )
        if pcmci_ami_result is None:
            skipped_optional_methods.add("pcmci_ami")
        else:
            active_methods.add("pcmci_ami")

    conditioning = _build_conditioning_metadata(active_methods)
    pcmci_links = (
        _build_link_lookup(graph=pcmci_graph, var_names=var_names)
        if pcmci_graph is not None
        else {}
    )
    pcmci_ami_parents = (
        set(pcmci_ami_result.causal_graph.parents.get(target_name, []))
        if pcmci_ami_result is not None
        else set()
    )

    pcmci_ran = pcmci_graph is not None or pcmci_ami_result is not None

    rows: list[CovariantSummaryRow] = []
    for driver_name in validated_drivers:
        te_curve = te_curves.get(driver_name)
        gcmi_curve = gcmi_curves.get(driver_name)
        cross_ami_curve = cross_ami_curves.get(driver_name)
        cross_pami_curve = cross_pami_curves.get(driver_name)
        for lag in horizons:
            te_value = (
                float(te_curve[lag - 1])
                if "te" in requested_method_set and te_curve is not None
                else None
            )
            gcmi_value = (
                float(gcmi_curve[lag - 1])
                if "gcmi" in requested_method_set and gcmi_curve is not None
                else None
            )
            if te_value is not None:
                te_results.append(
                    TransferEntropyResult(
                        source=driver_name,
                        target=target_name,
                        lag=lag,
                        te_value=te_value,
                    )
                )
            if gcmi_value is not None:
                gcmi_results.append(
                    GcmiResult(
                        source=driver_name,
                        target=target_name,
                        lag=lag,
                        gcmi_value=gcmi_value,
                    )
                )

            row_cross_ami = (
                float(cross_ami_curve[lag - 1])
                if "cross_ami" in requested_method_set and cross_ami_curve is not None
                else None
            )
            row_cross_pami = (
                float(cross_pami_curve[lag - 1])
                if "cross_pami" in requested_method_set and cross_pami_curve is not None
                else None
            )
            upper_band_at_lag = (
                float(cross_ami_upper_bands[driver_name][lag - 1])
                if driver_name in cross_ami_upper_bands
                else None
            )
            row_significance = _significance_tag(row_cross_ami, upper_band_at_lag)
            row_pcmci_link = pcmci_links.get((driver_name, target_name, lag))
            rows.append(
                CovariantSummaryRow(
                    target=target_name,
                    driver=driver_name,
                    lag=lag,
                    cross_ami=row_cross_ami,
                    cross_pami=row_cross_pami,
                    transfer_entropy=te_value,
                    gcmi=gcmi_value,
                    pcmci_link=row_pcmci_link,
                    pcmci_ami_parent=(
                        (driver_name, lag) in pcmci_ami_parents
                        if "pcmci_ami" in active_methods
                        else None
                    ),
                    lagged_exog_conditioning=conditioning,
                    significance=row_significance,
                    interpretation_tag=_interpretation_tag(
                        cross_ami=row_cross_ami,
                        cross_pami=row_cross_pami,
                        transfer_entropy=te_value,
                        gcmi=gcmi_value,
                        pcmci_link=row_pcmci_link,
                        significance=row_significance,
                        pcmci_ran=pcmci_ran,
                    ),
                )
            )

    rows = _assign_ranks(rows)

    if include_lagged_exog_triage:
        lagged_exog = run_lagged_exogenous_triage(
            validated_target,
            validated_drivers,
            target_name=target_name,
            max_lag=max_lag,
            n_surrogates=n_surrogates,
            alpha=alpha,
            random_state=random_state,
        )

    return CovariantAnalysisBundle(
        summary_table=rows,
        te_results=te_results or None,
        gcmi_results=gcmi_results or None,
        pcmci_graph=pcmci_graph,
        pcmci_ami_result=pcmci_ami_result,
        lagged_exog=lagged_exog,
        target_name=target_name,
        driver_names=list(validated_drivers.keys()),
        horizons=horizons,
        metadata=_build_bundle_metadata(
            requested_methods=requested_methods,
            active_methods=active_methods,
            skipped_optional_methods=skipped_optional_methods,
            n_surrogates=n_surrogates,
        ),
    )
