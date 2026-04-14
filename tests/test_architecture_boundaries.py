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

DOMAIN_MODULE_PATHS = [
    "src/forecastability/metrics/metrics.py",
    "src/forecastability/utils/validation.py",
    "src/forecastability/reporting/interpretation.py",
    "src/forecastability/utils/types.py",
    "src/forecastability/utils/config.py",
    "src/forecastability/metrics/scorers.py",
    "src/forecastability/diagnostics/cmi.py",
    "src/forecastability/diagnostics/surrogates.py",
    # AGT-026: additional domain-like modules added to coverage
    "src/forecastability/utils/aggregation.py",  # pure domain: numpy/pandas/scipy only
    # reporting.py: output transformation, not domain compute; no forbidden imports
    "src/forecastability/reporting/reporting.py",
    # C11: analyzer.py no longer imports matplotlib at module level
    "src/forecastability/pipeline/analyzer.py",
    # C15: triage domain models must not import infrastructure
    "src/forecastability/triage/models.py",
    "src/forecastability/triage/events.py",
    "src/forecastability/triage/batch_models.py",
    "src/forecastability/triage/result_bundle.py",
    "src/forecastability/triage/forecastability_profile.py",
    "src/forecastability/triage/readiness.py",
    "src/forecastability/triage/router.py",
    "src/forecastability/triage/complexity_band.py",
    "src/forecastability/triage/lyapunov.py",
    "src/forecastability/triage/spectral_predictability.py",
    "src/forecastability/triage/theoretical_limit_diagnostics.py",
    "src/forecastability/triage/predictive_info_learning_curve.py",
    # C15: TODO — comparison_report.py imports matplotlib; excluded until fixed
]

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


@pytest.mark.parametrize("module_path", DOMAIN_MODULE_PATHS)
def test_domain_modules_have_no_infra_imports(module_path: str) -> None:
    path = ROOT / module_path
    imported = _get_imports(path)
    violations = [pkg for pkg in imported if pkg in _DOMAIN_FORBIDDEN]
    assert not violations, (
        f"{module_path} imports forbidden infrastructure package(s): "
        f"{sorted(set(violations))}. "
        "Domain modules must not depend on infrastructure or presentation layers."
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

    assert not violations, "use_cases/ modules must not import from adapters/.\n" + "\n".join(
        violations
    )


# ---------------------------------------------------------------------------
# Rule 4 — services/ modules must not import adapters/ or matplotlib
# ---------------------------------------------------------------------------

_SERVICES_FORBIDDEN_INFRA = frozenset(
    ["pydantic_ai", "fastapi", "mcp", "httpx", "click", "typer", "matplotlib"]
)


def test_services_do_not_import_adapters() -> None:
    services_dir = ROOT / "src/forecastability/services"
    py_files = sorted(p for p in services_dir.glob("*.py") if p.name != "__init__.py")
    assert py_files, "No .py files found under src/forecastability/services/"

    violations: list[str] = []
    for py_file in py_files:
        full_imports = _get_full_imports(py_file)
        for dotted in full_imports:
            if dotted.startswith("forecastability.adapters"):
                relative = str(py_file.relative_to(ROOT))
                violations.append(f"{relative}: imports '{dotted}'")

    assert not violations, "services/ modules must not import from adapters/.\n" + "\n".join(
        violations
    )


def test_services_have_no_infra_imports() -> None:
    services_dir = ROOT / "src/forecastability/services"
    py_files = sorted(p for p in services_dir.glob("*.py") if p.name != "__init__.py")
    assert py_files, "No .py files found under src/forecastability/services/"

    violations: list[str] = []
    for py_file in py_files:
        imported = _get_imports(py_file)
        bad = [pkg for pkg in imported if pkg in _SERVICES_FORBIDDEN_INFRA]
        if bad:
            relative = str(py_file.relative_to(ROOT))
            violations.append(f"{relative}: {sorted(set(bad))}")

    assert not violations, (
        "services/ modules must not import infrastructure or presentation packages.\n"
        + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# Rule 5 — adapter utilities must not import primary transport adapters
# ---------------------------------------------------------------------------

_TRANSPORT_ADAPTER_NAMES = frozenset(["api", "cli", "dashboard", "mcp_server", "pydantic_ai_agent"])


def test_adapter_utilities_do_not_import_transport_adapters() -> None:
    """Shared adapter utilities must not reverse-couple to primary transport adapters.

    Primary transport adapters (api, cli, dashboard, mcp_server, pydantic_ai_agent)
    may use shared utilities, but shared utilities must not depend back on them.
    """
    adapters_dir = ROOT / "src/forecastability/adapters"
    utility_files: list[Path] = [
        p
        for p in adapters_dir.glob("*.py")
        if p.stem not in _TRANSPORT_ADAPTER_NAMES and p.name != "__init__.py"
    ]
    # include agents/ sub-package
    agents_dir = adapters_dir / "agents"
    if agents_dir.exists():
        utility_files += [p for p in agents_dir.glob("*.py") if p.name != "__init__.py"]

    violations: list[str] = []
    for py_file in utility_files:
        full_imports = _get_full_imports(py_file)
        for dotted in full_imports:
            parts = dotted.split(".")
            # e.g. forecastability.adapters.api  -> parts[2] = "api"
            if (
                len(parts) >= 3
                and parts[0] == "forecastability"
                and parts[1] == "adapters"
                and parts[2] in _TRANSPORT_ADAPTER_NAMES
            ):
                relative = str(py_file.relative_to(ROOT))
                violations.append(f"{relative}: imports '{dotted}'")

    assert not violations, (
        "Adapter utility modules must not import primary transport adapters "
        "(api, cli, dashboard, mcp_server, pydantic_ai_agent).\n" + "\n".join(violations)
    )
