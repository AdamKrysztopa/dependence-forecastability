<!-- type: how-to -->
<!-- Last verified for release 0.2.0 -->

# Automated Release Pipeline

This repository uses three GitHub Actions workflows that together form the full release
pipeline. [ci.yml](.github/workflows/ci.yml) runs on every push and PR to `main`.
[release.yml](.github/workflows/release.yml) and
[publish-pypi.yml](.github/workflows/publish-pypi.yml) both trigger on a version tag push
(`v*`) and run in parallel — one creates the GitHub release with attached distribution
artifacts, the other publishes to PyPI via OIDC trusted publishing.

---

## CI Workflow ([ci.yml](.github/workflows/ci.yml))

**Trigger:** `push` or `pull_request` targeting `main`.

**Concurrency:** group `ci-<workflow>-<ref>` with `cancel-in-progress: true`. A new push
cancels any in-progress run for the same branch or PR.

**Permissions:** `contents: read` only.

**Single job — `quality`** runs on `ubuntu-latest`, Python 3.11:

```bash
uv sync --dev --all-extras   # install all development and optional dependencies
uv run ruff check .          # lint
uv run ty check              # type check (Astral ty)
uv run pytest -q -ra         # full test suite
uv build                     # verify the package builds cleanly
```

All four steps must pass for the job to succeed. There are no separate jobs — the entire
quality gate is serialised within one runner.

---

## Release Workflow ([release.yml](.github/workflows/release.yml))

**Trigger:** `push: tags: v*`.

**Concurrency:** group `release-<ref>` with `cancel-in-progress: false` (never interrupt
a running release).

### Job `build-dist`

Checks out the repo, installs deps (`uv sync --dev --all-extras`), builds artifacts
(`uv build`), validates them (`uv run twine check dist/*`), and uploads them as the
`dist-artifacts` GitHub Actions artifact.

**Permissions:** `contents: read`.

### Job `publish-release`

Runs after `build-dist`. Downloads `dist-artifacts`, then:

- **If the tag already has a GitHub release** — edits the release notes from
  `docs/releases/<tag>.md` (if the file exists) and uploads the dist files.
- **If no GitHub release exists yet** — creates one. Uses `docs/releases/<tag>.md` as
  the release notes body if the file is present; otherwise falls back to
  `--generate-notes` (auto-generated from merged PRs).

**Permissions:** `contents: write` (required to create/edit releases and upload assets).

### `docs/releases/vX.Y.Z.md` convention

Create this file before pushing the tag. The workflow looks for it at the exact path
`docs/releases/${TAG_NAME}.md` where `TAG_NAME` is the full tag string (e.g. `v0.2.0`).
The file content becomes the GitHub release body verbatim. If the file is absent,
GitHub auto-generates notes from PR titles merged since the previous tag.

---

## Publish to PyPI Workflow ([publish-pypi.yml](.github/workflows/publish-pypi.yml))

**Trigger:** `push: tags: v*` — starts in parallel with `release.yml`.

**Concurrency:** group `publish-pypi-<ref>` with `cancel-in-progress: false`.

### Job `build-dist`

Runs the full quality gate again independently of `release.yml`:

```bash
uv sync --dev --all-extras
uv run ruff check .
uv run ty check
uv run pytest -q -ra
uv build
uv run twine check dist/*
```

Artifacts are uploaded as `pypi-dist-artifacts`. Building independently in each workflow
ensures PyPI never receives artifacts that bypassed the quality gate, even if the two
workflows diverge.

### Job `publish-pypi`

Runs after `build-dist`. Downloads `pypi-dist-artifacts` and publishes using
`pypa/gh-action-pypi-publish@release/v1`.

**Trusted publishing (OIDC)** — no long-lived `PYPI_API_TOKEN` secret is stored. GitHub
exchanges a short-lived OIDC token for a PyPI upload credential at runtime. The
`id-token: write` permission enables this exchange.

**Protected environment:** the job runs in the `pypi` GitHub environment. Any branch
protection rules or required reviewer gates configured on that environment apply before
the publish step executes.

---

## Pre-commit Hooks ([.pre-commit-config.yaml](.pre-commit-config.yaml))

Install once locally:

```bash
pre-commit install
```

Hooks that run automatically on `git commit`:

| Hook | Source | What it does |
|---|---|---|
| `check-toml` | `pre-commit-hooks` v6.0.0 | Validates `pyproject.toml` syntax |
| `end-of-file-fixer` | `pre-commit-hooks` v6.0.0 | Ensures files end with a newline |
| `trailing-whitespace` | `pre-commit-hooks` v6.0.0 | Strips trailing whitespace |
| `ruff` | `ruff-pre-commit` v0.11.0 | Lint with auto-fix |
| `ruff-format` | `ruff-pre-commit` v0.11.0 | Format (Black-compatible) |

> [!TIP]
> Run `pre-commit run --all-files` to apply all hooks to the entire repo without making
> a commit.

---

## Dependabot ([.github/dependabot.yml](.github/dependabot.yml))

| Ecosystem | Schedule | Labels | Commit prefix |
|---|---|---|---|
| `github-actions` | Weekly | `dependencies`, `github-actions` | `ci` |
| `pip` | Weekly | `dependencies`, `python` | `deps` |

Dependabot PRs appear with titles like `ci: bump actions/checkout from 4.1.0 to 4.2.0`
and `deps: bump ruff from 0.11.0 to 0.11.1`. Merge them routinely — CI runs on each PR.

---

## How to Do a Release

1. **Confirm CI is green on `main`** — check the Actions tab before proceeding.

2. **Bump the version** in `pyproject.toml` and `src/forecastability/__init__.py`:
   ```bash
   # edit pyproject.toml: version = "X.Y.Z"
   # edit src/forecastability/__init__.py: __version__ = "X.Y.Z"
   ```

3. **Update `CHANGELOG.md`** — add a `## [X.Y.Z]` section with release highlights.

4. **Create release notes** at `docs/releases/vX.Y.Z.md`. This file becomes the body
   of the GitHub release. If absent, notes are auto-generated from PR titles.

5. **Run a local smoke check:**
   ```bash
   uv build
   uv run twine check dist/*
   ```

6. **Commit and push to `main`, then wait for CI green:**
   ```bash
   git add pyproject.toml src/forecastability/__init__.py CHANGELOG.md \
           docs/releases/vX.Y.Z.md
   git commit -m "chore: release vX.Y.Z"
   git push
   ```

7. **Tag and push:**
   ```bash
   git tag vX.Y.Z
   git push --tags
   ```

8. **`release.yml` and `publish-pypi.yml` trigger in parallel.** Each builds
   independently, then:
   - `release.yml` creates the GitHub release with the dist assets attached.
   - `publish-pypi.yml` publishes the wheel and sdist to PyPI.

9. **Verify:**
   - GitHub: `https://github.com/AdamKrysztopa/dependence-forecastability/releases/tag/vX.Y.Z`
   - PyPI: `https://pypi.org/project/dependence-forecastability/X.Y.Z/`
   - Quick install check: `pip install dependence-forecastability==X.Y.Z`

---

## One-Time Setup: PyPI Trusted Publishing

These steps are required once per repository and are prerequisites for
`publish-pypi.yml` to succeed. Full details in [pypi_publication.md](pypi_publication.md).

1. **Claim the project on PyPI** — create or verify ownership of
   `dependence-forecastability` at `https://pypi.org`.

2. **Add a Trusted Publisher entry on PyPI** with these exact values:

   | Field | Value |
   |---|---|
   | Owner | `AdamKrysztopa` |
   | Repository | `dependence-forecastability` |
   | Workflow | `publish-pypi.yml` |
   | Environment | `pypi` |

3. **Create the `pypi` protected environment on GitHub** — go to
   *Settings → Environments → New environment*, name it `pypi`, and add any required
   reviewer rules.

---

## GitHub UI Actions (Manual)

These cannot be expressed in workflow files and must be configured via the GitHub web UI:

| Action | Location |
|---|---|
| Branch protection on `main` (require CI, no force-push) | *Settings → Branches* |
| Repository topics / description | *About* section on the repo home page |
| `pypi` environment protection rules (required reviewers, wait timer) | *Settings → Environments → pypi* |

---

## Troubleshooting Quick Reference

| Symptom | Where to look |
|---|---|
| Lint or type-check fails in CI | [ci.yml](.github/workflows/ci.yml) run logs → `Lint with ruff` / `Type check with ty` step |
| Tests fail in CI | ci.yml logs → `Run test suite` step; reproduce locally with `uv run pytest -q -ra` |
| PyPI publish fails (403 / OIDC error) | Check Trusted Publisher config on PyPI matches `publish-pypi.yml` exactly (owner, repo, workflow file name, environment name) |
| PyPI publish fails (artifact validation) | ci.yml / publish-pypi.yml logs → `Validate artifacts`; reproduce with `uv run twine check dist/*` |
| GitHub release not created | release.yml logs → `publish-release` job; confirm `docs/releases/vX.Y.Z.md` path matches the tag exactly |
| Dependabot PR fails CI | Check if the version bump introduced a breaking change; review the specific failing step in ci.yml |
| Pre-commit blocks commit | Run `pre-commit run --all-files` to see all failures; ruff auto-fixes lint issues |
