"""PBE-F07 smoke tests: ``--n-jobs`` parser plumbing for geometry-aware scripts."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, script: str):
    spec = importlib.util.spec_from_file_location(name, _REPO_ROOT / "scripts" / script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_csv_geometry_runner_parser_accepts_n_jobs() -> None:
    """The CSV geometry runner should expose ``--n-jobs`` with a serial default."""
    module = _load_module(
        "run_ami_information_geometry_csv_under_test",
        "run_ami_information_geometry_csv.py",
    )
    parser = module._build_parser()
    default_args = parser.parse_args(["--input-csv", "ignored.csv"])
    assert default_args.n_jobs == 1
    parallel_args = parser.parse_args(["--input-csv", "ignored.csv", "--n-jobs", "4"])
    assert parallel_args.n_jobs == 4


def test_csv_geometry_runner_rejects_n_jobs_zero(tmp_path: Path) -> None:
    """``--n-jobs 0`` must raise the convention-aligned validation error."""
    module = _load_module(
        "run_ami_information_geometry_csv_under_test_main",
        "run_ami_information_geometry_csv.py",
    )
    csv_path = tmp_path / "input.csv"
    csv_path.write_text("col\n1\n2\n3\n", encoding="utf-8")
    import sys

    saved_argv = sys.argv
    try:
        sys.argv = [
            "run_ami_information_geometry_csv.py",
            "--input-csv",
            str(csv_path),
            "--n-jobs",
            "0",
        ]
        with pytest.raises(ValueError, match="--n-jobs"):
            module.main()
    finally:
        sys.argv = saved_argv


def test_showcase_fingerprint_parser_accepts_n_jobs() -> None:
    """The fingerprint showcase script should expose ``--n-jobs`` with a serial default."""
    module = _load_module(
        "run_showcase_fingerprint_n_jobs_parser",
        "run_showcase_fingerprint.py",
    )
    default_args = module._parse_args([])
    assert default_args.n_jobs == 1
    parallel_args = module._parse_args(["--n-jobs", "-1"])
    assert parallel_args.n_jobs == -1
