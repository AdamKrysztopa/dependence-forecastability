#!/usr/bin/env bash
# bootstrap_local_workspace.sh — EX-LOCAL-01
#
# Set up the local two-repo development workspace for dependence-forecastability.
#
# Usage:
#   cd /path/to/dependence-forecastability   # core repo root
#   bash scripts/bootstrap_local_workspace.sh
#
# What it does (idempotent — safe to re-run):
#   1. Verifies this script is run from the core repo root.
#   2. Clones forecastability-examples at ../forecastability-examples if absent.
#   3. Generates ../forecastability.code-workspace (VS Code multi-root descriptor).
#   4. Runs `uv sync` in the sibling repo to install all extras.
#   5. Installs the core repo in editable mode into the sibling's venv so
#      local changes to the core are immediately visible without a reinstall.
#   6. Runs the sibling import-surface lint and reports any violations.
#
# Environment variable:
#   FORECASTABILITY_LOCAL_DEV=1   (export before running for local-dev mode)
#   Skip setting it if you only want to verify the non-editable state.
#
# Acceptance criteria (EX-LOCAL-01):
#   - Clones sibling at ../forecastability-examples if absent.
#   - Generates forecastability.code-workspace at the parent level.
#   - Runs uv sync in sibling and prints the resolved core install path.
#   - Runs sibling import-surface lint and reports zero hits.
#   - Re-running the script is a no-op: exit 0, no filesystem changes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PARENT_DIR="$(cd "${CORE_ROOT}/.." && pwd)"
SIBLING_DIR="${PARENT_DIR}/forecastability-examples"
WORKSPACE_FILE="${PARENT_DIR}/forecastability.code-workspace"
SIBLING_REMOTE="https://github.com/AdamKrysztopa/forecastability-examples.git"

# ── Helpers ────────────────────────────────────────────────────────────────

info()  { echo "[bootstrap] $*"; }
ok()    { echo "[bootstrap] ✓ $*"; }
warn()  { echo "[bootstrap] ⚠ $*"; }
fail()  { echo "[bootstrap] ✗ $*" >&2; exit 1; }

# ── 1. Verify run location ─────────────────────────────────────────────────

if [[ ! -f "${CORE_ROOT}/pyproject.toml" ]]; then
    fail "Run this script from the core repo root (dependence-forecastability/)."
fi

CORE_NAME=$(grep -m1 '^name = ' "${CORE_ROOT}/pyproject.toml" | sed 's/name = "\(.*\)"/\1/')

if [[ "${CORE_NAME}" != "dependence-forecastability" ]]; then
    fail "pyproject.toml does not look like the core repo (name != dependence-forecastability). Aborting."
fi

ok "Core repo confirmed at ${CORE_ROOT}"

# ── 2. Clone sibling if absent ─────────────────────────────────────────────

if [[ -d "${SIBLING_DIR}/.git" ]]; then
    ok "Sibling repo already present at ${SIBLING_DIR}"
else
    info "Cloning ${SIBLING_REMOTE} → ${SIBLING_DIR}"
    git clone "${SIBLING_REMOTE}" "${SIBLING_DIR}"
    ok "Sibling repo cloned"
fi

# ── 3. Generate forecastability.code-workspace ─────────────────────────────

CORE_RELNAME="$(basename "${CORE_ROOT}")"
SIBLING_RELNAME="$(basename "${SIBLING_DIR}")"

# Compute relative paths from the parent dir to each repo
CORE_REL_PATH="${CORE_RELNAME}"
SIBLING_REL_PATH="${SIBLING_RELNAME}"

WORKSPACE_CONTENT='{
    "folders": [
        {
            "name": "dependence-forecastability (core)",
            "path": "'"${CORE_REL_PATH}"'"
        },
        {
            "name": "forecastability-examples (sibling)",
            "path": "'"${SIBLING_REL_PATH}"'"
        }
    ],
    "settings": {
        "python.analysis.extraPaths": [
            "${workspaceFolder:dependence-forecastability (core)}/src"
        ],
        "python.defaultInterpreterPath": "${workspaceFolder:dependence-forecastability (core)}/.venv/bin/python"
    },
    "extensions": {
        "recommendations": [
            "ms-python.python",
            "ms-python.pylance",
            "github.copilot",
            "github.copilot-chat"
        ]
    }
}'

if [[ -f "${WORKSPACE_FILE}" ]]; then
    ok "forecastability.code-workspace already exists at ${WORKSPACE_FILE}"
else
    echo "${WORKSPACE_CONTENT}" > "${WORKSPACE_FILE}"
    ok "Created ${WORKSPACE_FILE}"
fi

# ── 4. uv sync in sibling ──────────────────────────────────────────────────

info "Running uv sync --all-extras in ${SIBLING_DIR}"
cd "${SIBLING_DIR}"
uv sync --all-extras
ok "uv sync complete"

# ── 5. Editable install of core into sibling venv (local-dev mode) ─────────

if [[ "${FORECASTABILITY_LOCAL_DEV:-}" == "1" ]]; then
    info "FORECASTABILITY_LOCAL_DEV=1 detected — installing core in editable mode"
    uv pip install -e "${CORE_ROOT}"
    CORE_INSTALL_PATH=$(uv run python -c "import importlib.metadata as m; print(m.packages_distributions())" 2>/dev/null | \
        python3 -c "import sys, ast; d = ast.literal_eval(sys.stdin.read()); print(d.get('forecastability', ['<not found>'])[0])" 2>/dev/null || echo "<see .venv/lib>")
    CORE_INSTALL_PATH=$(uv run python -c "import forecastability; import pathlib; print(pathlib.Path(forecastability.__file__).parent.resolve())" 2>/dev/null || echo "${CORE_ROOT}/src/forecastability")
    ok "Core installed in editable mode → ${CORE_INSTALL_PATH}"
else
    info "FORECASTABILITY_LOCAL_DEV not set — skipping editable install (PyPI version active)"
    info "To enable local-dev mode: export FORECASTABILITY_LOCAL_DEV=1 && bash scripts/bootstrap_local_workspace.sh"
fi

# ── 6. Sibling import-surface lint ─────────────────────────────────────────

info "Running sibling import-surface lint"
cd "${SIBLING_DIR}"

LINT_HITS=$(grep -rn \
    'from forecastability\.\(services\|use_cases\|utils\|adapters\|diagnostics\)' \
    walkthroughs triage_walkthroughs recipes 2>/dev/null || true)

if [[ -n "${LINT_HITS}" ]]; then
    warn "Import-surface violations found — sibling notebooks must only import from the public API:"
    echo "${LINT_HITS}"
    warn "Fix these before opening a PR against the sibling repo."
else
    ok "Import-surface lint: zero violations"
fi

# ── Done ───────────────────────────────────────────────────────────────────

cd "${CORE_ROOT}"
echo ""
echo "────────────────────────────────────────────────────"
echo "  Local workspace bootstrap complete."
echo ""
echo "  Core repo  : ${CORE_ROOT}"
echo "  Sibling    : ${SIBLING_DIR}"
echo "  Workspace  : ${WORKSPACE_FILE}"
echo ""
echo "  Open in VS Code:"
echo "    code ${WORKSPACE_FILE}"
echo ""
echo "  Daily dev loop:"
echo "    1. Edit core → commit/push in ${CORE_RELNAME}/"
echo "    2. Edit notebooks → commit/push in ${SIBLING_RELNAME}/"
echo "    3. See docs/development/local_workspace.md for the full guide."
echo "────────────────────────────────────────────────────"
