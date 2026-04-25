"""Release-truth autofixer for the AMI repository contract.

Rewrites configured surfaces to bring the repository into contract compliance.
Dry-run by default; pass --write to apply changes.

Never edits: src/, tests/, *.json files, or docs/releases/.
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

_VERSION_HEADER_RE = re.compile(r"(\*\*Current released version:\*\*\s+`)[^`]+(`)")
_FORBIDDEN_PATHS_SUFFIXES = (".json",)
_FORBIDDEN_PATH_PREFIXES = ("src/", "tests/", "docs/releases/")


def _repo_root_from_args(args: argparse.Namespace) -> Path:
    """Return the repository root path from parsed CLI arguments."""
    if args.repo_root:
        return Path(args.repo_root).resolve()
    return Path(__file__).resolve().parents[1]


def _is_rewrite_protected(file_path: Path, repo_root: Path) -> bool:
    """Return True if the file must not be rewritten.

    Args:
        file_path: Absolute path to the candidate file.
        repo_root: Absolute path to the repository root.

    Returns:
        True if the file is protected from rewriting.
    """
    try:
        rel = str(file_path.relative_to(repo_root))
    except ValueError:
        return True
    for prefix in _FORBIDDEN_PATH_PREFIXES:
        if rel.startswith(prefix):
            return True
    for suffix in _FORBIDDEN_PATHS_SUFFIXES:
        if file_path.suffix == suffix:
            return True
    return False


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
        print(f"ERROR: Cannot read pyproject.toml: {exc}", file=sys.stderr)
        sys.exit(1)
    data: object = tomllib.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        print("ERROR: pyproject.toml is not a TOML mapping.", file=sys.stderr)
        sys.exit(1)
    project_section: object = data.get("project")
    if not isinstance(project_section, dict):
        print("ERROR: pyproject.toml has no [project] section.", file=sys.stderr)
        sys.exit(1)
    version: object = project_section.get("version")
    if not isinstance(version, str):
        print(
            "ERROR: pyproject.toml [project].version is missing or not a string.",
            file=sys.stderr,
        )
        sys.exit(1)
    return version


def _sync_plan_headers(repo_root: Path, v_pkg: str, *, write: bool) -> list[str]:
    """Sync version headers in active plan markdown files.

    Args:
        repo_root: Absolute path to the repository root.
        v_pkg: Target version string to insert.
        write: If True, apply changes; otherwise report only.

    Returns:
        List of rewrite message strings.
    """
    messages: list[str] = []
    plan_dir = repo_root / "docs" / "plan"
    if not plan_dir.is_dir():
        return messages
    for md_file in sorted(plan_dir.iterdir()):
        if md_file.is_dir() or md_file.suffix != ".md":
            continue
        if _is_rewrite_protected(md_file, repo_root):
            continue
        original = md_file.read_text(encoding="utf-8")
        updated = _VERSION_HEADER_RE.sub(rf"\g<1>{v_pkg}\g<2>", original)
        if updated != original:
            rel = md_file.relative_to(repo_root)
            msg = f"{rel}: plan version header → {v_pkg}"
            if write:
                md_file.write_text(updated, encoding="utf-8")
                messages.append(f"REWRITE: {msg}")
            else:
                messages.append(f"WOULD REWRITE: {msg}")
    return messages


def _collect_doc_targets(repo_root: Path) -> list[Path]:
    """Collect all markdown and text files eligible for link rewriting.

    Args:
        repo_root: Absolute path to the repository root.

    Returns:
        List of absolute file paths.
    """
    targets: list[Path] = []
    readme = repo_root / "README.md"
    if readme.exists():
        targets.append(readme)
    llms_txt = repo_root / "llms.txt"
    if llms_txt.exists():
        targets.append(llms_txt)
    docs_dir = repo_root / "docs"
    if docs_dir.is_dir():
        for p in sorted(docs_dir.rglob("*.md")):
            # Exclude implemented plans and release notes
            rel = str(p.relative_to(repo_root))
            if rel.startswith("docs/plan/implemented/"):
                continue
            if rel.startswith("docs/releases/"):
                continue
            targets.append(p)
    return targets


def _sync_deprecated_links(
    repo_root: Path,
    deprecated_paths: dict[str, str],
    *,
    write: bool,
) -> list[str]:
    """Replace deprecated link targets with canonical equivalents.

    Args:
        repo_root: Absolute path to the repository root.
        deprecated_paths: Mapping of stale → canonical path strings.
        write: If True, apply changes; otherwise report only.

    Returns:
        List of rewrite message strings.
    """
    messages: list[str] = []
    targets = _collect_doc_targets(repo_root)

    for stale_path, canonical_path in deprecated_paths.items():
        stale_escaped = re.escape(stale_path)
        pattern = re.compile(r"\](\(" + stale_escaped + r")(#[^)]*)?\)")

        for file_path in targets:
            if _is_rewrite_protected(file_path, repo_root):
                continue
            original = file_path.read_text(encoding="utf-8")

            def _replace(m: re.Match[str], _cp: str = canonical_path) -> str:
                anchor = m.group(2) or ""
                return f"]({_cp}{anchor})"

            updated = pattern.sub(_replace, original)
            if updated != original:
                rel = file_path.relative_to(repo_root)
                msg = f"{rel}: deprecated link '{stale_path}' → '{canonical_path}'"
                if write:
                    file_path.write_text(updated, encoding="utf-8")
                    messages.append(f"REWRITE: {msg}")
                else:
                    messages.append(f"WOULD REWRITE: {msg}")
    return messages


def _sync_forbidden_headings(
    repo_root: Path,
    forbidden_headings: list[str],
    *,
    write: bool,
) -> list[str]:
    """Remove forbidden headings from README.md.

    Args:
        repo_root: Absolute path to the repository root.
        forbidden_headings: Heading texts to remove (without leading ##).
        write: If True, apply changes; otherwise report only.

    Returns:
        List of rewrite message strings.
    """
    messages: list[str] = []
    readme = repo_root / "README.md"
    if not readme.exists():
        return messages

    original = readme.read_text(encoding="utf-8")
    updated = original
    for heading in forbidden_headings:
        escaped = re.escape(heading)
        pattern = re.compile(r"^#{1,6}\s+" + escaped + r"\s*$", re.MULTILINE)
        updated = pattern.sub("", updated)

    if updated != original:
        rel = readme.relative_to(repo_root)
        msg = f"{rel}: forbidden heading(s) removed"
        if write:
            readme.write_text(updated, encoding="utf-8")
            messages.append(f"REWRITE: {msg}")
        else:
            messages.append(f"WOULD REWRITE: {msg}")
    return messages


def _sync_dep_group_renames(
    repo_root: Path,
    rename_map: dict[str, str],
    *,
    write: bool,
) -> list[str]:
    """Rename dependency group keys in pyproject.toml.

    Args:
        repo_root: Absolute path to the repository root.
        rename_map: Mapping of old_name → new_name.
        write: If True, apply changes; otherwise report only.

    Returns:
        List of rewrite message strings.
    """
    messages: list[str] = []
    pyproject_path = repo_root / "pyproject.toml"
    if not pyproject_path.exists():
        return messages

    original = pyproject_path.read_text(encoding="utf-8")
    updated = original

    for old_name, new_name in rename_map.items():
        # Match the key at the start of a line inside [dependency-groups].
        # Pattern: key followed by " = [" (handles optional spaces).
        pattern = re.compile(
            r"(^\[dependency-groups\][^\[]*?)^" + re.escape(old_name) + r"(\s*=\s*\[)",
            re.MULTILINE | re.DOTALL,
        )
        # Use a line-level replacement to be safe.
        line_pattern = re.compile(
            r"^(" + re.escape(old_name) + r")(\s*=\s*\[)",
            re.MULTILINE,
        )
        # Only replace if we are inside [dependency-groups] context.
        if _is_inside_dep_groups(updated, old_name):
            new_updated = line_pattern.sub(lambda m, nn=new_name: nn + m.group(2), updated)
            if new_updated != updated:
                updated = new_updated
                rel = pyproject_path.relative_to(repo_root)
                msg = f"{rel}: dependency-group rename '{old_name}' → '{new_name}'"
                if write:
                    messages.append(f"REWRITE: {msg}")
                else:
                    messages.append(f"WOULD REWRITE: {msg}")
        _ = pattern  # suppress unused-variable lint

    if write and updated != original:
        pyproject_path.write_text(updated, encoding="utf-8")
    return messages


def _is_inside_dep_groups(content: str, key: str) -> bool:
    """Return True if key appears as a top-level entry under [dependency-groups].

    Args:
        content: Full text of pyproject.toml.
        key: Dependency group key to search for.

    Returns:
        True if the key exists under [dependency-groups].
    """
    in_section = False
    key_pattern = re.compile(r"^" + re.escape(key) + r"\s*=\s*\[")
    section_pattern = re.compile(r"^\[dependency-groups\]")
    other_section_pattern = re.compile(r"^\[[^\]]+\]")
    for line in content.splitlines():
        if section_pattern.match(line):
            in_section = True
            continue
        if in_section and other_section_pattern.match(line) and not section_pattern.match(line):
            in_section = False
        if in_section and key_pattern.match(line):
            return True
    return False


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments.

    Args:
        argv: Argument list (defaults to sys.argv).

    Returns:
        Parsed namespace.
    """
    parser = argparse.ArgumentParser(description="Sync AMI repository surfaces to contract truth.")
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
        "--write",
        action="store_true",
        help="Apply rewrites; without this flag the tool is a dry-run.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Entry point for the release-truth autofixer.

    Args:
        argv: Optional argument list for testing; defaults to sys.argv[1:].
    """
    args = _parse_args(argv)
    repo_root = _repo_root_from_args(args)
    contract_path = Path(args.contract).resolve() if args.contract else None
    write = args.write

    try:
        contract = load_repo_contract(contract_path)
    except RepoContractError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    v_pkg = _read_pkg_version(repo_root)

    messages: list[str] = []
    messages.extend(_sync_plan_headers(repo_root, v_pkg, write=write))
    messages.extend(_sync_deprecated_links(repo_root, dict(contract.deprecated_paths), write=write))
    messages.extend(
        _sync_forbidden_headings(
            repo_root,
            contract.landing_surface.forbidden_root_headings,
            write=write,
        )
    )
    messages.extend(
        _sync_dep_group_renames(
            repo_root,
            dict(contract.dependency_group_policy.rename_map),
            write=write,
        )
    )

    for msg in messages:
        print(msg)


if __name__ == "__main__":
    main()
