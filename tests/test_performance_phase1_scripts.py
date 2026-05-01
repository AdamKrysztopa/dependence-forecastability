"""Smoke tests for Phase 1 performance measurement tooling."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path


def _load_performance_config(path: Path):
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "performance_common.py"
    spec = importlib.util.spec_from_file_location("performance_common", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.load_performance_config(path)


def test_performance_baseline_config_defines_required_sizes() -> None:
    config = _load_performance_config(Path("configs/performance_baseline.yaml"))
    labels = {case.size_label for case in config.cases}

    assert {"small", "medium", "large"}.issubset(labels)
    assert all(case.n_surrogates >= 99 for case in config.cases)


def test_performance_summary_artifact_contract() -> None:
    path = Path("outputs/performance/performance_summary.json")
    if not path.exists():
        return

    payload = json.loads(path.read_text(encoding="utf-8"))
    metadata = payload["command_metadata"]

    assert payload["artifact_type"] == "performance_baseline_summary"
    assert {"small", "medium", "large"}.issubset({case["size_label"] for case in payload["cases"]})
    for key in [
        "git_sha",
        "config_hash",
        "numpy_show_config_digest",
        "threadpoolctl_snapshot",
        "omp_num_threads",
        "mkl_num_threads",
        "forecastability_version",
        "uv_lock_hash",
    ]:
        assert key in metadata


def test_hotspots_csv_artifact_contract() -> None:
    path = Path("outputs/performance/hotspots.csv")
    if not path.exists():
        return

    rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
    target_ids = {row["target_id"] for row in rows}

    assert "callable.forecastability.run_triage" in target_ids
    assert "script.run_canonical_triage" in target_ids
    assert "command.forecastability" in target_ids
    assert any(row["profiled"] == "True" for row in rows)
    assert any(row["skip_reason"] for row in rows if row["profiled"] == "False")
