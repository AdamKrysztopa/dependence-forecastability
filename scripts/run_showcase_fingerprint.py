"""Canonical showcase for the v0.3.1 forecastability fingerprint release.

Runs the prepared synthetic archetype panel from ``synthetic.py`` through the
geometry-backed fingerprint workflow, then emits stable figures, tables, JSON,
and deterministic A1/A2/A3 agent artifacts. The final markdown report ends with
the mathematics translated into plain human language.

Usage::

    uv run scripts/run_showcase_fingerprint.py
    uv run scripts/run_showcase_fingerprint.py --smoke
    uv run scripts/run_showcase_fingerprint.py --quiet
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

from forecastability.reporting.fingerprint_showcase import (
    build_fingerprint_showcase_record,
    build_showcase_report,
    build_verification_markdown,
    routing_table_frame,
    save_metric_overview,
    save_showcase_profile_grid,
    showcase_summary_frame,
    verify_showcase_records,
    write_frame_csv,
)
from forecastability.services.linear_information_service import compute_linear_information_curve
from forecastability.use_cases.run_forecastability_fingerprint import (
    run_forecastability_fingerprint,
)
from forecastability.utils.synthetic import generate_fingerprint_archetypes

_logger = logging.getLogger(__name__)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Canonical deterministic showcase for the forecastability fingerprint release"
    )
    parser.add_argument("--output-root", type=str, default="outputs", help="output root directory")
    parser.add_argument("--random-state", type=int, default=42, help="reproducibility seed")
    parser.add_argument("--max-lag", type=int, default=24, help="maximum lag horizon")
    parser.add_argument(
        "--n-surrogates",
        type=int,
        default=99,
        help="number of surrogates; must be at least 99",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=320,
        help="number of observations per synthetic archetype",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help=(
            "CI-friendly preset: use the prepared archetypes at n=240 while keeping the "
            "full method surface and strict deterministic agent checks"
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress the verbose stage banners; only print the final verification line",
    )
    return parser.parse_args(argv)


def _ensure_dirs(output_root: Path) -> tuple[Path, Path, Path, Path]:
    json_dir = output_root / "json" / "showcase_fingerprint"
    tables_dir = output_root / "tables" / "showcase_fingerprint"
    reports_dir = output_root / "reports" / "showcase_fingerprint"
    figures_dir = output_root / "figures" / "showcase_fingerprint"
    for path in (json_dir, tables_dir, reports_dir, figures_dir):
        path.mkdir(parents=True, exist_ok=True)
    return json_dir, tables_dir, reports_dir, figures_dir


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _say(quiet: bool, message: str) -> None:
    if not quiet:
        print(message, flush=True)


def _resolved_n(args: argparse.Namespace) -> int:
    if args.smoke:
        return 240
    return args.n


def main(argv: list[str] | None = None) -> int:
    """Run the fingerprint showcase and return a POSIX-style exit code."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
    args = _parse_args(argv)
    if args.n_surrogates < 99:
        raise ValueError(f"n_surrogates must be >= 99, got {args.n_surrogates}")

    quiet = bool(args.quiet)
    n_obs = _resolved_n(args)
    output_root = Path(args.output_root)
    json_dir, tables_dir, reports_dir, figures_dir = _ensure_dirs(output_root)

    _say(quiet, "=" * 72)
    _say(quiet, "[fingerprint-showcase] V3_1-F07 canonical run")
    _say(quiet, "=" * 72)
    _say(
        quiet,
        "[fingerprint-showcase] methods         : "
        "generate_fingerprint_archetypes -> run_forecastability_fingerprint -> "
        "compute_linear_information_curve -> A1/A2/A3 strict agent adapters",
    )
    _say(
        quiet,
        f"[fingerprint-showcase] panel           : prepared synthetic archetypes "
        f"(n={n_obs}, seed={args.random_state})",
    )
    _say(
        quiet,
        f"[fingerprint-showcase] max_lag         : {args.max_lag}     "
        f"n_surrogates : {args.n_surrogates}",
    )
    _say(
        quiet,
        f"[fingerprint-showcase] mode            : {'smoke' if args.smoke else 'full'}",
    )
    _say(quiet, f"[fingerprint-showcase] output_root     : {output_root}")
    _say(quiet, "")

    t_gen_start = time.perf_counter()
    _say(quiet, "[fingerprint-showcase] step 1/4  generating canonical archetype panel ...")
    series_map = generate_fingerprint_archetypes(n=n_obs, seed=args.random_state)
    t_gen = time.perf_counter() - t_gen_start
    _say(
        quiet,
        "[fingerprint-showcase]           -> "
        f"{len(series_map)} series {list(series_map)} [{t_gen:.2f}s]",
    )

    t_bundle_start = time.perf_counter()
    _say(
        quiet,
        "[fingerprint-showcase] step 2/4  running geometry -> fingerprint -> "
        "routing -> A1/A2/A3 ...",
    )
    records = []
    for target_name, series in series_map.items():
        bundle = run_forecastability_fingerprint(
            series,
            target_name=target_name,
            max_lag=args.max_lag,
            n_surrogates=args.n_surrogates,
            random_state=args.random_state,
        )
        baseline = compute_linear_information_curve(
            series,
            horizons=[point.horizon for point in bundle.geometry.curve if point.valid],
        )
        records.append(
            build_fingerprint_showcase_record(
                bundle=bundle,
                baseline=baseline,
            )
        )
    t_bundle = time.perf_counter() - t_bundle_start
    _say(
        quiet,
        f"[fingerprint-showcase]           -> {len(records)} showcase records [{t_bundle:.2f}s]",
    )

    t_verify_start = time.perf_counter()
    _say(quiet, "[fingerprint-showcase] step 3/4  deterministic verification ...")
    verification_issues = verify_showcase_records(records)
    t_verify = time.perf_counter() - t_verify_start
    _say(
        quiet,
        f"[fingerprint-showcase]           -> issues={len(verification_issues)} [{t_verify:.2f}s]",
    )

    t_write_start = time.perf_counter()
    _say(quiet, "[fingerprint-showcase] step 4/4  writing figures, tables, JSON, and reports ...")
    summary_frame = showcase_summary_frame(records)
    routing_frame = routing_table_frame(records)
    settings = {
        "release": "0.3.1",
        "panel": "generate_fingerprint_archetypes",
        "agent_mode": "strict_deterministic_a3",
        "n": n_obs,
        "max_lag": args.max_lag,
        "n_surrogates": args.n_surrogates,
        "random_state": args.random_state,
    }

    profile_path = figures_dir / "fingerprint_profiles.png"
    metric_path = figures_dir / "fingerprint_metrics.png"
    summary_csv_path = tables_dir / "fingerprint_summary.csv"
    routing_csv_path = tables_dir / "fingerprint_routing.csv"
    report_path = reports_dir / "showcase_report.md"
    verification_path = reports_dir / "verification.md"
    manifest_path = json_dir / "showcase_manifest.json"

    save_showcase_profile_grid(records, output_path=profile_path)
    save_metric_overview(records, output_path=metric_path)
    write_frame_csv(summary_frame, output_path=summary_csv_path)
    write_frame_csv(routing_frame, output_path=routing_csv_path)
    report_path.write_text(
        build_showcase_report(
            records,
            settings=settings,
            verification_issues=verification_issues,
        ),
        encoding="utf-8",
    )
    verification_path.write_text(
        build_verification_markdown(
            records,
            verification_issues=verification_issues,
        ),
        encoding="utf-8",
    )

    manifest_items: list[dict[str, object]] = []
    for record in records:
        target_name = record.bundle.target_name
        bundle_path = json_dir / f"{target_name}_bundle.json"
        payload_path = json_dir / f"{target_name}_agent_payload.json"
        envelope_path = json_dir / f"{target_name}_agent_envelope.json"
        interpretation_path = json_dir / f"{target_name}_agent_interpretation.json"
        _write_json(bundle_path, record.bundle.model_dump(mode="json"))
        _write_json(payload_path, record.payload.model_dump(mode="json"))
        _write_json(envelope_path, record.serialised_payload.model_dump(mode="json"))
        _write_json(interpretation_path, record.interpretation.model_dump(mode="json"))
        manifest_items.append(
            {
                "target_name": target_name,
                "bundle_path": str(bundle_path),
                "payload_path": str(payload_path),
                "envelope_path": str(envelope_path),
                "interpretation_path": str(interpretation_path),
            }
        )

    _write_json(
        manifest_path,
        {
            "settings": settings,
            "artifacts": {
                "profile_figure": str(profile_path),
                "metric_figure": str(metric_path),
                "summary_csv": str(summary_csv_path),
                "routing_csv": str(routing_csv_path),
                "report": str(report_path),
                "verification": str(verification_path),
            },
            "items": manifest_items,
        },
    )

    t_write = time.perf_counter() - t_write_start
    _say(quiet, f"[fingerprint-showcase]           -> {profile_path}")
    _say(quiet, f"[fingerprint-showcase]           -> {metric_path}")
    _say(quiet, f"[fingerprint-showcase]           -> {summary_csv_path}")
    _say(quiet, f"[fingerprint-showcase]           -> {routing_csv_path}")
    _say(quiet, f"[fingerprint-showcase]           -> {report_path}")
    _say(quiet, f"[fingerprint-showcase]           -> {verification_path}")
    _say(quiet, f"[fingerprint-showcase]           -> {manifest_path} [{t_write:.2f}s]")

    total = t_gen + t_bundle + t_verify + t_write
    _say(quiet, "")
    _say(
        quiet,
        f"[fingerprint-showcase] timings  gen={t_gen:.2f}s  bundle={t_bundle:.2f}s  "
        f"verify={t_verify:.2f}s  write={t_write:.2f}s  total={total:.2f}s",
    )

    status = "PASS" if not verification_issues else "FAIL"
    if verification_issues:
        _say(quiet, "")
        _say(quiet, f"[fingerprint-showcase] issues ({len(verification_issues)}):")
        for issue in verification_issues:
            _say(quiet, f"  - {issue}")
        _say(quiet, f"[fingerprint-showcase] see {verification_path} for full details")
    else:
        _say(quiet, "")
        _say(
            quiet,
            "[fingerprint-showcase] strict deterministic verification passed for "
            "all four archetypes",
        )

    _say(quiet, "")
    print(f"VERIFICATION: {status}", flush=True)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
