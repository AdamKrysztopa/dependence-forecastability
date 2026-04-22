"""Canonical showcase for the v0.3.2 lagged-exogenous triage surface.

Runs the deterministic lagged-exogenous benchmark panel through
``run_lagged_exogenous_triage`` and emits JSON, tables, figures, and markdown
summaries.

Usage::

    uv run scripts/run_showcase_lagged_exogenous.py
    uv run scripts/run_showcase_lagged_exogenous.py --smoke
    uv run scripts/run_showcase_lagged_exogenous.py --smoke --quiet
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import time
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

from forecastability import (
    LaggedExogBundle,
    generate_lagged_exog_panel,
    run_lagged_exogenous_triage,
)
from forecastability.adapters.rendering import (
    save_lagged_exog_profile_figure,
    save_lagged_exog_selection_heatmap,
)

_logger = logging.getLogger(__name__)

_KNOWN_FUTURE_DRIVER = "known_future_calendar"
_DRIVER_ORDER: tuple[str, ...] = (
    "direct_lag2",
    "mediated_lag1",
    "redundant",
    "noise",
    "instant_only",
    "nonlinear_lag1",
    _KNOWN_FUTURE_DRIVER,
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Canonical lagged-exogenous showcase (v0.3.2 Phase 4)"
    )
    parser.add_argument("--output-root", type=str, default="outputs", help="output root directory")
    parser.add_argument("--random-state", type=int, default=42, help="reproducibility seed")
    parser.add_argument("--max-lag", type=int, default=6, help="maximum lag horizon")
    parser.add_argument(
        "--n-surrogates",
        type=int,
        default=99,
        help="number of surrogates; must be at least 99",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=1500,
        help="number of observations in the benchmark panel",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="CI-friendly preset (n=700, max_lag=min(max_lag, 4))",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress stage banners; only print final verification line",
    )
    return parser.parse_args(argv)


def _resolved_n(args: argparse.Namespace) -> int:
    return 700 if args.smoke else int(args.n)


def _resolved_max_lag(args: argparse.Namespace) -> int:
    if args.smoke:
        return min(int(args.max_lag), 4)
    return int(args.max_lag)


def _ensure_dirs(output_root: Path) -> tuple[Path, Path, Path, Path]:
    json_dir = output_root / "json" / "showcase_lagged_exogenous"
    tables_dir = output_root / "tables" / "showcase_lagged_exogenous"
    reports_dir = output_root / "reports" / "showcase_lagged_exogenous"
    figures_dir = output_root / "figures" / "showcase_lagged_exogenous"
    for path in (json_dir, tables_dir, reports_dir, figures_dir):
        path.mkdir(parents=True, exist_ok=True)
    return json_dir, tables_dir, reports_dir, figures_dir


def _say(quiet: bool, message: str) -> None:
    if not quiet:
        print(message, flush=True)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_profile_csv(path: Path, bundle: LaggedExogBundle) -> None:
    fieldnames = [
        "target",
        "driver",
        "lag",
        "lag_role",
        "tensor_role",
        "correlation",
        "cross_ami",
        "cross_pami",
        "significance",
        "significance_source",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted(bundle.profile_rows, key=lambda item: (item.driver, item.lag)):
            writer.writerow(
                {
                    "target": row.target,
                    "driver": row.driver,
                    "lag": row.lag,
                    "lag_role": row.lag_role,
                    "tensor_role": row.tensor_role,
                    "correlation": row.correlation,
                    "cross_ami": row.cross_ami,
                    "cross_pami": row.cross_pami,
                    "significance": row.significance,
                    "significance_source": row.significance_source,
                }
            )


def _write_selection_csv(path: Path, bundle: LaggedExogBundle) -> None:
    fieldnames = [
        "target",
        "driver",
        "lag",
        "selected_for_tensor",
        "selection_order",
        "selector_name",
        "score",
        "tensor_role",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted(bundle.selected_lags, key=lambda item: (item.driver, item.lag)):
            writer.writerow(
                {
                    "target": row.target,
                    "driver": row.driver,
                    "lag": row.lag,
                    "selected_for_tensor": int(row.selected_for_tensor),
                    "selection_order": row.selection_order,
                    "selector_name": row.selector_name,
                    "score": row.score,
                    "tensor_role": row.tensor_role,
                }
            )


def _selected_lag_map(bundle: LaggedExogBundle) -> dict[str, list[int]]:
    selected: dict[str, list[int]] = {}
    for row in sorted(bundle.selected_lags, key=lambda item: (item.driver, item.lag)):
        if row.selected_for_tensor:
            selected.setdefault(row.driver, []).append(int(row.lag))
    return selected


def _max_profile_lags(bundle: LaggedExogBundle) -> dict[str, dict[str, int | None]]:
    output: dict[str, dict[str, int | None]] = {}
    for driver in bundle.driver_names:
        rows = [row for row in bundle.profile_rows if row.driver == driver]
        corr_candidates = [
            (row.lag, row.correlation) for row in rows if row.correlation is not None
        ]
        ami_candidates = [(row.lag, row.cross_ami) for row in rows if row.cross_ami is not None]

        best_corr_lag: int | None = None
        if corr_candidates:
            best_corr_lag = min(
                corr_candidates,
                key=lambda item: (-abs(float(item[1])), int(item[0])),
            )[0]

        best_ami_lag: int | None = None
        if ami_candidates:
            best_ami_lag = min(
                ami_candidates,
                key=lambda item: (-float(item[1]), int(item[0])),
            )[0]

        output[driver] = {
            "best_corr_lag": best_corr_lag,
            "best_cross_ami_lag": best_ami_lag,
        }
    return output


def _verify_bundle(bundle: LaggedExogBundle) -> list[str]:
    violations: list[str] = []

    lag_zero_rows = [row for row in bundle.profile_rows if row.lag == 0]
    if len(lag_zero_rows) != len(bundle.driver_names):
        violations.append(
            "profile_rows must contain exactly one lag=0 row per driver "
            f"(got {len(lag_zero_rows)} rows for {len(bundle.driver_names)} drivers)"
        )

    lag_zero_counts_by_driver = {driver: 0 for driver in bundle.driver_names}
    unknown_lag_zero_drivers: set[str] = set()
    for row in lag_zero_rows:
        if row.driver in lag_zero_counts_by_driver:
            lag_zero_counts_by_driver[row.driver] += 1
        else:
            unknown_lag_zero_drivers.add(row.driver)
    invalid_lag_zero_counts = {
        driver: count for driver, count in lag_zero_counts_by_driver.items() if count != 1
    }
    if invalid_lag_zero_counts:
        violations.append(
            "profile_rows must contain exactly one lag=0 row for each listed driver: "
            f"{invalid_lag_zero_counts}"
        )
    if unknown_lag_zero_drivers:
        violations.append(
            "profile_rows include lag=0 rows for unknown drivers: "
            f"{sorted(unknown_lag_zero_drivers)}"
        )

    non_opt_in_lag_zero_selected = [
        row.driver
        for row in bundle.selected_lags
        if row.selected_for_tensor
        and row.lag == 0
        and row.driver not in set(bundle.known_future_drivers)
    ]
    if non_opt_in_lag_zero_selected:
        violations.append(
            "lag=0 selected_for_tensor rows found without known-future opt-in: "
            f"{sorted(set(non_opt_in_lag_zero_selected))}"
        )

    if _KNOWN_FUTURE_DRIVER not in bundle.known_future_drivers:
        violations.append(
            "known_future_calendar should be present in known_future_drivers for this showcase"
        )
    has_known_future_lag_zero = any(
        row.driver == _KNOWN_FUTURE_DRIVER and row.selected_for_tensor and row.lag == 0
        for row in bundle.selected_lags
    )
    if not has_known_future_lag_zero:
        violations.append("known_future_calendar must have a selected lag=0 row in this showcase")

    direct_predictive_selected = [
        row.lag
        for row in bundle.selected_lags
        if row.driver == "direct_lag2" and row.selected_for_tensor and row.lag >= 1
    ]
    if not direct_predictive_selected:
        violations.append("direct_lag2 must include at least one selected predictive lag")

    return violations


def _build_summary_markdown(
    *,
    bundle: LaggedExogBundle,
    settings: dict[str, int | str],
    selected_lag_map: dict[str, list[int]],
    max_profile_lags: dict[str, dict[str, int | None]],
) -> str:
    lines: list[str] = [
        "# Lagged Exogenous Showcase Summary",
        "",
        "This showcase runs deterministic lagged-exogenous triage first, then surfaces",
        "a sparse lag map for downstream forecasting tensors.",
        "",
        "## Settings",
        "",
    ]
    for key, value in settings.items():
        lines.append(f"- {key}: `{value}`")

    lines.extend(
        [
            "",
            "## Selected Lag Map",
            "",
            "| Driver | Selected lags |",
            "| --- | --- |",
        ]
    )
    for driver in bundle.driver_names:
        lags = selected_lag_map.get(driver, [])
        lines.append(f"| {driver} | {lags} |")

    lines.extend(
        [
            "",
            "## Profile Peaks",
            "",
            "| Driver | Best |rho| lag | Best cross_ami lag |",
            "| --- | ---: | ---: |",
        ]
    )
    for driver in bundle.driver_names:
        peaks = max_profile_lags.get(driver, {})
        lines.append(
            f"| {driver} | {peaks.get('best_corr_lag')} | {peaks.get('best_cross_ami_lag')} |"
        )

    lines.extend(
        [
            "",
            "## Contract Notes",
            "",
            "- lag=0 rows are visualised as diagnostics and separated by a boundary line.",
            "- selected predictive lags are highlighted directly in profile plots.",
            "- lag=0 selection is only allowed when the driver is explicitly marked known future.",
        ]
    )
    return "\n".join(lines)


def _build_verification_markdown(*, violations: list[str]) -> str:
    status = "PASS" if not violations else "FAIL"
    lines = [
        "# Lagged Exogenous Showcase Verification",
        "",
        f"- status: **{status}**",
        "",
        "## Violations",
        "",
    ]
    if violations:
        for violation in violations:
            lines.append(f"- {violation}")
    else:
        lines.append("- none")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Run the lagged-exogenous showcase and return POSIX-style exit code."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")

    args = _parse_args(argv)
    if args.n_surrogates < 99:
        raise ValueError(f"n_surrogates must be >= 99, got {args.n_surrogates}")

    n_obs = _resolved_n(args)
    max_lag = _resolved_max_lag(args)
    quiet = bool(args.quiet)

    output_root = Path(args.output_root)
    json_dir, tables_dir, reports_dir, figures_dir = _ensure_dirs(output_root)

    _say(quiet, "=" * 72)
    _say(quiet, "[lagged-exog-showcase] V3_2-F09 canonical run")
    _say(quiet, "=" * 72)
    _say(
        quiet,
        "[lagged-exog-showcase] methods         : generate_lagged_exog_panel -> "
        "run_lagged_exogenous_triage -> rendering adapters",
    )
    _say(
        quiet,
        f"[lagged-exog-showcase] panel           : synthetic lagged exogenous "
        f"benchmark (n={n_obs}, seed={args.random_state})",
    )
    _say(
        quiet,
        f"[lagged-exog-showcase] max_lag         : {max_lag}"
        f"     n_surrogates : {args.n_surrogates}",
    )
    _say(quiet, f"[lagged-exog-showcase] mode            : {'smoke' if args.smoke else 'full'}")
    _say(quiet, f"[lagged-exog-showcase] output_root     : {output_root}")
    _say(quiet, "")

    t_panel = time.perf_counter()
    panel = generate_lagged_exog_panel(n=n_obs, seed=args.random_state)
    target = panel["target"].to_numpy()
    drivers = {driver: panel[driver].to_numpy() for driver in _DRIVER_ORDER}
    _say(
        quiet,
        "[lagged-exog-showcase] step 1/4  generated benchmark panel "
        f"[{time.perf_counter() - t_panel:.2f}s]",
    )

    t_triage = time.perf_counter()
    bundle = run_lagged_exogenous_triage(
        target,
        drivers,
        target_name="target",
        max_lag=max_lag,
        n_surrogates=int(args.n_surrogates),
        random_state=int(args.random_state),
        known_future_drivers={_KNOWN_FUTURE_DRIVER: True},
    )
    _say(
        quiet,
        "[lagged-exog-showcase] step 2/4  ran lagged-exogenous triage "
        f"[{time.perf_counter() - t_triage:.2f}s]",
    )

    t_fig = time.perf_counter()
    profile_figure_path = figures_dir / "lagged_exog_profiles.png"
    selection_figure_path = figures_dir / "lagged_exog_selected_lags.png"
    save_lagged_exog_profile_figure(
        bundle,
        output_path=profile_figure_path,
        driver_order=list(_DRIVER_ORDER),
    )
    save_lagged_exog_selection_heatmap(
        bundle,
        output_path=selection_figure_path,
        driver_order=list(_DRIVER_ORDER),
    )
    _say(
        quiet,
        f"[lagged-exog-showcase] step 3/4  rendered figures [{time.perf_counter() - t_fig:.2f}s]",
    )

    t_write = time.perf_counter()
    bundle_json_path = json_dir / "lagged_exog_bundle.json"
    profile_csv_path = tables_dir / "lagged_exog_profile_rows.csv"
    selection_csv_path = tables_dir / "lagged_exog_selected_lags.csv"
    summary_path = reports_dir / "showcase_summary.md"
    verification_path = reports_dir / "verification.md"
    manifest_path = json_dir / "showcase_manifest.json"

    selected_lag_map = _selected_lag_map(bundle)
    max_profile_lags = _max_profile_lags(bundle)
    violations = _verify_bundle(bundle)

    settings: dict[str, int | str] = {
        "release": "0.3.2",
        "n": n_obs,
        "max_lag": max_lag,
        "n_surrogates": int(args.n_surrogates),
        "random_state": int(args.random_state),
        "known_future_driver": _KNOWN_FUTURE_DRIVER,
    }

    _write_json(bundle_json_path, bundle.model_dump(mode="json"))
    _write_profile_csv(profile_csv_path, bundle)
    _write_selection_csv(selection_csv_path, bundle)
    summary_path.write_text(
        _build_summary_markdown(
            bundle=bundle,
            settings=settings,
            selected_lag_map=selected_lag_map,
            max_profile_lags=max_profile_lags,
        ),
        encoding="utf-8",
    )
    verification_path.write_text(
        _build_verification_markdown(violations=violations),
        encoding="utf-8",
    )

    _write_json(
        manifest_path,
        {
            "settings": settings,
            "status": "PASS" if not violations else "FAIL",
            "artifacts": {
                "bundle_json": str(bundle_json_path),
                "profile_csv": str(profile_csv_path),
                "selection_csv": str(selection_csv_path),
                "summary_report": str(summary_path),
                "verification_report": str(verification_path),
                "profile_figure": str(profile_figure_path),
                "selection_figure": str(selection_figure_path),
            },
            "selected_lag_map": selected_lag_map,
            "profile_peaks": max_profile_lags,
        },
    )

    _say(
        quiet,
        f"[lagged-exog-showcase] step 4/4  wrote artifacts [{time.perf_counter() - t_write:.2f}s]",
    )

    _say(quiet, f"[lagged-exog-showcase]           -> {bundle_json_path}")
    _say(quiet, f"[lagged-exog-showcase]           -> {profile_csv_path}")
    _say(quiet, f"[lagged-exog-showcase]           -> {selection_csv_path}")
    _say(quiet, f"[lagged-exog-showcase]           -> {summary_path}")
    _say(quiet, f"[lagged-exog-showcase]           -> {verification_path}")
    _say(quiet, f"[lagged-exog-showcase]           -> {profile_figure_path}")
    _say(quiet, f"[lagged-exog-showcase]           -> {selection_figure_path}")
    _say(quiet, f"[lagged-exog-showcase]           -> {manifest_path}")

    status = "PASS" if not violations else "FAIL"
    if violations:
        _logger.warning(
            "Lagged exogenous showcase verification found %d violation(s)",
            len(violations),
        )

    print(f"VERIFICATION: {status}", flush=True)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
