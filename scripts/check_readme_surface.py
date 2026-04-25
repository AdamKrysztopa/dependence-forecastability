"""Check README landing surface rules for release truth integrity."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Allow running as a script from the repo root without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent))

_FORBIDDEN_HEADING = "## Notebook Path And Artifact Surfaces"
_NOTEBOOK_LABEL_PATTERN = re.compile(r"\b(supplementary|transitional)\b", re.IGNORECASE)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments.

    Args:
        argv: Argument list (defaults to sys.argv).

    Returns:
        Parsed namespace.
    """
    parser = argparse.ArgumentParser(description="Check root README landing surface rules.")
    parser.add_argument(
        "--repo-root",
        metavar="PATH",
        help="Path to repository root (default: derived from script location).",
    )
    return parser.parse_args(argv)


def _repo_root_from_args(args: argparse.Namespace) -> Path:
    """Return repository root from parsed args."""
    if args.repo_root:
        return Path(args.repo_root).resolve()
    return Path(__file__).resolve().parents[1]


def _check_readme(readme_path: Path, repo_root: Path) -> list[str]:
    """Return FAIL lines for README surface violations."""
    failures: list[str] = []
    in_code_fence = False

    lines = readme_path.read_text(encoding="utf-8").splitlines()
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()

        if stripped.startswith("```"):
            in_code_fence = not in_code_fence
            continue

        if stripped == _FORBIDDEN_HEADING:
            rel = readme_path.relative_to(repo_root).as_posix()
            failures.append(f"FAIL: {rel}:{line_number}: forbidden heading: {_FORBIDDEN_HEADING}")

        if not in_code_fence and "notebooks/" in line:
            if _NOTEBOOK_LABEL_PATTERN.search(line) is None:
                rel = readme_path.relative_to(repo_root).as_posix()
                failures.append(
                    "FAIL: "
                    f"{rel}:{line_number}: "
                    "notebook reference without supplementary/transitional label"
                )

    return failures


def main(argv: list[str] | None = None) -> None:
    """Run README surface checks and exit non-zero on violations.

    Args:
        argv: Optional argument list for testing; defaults to sys.argv[1:].
    """
    args = _parse_args(argv)
    repo_root = _repo_root_from_args(args)
    readme_path = repo_root / "README.md"

    if not readme_path.exists():
        print("FAIL: README.md:1: missing README.md")
        raise SystemExit(1)

    failures = _check_readme(readme_path, repo_root)
    if failures:
        for line in failures:
            print(line)
        raise SystemExit(1)

    print("OK: README surface checks passed.")


if __name__ == "__main__":
    main()
