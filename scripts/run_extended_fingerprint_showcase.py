"""Canonical Phase 3 extended fingerprint showcase for the core repository.

Usage::

    uv run scripts/run_extended_fingerprint_showcase.py
    uv run scripts/run_extended_fingerprint_showcase.py --smoke
    uv run scripts/run_extended_fingerprint_showcase.py --quiet
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

from forecastability import run_extended_forecastability_analysis
from forecastability.reporting.extended_fingerprint_showcase import (
    build_extended_fingerprint_showcase_record,
    build_showcase_brief,
    build_showcase_report,
    build_verification_markdown,
    routing_table_frame,
    save_metric_overview,
    save_showcase_profile_grid,
    showcase_summary_frame,
    verify_showcase_records,
    write_frame_csv,
)
from forecastability.utils.synthetic import generate_extended_fingerprint_showcase_panel

_logger = logging.getLogger(__name__)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deterministic AMI-first extended fingerprint showcase for v0.4.2"
    )
    parser.add_argument("--output-root", type=str, default="outputs", help="output root directory")
    parser.add_argument("--random-state", type=int, default=42, help="reproducibility seed")
    parser.add_argument("--max-lag", type=int, default=18, help="maximum AMI lag horizon")
    parser.add_argument(
        "--n",
        type=int,
        default=360,
        help="number of observations per synthetic showcase series",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help=(
            "CI-friendly preset: use n=240 and cap max_lag at 16 while keeping the "
            "full extended diagnostic surface enabled"
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress verbose stage banners and only print the final verification line",
    )
    return parser.parse_args(argv)


def _ensure_dirs(output_root: Path) -> tuple[Path, Path, Path, Path]:
    json_dir = output_root / "json" / "extended_fingerprint"
    tables_dir = output_root / "tables" / "extended_fingerprint"
    reports_dir = output_root / "reports" / "extended_fingerprint"
    figures_dir = output_root / "figures" / "extended_fingerprint"
    for path in (json_dir, tables_dir, reports_dir, figures_dir):
        path.mkdir(parents=True, exist_ok=True)
    return json_dir, tables_dir, reports_dir, figures_dir


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _say(quiet: bool, message: str) -> None:
    if not quiet:
        print(message, flush=True)


def _resolved_n(args: argparse.Namespace) -> int:
    return 240 if args.smoke else args.n


def _resolved_max_lag(args: argparse.Namespace) -> int:
    return min(args.max_lag, 16) if args.smoke else args.max_lag


def main(argv: list[str] | None = None) -> int:
    """Run the extended fingerprint showcase and return a POSIX-style exit code."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
    args = _parse_args(argv)
    quiet = bool(args.quiet)
    n_obs = _resolved_n(args)
    max_lag = _resolved_max_lag(args)
    output_root = Path(args.output_root)
    json_dir, tables_dir, reports_dir, figures_dir = _ensure_dirs(output_root)

    _say(quiet, "=" * 72)
    _say(quiet, "[extended-showcase] Phase 3 core-repo canonical run")
    _say(quiet, "=" * 72)
    _say(
        quiet,
        "[extended-showcase] methods         : generate_extended_fingerprint_showcase_panel -> "
        "run_extended_forecastability_analysis -> reporting artifacts",
    )
    _say(
        quiet,
        f"[extended-showcase] panel           : deterministic seven-series synthetic showcase "
        f"(n={n_obs}, seed={args.random_state})",
    )
    _say(quiet, f"[extended-showcase] max_lag         : {max_lag}")
    _say(quiet, f"[extended-showcase] mode            : {'smoke' if args.smoke else 'full'}")
    _say(quiet, f"[extended-showcase] output_root     : {output_root}")
    _say(quiet, "")

    t_generate_start = time.perf_counter()
    _say(quiet, "[extended-showcase] step 1/4  generating deterministic showcase panel ...")
    panel = generate_extended_fingerprint_showcase_panel(n=n_obs, seed=args.random_state)
    t_generate = time.perf_counter() - t_generate_start
    _say(
        quiet,
        "[extended-showcase]           -> "
        f"{len(panel)} series {[case.series_name for case in panel]} [{t_generate:.2f}s]",
    )

    t_analysis_start = time.perf_counter()
    _say(quiet, "[extended-showcase] step 2/4  running AMI-first extended analysis ...")
    records = []
    for case in panel:
        analysis = run_extended_forecastability_analysis(
            case.series,
            name=case.series_name,
            max_lag=max_lag,
            period=case.period,
            random_state=args.random_state,
        )
        records.append(
            build_extended_fingerprint_showcase_record(
                case=case,
                analysis=analysis,
            )
        )
    t_analysis = time.perf_counter() - t_analysis_start
    _say(
        quiet,
        f"[extended-showcase]           -> {len(records)} showcase analyses [{t_analysis:.2f}s]",
    )

    t_verify_start = time.perf_counter()
    _say(
        quiet,
        "[extended-showcase] step 3/4  deterministic verification "
        "(metadata + coarse semantics) ...",
    )
    verification_issues = verify_showcase_records(records)
    status = "PASS" if not verification_issues else "FAIL"
    t_verify = time.perf_counter() - t_verify_start
    _say(
        quiet,
        f"[extended-showcase]           -> issues={len(verification_issues)} [{t_verify:.2f}s]",
    )

    t_write_start = time.perf_counter()
    _say(quiet, "[extended-showcase] step 4/4  writing figures, tables, JSON, and reports ...")
    summary_frame = showcase_summary_frame(records)
    routing_frame = routing_table_frame(records)
    settings = {
        "release": "0.4.2",
        "panel": "generate_extended_fingerprint_showcase_panel",
        "n": n_obs,
        "max_lag": max_lag,
        "random_state": args.random_state,
        "series_count": len(records),
    }

    profile_path = figures_dir / "extended_ami_profiles.png"
    metric_path = figures_dir / "extended_metric_overview.png"
    summary_csv_path = tables_dir / "extended_summary.csv"
    routing_csv_path = tables_dir / "extended_routing.csv"
    report_path = reports_dir / "showcase_report.md"
    brief_path = reports_dir / "brief.md"
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
    brief_path.write_text(build_showcase_brief(records, settings=settings), encoding="utf-8")
    verification_path.write_text(
        build_verification_markdown(records, verification_issues=verification_issues),
        encoding="utf-8",
    )

    manifest_items: list[dict[str, object]] = []
    for record in records:
        result_path = json_dir / f"{record.series_name}_analysis.json"
        _write_json(result_path, record.analysis.model_dump(mode="json"))
        manifest_items.append(
            {
                "series_name": record.series_name,
                "description": record.description,
                "generator": record.generator,
                "period": record.period,
                "expected_story": record.expected_story,
                "result_path": str(result_path),
            }
        )

    artifacts = {
        "profile_figure": str(profile_path),
        "metric_figure": str(metric_path),
        "summary_csv": str(summary_csv_path),
        "routing_csv": str(routing_csv_path),
        "report": str(report_path),
        "brief": str(brief_path),
        "verification": str(verification_path),
    }

    _write_json(
        manifest_path,
        {
            "settings": settings,
            "status": status,
            "verification_issue_count": len(verification_issues),
            "verification_issues": verification_issues,
            "artifacts": artifacts,
            "items": manifest_items,
        },
    )

    t_write = time.perf_counter() - t_write_start
    _say(quiet, f"[extended-showcase]           -> {profile_path}")
    _say(quiet, f"[extended-showcase]           -> {metric_path}")
    _say(quiet, f"[extended-showcase]           -> {summary_csv_path}")
    _say(quiet, f"[extended-showcase]           -> {routing_csv_path}")
    _say(quiet, f"[extended-showcase]           -> {report_path}")
    _say(quiet, f"[extended-showcase]           -> {brief_path}")
    _say(quiet, f"[extended-showcase]           -> {verification_path}")
    _say(quiet, f"[extended-showcase]           -> {manifest_path} [{t_write:.2f}s]")

    total = t_generate + t_analysis + t_verify + t_write
    _say(quiet, "")
    _say(
        quiet,
        f"[extended-showcase] timings  gen={t_generate:.2f}s  analysis={t_analysis:.2f}s  "
        f"verify={t_verify:.2f}s  write={t_write:.2f}s  total={total:.2f}s",
    )

    if verification_issues:
        _say(quiet, "")
        _say(quiet, f"[extended-showcase] issues ({len(verification_issues)}):")
        for issue in verification_issues:
            _say(quiet, f"  - {issue}")
        _say(quiet, f"[extended-showcase] see {verification_path} for full details")
    else:
        _say(quiet, "")
        _say(
            quiet,
            "[extended-showcase] AMI-first deterministic verification passed for all seven "
            "showcase series, including the coarse per-series semantic checks",
        )

    if quiet:
        print(f"[extended-showcase] verification {status}", flush=True)
    return 0 if not verification_issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
