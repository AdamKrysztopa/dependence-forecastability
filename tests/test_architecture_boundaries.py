"""AST-level architecture boundary tests.

These tests parse source files with the `ast` module — no runtime imports of
heavy packages — and verify that hexagonal-architecture boundaries are
respected:

1. Domain modules must not import infrastructure packages.
2. ports/ modules must not import infrastructure packages.
3. use_cases/ modules must not import from adapters/.
"""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DOMAIN_MODULES = [
    "src/forecastability/metrics.py",
    "src/forecastability/validation.py",
    "src/forecastability/interpretation.py",
    "src/forecastability/types.py",
    "src/forecastability/config.py",
    "src/forecastability/scorers.py",
    "src/forecastability/cmi.py",
    "src/forecastability/surrogates.py",
    # AGT-026: additional domain-like modules added to coverage
    "src/forecastability/aggregation.py",  # pure domain: numpy/pandas/scipy only
    # reporting.py: output transformation, not domain compute; no forbidden imports
    "src/forecastability/reporting.py",
]

# Modules that are domain-like but have justified partial exceptions to the rule.
# Each entry maps module path → frozenset of additional allowed packages.
_DOMAIN_MODULE_EXEMPTIONS: dict[str, frozenset[str]] = {
    # analyzer.py contains a legacy .plot() method (pre-dates boundary rule).
    # The plotting concern should eventually migrate to plots.py; tracked separately.
    "src/forecastability/analyzer.py": frozenset({"matplotlib"}),
}

_DOMAIN_FORBIDDEN = frozenset(
    ["pydantic_ai", "fastapi", "mcp", "httpx", "click", "typer", "matplotlib"]
)

_PORTS_FORBIDDEN = frozenset(
    [
        "pydantic_ai",
        "fastapi",
        "mcp",
        "httpx",
        "click",
        "typer",
        "matplotlib",
        "sklearn",
        "scipy",
        "pandas",
        "statsmodels",
    ]
)


def _get_imports(path: Path) -> list[str]:
    """Return list of top-level package names imported in a Python source file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    tops: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                tops.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                tops.append(node.module.split(".")[0])
            # relative imports where node.module is None stay within the
            # package, so they are always acceptable
    return tops


def _get_full_imports(path: Path) -> list[str]:
    """Return full dotted module names for all imports in a Python source file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    fulls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                fulls.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                fulls.append(node.module)
    return fulls


# ---------------------------------------------------------------------------
# Rule 1 — Domain modules must not import infrastructure packages
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module_path", _DOMAIN_MODULES)
def test_domain_modules_have_no_infra_imports(module_path: str) -> None:
    path = ROOT / module_path
    imported = _get_imports(path)
    violations = [pkg for pkg in imported if pkg in _DOMAIN_FORBIDDEN]
    assert not violations, (
        f"{module_path} imports forbidden infrastructure package(s): "
        f"{sorted(set(violations))}. "
        "Domain modules must not depend on infrastructure or presentation layers."
    )


@pytest.mark.parametrize("module_path,extra_allowed", list(_DOMAIN_MODULE_EXEMPTIONS.items()))
def test_domain_modules_with_exemptions_have_no_other_infra_imports(
    module_path: str, extra_allowed: frozenset[str]
) -> None:
    """AGT-026: modules with justified exemptions must not import other forbidden packages."""
    path = ROOT / module_path
    imported = _get_imports(path)
    effective_forbidden = _DOMAIN_FORBIDDEN - extra_allowed
    violations = [pkg for pkg in imported if pkg in effective_forbidden]
    assert not violations, (
        f"{module_path} imports forbidden infrastructure package(s) "
        f"(allowed exemptions: {sorted(extra_allowed)}): "
        f"{sorted(set(violations))}."
    )


# ---------------------------------------------------------------------------
# Rule 2 — ports/ modules must not import infrastructure packages
# ---------------------------------------------------------------------------


def test_ports_have_no_infra_imports() -> None:
    ports_init = ROOT / "src/forecastability/ports/__init__.py"
    imported = _get_imports(ports_init)
    violations = [pkg for pkg in imported if pkg in _PORTS_FORBIDDEN]
    assert not violations, (
        f"src/forecastability/ports/__init__.py imports forbidden infrastructure "
        f"package(s): {sorted(set(violations))}. "
        "Port definitions must only depend on stdlib, numpy, pydantic, and the "
        "forecastability package itself."
    )


# ---------------------------------------------------------------------------
# Rule 3 — use_cases/ modules must not import from adapters/
# ---------------------------------------------------------------------------


def test_use_cases_do_not_import_adapters() -> None:
    use_cases_dir = ROOT / "src/forecastability/use_cases"
    py_files = sorted(use_cases_dir.glob("*.py"))
    assert py_files, "No .py files found under src/forecastability/use_cases/"

    violations: list[str] = []
    for py_file in py_files:
        full_imports = _get_full_imports(py_file)
        for dotted in full_imports:
            if dotted.startswith("forecastability.adapters"):
                relative = str(py_file.relative_to(ROOT))
                violations.append(f"{relative}: imports '{dotted}'")

    assert not violations, (
        "use_cases/ modules must not import from adapters/.\n"
        + "\n".join(violations)
    )
