"""Loader for the v0.3.3 routing-validation real-series panel manifest."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class RoutingValidationRealPanelCase(BaseModel):
    """One real-series case entry for routing validation."""

    model_config = ConfigDict(frozen=True)

    name: str
    source: Literal["bundled", "download"]
    path: str
    column: str
    expected_primary_families: list[str]
    expected_caution_flags: list[str] = Field(default_factory=list)
    license: str
    download_command: str | None = None

    @field_validator("expected_primary_families")
    @classmethod
    def _validate_expected_primary_families(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("expected_primary_families must be non-empty")
        return value

    @field_validator("license")
    @classmethod
    def _validate_license(cls, value: str) -> str:
        if value.strip() == "":
            raise ValueError("license must be non-empty")
        return value


class RoutingValidationRealPanelManifest(BaseModel):
    """Typed manifest for the routing-validation real-series panel."""

    model_config = ConfigDict(frozen=True)

    panel_version: str
    cases: list[RoutingValidationRealPanelCase]


def load_routing_validation_real_panel(
    manifest_path: str | Path,
) -> RoutingValidationRealPanelManifest:
    """Load and validate a real-panel manifest YAML file."""
    path = Path(manifest_path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if payload is None:
        payload = {}
    return RoutingValidationRealPanelManifest.model_validate(payload)


def load_default_routing_validation_real_panel(
    *,
    repo_root: Path | None = None,
) -> RoutingValidationRealPanelManifest:
    """Load the repository-default real panel manifest."""
    root = repo_root if repo_root is not None else Path.cwd()
    return load_routing_validation_real_panel(root / "configs/routing_validation_real_panel.yaml")


def resolve_case_path(
    case: RoutingValidationRealPanelCase,
    *,
    repo_root: Path | None = None,
) -> Path:
    """Resolve a case path relative to the repository root."""
    root = repo_root if repo_root is not None else Path.cwd()
    return (root / case.path).resolve()
