"""Smoke test for scripts/run_showcase_fingerprint.py (V3_1-F07)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "run_showcase_fingerprint.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "run_showcase_fingerprint_under_test",
        _SCRIPT_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_showcase_fingerprint_passes_verification(tmp_path: Path) -> None:
    module = _load_module()

    exit_code = module.main(
        [
            "--output-root",
            str(tmp_path),
            "--smoke",
            "--quiet",
        ]
    )

    assert exit_code == 0, "fingerprint showcase verification should pass"

    report_path = tmp_path / "reports" / "showcase_fingerprint" / "showcase_report.md"
    verification_path = tmp_path / "reports" / "showcase_fingerprint" / "verification.md"
    summary_csv_path = tmp_path / "tables" / "showcase_fingerprint" / "fingerprint_summary.csv"
    routing_csv_path = tmp_path / "tables" / "showcase_fingerprint" / "fingerprint_routing.csv"
    manifest_path = tmp_path / "json" / "showcase_fingerprint" / "showcase_manifest.json"
    profile_path = tmp_path / "figures" / "showcase_fingerprint" / "fingerprint_profiles.png"
    metric_path = tmp_path / "figures" / "showcase_fingerprint" / "fingerprint_metrics.png"

    assert report_path.exists()
    assert verification_path.exists()
    assert summary_csv_path.exists()
    assert routing_csv_path.exists()
    assert manifest_path.exists()
    assert profile_path.exists()
    assert metric_path.exists()

    report_text = report_path.read_text(encoding="utf-8")
    verification_text = verification_path.read_text(encoding="utf-8")
    summary_frame = pd.read_csv(summary_csv_path)
    routing_frame = pd.read_csv(routing_csv_path)

    assert "Plain-language summary of the mathematics" in report_text
    assert "strict A1/A2/A3 outputs remain aligned" in report_text
    assert "- status: **PASS**" in verification_text
    assert len(summary_frame) == 4
    assert len(routing_frame) == 4
