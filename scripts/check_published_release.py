"""Verify published release consistency on PyPI and GitHub releases.

This script is intended for post-publish workflow checks.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path
from typing import cast


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify published release on PyPI and GitHub.")
    parser.add_argument(
        "--project-name",
        default="dependence-forecastability",
        help="PyPI project name (default: dependence-forecastability).",
    )
    parser.add_argument(
        "--version",
        help="Expected package version. If omitted, read from pyproject.toml.",
    )
    parser.add_argument(
        "--tag",
        help="Expected git tag (default: v{version}).",
    )
    parser.add_argument(
        "--repository",
        help="GitHub repository in owner/repo format. Defaults to GITHUB_REPOSITORY.",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=5,
        help="Maximum retry attempts for PyPI visibility check (default: 5).",
    )
    parser.add_argument(
        "--initial-backoff-seconds",
        type=float,
        default=2.0,
        help="Initial exponential backoff interval in seconds (default: 2.0).",
    )
    parser.add_argument(
        "--repo-root",
        metavar="PATH",
        help="Repository root path (default: derived from script location).",
    )
    return parser.parse_args(argv)


def _repo_root_from_args(args: argparse.Namespace) -> Path:
    if args.repo_root:
        return Path(args.repo_root).resolve()
    return Path(__file__).resolve().parents[1]


def _read_version_from_pyproject(repo_root: Path) -> str:
    pyproject_path = repo_root / "pyproject.toml"
    raw = pyproject_path.read_bytes()
    data: object = tomllib.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("pyproject.toml is not a TOML mapping")
    project_section: object = data.get("project")
    if not isinstance(project_section, dict):
        raise ValueError("pyproject.toml missing [project] section")
    version: object = project_section.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError("pyproject.toml [project].version missing or invalid")
    return version


def _http_get_json(url: str, *, headers: dict[str, str] | None = None) -> object:
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def _check_pypi_version(
    project_name: str,
    version: str,
    max_attempts: int,
    initial_backoff: float,
) -> str:
    url = f"https://pypi.org/pypi/{project_name}/json"
    backoff = initial_backoff
    last_observed = "<unavailable>"
    last_error: str | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            payload = _http_get_json(url)
            if isinstance(payload, dict):
                payload_map = cast(dict[str, object], payload)
                info: object = payload_map.get("info")
                if isinstance(info, dict):
                    info_map = cast(dict[str, object], info)
                    observed: object = info_map.get("version")
                    if isinstance(observed, str) and observed:
                        last_observed = observed
                        if observed == version:
                            return observed
                        last_error = (
                            f"PyPI version mismatch on attempt {attempt}: "
                            f"observed '{observed}', expected '{version}'"
                        )
                    else:
                        last_error = f"PyPI payload missing info.version on attempt {attempt}"
                else:
                    last_error = f"PyPI payload missing info object on attempt {attempt}"
            else:
                last_error = f"PyPI response is not a JSON object on attempt {attempt}"
        except (
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
            UnicodeDecodeError,
        ) as exc:
            last_error = f"PyPI query failed on attempt {attempt}: {exc}"

        if attempt < max_attempts:
            time.sleep(backoff)
            backoff *= 2.0

    if last_error is None:
        last_error = "PyPI verification failed for unknown reasons"
    raise RuntimeError(f"{last_error}; last observed version: '{last_observed}'")


def _check_github_release(repository: str, tag: str) -> None:
    url = f"https://api.github.com/repos/{repository}/releases/tags/{tag}"
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        payload = _http_get_json(url, headers=headers)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise RuntimeError(
                f"GitHub release for tag '{tag}' not found in repository '{repository}'"
            ) from exc
        raise RuntimeError(
            f"GitHub release lookup failed for tag '{tag}' in '{repository}': HTTP {exc.code}"
        ) from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError(
            f"GitHub release lookup failed for tag '{tag}' in '{repository}': {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise RuntimeError("GitHub release API payload is not a JSON object")


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    repo_root = _repo_root_from_args(args)

    try:
        version = args.version or _read_version_from_pyproject(repo_root)
    except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        print(f"FAIL: Could not determine expected version: {exc}")
        raise SystemExit(1) from exc

    tag = args.tag or f"v{version}"
    repository = args.repository or os.environ.get("GITHUB_REPOSITORY", "")
    if not repository or "/" not in repository:
        print("FAIL: --repository (owner/repo) is required when GITHUB_REPOSITORY is unset")
        raise SystemExit(1)

    if args.max_attempts < 1:
        print("FAIL: --max-attempts must be >= 1")
        raise SystemExit(1)

    try:
        observed_version = _check_pypi_version(
            args.project_name,
            version,
            args.max_attempts,
            args.initial_backoff_seconds,
        )
        _check_github_release(repository, tag)
    except RuntimeError as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1) from exc

    print(
        "OK: Published release verified: "
        f"project={args.project_name}, "
        f"version={observed_version}, "
        f"repository={repository}, "
        f"tag={tag}"
    )


if __name__ == "__main__":
    main()
