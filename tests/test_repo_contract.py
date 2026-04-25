"""Tests for check_repo_contract and sync_repo_contract scripts."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

# Allow direct imports from scripts/ without installing the package.
_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import check_markdown_links  # noqa: E402
import check_readme_surface  # noqa: E402
import check_repo_contract  # noqa: E402
import sync_repo_contract  # noqa: E402

_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "repo_contract"
_BROKEN_DIR = _FIXTURES_DIR / "broken"
_FIXED_DIR = _FIXTURES_DIR / "fixed"


def _checker_args(repo_root: Path, extra: list[str] | None = None) -> list[str]:
    """Build CLI argument list for the checker pointing at a fixture tree.

    Args:
        repo_root: Path to the fixture repository root.
        extra: Additional CLI args (e.g. ['--release-tag', 'v0.3.4']).

    Returns:
        Argument list for check_repo_contract.main().
    """
    contract_path = repo_root / "repo_contract.yaml"
    args = [
        "--contract",
        str(contract_path),
        "--repo-root",
        str(repo_root),
    ]
    if extra:
        args.extend(extra)
    return args


def _fixer_args(repo_root: Path, *, write: bool = False) -> list[str]:
    """Build CLI argument list for the fixer pointing at a fixture tree.

    Args:
        repo_root: Path to the fixture repository root.
        write: If True, include --write flag.

    Returns:
        Argument list for sync_repo_contract.main().
    """
    contract_path = repo_root / "repo_contract.yaml"
    args = [
        "--contract",
        str(contract_path),
        "--repo-root",
        str(repo_root),
    ]
    if write:
        args.append("--write")
    return args


class TestCheckerOnBrokenFixture:
    """RTI-F01: checker fails on the broken fixture tree."""

    def test_checker_fails_on_broken_fixture(self) -> None:
        """Checker exits 1 when the broken fixture has contract violations."""
        with pytest.raises(SystemExit) as exc_info:
            check_repo_contract.main(_checker_args(_BROKEN_DIR))
        assert exc_info.value.code == 1


class TestCheckerOnFixedFixture:
    """RTI-F01: checker passes on the fixed fixture tree."""

    def test_checker_passes_on_fixed_fixture(self) -> None:
        """Checker exits 0 when the fixed fixture satisfies all checks."""
        # Should not raise; if it raises SystemExit(1) the test will fail.
        try:
            check_repo_contract.main(_checker_args(_FIXED_DIR))
        except SystemExit as exc:
            pytest.fail(f"Checker unexpectedly exited with code {exc.code}")


class TestFixerRepairsBrokenFixture:
    """RTI-F02: fixer repairs the broken fixture tree."""

    def test_fixer_repairs_broken_fixture(self, tmp_path: Path) -> None:
        """Fixer applied to broken/ brings the tree to contract compliance."""
        workdir = tmp_path / "broken"
        shutil.copytree(_BROKEN_DIR, workdir)

        # Create the missing release notes file (fixer does not create new files).
        release_dir = workdir / "docs" / "releases"
        release_dir.mkdir(parents=True, exist_ok=True)
        (release_dir / "v0.3.4.md").write_text("# v0.3.4 Release Notes\n", encoding="utf-8")

        sync_repo_contract.main(_fixer_args(workdir, write=True))

        # After fixer, checker should pass.
        try:
            check_repo_contract.main(_checker_args(workdir))
        except SystemExit as exc:
            pytest.fail(f"Checker failed after fixer with exit code {exc.code}")


class TestFixerIdempotent:
    """RTI-F02: fixer is idempotent."""

    def test_fixer_is_idempotent(self, tmp_path: Path) -> None:
        """Running fixer twice on the fixed/ tree produces no additional changes."""
        workdir = tmp_path / "fixed"
        shutil.copytree(_FIXED_DIR, workdir)

        sync_repo_contract.main(_fixer_args(workdir, write=True))

        # Capture content after first run.
        snapshot_after_first: dict[str, str] = {}
        for p in sorted(workdir.rglob("*")):
            if p.is_file():
                snapshot_after_first[str(p.relative_to(workdir))] = p.read_text(encoding="utf-8")

        sync_repo_contract.main(_fixer_args(workdir, write=True))

        # Content must be identical after second run.
        for rel_path, content_after_first in snapshot_after_first.items():
            content_after_second = (workdir / rel_path).read_text(encoding="utf-8")
            assert content_after_second == content_after_first, (
                f"Fixer changed {rel_path} on second run (not idempotent)"
            )


class TestReleaseModeTagMismatch:
    """RTI-F01: release mode rejects mismatched tags."""

    def test_release_mode_tag_mismatch(self) -> None:
        """Checker exits 1 when --release-tag does not match V_pkg."""
        with pytest.raises(SystemExit) as exc_info:
            check_repo_contract.main(_checker_args(_FIXED_DIR, extra=["--release-tag", "v9.9.9"]))
        assert exc_info.value.code == 1


class TestReleaseModeTagMatch:
    """RTI-F01: release mode accepts matching tags."""

    def test_release_mode_tag_match(self) -> None:
        """Checker exits 0 when --release-tag matches V_pkg."""
        try:
            check_repo_contract.main(_checker_args(_FIXED_DIR, extra=["--release-tag", "v0.3.4"]))
        except SystemExit as exc:
            pytest.fail(f"Checker unexpectedly failed with release tag: {exc.code}")


class TestMarkdownLinkChecker:
    """RTI-F03: markdown link checker behavior."""

    def test_checker_passes_on_valid_relative_link(self, tmp_path: Path) -> None:
        """Checker exits 0 when all repository-relative links resolve."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir(parents=True)
        target = docs_dir / "target.md"
        target.write_text("# Target\n", encoding="utf-8")
        readme = tmp_path / "README.md"
        readme.write_text("[see](docs/target.md)\n", encoding="utf-8")

        try:
            check_markdown_links.main(["--repo-root", str(tmp_path)])
        except SystemExit as exc:
            pytest.fail(f"Markdown link checker unexpectedly exited with code {exc.code}")

    def test_checker_fails_on_broken_link(self, tmp_path: Path) -> None:
        """Checker exits 1 when a repository-relative link is broken."""
        readme = tmp_path / "README.md"
        readme.write_text("[see](does_not_exist.md)\n", encoding="utf-8")

        with pytest.raises(SystemExit) as exc_info:
            check_markdown_links.main(["--repo-root", str(tmp_path)])
        assert exc_info.value.code == 1


class TestReadmeSurfaceChecker:
    """RTI-F04: README landing surface checker behavior."""

    def test_checker_passes_on_clean_readme(self, tmp_path: Path) -> None:
        """Checker exits 0 when README has no forbidden heading and labeled notebook refs."""
        readme = tmp_path / "README.md"
        readme.write_text(
            "\n".join(
                [
                    "## Install",
                    "See notebooks/demo.ipynb (supplementary)",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        try:
            check_readme_surface.main(["--repo-root", str(tmp_path)])
        except SystemExit as exc:
            pytest.fail(f"README surface checker unexpectedly exited with code {exc.code}")

    def test_checker_fails_on_forbidden_heading(self, tmp_path: Path) -> None:
        """Checker exits 1 when forbidden heading appears in README."""
        readme = tmp_path / "README.md"
        readme.write_text(
            "\n".join(["## Install", "## Notebook Path And Artifact Surfaces"]) + "\n",
            encoding="utf-8",
        )

        with pytest.raises(SystemExit) as exc_info:
            check_readme_surface.main(["--repo-root", str(tmp_path)])
        assert exc_info.value.code == 1

    def test_checker_fails_on_unlabeled_notebook_ref(self, tmp_path: Path) -> None:
        """Checker exits 1 when notebook refs are unlabeled outside code fences."""
        readme = tmp_path / "README.md"
        readme.write_text("See notebooks/foo.ipynb\n", encoding="utf-8")

        with pytest.raises(SystemExit) as exc_info:
            check_readme_surface.main(["--repo-root", str(tmp_path)])
        assert exc_info.value.code == 1
