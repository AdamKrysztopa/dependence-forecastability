"""Tests for post-publish release verification script."""

from __future__ import annotations

import io
import json
import sys
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request

import pytest

# Allow direct imports from scripts/ without installing the package.
_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import check_published_release  # noqa: E402


class _MockResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> _MockResponse:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False


def test_main_passes_when_pypi_and_github_match(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "0.3.6"\n', encoding="utf-8")

    def _fake_urlopen(request: Request, timeout: int = 30) -> _MockResponse:
        url = request.full_url
        if "pypi.org" in url:
            return _MockResponse({"info": {"version": "0.3.6"}})
        if "api.github.com" in url:
            return _MockResponse({"tag_name": "v0.3.6"})
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(check_published_release.urllib.request, "urlopen", _fake_urlopen)

    check_published_release.main(
        [
            "--repo-root",
            str(tmp_path),
            "--repository",
            "owner/repo",
            "--max-attempts",
            "1",
        ]
    )


def test_main_fails_when_pypi_version_never_matches(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "0.3.6"\n', encoding="utf-8")

    def _fake_urlopen(request: Request, timeout: int = 30) -> _MockResponse:
        url = request.full_url
        if "pypi.org" in url:
            return _MockResponse({"info": {"version": "0.3.5"}})
        if "api.github.com" in url:
            return _MockResponse({"tag_name": "v0.3.6"})
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(check_published_release.urllib.request, "urlopen", _fake_urlopen)
    monkeypatch.setattr(check_published_release.time, "sleep", lambda _x: None)

    with pytest.raises(SystemExit) as exc_info:
        check_published_release.main(
            [
                "--repo-root",
                str(tmp_path),
                "--repository",
                "owner/repo",
                "--max-attempts",
                "2",
                "--initial-backoff-seconds",
                "0.01",
            ]
        )
    assert exc_info.value.code == 1


def test_main_fails_when_github_release_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "0.3.6"\n', encoding="utf-8")

    def _fake_urlopen(request: Request, timeout: int = 30) -> _MockResponse:
        url = request.full_url
        if "pypi.org" in url:
            return _MockResponse({"info": {"version": "0.3.6"}})
        if "api.github.com" in url:
            raise HTTPError(
                url=url,
                code=404,
                msg="Not Found",
                hdrs=Message(),
                fp=io.BytesIO(b""),
            )
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(check_published_release.urllib.request, "urlopen", _fake_urlopen)

    with pytest.raises(SystemExit) as exc_info:
        check_published_release.main(
            [
                "--repo-root",
                str(tmp_path),
                "--repository",
                "owner/repo",
                "--max-attempts",
                "1",
            ]
        )
    assert exc_info.value.code == 1
