"""Contract tests for the V3_1-F07.1 fingerprint walkthrough notebook."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_NOTEBOOK_PATH = (
    _REPO_ROOT / "notebooks" / "walkthroughs" / "02_forecastability_fingerprint_showcase.ipynb"
)
_CONTRACT_SCRIPT = _REPO_ROOT / "scripts" / "check_notebook_contract.py"


def _load_contract_script():
    spec = importlib.util.spec_from_file_location(
        "check_notebook_contract_under_test_fingerprint",
        _CONTRACT_SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fingerprint_walkthrough_notebook_contains_required_sections() -> None:
    notebook = json.loads(_NOTEBOOK_PATH.read_text(encoding="utf-8"))
    headings = [
        "".join(cell.get("source", [])).strip().splitlines()[0]
        for cell in notebook["cells"]
        if cell.get("cell_type") == "markdown" and "".join(cell.get("source", [])).strip()
    ]

    required_headings = {
        "# Forecastability Fingerprint Showcase",
        "## A — What the fingerprint solves",
        "## B — Why four fields instead of disconnected diagnostics",
        "## C — Canonical benchmark series generation",
        "## D — information_mass walkthrough",
        "## E — information_horizon walkthrough",
        "## F — information_structure walkthrough with peak-spacing visuals",
        "## G — nonlinear_share walkthrough against Gaussian baseline",
        "## H — Routing walkthrough with caution flags and confidence labels",
        "## I — Agent-layer summary in plain language",
        "## J — Verification and caveats",
    }

    assert required_headings.issubset(set(headings))

    source_text = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])
    assert "generate_fingerprint_archetypes" in source_text
    assert "run_forecastability_fingerprint" in source_text
    assert "build_fingerprint_showcase_record" in source_text
    assert "build_plain_language_math_summary" in source_text


def test_notebook_contract_script_tracks_fingerprint_walkthrough() -> None:
    module = _load_contract_script()
    assert "walkthroughs/02_forecastability_fingerprint_showcase.ipynb" in module.EXPECTED_NOTEBOOKS
