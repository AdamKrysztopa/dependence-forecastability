"""Smoke integration test for scripts/run_showcase_lagged_exogenous.py (V3_2-F09)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "run_showcase_lagged_exogenous.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "run_showcase_lagged_exogenous_under_test",
        _SCRIPT_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.slow
def test_run_showcase_lagged_exogenous_passes_smoke_and_manifest_contract(tmp_path: Path) -> None:
    module = _load_module()

    exit_code = module.main(
        [
            "--output-root",
            str(tmp_path),
            "--smoke",
            "--quiet",
        ]
    )

    assert exit_code == 0, "lagged-exogenous showcase verification should pass"

    bundle_path = tmp_path / "json" / "showcase_lagged_exogenous" / "lagged_exog_bundle.json"
    profile_csv_path = (
        tmp_path / "tables" / "showcase_lagged_exogenous" / "lagged_exog_profile_rows.csv"
    )
    selection_csv_path = (
        tmp_path / "tables" / "showcase_lagged_exogenous" / "lagged_exog_selected_lags.csv"
    )
    summary_path = tmp_path / "reports" / "showcase_lagged_exogenous" / "showcase_summary.md"
    verification_path = tmp_path / "reports" / "showcase_lagged_exogenous" / "verification.md"
    profile_figure_path = (
        tmp_path / "figures" / "showcase_lagged_exogenous" / "lagged_exog_profiles.png"
    )
    selection_figure_path = (
        tmp_path / "figures" / "showcase_lagged_exogenous" / "lagged_exog_selected_lags.png"
    )
    manifest_path = tmp_path / "json" / "showcase_lagged_exogenous" / "showcase_manifest.json"

    for path in (
        bundle_path,
        profile_csv_path,
        selection_csv_path,
        summary_path,
        verification_path,
        profile_figure_path,
        selection_figure_path,
        manifest_path,
    ):
        assert path.exists(), f"missing artifact: {path}"

    verification_text = verification_path.read_text(encoding="utf-8")
    assert "- status: **PASS**" in verification_text

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "PASS"
    assert manifest["settings"]["known_future_driver"] == "known_future_calendar"

    artifacts = manifest["artifacts"]
    required_artifacts = {
        "bundle_json",
        "profile_csv",
        "selection_csv",
        "summary_report",
        "verification_report",
        "profile_figure",
        "selection_figure",
    }
    assert required_artifacts.issubset(artifacts)
    for key in required_artifacts:
        assert Path(artifacts[key]).exists()

    selected_lag_map = manifest["selected_lag_map"]
    assert 0 in selected_lag_map.get("known_future_calendar", [])
    non_opt_in_zero_lag_drivers = [
        driver
        for driver, lags in selected_lag_map.items()
        if driver != "known_future_calendar" and 0 in lags
    ]
    assert not non_opt_in_zero_lag_drivers
