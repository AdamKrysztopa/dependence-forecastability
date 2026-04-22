"""Smoke test for scripts/run_showcase_covariant.py (V3-F09)."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from forecastability.utils.types import (
    CausalGraphResult,
    CovariantAnalysisBundle,
    CovariantMethodConditioning,
    CovariantSummaryRow,
    PcmciAmiResult,
)

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


# ---------------------------------------------------------------------------
# Unit tests for _verify_against_ground_truth (rubber-duck concern #2)
# ---------------------------------------------------------------------------

_CONDITIONING = CovariantMethodConditioning(
    cross_ami="none",
    cross_pami="target_only",
    transfer_entropy="target_only",
    gcmi="none",
    pcmci="full_mci",
    pcmci_ami="full_mci",
)


def _stub_row(driver: str, lag: int) -> CovariantSummaryRow:
    return CovariantSummaryRow(
        target="target",
        driver=driver,
        lag=lag,
        cross_ami=0.0,
        significance="below_band",
        lagged_exog_conditioning=_CONDITIONING,
    )


def _stub_bundle(*, driver_redundant_is_pcmci_ami_parent: bool) -> CovariantAnalysisBundle:
    """Return a minimal bundle with pcmci_ami_result to exercise the verifier branch."""
    drivers = [
        "driver_direct",
        "driver_mediated",
        "driver_redundant",
        "driver_noise",
        "driver_contemp",
        "driver_nonlin_sq",
        "driver_nonlin_abs",
    ]
    rows = [_stub_row(d, 1) for d in drivers]
    pcmci_ami_parents_list: list[tuple[str, int]] = []
    if driver_redundant_is_pcmci_ami_parent:
        pcmci_ami_parents_list.append(("driver_redundant", 1))
    graph = CausalGraphResult(parents={"target": pcmci_ami_parents_list})
    pcmci_ami_result = PcmciAmiResult(
        causal_graph=graph,
        phase0_mi_scores=[],
        phase0_pruned_count=0,
        phase0_kept_count=0,
        phase1_skeleton=graph,
        phase2_final=graph,
        ami_threshold=0.05,
    )
    return CovariantAnalysisBundle(
        summary_table=rows,
        pcmci_graph=None,
        pcmci_ami_result=pcmci_ami_result,
        target_name="target",
        driver_names=drivers,
        horizons=[1],
    )


def test_verify_redundant_not_pcmci_ami_parent_passes() -> None:
    """driver_redundant absent from pcmci_ami parents must not produce a violation."""
    module = _load_script()
    bundle = _stub_bundle(driver_redundant_is_pcmci_ami_parent=False)
    interpretation = MagicMock()
    interpretation.driver_roles = [
        MagicMock(driver=d, role="noise_or_weak", best_lag=1) for d in bundle.driver_names
    ]
    interpretation.primary_drivers = []
    violations = module._verify_against_ground_truth(bundle, interpretation)
    redundant_viols = [v for v in violations if "driver_redundant" in v and "pcmci_ami" in v]
    assert not redundant_viols


def test_verify_redundant_as_pcmci_ami_parent_is_a_violation() -> None:
    """driver_redundant in pcmci_ami parents must produce exactly one violation."""
    module = _load_script()
    bundle = _stub_bundle(driver_redundant_is_pcmci_ami_parent=True)
    interpretation = MagicMock()
    interpretation.driver_roles = [
        MagicMock(driver=d, role="noise_or_weak", best_lag=1) for d in bundle.driver_names
    ]
    interpretation.primary_drivers = []
    violations = module._verify_against_ground_truth(bundle, interpretation)
    redundant_viols = [v for v in violations if "driver_redundant" in v and "must NOT" in v]
    assert len(redundant_viols) == 1
