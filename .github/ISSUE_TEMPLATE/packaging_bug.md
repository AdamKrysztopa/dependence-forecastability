---
name: Packaging / installation bug
about: Report a problem with installing, importing, or running the package from PyPI
labels: ["bug", "packaging"]
assignees: ""
---

## Environment

- **Install command** (e.g. `pip install dependence-forecastability==0.1.0`):
- **Python version** (`python --version`):
- **OS / platform**:
- **Virtual environment tool** (venv / conda / uv):

## What happened

<!-- Paste the full error output here. Include the traceback if one was produced. -->

```
<error output here>
```

## What you expected

<!-- What should have happened instead? -->

## Steps to reproduce

1.
2.
3.

## Verification checklist

- [ ] Reproduced in a **clean virtual environment** (no other packages installed first)
- [ ] Tried with `--no-cache-dir` to rule out a cached broken wheel
- [ ] Checked `pip show dependence-forecastability` — version looks correct
- [ ] Checked `python -c "import forecastability; print(forecastability.__version__)"` output

## Additional context

<!-- Any other information, system details, or workarounds you have tried. -->
