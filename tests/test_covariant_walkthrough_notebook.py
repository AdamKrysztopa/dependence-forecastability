"""Contract tests for the V3-F10 covariant walkthrough notebook."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from forecastability.reporting.covariant_walkthrough import (
    conditioning_scope_frame,
    save_directionality_plot,
)
from forecastability.use_cases.run_covariant_analysis import run_covariant_analysis
from forecastability.utils.synthetic import generate_covariant_benchmark, generate_directional_pair

_REPO_ROOT = Path(__file__).resolve().parents[1]
_NOTEBOOK_PATH = (
    _REPO_ROOT / "notebooks" / "walkthroughs" / "01_covariant_informative_showcase.ipynb"
)
_CONTRACT_SCRIPT = _REPO_ROOT / "scripts" / "check_notebook_contract.py"


def _load_contract_script():
    spec = importlib.util.spec_from_file_location(
        "check_notebook_contract_under_test",
        _CONTRACT_SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_covariant_walkthrough_notebook_contains_required_sections() -> None:
    notebook = json.loads(_NOTEBOOK_PATH.read_text(encoding="utf-8"))
    headings = [
        "".join(cell.get("source", [])).strip().splitlines()[0]
        for cell in notebook["cells"]
        if cell.get("cell_type") == "markdown" and "".join(cell.get("source", [])).strip()
    ]

    required_headings = {
        "# Covariant Informative Showcase",
        "## A — Why covariant",
        "## B — Data setup",
        "## C — Baseline: CrossAMI + CrosspAMI",
        "## D — GCMI",
        "## E — Transfer entropy",
        "## F — PCMCI+",
        "## G — PCMCI-AMI",
        "## H — Unified interpretation table",
        (
            "## Known limitation: exogenous autohistory is not conditioned out in "
            "CrossMI/pCrossAMI/TE—see v0.3.1"
        ),
    }

    assert required_headings.issubset(set(headings))

    source_text = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])
    assert "generate_covariant_benchmark" in source_text
    assert "run_covariant_analysis" in source_text


def test_notebook_contract_script_tracks_covariant_walkthrough() -> None:
    module = _load_contract_script()
    assert "walkthroughs/01_covariant_informative_showcase.ipynb" in module.EXPECTED_NOTEBOOKS


def test_conditioning_scope_frame_matches_covariant_bundle() -> None:
    df = generate_covariant_benchmark(n=260, seed=42)
    target = df["target"].to_numpy()
    drivers = {name: df[name].to_numpy() for name in df.columns if name != "target"}

    bundle = run_covariant_analysis(
        target,
        drivers,
        methods=["cross_ami", "cross_pami", "te", "gcmi"],
        max_lag=3,
        n_surrogates=99,
        random_state=42,
    )
    frame = conditioning_scope_frame(bundle)

    scope_by_method = dict(zip(frame["method"], frame["scope"], strict=True))
    assert scope_by_method["cross_ami"] == "none"
    assert scope_by_method["cross_pami"] == "target_only"
    assert scope_by_method["transfer_entropy"] == "target_only"
    assert scope_by_method["gcmi"] == "none"
    assert scope_by_method["pcmci"] == "not_requested"
    assert scope_by_method["pcmci_ami"] == "not_requested"


def test_directionality_plot_helper_saves_artifact_and_preserves_direction(tmp_path: Path) -> None:
    pair_df = generate_directional_pair(n=1500, seed=42)
    output_path = tmp_path / "directionality.png"

    frame = save_directionality_plot(
        source=pair_df["x"].to_numpy(),
        target=pair_df["y"].to_numpy(),
        output_path=output_path,
        max_lag=5,
        random_state=42,
        source_name="x",
        target_name="y",
    )

    assert output_path.exists()
    assert frame["te_x_to_y"].max() > frame["te_y_to_x"].max()
