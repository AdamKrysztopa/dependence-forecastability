<!-- type: how-to -->
# PyPI Publication Flow

## Decision

As of 2026-04-12, this repository will publish package releases to PyPI using GitHub OIDC trusted publishing.
PyPI API token secrets are intentionally not used.

## Workflow

- Workflow file: `.github/workflows/publish-pypi.yml`
- Trigger: `release.published` events for version tags that start with `v`
- Build output: wheel and sdist from `python -m build`
- Publish action: `pypa/gh-action-pypi-publish@release/v1` with `id-token: write`

## One-Time Maintainer Setup

1. Create or claim the `forecastability` project on PyPI.
2. Add a Trusted Publisher in PyPI with these values:
   - Owner: `AdamKrysztopa`
   - Repository: `dependence-forecastability`
   - Workflow: `publish-pypi.yml`
   - Environment: `pypi`
3. Protect the `pypi` environment in GitHub with required reviewers.

## Release-Time Flow

1. Bump package version in `pyproject.toml`.
2. Add release notes in `docs/releases/vX.Y.Z.md`.
3. Push tag `vX.Y.Z`.
4. `Release` workflow creates or updates the GitHub release and attaches artifacts.
5. `Publish to PyPI` workflow publishes the same distributions to PyPI.

## Security Notes

- No long-lived `PYPI_API_TOKEN` is stored in repository secrets.
- Publishing is constrained to signed GitHub OIDC identity plus environment protections.
- Restricting to release publication reduces accidental package pushes from branch builds.