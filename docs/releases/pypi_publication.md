<!-- type: how-to -->
# PyPI Publication Flow

## Decision

As of 2026-04-12, this repository will publish package releases to PyPI using GitHub OIDC trusted publishing.
PyPI API token secrets are intentionally not used.

## Workflow

- Workflow file: `.github/workflows/publish-pypi.yml`
- Trigger: `push: tags: v*` (version tags starting with `v`)
- Build output: wheel and sdist via `uv build`
- Publish action: `pypa/gh-action-pypi-publish@release/v1` with `id-token: write`

## One-Time Maintainer Setup

1. Create or claim the `dependence-forecastability` project on PyPI.
2. Add a Trusted Publisher in PyPI with these values:
   - Owner: `AdamKrysztopa`
   - Repository: `dependence-forecastability`
   - Workflow: `publish-pypi.yml`
   - Environment: `pypi`
3. Protect the `pypi` environment in GitHub with required reviewers.

## TestPyPI Dry Run (R8)

Before the first production release, rehearse on TestPyPI. Requires a TestPyPI API token
stored as `TWINE_API_KEY` (or in `~/.pypirc`).

```bash
# 1. Build fresh artifacts
rm -rf dist/ build/
uv build
uv run twine check dist/*

# 2. Upload to TestPyPI
uv run twine upload --repository testpypi dist/*

# 3. Install from TestPyPI in a clean environment
python3.11 -m venv .venv-testpypi
source .venv-testpypi/bin/activate
pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  dependence-forecastability

# 4. Validate import and CLI entry point
python -c "import forecastability; print('import ok')"
forecastability --help

# 5. Clean up
deactivate
rm -rf .venv-testpypi
```

Inspect the project page at `https://test.pypi.org/project/dependence-forecastability/`
and confirm README renders, metadata is correct, and entry points are listed.

## Release-Time Flow

1. Bump package version in `pyproject.toml`.
2. Add release notes in `docs/releases/vX.Y.Z.md`.
3. Push tag `vX.Y.Z` — both `release.yml` and `publish-pypi.yml` trigger in parallel.
4. `release.yml` builds artifacts and creates the GitHub release with dist assets attached.
5. `publish-pypi.yml` builds artifacts independently and publishes them to PyPI via trusted publishing.

## Hotfix Process

A hotfix release follows the same publication flow as a normal release, but uses a
patch-version increment and a short targeted branch.

### When to issue a hotfix

- Installation fails from PyPI (import error, missing files, broken entry points)
- Critical bug in the deterministic core that produces wrong results silently
- Security issue identified post-release

### Hotfix steps

1. **Create a hotfix branch** from the affected release tag:
   ```bash
   git checkout -b hotfix/vX.Y.Z vX.Y.Z
   ```
2. **Apply the minimal fix.** Do not bundle unrelated changes.
3. **Bump the patch version** in `pyproject.toml` (e.g. `0.1.0` → `0.1.1`).
4. **Add a `[X.Y.Z]` CHANGELOG section** with a brief "Fixed" entry.
5. **Add release notes** in `docs/releases/vX.Y.Z.md`.
6. **Run the full local pipeline** (see `docs/releases/release_checklist.md`):
   ```bash
   uv run pytest -q -ra
   uv run ruff check .
   uv run ty check
   uv build
   uv run twine check dist/*
   ```
7. **Create a pull request** to `main` and merge after review.
8. **Push the hotfix tag** from `main`:
   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```
9. The `Release` workflow creates the GitHub Release and the `Publish to PyPI` workflow
   publishes the hotfix to PyPI.

> [!WARNING]
> Never push a hotfix tag from a feature or development branch. Always tag from `main`
> after the hotfix PR has been merged and verified.

### Post-hotfix checks

- [ ] `pip install dependence-forecastability==X.Y.Z` installs cleanly in a fresh venv
- [ ] `python -c "import forecastability; print(forecastability.__version__)"` returns `X.Y.Z`
- [ ] `forecastability --help` succeeds
- [ ] Close any related packaging bug issues on GitHub
- [ ] Update badges in `README.md` if the latest stable version changed

## Security Notes

- No long-lived `PYPI_API_TOKEN` is stored in repository secrets.
- Publishing is constrained to signed GitHub OIDC identity plus environment protections.
- Restricting to tag pushes only (not every branch push) reduces accidental package pushes from branch builds.