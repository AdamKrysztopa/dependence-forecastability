"""Check repository-relative markdown links across repository surfaces.

Scans README.md, docs/**/*.md, and llms.txt for markdown links of the form
[text](target). For non-http(s), non-anchor targets, resolves links relative to
the containing file and reports missing targets.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Allow running as a script from the repo root without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent))

_LINK_PATTERN = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
_ENFORCED_DOC_FILES = {
    "docs/README.md",
    "docs/quickstart.md",
    "docs/public_api.md",
    "docs/maintenance/repository_contract.md",
}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments.

    Args:
        argv: Argument list (defaults to sys.argv).

    Returns:
        Parsed namespace.
    """
    parser = argparse.ArgumentParser(description="Check repo-relative markdown links.")
    parser.add_argument(
        "--repo-root",
        metavar="PATH",
        help="Path to repository root (default: derived from script location).",
    )
    parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Optional path to write JSON summary; stdout remains human-readable.",
    )
    return parser.parse_args(argv)


def _repo_root_from_args(args: argparse.Namespace) -> Path:
    """Return repository root from parsed args."""
    if args.repo_root:
        return Path(args.repo_root).resolve()
    return Path(__file__).resolve().parents[1]


def _should_skip_file(file_path: Path, repo_root: Path) -> bool:
    """Return True when file should be excluded from scanning."""
    rel = file_path.relative_to(repo_root)
    rel_posix = rel.as_posix()
    if rel_posix.startswith("docs/plan/implemented/"):
        return True
    if rel_posix.startswith("tests/fixtures/"):
        return True
    if rel_posix.startswith("docs/"):
        if rel_posix in _ENFORCED_DOC_FILES:
            return False
        if rel_posix.startswith("docs/releases/v") and rel_posix.endswith(".md"):
            return False
        return True
    return False


def _collect_scan_files(repo_root: Path) -> list[Path]:
    """Collect files included in markdown-link scanning."""
    files: list[Path] = []

    for root_file_name in ("README.md", "llms.txt"):
        root_file = repo_root / root_file_name
        if root_file.exists() and not _should_skip_file(root_file, repo_root):
            files.append(root_file)

    docs_dir = repo_root / "docs"
    if docs_dir.is_dir():
        for md_file in sorted(docs_dir.rglob("*.md")):
            if _should_skip_file(md_file, repo_root):
                continue
            files.append(md_file)

    return files


def _is_repo_relative_target(target: str) -> bool:
    """Return True if the markdown target is repository-relative for this check."""
    lowered = target.lower()
    if lowered.startswith("http://") or lowered.startswith("https://"):
        return False
    if lowered.startswith("mailto:"):
        return False
    if target.startswith("#"):
        return False
    return True


def _strip_anchor(target: str) -> str:
    """Strip optional anchor fragment from a markdown target."""
    return target.split("#", 1)[0]


def _is_placeholder_target(target: str) -> bool:
    """Return True for intentionally non-resolvable placeholder targets."""
    if "{" in target or "}" in target:
        return True
    if "<" in target or ">" in target:
        return True
    if "..." in target:
        return True
    return False


def _is_generated_artifact_target(target: str) -> bool:
    """Return True when a link points to runtime-generated artifact surfaces."""
    normalized = target.lstrip("./")
    while normalized.startswith("../"):
        normalized = normalized[3:]
    return normalized.startswith("outputs/")


def _resolve_link_target(file_path: Path, link_target: str, repo_root: Path) -> Path | None:
    """Resolve a link target against file-relative and repo-root-oriented forms."""
    primary = (file_path.parent / link_target).resolve()
    if primary.exists():
        return primary

    # Some docs use repository-root-oriented paths without a leading slash.
    stripped = link_target.lstrip("/")
    while stripped.startswith("../"):
        stripped = stripped[3:]
    if stripped.startswith("./"):
        stripped = stripped[2:]
    fallback = (repo_root / stripped).resolve()
    if fallback.exists():
        return fallback

    return None


def _scan_file(file_path: Path, repo_root: Path) -> tuple[int, list[dict[str, object]]]:
    """Scan one file and return checked-count plus broken-link entries."""
    checked = 0
    broken: list[dict[str, object]] = []
    text = file_path.read_text(encoding="utf-8")

    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in _LINK_PATTERN.finditer(line):
            target = match.group(2).strip()
            if not _is_repo_relative_target(target):
                continue

            link_target = _strip_anchor(target)
            if not link_target:
                continue
            if _is_placeholder_target(link_target):
                continue
            if _is_generated_artifact_target(link_target):
                continue

            checked += 1
            resolved = _resolve_link_target(file_path, link_target, repo_root)
            if resolved is None:
                broken.append(
                    {
                        "file": str(file_path.relative_to(repo_root).as_posix()),
                        "line": line_number,
                        "target": target,
                    }
                )

    return checked, broken


def main(argv: list[str] | None = None) -> None:
    """Run markdown link checks and exit non-zero on broken links.

    Args:
        argv: Optional argument list for testing; defaults to sys.argv[1:].
    """
    args = _parse_args(argv)
    repo_root = _repo_root_from_args(args)
    files = _collect_scan_files(repo_root)

    checked_total = 0
    broken_total: list[dict[str, object]] = []

    for file_path in files:
        checked, broken = _scan_file(file_path, repo_root)
        checked_total += checked
        broken_total.extend(broken)

    summary = {
        "checked": checked_total,
        "broken": broken_total,
    }

    for item in broken_total:
        print(f"FAIL: {item['file']}:{item['line']}: broken link: {item['target']}")

    if not broken_total:
        print(f"OK: {checked_total} links checked, 0 broken.")

    summary_json = json.dumps(summary, ensure_ascii=True)
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(summary_json + "\n", encoding="utf-8")
    else:
        print(summary_json)

    if broken_total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
