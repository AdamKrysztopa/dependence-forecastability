"""Smoke test for scripts/run_routing_validation_report.py (plan v0.3.3 V3_4-F07)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "run_routing_validation_report.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "run_routing_validation_report_under_test",
        _SCRIPT_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_routing_validation_report_smoke(tmp_path: Path) -> None:
    module = _load_module()

    exit_code = module.main(
        [
            "--output-root",
            str(tmp_path),
            "--smoke",
            "--no-real-panel",
        ]
    )

    assert exit_code == 0

    json_dir = tmp_path / "json" / "routing_validation"
    reports_dir = tmp_path / "reports" / "routing_validation"
    figures_dir = tmp_path / "figures" / "routing_validation"

    bundle_path = json_dir / "routing_validation_bundle.json"
    manifest_path = json_dir / "routing_validation_report_manifest.json"
    report_path = reports_dir / "routing_validation_report.md"
    outcome_path = figures_dir / "routing_validation_outcomes.png"
    confidence_path = figures_dir / "routing_validation_confidence.png"
    margin_hist_path = figures_dir / "routing_validation_threshold_margin_histogram.png"
    scatter_path = figures_dir / "routing_validation_margin_stability.png"

    assert bundle_path.exists()
    assert manifest_path.exists()
    assert report_path.exists()
    assert outcome_path.exists()
    assert confidence_path.exists()
    assert margin_hist_path.exists()
    assert scatter_path.exists()

    report_text = report_path.read_text(encoding="utf-8")
    bundle_payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert "# Routing Validation Report" in report_text
    assert "## Overall Counts" in report_text
    assert "## Per-Case Outcomes" in report_text
    assert "weak_seasonal_near_threshold" in report_text
    assert bundle_payload["audit"]["total_cases"] == len(bundle_payload["cases"])
    assert manifest_payload["settings"]["smoke"] is True
    assert manifest_payload["settings"]["real_panel_enabled"] is False
    assert manifest_payload["settings"]["weak_seasonal_amplitude"] == 1.98
    assert "flagged_cases" in manifest_payload
