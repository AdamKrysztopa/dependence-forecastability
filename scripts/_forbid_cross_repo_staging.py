#!/usr/bin/env python3
"""forbid-cross-repo-staging — pre-commit hook (EX-LOCAL-01).

Fails when the staging area in the core repo contains any path that resolves
outside the core repo's working tree. This catches the case where a contributor
accidentally ran `git add ../../forecastability-examples/...` from inside the
core checkout.

This scenario should not occur in normal use because `git add` inside one
checkout only stages files tracked by that repo's index. The hook is a
paranoia catch for shell aliases or editor integrations that might not
respect working-tree boundaries.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    # Resolve the root of the current git repo
    rc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if rc.returncode != 0:
        print("forbid-cross-repo-staging: could not determine repo root", file=sys.stderr)
        return 1

    repo_root = Path(rc.stdout.strip()).resolve()

    # List staged files (cached diff; includes new, modified, deleted)
    diff = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACDMRT"],
        capture_output=True,
        text=True,
    )
    if diff.returncode != 0:
        return 0  # nothing staged or git error — not our problem

    violations: list[str] = []
    for rel_path in diff.stdout.splitlines():
        abs_path = (repo_root / rel_path).resolve()
        try:
            abs_path.relative_to(repo_root)
        except ValueError:
            violations.append(rel_path)

    if violations:
        print(
            "forbid-cross-repo-staging: staged path(s) outside the core repo tree detected.",
            file=sys.stderr,
        )
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        print(
            "\nUnstage with: git restore --staged <file>",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
