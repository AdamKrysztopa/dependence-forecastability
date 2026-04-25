"""Typed loader for repository contract metadata."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError


class RepoContractError(ValueError):
    """Raised when the repository contract is missing or malformed."""


class CanonicalPaths(BaseModel):
    """Canonical target locations for rewritten or enforced references."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    forecast_prep_contract: str
    scope_directive: str


class LandingSurfacePolicy(BaseModel):
    """Rules for root README landing-surface wording and headings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    notebook_policy: str
    forbidden_root_headings: list[str]


class DependencyGroupPolicy(BaseModel):
    """Rules for public dependency-group naming and migration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    forbidden_public_names: list[str]
    rename_map: dict[str, str]


class RepoContract(BaseModel):
    """Structured repository contract consumed by maintenance scripts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    current_released_version: str
    next_planned_version: str
    canonical_paths: CanonicalPaths
    deprecated_paths: dict[str, str]
    landing_surface: LandingSurfacePolicy
    dependency_group_policy: DependencyGroupPolicy


_REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT_PATH = _REPO_ROOT / "repo_contract.yaml"


def _validation_summary(exc: ValidationError) -> str:
    """Build a compact validation summary from a Pydantic exception."""
    errors: list[str] = []
    for err in exc.errors(include_url=False):
        loc = ".".join(str(part) for part in err["loc"])
        msg = str(err["msg"])
        errors.append(f"{loc}: {msg}")
    return "; ".join(errors)


def load_repo_contract(path: Path | None = None) -> RepoContract:
    """Load and validate the repository contract.

    Args:
        path: Optional contract path. Defaults to the repository root contract file.

    Returns:
        Parsed and validated repository contract model.

    Raises:
        RepoContractError: If the file is missing, unreadable, invalid YAML,
            or fails schema validation.
    """
    contract_path = path if path is not None else DEFAULT_CONTRACT_PATH

    try:
        raw_text = contract_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RepoContractError(
            f"Could not read repository contract at {contract_path}: {exc}"
        ) from exc

    try:
        parsed_obj: object = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise RepoContractError(
            f"Malformed YAML in repository contract at {contract_path}: {exc}"
        ) from exc

    if not isinstance(parsed_obj, dict):
        actual_type = type(parsed_obj).__name__
        raise RepoContractError(
            "Malformed repository contract: expected a top-level mapping "
            f"in {contract_path}, got {actual_type}."
        )

    try:
        return RepoContract.model_validate(parsed_obj)
    except ValidationError as exc:
        summary = _validation_summary(exc)
        raise RepoContractError(
            f"Repository contract validation failed for {contract_path}: {summary}"
        ) from exc
