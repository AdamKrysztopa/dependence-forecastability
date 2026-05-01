"""Lagged-exogenous triage orchestration use case.

This use case assembles lag-domain diagnostics and sparse predictive lag
selection into a typed :class:`LaggedExogBundle` output.
"""

from __future__ import annotations

from typing import cast

import numpy as np

from forecastability.metrics.scorers import DependenceScorer, default_registry
from forecastability.services.cross_correlation_profile_service import (
    compute_cross_correlation_profile,
)
from forecastability.services.exog_raw_curve_service import compute_exog_raw_curve
from forecastability.services.significance_service import compute_significance_bands_generic
from forecastability.services.sparse_lag_selection_service import (
    SparseLagSelectionConfig,
    select_sparse_lags,
)
from forecastability.utils.types import (
    LaggedExogBundle,
    LaggedExogProfileRow,
    LaggedExogSelectionRow,
    LagRoleLabel,
    TensorRoleLabel,
)
from forecastability.utils.validation import validate_time_series

_DEFAULT_SPARSE_SELECTOR_CONFIG = SparseLagSelectionConfig()
_KNOWN_FUTURE_CAUTION = (
    "Known-future lag=0 selection is a user contractual claim that the driver is "
    "available at prediction time."
)


def _validate_inputs(
    *,
    target: np.ndarray,
    drivers: dict[str, np.ndarray],
    target_name: str,
    max_lag: int,
    n_surrogates: int,
    alpha: float,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Validate use-case inputs and return aligned series.

    Args:
        target: Target time series.
        drivers: Driver name to time-series mapping.
        target_name: Human-readable target name.
        max_lag: Maximum lag horizon.
        n_surrogates: Number of surrogates for significance computation.
        alpha: Significance level.

    Returns:
        Tuple of validated target and sorted driver mapping.

    Raises:
        ValueError: If any contract condition is violated.
    """
    if n_surrogates < 99:
        raise ValueError(f"n_surrogates must be >= 99, got {n_surrogates}")
    if max_lag < 1:
        raise ValueError(f"max_lag must be >= 1, got {max_lag}")
    if not target_name.strip():
        raise ValueError("target_name must be non-empty")
    if not (0.0 < alpha < 1.0):
        raise ValueError("alpha must be in (0, 1)")
    if len(drivers) == 0:
        raise ValueError("drivers must contain at least one driver series")

    validated_target = validate_time_series(target, min_length=max_lag + 2)

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


def _resolve_known_future_driver_names(
    *,
    known_future_drivers: dict[str, bool] | None,
    driver_names: set[str],
) -> list[str]:
    """Resolve and validate known-future opt-in driver names.

    Args:
        known_future_drivers: Optional opt-in mapping from driver name to bool.
        driver_names: Available validated driver names.

    Returns:
        Sorted list of opted-in driver names.

    Raises:
        ValueError: If unknown driver names or non-bool values are provided.
    """
    if known_future_drivers is None:
        return []

    unknown = sorted(set(known_future_drivers) - driver_names)
    if unknown:
        raise ValueError(f"known_future_drivers includes unknown drivers: {unknown}")

    opted_in: list[str] = []
    for driver_name, is_known_future in known_future_drivers.items():
        if not isinstance(is_known_future, bool):
            raise ValueError(
                "known_future_drivers values must be bool entries, "
                f"got {driver_name}={is_known_future!r}"
            )
        if is_known_future:
            opted_in.append(driver_name)

    return sorted(opted_in)


def _lag_domain(*, include_zero_lag_diagnostic: bool, max_lag: int) -> tuple[int, int]:
    """Return the inclusive lag-domain bounds for profile rows."""
    return (0, max_lag) if include_zero_lag_diagnostic else (1, max_lag)


def _lag_role(*, lag: int) -> LagRoleLabel:
    """Return role label for a lag index."""
    return "instant" if lag == 0 else "predictive"


def _profile_tensor_role(*, lag: int, is_known_future: bool) -> TensorRoleLabel:
    """Return tensor role for a profile row."""
    if lag >= 1:
        return "predictive"
    if is_known_future:
        return "known_future"
    return "diagnostic"


def _significance_tag(*, value: float | None, upper: float | None) -> str | None:
    """Return ``above_band`` or ``below_band`` when a band is available."""
    if value is None or upper is None:
        return None
    return "above_band" if value > upper else "below_band"


def _known_future_selection_row(
    *,
    target_name: str,
    driver_name: str,
) -> LaggedExogSelectionRow:
    """Build the explicit lag-0 known-future selection row."""
    return LaggedExogSelectionRow(
        target=target_name,
        driver=driver_name,
        lag=0,
        selected_for_tensor=True,
        selection_order=None,
        selector_name="xami_sparse",
        score=None,
        tensor_role="known_future",
        metadata={
            "selection_origin": "known_future_opt_in",
            "caution": "user_asserted_prediction_time_availability",
        },
    )


def run_lagged_exogenous_triage(
    target: np.ndarray,
    drivers: dict[str, np.ndarray],
    *,
    target_name: str,
    max_lag: int,
    n_surrogates: int = 199,
    alpha: float = 0.05,
    random_state: int = 42,
    selector_config: SparseLagSelectionConfig = _DEFAULT_SPARSE_SELECTOR_CONFIG,
    known_future_drivers: dict[str, bool] | None = None,
    include_zero_lag_diagnostic: bool = True,
    include_cross_correlation: bool = True,
    include_cross_ami: bool = True,
    n_jobs: int = 1,
) -> LaggedExogBundle:
    """Run fixed-lag exogenous triage and return a typed lagged-exog bundle.

    Args:
        target: One-dimensional target series.
        drivers: Driver name to one-dimensional series mapping.
        target_name: Human-readable target name.
        max_lag: Maximum lag horizon for profile/selection computation.
        n_surrogates: Number of surrogates used for cross-AMI significance bands.
        alpha: Significance level metadata recorded in the output bundle.
        random_state: Deterministic random seed.
        selector_config: Sparse lag selector configuration.
        known_future_drivers: Optional opt-in mapping for lag-0 known-future drivers.
        include_zero_lag_diagnostic: Whether profile rows should include lag 0.
        include_cross_correlation: Whether to compute signed cross-correlation profile.
        include_cross_ami: Whether to compute cross-AMI profile and surrogate bands.
        n_jobs: Worker count forwarded to the surrogate-band executor.
            ``1`` (default) preserves serial behaviour; ``-1`` uses all CPUs.
            Per-driver iteration order is always deterministic regardless of
            ``n_jobs`` because parallelism only fans out within each driver's
            surrogate-band call.

    Returns:
        Composite :class:`LaggedExogBundle` with profile rows and sparse selections.

    Raises:
        ValueError: If inputs are invalid.
    """
    if n_jobs != -1 and n_jobs < 1:
        raise ValueError("n_jobs must be -1 or >= 1")

    validated_target, validated_drivers = _validate_inputs(
        target=target,
        drivers=drivers,
        target_name=target_name,
        max_lag=max_lag,
        n_surrogates=n_surrogates,
        alpha=alpha,
    )

    known_future_driver_names = _resolve_known_future_driver_names(
        known_future_drivers=known_future_drivers,
        driver_names=set(validated_drivers),
    )
    known_future_driver_set = set(known_future_driver_names)

    lag_start, lag_end = _lag_domain(
        include_zero_lag_diagnostic=include_zero_lag_diagnostic,
        max_lag=max_lag,
    )
    lag_range = (lag_start, lag_end)

    registry = default_registry()
    mi_info = registry.get("mi")
    mi_scorer = cast(DependenceScorer, mi_info.scorer)

    profile_rows: list[LaggedExogProfileRow] = []
    selected_lags: list[LaggedExogSelectionRow] = []

    for index, (driver_name, driver_series) in enumerate(validated_drivers.items()):
        seed = random_state + index

        xcorr_profile = (
            compute_cross_correlation_profile(
                validated_target,
                driver_series,
                max_lag=max_lag,
                lag_range=lag_range,
                method="pearson",
            )
            if include_cross_correlation
            else None
        )

        cross_ami_profile = (
            compute_exog_raw_curve(
                validated_target,
                driver_series,
                max_lag,
                mi_scorer,
                min_pairs=30,
                random_state=seed,
                lag_range=lag_range,
            )
            if include_cross_ami
            else None
        )

        upper_band: np.ndarray | None = None
        if include_cross_ami:
            _, upper_band = compute_significance_bands_generic(
                validated_target,
                n_surrogates,
                seed,
                max_lag,
                mi_info,
                "raw",
                exog=driver_series,
                min_pairs=30,
                n_jobs=n_jobs,
                lag_range=lag_range,
            )

        is_known_future_driver = driver_name in known_future_driver_set
        for lag in range(lag_start, lag_end + 1):
            offset = lag - lag_start
            corr_value = float(xcorr_profile[offset]) if xcorr_profile is not None else None
            ami_value = float(cross_ami_profile[offset]) if cross_ami_profile is not None else None
            band_upper_value = float(upper_band[offset]) if upper_band is not None else None
            significance = _significance_tag(value=ami_value, upper=band_upper_value)

            profile_rows.append(
                LaggedExogProfileRow(
                    target=target_name,
                    driver=driver_name,
                    lag=lag,
                    lag_role=_lag_role(lag=lag),
                    tensor_role=_profile_tensor_role(
                        lag=lag,
                        is_known_future=is_known_future_driver,
                    ),
                    correlation=corr_value,
                    cross_ami=ami_value,
                    cross_pami=None,
                    significance=significance,
                    significance_source=(
                        "phase_surrogate_xami" if include_cross_ami else "not_computed"
                    ),
                )
            )

        selected_lags.extend(
            select_sparse_lags(
                validated_target,
                driver_series,
                max_lag=max_lag,
                scorer=mi_scorer,
                config=selector_config,
                random_state=seed,
                target_name=target_name,
                driver_name=driver_name,
            )
        )

        if is_known_future_driver:
            selected_lags.append(
                _known_future_selection_row(
                    target_name=target_name,
                    driver_name=driver_name,
                )
            )

    metadata: dict[str, str | int | float] = {
        "requested_n_surrogates": n_surrogates,
        "alpha": alpha,
        "include_zero_lag_diagnostic": int(include_zero_lag_diagnostic),
        "include_cross_correlation": int(include_cross_correlation),
        "include_cross_ami": int(include_cross_ami),
        "selector_name": selector_config.selector_name,
    }
    if known_future_driver_names:
        metadata["known_future_contract_caution"] = _KNOWN_FUTURE_CAUTION
        metadata["known_future_opt_in_count"] = len(known_future_driver_names)

    return LaggedExogBundle(
        target_name=target_name,
        driver_names=list(validated_drivers),
        max_lag=max_lag,
        profile_rows=profile_rows,
        selected_lags=selected_lags,
        known_future_drivers=known_future_driver_names,
        metadata=metadata,
    )
