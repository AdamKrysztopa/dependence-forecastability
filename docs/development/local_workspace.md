<!-- type: how-to -->

# Local Two-Repo Development Workflow

This guide covers how to work on [`dependence-forecastability`][core] and
[`forecastability-examples`][sibling] simultaneously from a single parent
workspace folder. This is the **EX-LOCAL-01** setup from the
[v0.4.0 plan](../plan/v0_4_0_examples_repo_split_ultimate_plan.md).

[core]: https://github.com/AdamKrysztopa/dependence-forecastability
[sibling]: https://github.com/AdamKrysztopa/forecastability-examples

---

## 1. One-time setup

### Prerequisites

- `git`, `uv >= 0.4`, `bash`
- (Optional) VS Code with the Python and Pylance extensions

### Bootstrap

Run the bootstrap script once from the **core repo root**:

```bash
cd /path/to/dependence-forecastability   # the core repo (often named "ami" locally)
bash scripts/bootstrap_local_workspace.sh
```

The script is idempotent — re-running it is always safe.

**What the script does:**

1. Clones `forecastability-examples` at `../forecastability-examples` (one level up from the core repo) if it is not already present.
2. Creates `../forecastability.code-workspace` — the VS Code multi-root descriptor that opens both repos in one editor window.
3. Runs `uv sync --all-extras` inside the sibling repo to install all optional extras.
4. When `FORECASTABILITY_LOCAL_DEV=1` is exported, installs the core repo in editable mode into the sibling's venv so changes to the core are immediately visible.
5. Runs the sibling import-surface lint and reports any violations.

### Open in VS Code

```bash
code ../forecastability.code-workspace
```

Both repos appear as roots in the Explorer. Cross-repo IntelliSense resolves
because the workspace pre-configures `python.analysis.extraPaths` to include
the core repo's `src/` directory.

---

## 2. Filesystem layout

After bootstrapping, the parent folder looks like this:

```text
~/projects/papers/               # parent folder — NOT a git repo
├── ami/                         # core repo (dependence-forecastability)
│   └── .git/                    # core remote → GitHub
├── forecastability-examples/    # sibling repo
│   └── .git/                    # sibling remote → GitHub
└── forecastability.code-workspace
```

> [!IMPORTANT]
> The parent folder is **not** a git repo. Each subdirectory is its own
> independent checkout with its own remote. Never run `git init` in the
> parent folder.

---

## 3. Enabling the local-dev editable install

By default, the sibling repo installs `dependence-forecastability` from PyPI.
To switch to the local core checkout, export the env var and re-run the
bootstrap script:

```bash
export FORECASTABILITY_LOCAL_DEV=1
bash scripts/bootstrap_local_workspace.sh
```

This runs `uv pip install -e /path/to/core` inside the sibling's venv, making
your local core changes immediately visible without a reinstall.

> [!NOTE]
> `uv pip install -e` installs into the sibling's `.venv` without modifying
> `pyproject.toml`. The sibling's lockfile and published dependency metadata
> remain unchanged. CI always resolves `dependence-forecastability` from PyPI
> because `FORECASTABILITY_LOCAL_DEV` is not set on GitHub Actions runners.

**Verify the editable install:**

```bash
cd ../forecastability-examples
uv run python -c "import forecastability; print(forecastability.__file__)"
# Should print a path inside the core repo, not inside .venv/lib/
```

**Reset to PyPI version:**

```bash
cd ../forecastability-examples
uv sync --reinstall-package dependence-forecastability
```

---

## 4. Daily development loop

### Making a change that touches both repos

```bash
# Step 1 — Edit the core API or logic
cd /path/to/ami
# ... edit src/forecastability/ ...
git add .
git commit -m "feat: add new public symbol"
git push origin feat/my-feature

# Step 2 — Update the sibling notebook(s) that use the new symbol
cd ../forecastability-examples
# FORECASTABILITY_LOCAL_DEV=1 should already be set; changes are live
# ... edit walkthroughs/05_forecast_prep_to_models.ipynb ...
# Clear outputs before committing (policy: EX-NB-EXEC-01)
uv run jupyter nbconvert --to notebook --clear-output --inplace walkthroughs/*.ipynb
git add .
git commit -m "docs(walkthroughs): demonstrate new public symbol"
git push origin feat/my-feature

# Step 3 — Open a PR in each repo and link them in the PR description
```

> [!IMPORTANT]
> **Each `git commit` runs in its own subdirectory.** Never `git add` files
> from one repo while inside the other. A pre-commit hook (`forbid-cross-repo-staging`)
> in the core repo catches accidental cross-repo staging and will fail the
> commit with a clear error message.

### Making a core-only change

```bash
cd /path/to/ami
# ... edit and commit normally ...
# No sibling changes needed
```

### Making a sibling-only change (e.g., update a notebook)

```bash
cd ../forecastability-examples
# ... edit walkthroughs/, triage_walkthroughs/, or recipes/ ...
git add .
git commit -m "..."
git push
```

---

## 5. The dual-push workflow

Because the two repos have independent remotes, each checkout pushes to its own GitHub remote:

```bash
# Core push
cd /path/to/ami
git push origin feat/my-branch

# Sibling push (separate terminal window or tab)
cd ../forecastability-examples
git push origin feat/my-sibling-branch
```

There is no shared remote. Do not try to add one; it will break the
independent CI on each repo.

---

## 6. When to flip FORECASTABILITY_LOCAL_DEV on/off

| Situation | Setting |
| --- | --- |
| Iterating on a new core API before release | `FORECASTABILITY_LOCAL_DEV=1` |
| Testing the sibling against a published PyPI release | Unset (default) |
| Running CI locally to simulate GitHub Actions | Unset (default) |
| Bisecting a regression in the sibling caused by a core change | `FORECASTABILITY_LOCAL_DEV=1`, then `git bisect` in core |

---

## 7. Cross-repo PR linking convention

When a PR in the core repo has a paired PR in the sibling repo:

1. In the core PR description, add a **"Sibling PR"** link:

   ```text
   Sibling PR: AdamKrysztopa/forecastability-examples#<N>
   ```

2. In the sibling PR description, add a **"Core PR"** link:

   ```text
   Core PR: AdamKrysztopa/dependence-forecastability#<N>
   ```
3. Both PRs should reference the same
   [v0.4.0 GitHub Project milestone](https://github.com/orgs/AdamKrysztopa/projects)
   so they are tracked together on the shared planning surface (EX-CPL-02).

---

## 8. Release coordination

See [`RELEASING.md`](../../RELEASING.md) in the sibling repo for the
step-by-step two-repo release dance (EX-REL-01). In brief:

1. Core publishes a release candidate (RC) to TestPyPI.
2. Sibling pre-flight matrix runs against the RC (`source ∈ {testpypi, git}`).
3. On a green gate, core tags and publishes to PyPI.
4. Sibling updates its `dependence-forecastability` pin, tags a matching release.
5. The cross-repo CI handshake (EX-CPL-01) posts a confirmation comment on the
   core release page.

The [`RELEASES.md`](../../RELEASES.md) file at the core repo root tracks
paired release tags across both repos.

---

## 9. Troubleshooting

**`uv pip install -e` fails with "not a valid package directory"**

Check that you are pointing at the correct core path:

```bash
uv pip install -e "$(cd ../ami && pwd)"
```

### VS Code does not resolve cross-repo imports

Make sure the workspace was opened via `forecastability.code-workspace` (not
by opening a single folder). Reload the window after opening the workspace:
`Ctrl+Shift+P → Developer: Reload Window`.

**Pre-commit `forbid-cross-repo-staging` fires unexpectedly**

You probably ran `git add ../<something>` from inside the core repo. Run
`git status` to confirm; use `git restore --staged <file>` to unstage.

### CI is red on a sibling PR that depends on an unreleased core change

This is by design. CI always installs `dependence-forecastability` from PyPI.
The sibling PR will go green only after the core change is published (the
[EX-REL-01 release dance](../plan/implemented/v0_4_0_examples_repo_split_ultimate_plan.md)).
Use the local editable install while iterating, then wait for the core release
before merging the sibling PR.
