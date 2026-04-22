"""Focused regression tests for tiny triage-first hand-off surfaces."""

from __future__ import annotations

import contextlib
import importlib.util
import io
from pathlib import Path
from types import ModuleType

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(module_name: str, relative_path: str) -> ModuleType:
    file_path = _REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("module_name", "relative_path", "required_markers"),
    [
        (
            "forecasting_triage_first_under_test",
            "examples/forecasting_triage_first.py",
            ["blocked", "forecastability_class", "primary_lags", "structure_signals"],
        ),
        (
            "run_triage_handoff_demo_under_test",
            "scripts/run_triage_handoff_demo.py",
            ["blocked=", "forecastability_class=", "primary_lags=", "structure_signals="],
        ),
    ],
)
def test_tiny_handoff_surfaces_deemphasize_recommendations(
    module_name: str,
    relative_path: str,
    required_markers: list[str],
) -> None:
    """Tiny public anchors should surface triage hand-off cues, not recommendations."""
    module = _load_module(module_name, relative_path)
    stdout = io.StringIO()

    with contextlib.redirect_stdout(stdout):
        module.main()

    output = stdout.getvalue()

    assert "recommendation" not in output
    assert "handoff" in output or "next_step" in output
    for marker in required_markers:
        assert marker in output
