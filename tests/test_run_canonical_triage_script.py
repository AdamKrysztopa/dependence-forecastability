"""Focused tests for scripts/run_canonical_triage.py flags and gating behavior."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType


def _load_script_module() -> ModuleType:
    """Load scripts/run_canonical_triage.py as an importable module.

    Returns:
        Loaded module object.

    Raises:
        RuntimeError: If the module cannot be loaded from disk.
    """
    repo_root = Path(__file__).resolve().parents[1]
    file_path = repo_root / "scripts" / "run_canonical_triage.py"
    spec = spec_from_file_location("run_canonical_triage_script", file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module spec for {file_path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_args_defaults_disable_extensions() -> None:
    """Default script flags should keep bands on and extensions off."""
    module = _load_script_module()

    args = module._parse_args([])

    assert args.no_bands is False
    assert args.with_extensions is False


def test_parse_args_allows_with_extensions_flag() -> None:
    """with-extensions flag should be parsed as True when provided."""
    module = _load_script_module()

    args = module._parse_args(["--with-extensions"])

    assert args.no_bands is False
    assert args.with_extensions is True


def test_extensions_enabled_requires_flag_and_bands() -> None:
    """Extensions are enabled only when explicitly requested and bands are active."""
    module = _load_script_module()

    assert module._extensions_enabled(with_extensions=True, skip_bands=False) is True
    assert module._extensions_enabled(with_extensions=False, skip_bands=False) is False
    assert module._extensions_enabled(with_extensions=True, skip_bands=True) is False
