"""Tests for the framework-agnostic ForecastPrepContract exporters (FPC-F04R)."""

from __future__ import annotations

import pathlib

from forecastability.utils.types import ForecastPrepContract

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _minimal_contract(**overrides: object) -> ForecastPrepContract:
    """Return a minimal ForecastPrepContract, accepting keyword overrides."""
    defaults: dict[str, object] = {
        "source_goal": "univariate",
        "blocked": False,
        "readiness_status": "ok",
    }
    defaults.update(overrides)
    return ForecastPrepContract(**defaults)  # type: ignore[arg-type]


def _rich_contract() -> ForecastPrepContract:
    """Return a contract with non-trivial lag, covariate, and family data."""
    return ForecastPrepContract(
        source_goal="covariant",
        blocked=False,
        readiness_status="ok",
        recommended_target_lags=[1, 2, 3],
        recommended_seasonal_lags=[12],
        excluded_target_lags=[6],
        lag_rationale=["Lag 1 is primary", "Lag 12 is seasonal", "Lag 6 excluded"],
        recommended_families=["ARIMA", "LightGBM"],
        baseline_families=["Naive"],
        past_covariates=["temp", "humidity"],
        future_covariates=["day_of_week"],
        rejected_covariates=["noise"],
        covariate_notes=["temp is informative"],
        caution_flags=["short series"],
        downstream_notes=["use rolling origin"],
        transformation_hints=["log-transform target"],
    )


# ---------------------------------------------------------------------------
# Markdown tests
# ---------------------------------------------------------------------------


def test_markdown_is_str() -> None:
    from forecastability.services.forecast_prep_export import (
        forecast_prep_contract_to_markdown,
    )

    result = forecast_prep_contract_to_markdown(_minimal_contract())
    assert isinstance(result, str)
    assert len(result) > 0


def test_markdown_covers_expected_sections() -> None:
    from forecastability.services.forecast_prep_export import (
        forecast_prep_contract_to_markdown,
    )

    md = forecast_prep_contract_to_markdown(_rich_contract())
    for section in ("Target Lags", "Covariates", "Model Families", "Notes"):
        assert section in md, f"Expected section '{section}' not found in markdown"


def test_markdown_blocked_contract_shows_blocked() -> None:
    from forecastability.services.forecast_prep_export import (
        forecast_prep_contract_to_markdown,
    )

    contract = _minimal_contract(blocked=True)
    md = forecast_prep_contract_to_markdown(contract)
    assert "blocked: True" in md


def test_markdown_is_stable() -> None:
    from forecastability.services.forecast_prep_export import (
        forecast_prep_contract_to_markdown,
    )

    contract = _rich_contract()
    assert forecast_prep_contract_to_markdown(contract) == forecast_prep_contract_to_markdown(
        contract
    )


# ---------------------------------------------------------------------------
# Lag table tests
# ---------------------------------------------------------------------------


def test_lag_table_returns_list_of_dicts() -> None:
    from forecastability.services.forecast_prep_export import (
        forecast_prep_contract_to_lag_table,
    )

    rows = forecast_prep_contract_to_lag_table(_rich_contract())
    assert isinstance(rows, list)
    assert all(isinstance(r, dict) for r in rows)


def test_lag_table_has_required_keys() -> None:
    from forecastability.services.forecast_prep_export import (
        forecast_prep_contract_to_lag_table,
    )

    required_keys = {"driver", "axis", "role", "lag", "selected_for_handoff", "rationale"}
    rows = forecast_prep_contract_to_lag_table(_rich_contract())
    assert rows, "Expected at least one row from rich contract"
    for row in rows:
        assert required_keys <= row.keys(), f"Row missing keys: {required_keys - row.keys()}"


def test_lag_table_is_deterministic_and_ordered() -> None:
    from forecastability.services.forecast_prep_export import (
        forecast_prep_contract_to_lag_table,
    )

    contract = _rich_contract()
    rows1 = forecast_prep_contract_to_lag_table(contract)
    rows2 = forecast_prep_contract_to_lag_table(contract)
    assert rows1 == rows2

    # Axis ordering: target < past < future
    _axis_order = {"target": 0, "past": 1, "future": 2}
    axes = [_axis_order[str(r["axis"])] for r in rows1]
    assert axes == sorted(axes), f"Rows not sorted by axis: {[r['axis'] for r in rows1]}"


def test_lag_table_target_lags_are_positive() -> None:
    from forecastability.services.forecast_prep_export import (
        forecast_prep_contract_to_lag_table,
    )

    rows = forecast_prep_contract_to_lag_table(_rich_contract())
    target_rows = [r for r in rows if r["axis"] == "target"]
    assert target_rows, "Expected target rows in rich contract"
    for row in target_rows:
        assert int(row["lag"]) >= 1, f"Target lag must be >= 1, got {row['lag']}"  # type: ignore[arg-type]


def test_lag_table_future_lags_are_nonneg() -> None:
    from forecastability.services.forecast_prep_export import (
        forecast_prep_contract_to_lag_table,
    )

    rows = forecast_prep_contract_to_lag_table(_rich_contract())
    future_rows = [r for r in rows if r["axis"] == "future"]
    assert future_rows, "Expected future rows in rich contract"
    for row in future_rows:
        assert int(row["lag"]) >= 0, f"Future lag must be >= 0, got {row['lag']}"  # type: ignore[arg-type]


def test_no_framework_imports_in_forecast_prep_export() -> None:
    source_path = (
        pathlib.Path(__file__).parent.parent
        / "src"
        / "forecastability"
        / "services"
        / "forecast_prep_export.py"
    )
    source = source_path.read_text(encoding="utf-8")

    forbidden = [
        "import darts",
        "from darts",
        "import mlforecast",
        "from mlforecast",
        "import statsforecast",
        "from statsforecast",
        "import nixtla",
        "from nixtla",
        "import pandas",
        "from pandas",
    ]
    for pattern in forbidden:
        assert pattern not in source, (
            f"Forbidden import pattern '{pattern}' found in forecast_prep_export.py"
        )


def test_no_framework_imports_in_forecast_prep_modules() -> None:
    """All forecast_prep source modules must be free of framework and pandas imports."""
    _src_root = pathlib.Path(__file__).parent.parent / "src" / "forecastability"
    modules_to_check = [
        _src_root / "services" / "forecast_prep_export.py",
        _src_root / "services" / "forecast_prep_mapper.py",
        _src_root / "services" / "calendar_feature_service.py",
        _src_root / "use_cases" / "build_forecast_prep_contract.py",
    ]
    framework_patterns = [
        "import darts",
        "from darts",
        "import mlforecast",
        "from mlforecast",
        "import statsforecast",
        "from statsforecast",
        "import nixtla",
        "from nixtla",
    ]
    for module_path in modules_to_check:
        assert module_path.exists(), f"Expected source module not found: {module_path}"
        source = module_path.read_text(encoding="utf-8")
        for pattern in framework_patterns:
            assert pattern not in source, (
                f"Forbidden import '{pattern}' found in {module_path.name}"
            )


def test_model_dump_json_round_trip() -> None:
    contract = _rich_contract()
    restored = ForecastPrepContract.model_validate_json(contract.model_dump_json())
    assert restored == contract


# ---------------------------------------------------------------------------
# Import surface tests
# ---------------------------------------------------------------------------


def test_exporters_importable_from_forecastability() -> None:
    from forecastability import (  # noqa: F401
        forecast_prep_contract_to_lag_table,
        forecast_prep_contract_to_markdown,
    )


def test_exporters_importable_from_forecastability_triage() -> None:
    from forecastability.triage import (  # noqa: F401
        forecast_prep_contract_to_lag_table,
        forecast_prep_contract_to_markdown,
    )
