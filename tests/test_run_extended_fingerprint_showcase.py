"""Smoke test for scripts/run_extended_fingerprint_showcase.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "run_extended_fingerprint_showcase.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "run_extended_fingerprint_showcase_under_test",
        _SCRIPT_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _count_unescaped_pipes(line: str) -> int:
    count = 0
    escaped = False
    for character in line:
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if character == "|":
            count += 1
    return count


def test_run_extended_fingerprint_showcase_passes_verification(tmp_path: Path) -> None:
    module = _load_module()

    exit_code = module.main(
        [
            "--output-root",
            str(tmp_path),
            "--smoke",
            "--quiet",
        ]
    )

    report_path = tmp_path / "reports" / "extended_fingerprint" / "showcase_report.md"
    brief_path = tmp_path / "reports" / "extended_fingerprint" / "brief.md"
    verification_path = tmp_path / "reports" / "extended_fingerprint" / "verification.md"
    summary_csv_path = tmp_path / "tables" / "extended_fingerprint" / "extended_summary.csv"
    routing_csv_path = tmp_path / "tables" / "extended_fingerprint" / "extended_routing.csv"
    manifest_path = tmp_path / "json" / "extended_fingerprint" / "showcase_manifest.json"
    profile_path = tmp_path / "figures" / "extended_fingerprint" / "extended_ami_profiles.png"
    metric_path = tmp_path / "figures" / "extended_fingerprint" / "extended_metric_overview.png"

    verification_details = (
        verification_path.read_text(encoding="utf-8")
        if verification_path.exists()
        else "<verification report missing>"
    )
    assert exit_code == 0, (
        "extended fingerprint showcase verification should pass; "
        f"exit_code={exit_code}; verification details:\n{verification_details}"
    )

    assert report_path.exists()
    assert brief_path.exists()
    assert verification_path.exists()
    assert summary_csv_path.exists()
    assert routing_csv_path.exists()
    assert manifest_path.exists()
    assert profile_path.exists()
    assert metric_path.exists()

    report_text = report_path.read_text(encoding="utf-8")
    brief_text = brief_path.read_text(encoding="utf-8")
    verification_text = verification_path.read_text(encoding="utf-8")
    summary_frame = pd.read_csv(summary_csv_path)
    routing_frame = pd.read_csv(routing_csv_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifacts = manifest["artifacts"]
    expected_artifacts = {
        "profile_figure": profile_path,
        "metric_figure": metric_path,
        "summary_csv": summary_csv_path,
        "routing_csv": routing_csv_path,
        "report": report_path,
        "brief": brief_path,
        "verification": verification_path,
    }

    assert "AMI-first" in report_text
    assert "Plain-language summary of the mathematics" in report_text
    assert "Extended Forecastability Brief" in brief_text
    assert "- status: **PASS**" in verification_text
    assert "## Coarse semantic snapshots" in verification_text
    routing_section = report_text.split("## Routing comparison\n\n", maxsplit=1)[1]
    routing_table_lines = []
    for line in routing_section.splitlines():
        if not line:
            break
        if line.startswith("|"):
            routing_table_lines.append(line)
    assert routing_table_lines
    header_pipe_count = _count_unescaped_pipes(routing_table_lines[0])
    assert all(
        _count_unescaped_pipes(line) == header_pipe_count for line in routing_table_lines[1:]
    )
    assert "\\|" in "\n".join(routing_table_lines[2:])
    assert len(summary_frame) == 7
    assert len(routing_frame) == 7
    assert len(manifest["items"]) == 7
    assert manifest["status"] == "PASS", (
        "showcase manifest should record a passing verifier status; "
        f"issues={manifest.get('verification_issues', [])}"
    )
    assert manifest["verification_issue_count"] == 0, (
        "showcase manifest should record zero verifier issues; "
        f"issues={manifest.get('verification_issues', [])}"
    )
    assert manifest["verification_issues"] == []
    assert set(artifacts) == set(expected_artifacts), (
        "showcase manifest artifacts block should contain the expected keys; "
        f"actual_keys={sorted(artifacts)}"
    )
    for key, expected_path in expected_artifacts.items():
        actual_path = Path(artifacts[key])
        assert actual_path == expected_path, (
            f"showcase manifest artifact '{key}' should point to {expected_path}, got {actual_path}"
        )
        assert actual_path.exists(), (
            f"showcase manifest artifact '{key}' should exist on disk at {actual_path}"
        )

    summary_by_name = summary_frame.set_index("target_name")
    routing_by_name = routing_frame.set_index("target_name")

    assert routing_by_name.loc["white_noise", "predictability_sources"] == "-"
    assert "lag_dependence" in routing_by_name.loc["ar1", "predictability_sources"]
    assert float(summary_by_name.loc["ar1", "information_horizon"]) >= 3.0
    assert "seasonality" in routing_by_name.loc["seasonal_plus_noise", "predictability_sources"]
    assert float(summary_by_name.loc["seasonal_plus_noise", "seasonal_strength"]) < float(
        summary_by_name.loc["clean_sine_wave", "seasonal_strength"]
    )
    assert (
        "lag_dependence" in routing_by_name.loc["long_memory_candidate", "predictability_sources"]
    )
    assert "long_memory" in routing_by_name.loc["long_memory_candidate", "predictability_sources"]
    assert "ordinal_redundancy" in routing_by_name.loc["henon_map", "predictability_sources"]
    assert float(summary_by_name.loc["henon_map", "ordinal_redundancy"]) > float(
        summary_by_name.loc["clean_sine_wave", "ordinal_redundancy"]
    )

    for item in manifest["items"]:
        result_path = Path(item["result_path"])
        assert result_path.exists(), (
            f"showcase manifest result payload for {item['series_name']} should exist at "
            f"{result_path}"
        )
