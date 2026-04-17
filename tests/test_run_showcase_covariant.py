"""Smoke test for scripts/run_showcase_covariant.py (V3-F09)."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "run_showcase_covariant.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_showcase_covariant_under_test", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.slow
def test_run_showcase_covariant_passes_verification(tmp_path: Path) -> None:
    module = _load_script()

    exit_code = module.main(
        [
            "--no-agent",
            "--output-root",
            str(tmp_path),
            "--max-lag",
            "3",
            "--random-state",
            "42",
        ]
    )

    assert exit_code == 0, "showcase verification should pass on the canonical benchmark"

    bundle_path = tmp_path / "json" / "covariant_bundle.json"
    interpretation_path = tmp_path / "json" / "covariant_interpretation.json"
    explanation_path = tmp_path / "json" / "covariant_agent_explanation.json"
    table_path = tmp_path / "tables" / "covariant_summary.csv"
    verification_path = tmp_path / "reports" / "showcase_covariant" / "verification.md"

    for path in (bundle_path, interpretation_path, explanation_path, table_path, verification_path):
        assert path.exists(), f"missing artifact: {path}"

    bundle_data = json.loads(bundle_path.read_text(encoding="utf-8"))
    interpretation_data = json.loads(interpretation_path.read_text(encoding="utf-8"))
    explanation_data = json.loads(explanation_path.read_text(encoding="utf-8"))

    assert bundle_data["target_name"] == "target"
    assert interpretation_data["target"] == "target"
    assert explanation_data["target"] == "target"
    assert explanation_data["narrative"] is None  # --no-agent path

    with table_path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows, "summary CSV must contain at least one row"

    report_text = verification_path.read_text(encoding="utf-8")
    assert "**PASS**" in report_text
