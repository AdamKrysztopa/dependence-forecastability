"""Release-truth checker for the AMI repository contract.

Run in PR CI (local-only mode) or with --release-tag for release tag workflows.
Exit 0 if all checks pass; exit 1 with per-failure lines otherwise.
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path

# Allow running as a script from the repo root without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_contract import RepoContractError, load_repo_contract

_VERSION_HEADER_RE = re.compile(r"\*\*Current released version:\*\*\s+`(?P<version>[^`]+)`")
_LINK_RE_TEMPLATE = r"\]\({stale}(?P<anchor>#[^)]*)?\)"


def _repo_root_from_args(args: argparse.Namespace) -> Path:
    """Return the repository root path from parsed CLI arguments."""
    if args.repo_root:
        return Path(args.repo_root).resolve()
    return Path(__file__).resolve().parents[1]


def _read_pkg_version(repo_root: Path) -> str:
    """Extract the package version from pyproject.toml.

    Args:
        repo_root: Absolute path to the repository root.

    Returns:
        The version string from [project].version.

    Raises:
        SystemExit: If pyproject.toml is missing or lacks a version field.
    """
    pyproject_path = repo_root / "pyproject.toml"
    try:
        raw = pyproject_path.read_bytes()
    except OSError as exc:
        print(f"FAIL: Cannot read pyproject.toml: {exc}", file=sys.stderr)
        sys.exit(1)
    data: object = tomllib.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        print("FAIL: pyproject.toml is not a TOML mapping.", file=sys.stderr)
        sys.exit(1)
    project_section: object = data.get("project")
    if not isinstance(project_section, dict):
        print("FAIL: pyproject.toml has no [project] section.", file=sys.stderr)
        sys.exit(1)
    version: object = project_section.get("version")
    if not isinstance(version, str):
        print("FAIL: pyproject.toml [project].version is missing or not a string.", file=sys.stderr)
        sys.exit(1)
    return version


def _check_plan_headers(repo_root: Path, v_pkg: str) -> list[str]:
    """Check that all active plan files have a matching version header.

    Args:
        repo_root: Absolute path to the repository root.
        v_pkg: Expected version string from pyproject.toml.

    Returns:
        List of failure message strings (empty if all pass).
    """
    failures: list[str] = []
    plan_dir = repo_root / "docs" / "plan"
    if not plan_dir.is_dir():
        return failures
    for md_file in sorted(plan_dir.iterdir()):
        if md_file.is_dir() or md_file.suffix != ".md":
            continue
        text = md_file.read_text(encoding="utf-8")
        for line in text.splitlines():
            match = _VERSION_HEADER_RE.search(line)
            if match:
                found = match.group("version")
                if found != v_pkg:
                    rel = md_file.relative_to(repo_root)
                    failures.append(f"Plan header mismatch in {rel}: expected {v_pkg}, got {found}")
    return failures


def _check_release_notes(repo_root: Path, v_pkg: str) -> list[str]:
    """Assert that the release notes file exists for the given version.

    Args:
        repo_root: Absolute path to the repository root.
        v_pkg: Package version string.

    Returns:
        List of failure message strings (empty if pass).
    """
    release_file = repo_root / "docs" / "releases" / f"v{v_pkg}.md"
    if not release_file.exists():
        return [f"Release notes missing: docs/releases/v{v_pkg}.md does not exist"]
    return []


def _check_deprecated_paths(repo_root: Path, deprecated_paths: dict[str, str]) -> list[str]:
    """Scan docs/README/llms.txt for links to deprecated paths.

    Args:
        repo_root: Absolute path to the repository root.
        deprecated_paths: Mapping of stale → canonical paths from the contract.

    Returns:
        List of failure message strings (empty if all pass).
    """
    failures: list[str] = []
    targets: list[Path] = []
    readme = repo_root / "README.md"
    if readme.exists():
        targets.append(readme)
    llms_txt = repo_root / "llms.txt"
    if llms_txt.exists():
        targets.append(llms_txt)
    docs_dir = repo_root / "docs"
    if docs_dir.is_dir():
        targets.extend(sorted(docs_dir.rglob("*.md")))

    filtered_targets: list[Path] = []
    for target in targets:
        rel_posix = target.relative_to(repo_root).as_posix()
        if rel_posix.startswith("docs/plan/implemented/"):
            continue
        if rel_posix.startswith("tests/fixtures/"):
            continue
        filtered_targets.append(target)

    for stale_path, _canonical_path in deprecated_paths.items():
        pattern = re.compile(r"\]\(" + re.escape(stale_path) + r"(?:#[^)]*)?\)")
        for file_path in filtered_targets:
            text = file_path.read_text(encoding="utf-8")
            if pattern.search(text):
                rel = file_path.relative_to(repo_root)
                failures.append(f"Deprecated link to '{stale_path}' found in {rel}")
    return failures


def _check_dep_group_names(repo_root: Path, forbidden_names: list[str]) -> list[str]:
    """Check pyproject.toml for forbidden dependency-group names.

    Args:
        repo_root: Absolute path to the repository root.
        forbidden_names: Names that must not appear as [dependency-groups] keys.

    Returns:
        List of failure message strings (empty if all pass).
    """
    failures: list[str] = []
    pyproject_path = repo_root / "pyproject.toml"
    try:
        raw = pyproject_path.read_bytes()
    except OSError:
        return failures  # already caught in version extraction

    data: object = tomllib.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        return failures
    dep_groups: object = data.get("dependency-groups")
    if not isinstance(dep_groups, dict):
        return failures
    for forbidden in forbidden_names:
        if forbidden in dep_groups:
            failures.append(
                f"Forbidden dependency-group name '{forbidden}' found in pyproject.toml"
            )
    return failures


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments.

    Args:
        argv: Argument list (defaults to sys.argv).

    Returns:
        Parsed namespace.
    """
    parser = argparse.ArgumentParser(description="Check AMI repository contract truth assertions.")
    parser.add_argument(
        "--contract",
        metavar="PATH",
        help="Path to a custom repo_contract.yaml (default: repo root).",
    )
    parser.add_argument(
        "--repo-root",
        metavar="PATH",
        help="Path to the repository root (default: derived from script location).",
    )
    parser.add_argument(
        "--release-tag",
        metavar="TAG",
        help="Release tag to verify against V_pkg (e.g. v0.3.6).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Entry point for the release-truth checker.

    Args:
        argv: Optional argument list for testing; defaults to sys.argv[1:].
    """
    args = _parse_args(argv)
    repo_root = _repo_root_from_args(args)
    contract_path = Path(args.contract).resolve() if args.contract else None

    try:
        contract = load_repo_contract(contract_path)
    except RepoContractError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)

    v_pkg = _read_pkg_version(repo_root)

    failures: list[str] = []
    failures.extend(_check_plan_headers(repo_root, v_pkg))
    failures.extend(_check_release_notes(repo_root, v_pkg))
    failures.extend(_check_deprecated_paths(repo_root, dict(contract.deprecated_paths)))
    failures.extend(
        _check_dep_group_names(repo_root, contract.dependency_group_policy.forbidden_public_names)
    )

    if args.release_tag is not None:
        expected_tag = f"v{v_pkg}"
        if args.release_tag != expected_tag:
            failures.append(
                f"Release tag mismatch: provided '{args.release_tag}', expected '{expected_tag}'"
            )

    if failures:
        for msg in failures:
            print(f"FAIL: {msg}")
        print(f"{len(failures)} check(s) failed.")
        sys.exit(1)

    print("All repo contract checks passed.")


if __name__ == "__main__":
    main()
