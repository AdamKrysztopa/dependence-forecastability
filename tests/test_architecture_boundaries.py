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

ROOT = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DOMAIN_STRUCTURAL_FORBIDDEN = frozenset(
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
        "statsmodels",
    ]
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


def test_domain_package_has_no_forbidden_imports() -> None:
    """Every module under src/forecastability/domain/ must be infra-clean."""
    domain_dir = ROOT / "src/forecastability/domain"
    py_files = [p for p in domain_dir.rglob("*.py") if p.name != "__init__.py"]
    assert py_files, "No .py files found under src/forecastability/domain/ — check the path"

    violations: list[str] = []
    for py_file in py_files:
        imported = _get_imports(py_file)
        bad = [pkg for pkg in imported if pkg in _DOMAIN_STRUCTURAL_FORBIDDEN]
        if bad:
            relative = str(py_file.relative_to(ROOT))
            violations.append(f"{relative}: {sorted(set(bad))}")

    assert not violations, (
        "domain/ modules must not import infrastructure or compute packages.\n"
        + "\n".join(violations)
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

_DIAGNOSTICS_FORBIDDEN_INFRA = frozenset(
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


def test_diagnostics_do_not_import_adapters() -> None:
    diagnostics_dir = ROOT / "src/forecastability/diagnostics"
    py_files = sorted(p for p in diagnostics_dir.glob("*.py") if p.name != "__init__.py")
    assert py_files, "No .py files found under src/forecastability/diagnostics/"

    violations: list[str] = []
    for py_file in py_files:
        full_imports = _get_full_imports(py_file)
        for dotted in full_imports:
            if dotted.startswith("forecastability.adapters"):
                relative = str(py_file.relative_to(ROOT))
                violations.append(f"{relative}: imports '{dotted}'")

    assert not violations, "diagnostics/ modules must not import from adapters/.\n" + "\n".join(
        violations
    )


def test_diagnostics_have_no_infra_imports() -> None:
    diagnostics_dir = ROOT / "src/forecastability/diagnostics"
    py_files = sorted(p for p in diagnostics_dir.glob("*.py") if p.name != "__init__.py")
    assert py_files, "No .py files found under src/forecastability/diagnostics/"

    violations: list[str] = []
    for py_file in py_files:
        imported = _get_imports(py_file)
        bad = [pkg for pkg in imported if pkg in _DIAGNOSTICS_FORBIDDEN_INFRA]
        if bad:
            relative = str(py_file.relative_to(ROOT))
            violations.append(f"{relative}: {sorted(set(bad))}")

    assert not violations, (
        "diagnostics/ modules must not import infrastructure or presentation packages.\n"
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
    # include agents/ sub-package (payloads/ and runtime/ subdirectories included)
    agents_dir = adapters_dir / "agents"
    if agents_dir.exists():
        utility_files += [p for p in agents_dir.rglob("*.py") if p.name != "__init__.py"]

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


# ---------------------------------------------------------------------------
# Rule 6 — LLM adapters must not import scripts/
# ---------------------------------------------------------------------------


def test_llm_adapters_do_not_import_scripts() -> None:
    """Agent adapters must not reach back into scripts/.

    This covers both adapters/llm/ (shim layer) and adapters/agents/runtime/
    (canonical implementations). The CLI showcase scripts are allowed to import
    from adapters/, but the reverse direction would couple library code to
    one-off entry points.
    """
    llm_dir = ROOT / "src/forecastability/adapters/llm"
    runtime_dir = ROOT / "src/forecastability/adapters/agents/runtime"
    py_files = sorted(p for p in llm_dir.glob("*.py") if p.name != "__init__.py")
    if runtime_dir.exists():
        py_files += sorted(p for p in runtime_dir.glob("*.py") if p.name != "__init__.py")
    assert py_files, (
        "No .py files found under src/forecastability/adapters/llm/ or adapters/agents/runtime/"
    )

    violations: list[str] = []
    for py_file in py_files:
        full_imports = _get_full_imports(py_file)
        for dotted in full_imports:
            if dotted == "scripts" or dotted.startswith("scripts."):
                relative = str(py_file.relative_to(ROOT))
                violations.append(f"{relative}: imports '{dotted}'")

    assert not violations, "adapters/llm/ modules must not import from scripts/.\n" + "\n".join(
        violations
    )


# ---------------------------------------------------------------------------
# Rule 7 — inner-ring (domain/, ports/) must not import outer first-party pkgs
#
# Tracked by docs/plan/implemented/v0_5_1_finish_hex_migration_plan.md (hex-migration
# completion). The domain leg is enforced once Slice 1 lands; the ports leg
# stays xfail until Slice 3 repoints port modules off the legacy packages.
# ---------------------------------------------------------------------------

# First-party OUTER packages the inner ring must not depend on. The inner ring
# may import only inward (domain -> domain; ports -> domain + ports) plus the
# allowed third-party numerics already governed by the rules above.
_OUTER_FIRST_PARTY_PACKAGES = frozenset(
    [
        "triage",
        "utils",
        "metrics",
        "pipeline",
        "reporting",
        "diagnostics",
        "kernels",
    ]
)


def _forbidden_first_party_imports(py_file: Path) -> list[str]:
    """Return outer first-party ``forecastability.<pkg>`` imports in a file."""
    bad: list[str] = []
    for dotted in _get_full_imports(py_file):
        parts = dotted.split(".")
        if (
            len(parts) >= 2
            and parts[0] == "forecastability"
            and parts[1] in (_OUTER_FIRST_PARTY_PACKAGES)
        ):
            bad.append(dotted)
    return bad


def test_domain_has_no_outer_first_party_imports() -> None:
    """domain/ modules must not import outer first-party packages.

    domain may import domain only; importing triage/utils/metrics/pipeline/
    reporting/diagnostics/kernels is an inner-ring violation.
    """
    domain_dir = ROOT / "src/forecastability/domain"
    py_files = [p for p in domain_dir.rglob("*.py") if p.name != "__init__.py"]
    assert py_files, "No .py files found under src/forecastability/domain/"

    violations: list[str] = []
    for py_file in py_files:
        bad = _forbidden_first_party_imports(py_file)
        if bad:
            relative = str(py_file.relative_to(ROOT))
            violations.append(f"{relative}: {sorted(set(bad))}")

    assert not violations, (
        "domain/ modules must not import outer first-party packages "
        f"({sorted(_OUTER_FIRST_PARTY_PACKAGES)}).\n" + "\n".join(violations)
    )


# Un-xfailed for the ports leg once Slice 3 repointed port modules off the
# legacy packages (triage/utils/metrics) onto domain + ports.
# See docs/plan/implemented/v0_5_1_finish_hex_migration_plan.md (hex-migration).
def test_ports_have_no_outer_first_party_imports() -> None:
    """ports/ modules must not import outer first-party packages.

    ports may import domain + ports only.
    """
    ports_dir = ROOT / "src/forecastability/ports"
    py_files = [p for p in ports_dir.rglob("*.py")]
    assert py_files, "No .py files found under src/forecastability/ports/"

    violations: list[str] = []
    for py_file in py_files:
        bad = _forbidden_first_party_imports(py_file)
        if bad:
            relative = str(py_file.relative_to(ROOT))
            violations.append(f"{relative}: {sorted(set(bad))}")

    assert not violations, (
        "ports/ modules must not import outer first-party packages "
        f"({sorted(_OUTER_FIRST_PARTY_PACKAGES)}).\n" + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# Rule 8 — no import cycles between architectural layers
#
# Tracked by docs/plan/implemented/v0_5_1_finish_hex_migration_plan.md (hex-migration
# completion). Expected to fail until the migration removes cross-layer cycles;
# will be un-xfailed when the layer graph becomes acyclic.
# ---------------------------------------------------------------------------

# Layer label -> top-level package directory under src/forecastability/.
_LAYER_PACKAGES = (
    "domain",
    "ports",
    "services",
    "use_cases",
    "api",
    "adapters",
    "triage",
    "utils",
    "metrics",
    "pipeline",
    "reporting",
    "diagnostics",
    "kernels",
)


def _layer_of(dotted: str) -> str | None:
    """Map a ``forecastability.<layer>....`` dotted import to its layer label."""
    parts = dotted.split(".")
    if len(parts) >= 2 and parts[0] == "forecastability" and parts[1] in _LAYER_PACKAGES:
        return parts[1]
    return None


def _build_layer_graph() -> dict[str, set[str]]:
    """Build a directed layer-to-layer import graph from AST imports."""
    pkg_root = ROOT / "src/forecastability"
    graph: dict[str, set[str]] = {layer: set() for layer in _LAYER_PACKAGES}
    for layer in _LAYER_PACKAGES:
        layer_dir = pkg_root / layer
        if not layer_dir.exists():
            continue
        for py_file in layer_dir.rglob("*.py"):
            for dotted in _get_full_imports(py_file):
                target = _layer_of(dotted)
                if target is not None and target != layer:
                    graph[layer].add(target)
    return graph


def _find_cycle(graph: dict[str, set[str]]) -> list[str] | None:
    """Return one detected cycle as a node list, or ``None`` if acyclic."""
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def _walk(node: str) -> list[str] | None:
        visiting.add(node)
        stack.append(node)
        for neighbour in sorted(graph.get(node, set())):
            if neighbour in visiting:
                cycle_start = stack.index(neighbour)
                return [*stack[cycle_start:], neighbour]
            if neighbour not in visited:
                found = _walk(neighbour)
                if found is not None:
                    return found
        visiting.discard(node)
        visited.add(node)
        stack.pop()
        return None

    for start in sorted(graph):
        if start not in visited:
            cycle = _walk(start)
            if cycle is not None:
                return cycle
    return None


def test_layer_graph_has_no_cycles() -> None:
    """The layer-level import graph must be acyclic."""
    graph = _build_layer_graph()
    cycle = _find_cycle(graph)
    assert cycle is None, "Import cycle detected between layers: " + " -> ".join(cycle or [])
