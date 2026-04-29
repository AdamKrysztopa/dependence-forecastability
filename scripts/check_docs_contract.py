"""Docs contract check for the forecastability repository.

Usage:
    uv run python scripts/check_docs_contract.py                    # run all checks
    uv run python scripts/check_docs_contract.py --import-contract
    uv run python scripts/check_docs_contract.py --version-coherence
    uv run python scripts/check_docs_contract.py --terminology
    uv run python scripts/check_docs_contract.py --plan-lifecycle
    uv run python scripts/check_docs_contract.py --no-framework-imports
    uv run python scripts/check_docs_contract.py --root-path-pinned
    uv run python scripts/check_docs_contract.py --version-consistent
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

PASS_SYM = "\u2713"
FAIL_SYM = "\u2717"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REDIRECT_STUB_RE = re.compile(
    r"^<!--\s*type:\s*reference\s*-->[\r\n]+#\s+Moved",
    re.MULTILINE,
)


def _is_redirect_stub(path: Path) -> bool:
    """Return True if *path* is a redirect stub (moved-doc placeholder)."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return bool(_REDIRECT_STUB_RE.match(text.lstrip()))


def _report(label: str, *, ok: bool) -> bool:
    sym = PASS_SYM if ok else FAIL_SYM
    print(f"[{sym}] {label}")
    return ok


# ---------------------------------------------------------------------------
# Check 1 — import-contract
# ---------------------------------------------------------------------------


def check_import_contract() -> bool:
    """Verify docs/public_api.md exists, is non-empty, and mentions forecastability."""
    print("import-contract:")
    public_api = REPO_ROOT / "docs" / "public_api.md"
    exists = public_api.is_file()
    if not _report(f"docs/public_api.md exists: {public_api}", ok=exists):
        return False
    text = public_api.read_text(encoding="utf-8", errors="replace")
    non_empty = len(text.strip()) > 0
    _report("docs/public_api.md is non-empty", ok=non_empty)
    mentions = "forecastability" in text
    _report("docs/public_api.md mentions 'forecastability'", ok=mentions)
    return non_empty and mentions


# ---------------------------------------------------------------------------
# Check 2 — version-coherence
# ---------------------------------------------------------------------------


def _parse_pyproject_version() -> str | None:
    """Extract version string from pyproject.toml."""
    pyproject = REPO_ROOT / "pyproject.toml"
    if not pyproject.is_file():
        return None
    text = pyproject.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return m.group(1) if m else None


def _parse_init_version() -> str | None:
    """Extract __version__ from src/forecastability/__init__.py if present."""
    init_path = REPO_ROOT / "src" / "forecastability" / "__init__.py"
    if not init_path.is_file():
        return None
    text = init_path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    return m.group(1) if m else None


def check_version_coherence() -> bool:
    """Verify the package version appears in CHANGELOG.md and matches __init__."""
    print("version-coherence:")
    version = _parse_pyproject_version()
    if version is None:
        _report("pyproject.toml version parsed", ok=False)
        return False
    _report(f"pyproject.toml version parsed: {version}", ok=True)

    changelog = REPO_ROOT / "CHANGELOG.md"
    if not changelog.is_file():
        _report("CHANGELOG.md exists", ok=False)
        return False
    changelog_text = changelog.read_text(encoding="utf-8", errors="replace")
    in_changelog = version in changelog_text
    _report(f"version {version!r} appears in CHANGELOG.md", ok=in_changelog)

    init_version = _parse_init_version()
    if init_version is not None:
        matches = init_version == version
        _report(
            f"__init__.__version__ {init_version!r} matches pyproject {version!r}",
            ok=matches,
        )
        return in_changelog and matches

    return in_changelog


# ---------------------------------------------------------------------------
# Check 3 — terminology
# ---------------------------------------------------------------------------

_FORBIDDEN_TERMS: list[str] = [
    "model zoo",
    "model-training framework",
    "forecasting framework",
    "fit_darts",
    "fit_mlforecast",
    "to_darts_spec",
    "to_mlforecast_spec",
    "forecast prep spec",
    "prep payload",
    "model handoff struct",
]

# Directories that are always excluded from the terminology scan.
_TERMINOLOGY_EXCLUDE_GLOBS = [
    "docs/recipes",
    "docs/archive",
    "docs/plan",
    "CHANGELOG.md",
]


def _is_excluded_terminology(path: Path, repo_root: Path) -> bool:
    """Return True if *path* should be skipped in the terminology scan."""
    rel = str(path.relative_to(repo_root)).replace("\\", "/")
    for excl in _TERMINOLOGY_EXCLUDE_GLOBS:
        if rel == excl or rel.startswith(excl + "/"):
            return True
    # Also skip the wording_policy.md itself (it defines the forbidden terms).
    if rel == "docs/wording_policy.md":
        return True
    return False


def _collect_terminology_targets(repo_root: Path) -> list[Path]:
    """Gather files to scan for forbidden terminology."""
    targets: list[Path] = []
    # README.md at root
    readme = repo_root / "README.md"
    if readme.is_file():
        targets.append(readme)
    # docs/**/*.md (excluding exempt subdirs)
    for p in sorted((repo_root / "docs").rglob("*.md")):
        if not _is_excluded_terminology(p, repo_root):
            targets.append(p)
    # examples/**/*.py and examples/**/*.md
    for p in sorted((repo_root / "examples").rglob("*")):
        if p.suffix in {".py", ".md"} and p.is_file():
            if not _is_excluded_terminology(p, repo_root):
                targets.append(p)
    return targets


def check_terminology() -> bool:
    """Scan target files for forbidden alternate terms."""
    print("terminology:")
    targets = _collect_terminology_targets(REPO_ROOT)
    violations: list[str] = []
    for path in targets:
        if _is_redirect_stub(path):
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        rel = str(path.relative_to(REPO_ROOT))
        for lineno, line in enumerate(lines, start=1):
            for term in _FORBIDDEN_TERMS:
                if term.lower() in line.lower():
                    violations.append(f"  {rel}:{lineno}: forbidden term {term!r}: {line.rstrip()}")
    if violations:
        for v in violations:
            print(v)
        _report(f"No forbidden terminology found ({len(violations)} violations)", ok=False)
        return False
    _report(f"No forbidden terminology found in {len(targets)} files", ok=True)
    return True


# ---------------------------------------------------------------------------
# Check 4 — plan-lifecycle
# ---------------------------------------------------------------------------

_ACTIVE_PLAN = "docs/plan/implemented/v0_4_0_examples_repo_split_ultimate_plan.md"


def check_plan_lifecycle() -> bool:
    """Verify the active v0.4.0 plan document exists."""
    print("plan-lifecycle:")
    plan_path = REPO_ROOT / _ACTIVE_PLAN
    exists = plan_path.is_file()
    _report(f"Active plan exists: {_ACTIVE_PLAN}", ok=exists)
    return exists


# ---------------------------------------------------------------------------
# Check 5 — no-framework-imports
# ---------------------------------------------------------------------------

_FRAMEWORK_IMPORT_RE = re.compile(r"^\s*(import|from)\s+(darts|mlforecast|statsforecast|nixtla)\b")

_FRAMEWORK_SCAN_DIRS = ["src/forecastability", "examples", "scripts", "tests"]

_FRAMEWORK_EXCLUDE_GLOBS = [
    "docs/recipes",
    "docs/archive",
    "docs/plan/aux_documents",
    "CHANGELOG.md",
]


def _is_excluded_framework(path: Path, repo_root: Path) -> bool:
    rel = str(path.relative_to(repo_root)).replace("\\", "/")
    for excl in _FRAMEWORK_EXCLUDE_GLOBS:
        if rel == excl or rel.startswith(excl + "/"):
            return True
    return False


def check_no_framework_imports() -> bool:
    """Scan src/, examples/, scripts/, and tests/ for forbidden framework imports."""
    print("no-framework-imports:")
    violations: list[str] = []
    scanned = 0
    for scan_dir in _FRAMEWORK_SCAN_DIRS:
        base = REPO_ROOT / scan_dir
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            if _is_excluded_framework(path, REPO_ROOT):
                continue
            scanned += 1
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            rel = str(path.relative_to(REPO_ROOT))
            for lineno, line in enumerate(lines, start=1):
                if _FRAMEWORK_IMPORT_RE.match(line):
                    violations.append(
                        f"  {rel}:{lineno}: forbidden framework import: {line.rstrip()}"
                    )
    if violations:
        for v in violations:
            print(v)
        _report(
            f"No forbidden framework imports found"
            f" ({len(violations)} violations in {scanned} files)",
            ok=False,
        )
        return False
    _report(f"No forbidden framework imports in {scanned} files", ok=True)
    return True


# ---------------------------------------------------------------------------
# Check 6 — root-path-pinned
# ---------------------------------------------------------------------------

_PINNED_DOCS = [
    "docs/quickstart.md",
    "docs/public_api.md",
]


def check_root_path_pinned() -> bool:
    """Verify pinned root docs exist and are not redirect stubs."""
    print("root-path-pinned:")
    all_ok = True
    for rel in _PINNED_DOCS:
        path = REPO_ROOT / rel
        if not path.is_file():
            _report(f"{rel}: pinned root doc missing or stubbed", ok=False)
            all_ok = False
        elif _is_redirect_stub(path):
            _report(f"{rel}: pinned root doc missing or stubbed (is a redirect stub)", ok=False)
            all_ok = False
        else:
            _report(f"{rel}: present and not a stub", ok=True)
    return all_ok


# ---------------------------------------------------------------------------
# Check 7 — version-consistent
# ---------------------------------------------------------------------------

_CITATION_VERSION_RE = re.compile(r'^version:\s*"([^"]+)"', re.MULTILINE)
_INIT_VERSION_RE = re.compile(r'^__version__\s*=\s*"([^"]+)"', re.MULTILINE)


def check_version_consistent() -> bool:
    """Verify version is identical across pyproject.toml, CITATION.cff, and __init__.py."""
    print("version-consistent:")
    all_ok = True

    # --- pyproject.toml (authoritative source) ---
    pyproject_path = REPO_ROOT / "pyproject.toml"
    if not pyproject_path.is_file():
        _report("pyproject.toml exists", ok=False)
        return False
    with pyproject_path.open("rb") as fh:
        pyproject_data = tomllib.load(fh)
    canonical: str | None = pyproject_data.get("project", {}).get("version")
    if canonical is None:
        _report("pyproject.toml [project].version parsed", ok=False)
        return False
    _report(f"pyproject.toml version: {canonical!r}", ok=True)

    # --- CITATION.cff ---
    citation_path = REPO_ROOT / "CITATION.cff"
    if not citation_path.is_file():
        _report("CITATION.cff exists", ok=False)
        all_ok = False
    else:
        citation_text = citation_path.read_text(encoding="utf-8", errors="replace")
        m = _CITATION_VERSION_RE.search(citation_text)
        if m is None:
            _report("CITATION.cff version parsed", ok=False)
            all_ok = False
        else:
            citation_version = m.group(1)
            match = citation_version == canonical
            _report(
                f"CITATION.cff version {citation_version!r} matches pyproject {canonical!r}",
                ok=match,
            )
            all_ok = all_ok and match

    # --- src/forecastability/__init__.py ---
    init_path = REPO_ROOT / "src" / "forecastability" / "__init__.py"
    if not init_path.is_file():
        _report("src/forecastability/__init__.py exists", ok=False)
        all_ok = False
    else:
        init_text = init_path.read_text(encoding="utf-8", errors="replace")
        m2 = _INIT_VERSION_RE.search(init_text)
        if m2 is None:
            _report("__init__.__version__ parsed", ok=False)
            all_ok = False
        else:
            init_version = m2.group(1)
            match2 = init_version == canonical
            _report(
                f"__init__.__version__ {init_version!r} matches pyproject {canonical!r}",
                ok=match2,
            )
            all_ok = all_ok and match2

    return all_ok


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

_CHECKS: dict[str, tuple[str, object]] = {
    "import-contract": ("import-contract", check_import_contract),
    "version-coherence": ("version-coherence", check_version_coherence),
    "terminology": ("terminology", check_terminology),
    "plan-lifecycle": ("plan-lifecycle", check_plan_lifecycle),
    "no-framework-imports": ("no-framework-imports", check_no_framework_imports),
    "root-path-pinned": ("root-path-pinned", check_root_path_pinned),
    "version-consistent": ("version-consistent", check_version_consistent),
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Docs contract checker for the forecastability repository.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    for key in _CHECKS:
        flag = f"--{key}"
        parser.add_argument(
            flag,
            action="store_true",
            default=False,
            help=f"Run only the {key} check.",
        )
    return parser


def main() -> None:
    """Entry point — parse flags and run the requested checks."""
    parser = _build_parser()
    args = parser.parse_args()

    # Determine which checks to run (all, or the selected subset).
    selected_keys = [key for key in _CHECKS if getattr(args, key.replace("-", "_"))]
    if not selected_keys:
        selected_keys = list(_CHECKS.keys())

    results: list[bool] = []
    for key in selected_keys:
        _, fn = _CHECKS[key]
        result = fn()  # type: ignore[operator]
        results.append(result)
        print()

    if all(results):
        print(f"[{PASS_SYM}] All docs contract checks passed.")
        sys.exit(0)
    else:
        failed = sum(1 for r in results if not r)
        print(f"[{FAIL_SYM}] {failed} of {len(results)} docs contract check(s) FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
