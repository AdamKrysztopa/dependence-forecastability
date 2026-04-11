"""Smoke-contract check for notebook-facing public API.

Verifies notebooks exist on disk, all notebook-facing imports resolve,
and a minimal representative computation runs without error.

Usage:
    uv run python scripts/check_notebook_contract.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).parent.parent
NOTEBOOKS_DIR = REPO_ROOT / "notebooks"

EXPECTED_NOTEBOOKS = [
    "01_canonical_forecastability.ipynb",
    "02_exogenous_analysis.ipynb",
]

PASS = "\u2713"
FAIL = "\u2717"


def _check(label: str, ok: bool) -> bool:
    status = PASS if ok else FAIL
    print(f"  [{status}] {label}")
    return ok


def check_notebooks_exist() -> bool:
    print("Notebooks on disk:")
    all_ok = True
    for name in EXPECTED_NOTEBOOKS:
        exists = (NOTEBOOKS_DIR / name).is_file()
        all_ok = _check(name, exists) and all_ok
    return all_ok


def check_imports() -> bool:
    print("Import resolution:")
    results: list[bool] = []

    checks: list[tuple[str, str | None]] = [
        ("forecastability", None),
        ("forecastability", "ForecastabilityAnalyzer"),
        ("forecastability", "ForecastabilityAnalyzerExog"),
        ("forecastability.pipeline", None),
        ("forecastability.pipeline", "run_canonical_example"),
        ("forecastability.pipeline", "run_rolling_origin_evaluation"),
        ("forecastability.config", "MetricConfig"),
        ("forecastability.datasets", "generate_ar1"),
    ]

    for module_name, attr in checks:
        label = f"{module_name}.{attr}" if attr else module_name
        try:
            mod = importlib.import_module(module_name)
            ok = True
            if attr is not None:
                ok = hasattr(mod, attr)
        except Exception:
            ok = False
        results.append(_check(label, ok))

    return all(results)


def check_representative_call() -> bool:
    print("Representative computation:")
    try:
        from forecastability import ForecastabilityAnalyzer

        rng = np.random.default_rng(0)
        series = rng.standard_normal(200)
        analyzer = ForecastabilityAnalyzer(n_surrogates=99, random_state=42)
        result = analyzer.compute_ami(series)
        ok = isinstance(result, np.ndarray)
    except Exception as exc:
        print(f"    Error: {exc}")
        ok = False
    return _check("ForecastabilityAnalyzer.compute_ami returns ndarray", ok)


def main() -> None:
    passed: list[bool] = []

    passed.append(check_notebooks_exist())
    passed.append(check_imports())
    passed.append(check_representative_call())

    print()
    if all(passed):
        print(f"{PASS} All notebook contract checks passed.")
        sys.exit(0)
    else:
        print(f"{FAIL} One or more notebook contract checks FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
