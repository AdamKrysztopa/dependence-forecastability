"""Focused tests for Phase 0 repository-contract loader."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_repo_contract_module = importlib.import_module("scripts._repo_contract")
RepoContractError = _repo_contract_module.RepoContractError
load_repo_contract = _repo_contract_module.load_repo_contract


def test_load_repo_contract_valid_payload(tmp_path: Path) -> None:
    contract_path = tmp_path / "repo_contract.yaml"
    contract_path.write_text(
        "\n".join(
            [
                'current_released_version: "0.3.4"',
                'next_planned_version: "0.3.6"',
                "canonical_paths:",
                "  forecast_prep_contract: docs/reference/forecast_prep_contract.md",
                "  scope_directive: docs/plan/aux_documents/developer_instruction_repo_scope.md",
                "deprecated_paths:",
                "  docs/forecast_prep_contract.md: docs/reference/forecast_prep_contract.md",
                "landing_surface:",
                "  notebook_policy: supplementary_only",
                "  forbidden_root_headings:",
                "    - Notebook Path And Artifact Surfaces",
                "dependency_group_policy:",
                "  forbidden_public_names:",
                "    - notebook",
                "  rename_map:",
                "    notebook: examples",
            ]
        ),
        encoding="utf-8",
    )

    contract = load_repo_contract(contract_path)

    assert contract.current_released_version == "0.3.4"
    assert contract.canonical_paths.scope_directive.endswith(
        "docs/plan/aux_documents/developer_instruction_repo_scope.md"
    )
    assert contract.dependency_group_policy.rename_map["notebook"] == "examples"


def test_load_repo_contract_rejects_non_mapping_root(tmp_path: Path) -> None:
    contract_path = tmp_path / "repo_contract.yaml"
    contract_path.write_text("- not-a-mapping\n", encoding="utf-8")

    with pytest.raises(RepoContractError, match="expected a top-level mapping"):
        load_repo_contract(contract_path)


def test_load_repo_contract_reports_missing_required_keys(tmp_path: Path) -> None:
    contract_path = tmp_path / "repo_contract.yaml"
    contract_path.write_text('current_released_version: "0.3.4"\n', encoding="utf-8")

    with pytest.raises(RepoContractError, match="validation failed"):
        load_repo_contract(contract_path)
