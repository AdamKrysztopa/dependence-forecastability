"""Framework-agnostic exporters for ForecastPrepContract.

Provides deterministic, stdlib-only serialisation helpers that convert a
:class:`~forecastability.utils.types.ForecastPrepContract` into human-readable
markdown or a flat list-of-dicts lag table suitable for downstream inspection.
No pandas, numpy, or forecasting-framework imports are used.
"""

from __future__ import annotations

from forecastability.utils.types import ForecastPrepContract


def forecast_prep_contract_to_markdown(contract: ForecastPrepContract) -> str:
    """Render a stable, deterministic markdown summary of a ForecastPrepContract.

    Args:
        contract: A frozen :class:`ForecastPrepContract` instance.

    Returns:
        A multi-line markdown string covering metadata, target lags, model
        families, covariates, and notes sections.
    """
    lines: list[str] = []

    def _bullet_list(items: list[str]) -> str:
        if not items:
            return "(none)"
        return "\n".join(f"- {item}" for item in items)

    def _int_bullet_list(items: list[int]) -> str:
        if not items:
            return "(none)"
        return "\n".join(f"- {item}" for item in items)

    # --- Header ---
    lines.append("# Forecast Prep Contract")
    lines.append("")

    # --- Metadata ---
    lines.append("## Metadata")
    lines.append("")
    lines.append(f"- source_goal: {contract.source_goal}")
    lines.append(f"- blocked: {contract.blocked}")
    lines.append(f"- readiness_status: {contract.readiness_status}")
    lines.append(f"- confidence_label: {contract.confidence_label}")
    lines.append(f"- target_frequency: {contract.target_frequency}")
    lines.append(f"- horizon: {contract.horizon}")
    lines.append(f"- contract_version: {contract.contract_version}")
    lines.append("")

    # --- Target Lags ---
    lines.append("## Target Lags")
    lines.append("")
    lines.append("**recommended_target_lags:**")
    lines.append(_int_bullet_list(list(contract.recommended_target_lags)))
    lines.append("")
    lines.append("**recommended_seasonal_lags:**")
    lines.append(_int_bullet_list(list(contract.recommended_seasonal_lags)))
    lines.append("")
    lines.append("**excluded_target_lags:**")
    lines.append(_int_bullet_list(list(contract.excluded_target_lags)))
    lines.append("")
    lines.append("**lag_rationale:**")
    lines.append(_bullet_list(list(contract.lag_rationale)))
    lines.append("")

    # --- Model Families ---
    lines.append("## Model Families")
    lines.append("")
    lines.append("**recommended_families:**")
    lines.append(_bullet_list(list(contract.recommended_families)))
    lines.append("")
    lines.append("**baseline_families:**")
    lines.append(_bullet_list(list(contract.baseline_families)))
    lines.append("")

    # --- Covariates ---
    lines.append("## Covariates")
    lines.append("")
    lines.append("**past_covariates:**")
    lines.append(_bullet_list(list(contract.past_covariates)))
    lines.append("")
    lines.append("**covariate_notes:**")
    lines.append(_bullet_list(list(contract.covariate_notes)))
    lines.append("")
    lines.append("**future_covariates:**")
    lines.append(_bullet_list(list(contract.future_covariates)))
    lines.append("")
    lines.append("**calendar_features:**")
    lines.append(_bullet_list(list(contract.calendar_features)))
    lines.append("")
    lines.append(f"**calendar_locale:** {contract.calendar_locale}")
    lines.append("")
    lines.append("**rejected_covariates:**")
    lines.append(_bullet_list(list(contract.rejected_covariates)))
    lines.append("")

    # --- Notes ---
    lines.append("## Notes")
    lines.append("")
    lines.append("**caution_flags:**")
    lines.append(_bullet_list(list(contract.caution_flags)))
    lines.append("")
    lines.append("**downstream_notes:**")
    lines.append(_bullet_list(list(contract.downstream_notes)))
    lines.append("")
    lines.append("**transformation_hints:**")
    lines.append(_bullet_list(list(contract.transformation_hints)))
    lines.append("")

    return "\n".join(lines)


def forecast_prep_contract_to_lag_table(
    contract: ForecastPrepContract,
) -> list[dict[str, object]]:
    """Return a deterministic flat lag table from a ForecastPrepContract.

    Each row is a plain :class:`dict` with keys: ``driver``, ``axis``,
    ``role``, ``lag``, ``selected_for_handoff``, and ``rationale``.

    Rows are sorted by ``(axis_order, driver, lag)`` where axis order is
    ``"target" < "past" < "future"``.

    Args:
        contract: A frozen :class:`ForecastPrepContract` instance.

    Returns:
        A list of row dicts; empty when the contract carries no lag or
        covariate information.
    """
    _axis_order = {"target": 0, "past": 1, "future": 2}

    def _find_rationale(lag: int) -> str:
        for entry in contract.lag_rationale:
            if str(lag) in entry:
                return entry
        return ""

    rows: list[dict[str, object]] = []

    # Target lags — direct/secondary (selected)
    for lag in contract.recommended_target_lags:
        rows.append(
            {
                "driver": "target",
                "axis": "target",
                "role": "direct",
                "lag": lag,
                "selected_for_handoff": True,
                "rationale": _find_rationale(lag),
            }
        )

    # Seasonal lags (selected)
    for lag in contract.recommended_seasonal_lags:
        rows.append(
            {
                "driver": "target",
                "axis": "target",
                "role": "seasonal",
                "lag": lag,
                "selected_for_handoff": True,
                "rationale": _find_rationale(lag),
            }
        )

    # Excluded target lags
    for lag in contract.excluded_target_lags:
        rows.append(
            {
                "driver": "target",
                "axis": "target",
                "role": "excluded",
                "lag": lag,
                "selected_for_handoff": False,
                "rationale": _find_rationale(lag),
            }
        )

    # Past covariates — lag=1 conservative default
    for name in contract.past_covariates:
        rows.append(
            {
                "driver": name,
                "axis": "past",
                "role": "past",
                "lag": 1,
                "selected_for_handoff": True,
                "rationale": "",
            }
        )

    # Future covariates — lag=0
    for name in contract.future_covariates:
        rows.append(
            {
                "driver": name,
                "axis": "future",
                "role": "future",
                "lag": 0,
                "selected_for_handoff": True,
                "rationale": "",
            }
        )

    rows.sort(
        key=lambda r: (
            _axis_order[str(r["axis"])],
            str(r["driver"]),
            int(r["lag"]),
        )
    )
    return rows
