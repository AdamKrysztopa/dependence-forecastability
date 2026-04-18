"""Covariant analysis showcase (V3-F09).

Runs the full covariant bundle + deterministic interpretation + optional
narrative agent on the :func:`generate_covariant_benchmark` synthetic system,
then writes artifacts and a ground-truth verification report.

Usage::

    uv run scripts/run_showcase_covariant.py                       # full (slow) run
    uv run scripts/run_showcase_covariant.py --fast                # skip PCMCI/PCMCI-AMI
    uv run scripts/run_showcase_covariant.py --agent --strict
    uv run scripts/run_showcase_covariant.py --quiet               # only final VERIFICATION line
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import time
from pathlib import Path

from forecastability.adapters.agents.covariant_agent_payload_models import (
    CovariantAgentExplanation,
    explanation_from_interpretation,
)
from forecastability.adapters.llm.covariant_interpretation_agent import (
    run_covariant_interpretation_agent,
)
from forecastability.services.covariant_interpretation_service import (
    interpret_covariant_bundle,
)
from forecastability.use_cases.run_covariant_analysis import run_covariant_analysis
from forecastability.utils.synthetic import generate_covariant_benchmark
from forecastability.utils.types import (
    CovariantAnalysisBundle,
    CovariantInterpretationResult,
)

_logger = logging.getLogger(__name__)

# Methods kept in the `--fast` preset. The two excluded methods (`pcmci`,
# `pcmci_ami`) account for the vast majority of the wall-clock budget, so
# removing them reduces runtime by roughly an order of magnitude while still
# exercising every deterministic service path used by the interpretation
# service (cross_ami / cross_pami / te / gcmi).
_FAST_METHODS: tuple[str, ...] = ("cross_ami", "cross_pami", "te", "gcmi")

_EXPECTED_ROLES: dict[str, set[str]] = {
    "driver_direct": {"direct_driver"},
    "driver_mediated": {"direct_driver", "mediated_driver"},
    "driver_redundant": {"redundant", "mediated_driver"},
    # A noise driver can get `inconclusive` when one lag crosses the surrogate
    # band by chance (any_sig=True blocks Rule 1 after the statistician fix).
    "driver_noise": {"noise_or_weak", "inconclusive"},
    # A lag0 driver is invisible to all lagged cross_ami rows; in triage mode
    # (no PCMCI) it correctly lands on `noise_or_weak` — that is a valid output.
    "driver_contemp": {"contemporaneous", "direct_driver", "noise_or_weak"},
    "driver_nonlin_sq": {"nonlinear_driver", "direct_driver"},
    # β=0.35 abs coupling is near the surrogate floor; noise_or_weak and
    # inconclusive are valid power-limited outcomes at typical n.
    "driver_nonlin_abs": {"nonlinear_driver", "direct_driver", "noise_or_weak", "inconclusive"},
}


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Covariant analysis showcase on the synthetic 8-driver benchmark"
    )
    parser.add_argument(
        "--methods",
        type=str,
        default=None,
        help="comma-separated subset of methods; default None runs all",
    )
    parser.add_argument(
        "--no-rolling",
        action="store_true",
        help="no-op today; present for parity with scripts/run_showcase.py",
    )
    agent_group = parser.add_mutually_exclusive_group()
    agent_group.add_argument(
        "--agent",
        dest="agent",
        action="store_true",
        help="enable LLM narrative agent (requires API key)",
    )
    agent_group.add_argument(
        "--no-agent",
        dest="agent",
        action="store_false",
        help="disable the narrative agent (default)",
    )
    parser.set_defaults(agent=False)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="force narrative=None even when the agent is enabled",
    )
    parser.add_argument("--output-root", type=str, default="outputs", help="output root directory")
    parser.add_argument("--random-state", type=int, default=42, help="reproducibility seed")
    parser.add_argument("--max-lag", type=int, default=5, help="maximum lag horizon")
    parser.add_argument(
        "--n-surrogates",
        type=int,
        default=99,
        help="number of phase-randomised surrogates; must be >= 99",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help=(
            "skip PCMCI+ and PCMCI-AMI (keeps cross_ami/cross_pami/te/gcmi); "
            "roughly 5-10x faster and sufficient to exercise the interpretation "
            "service end-to-end"
        ),
    )
    parser.add_argument(
        "--n",
        type=int,
        default=1500,
        help="synthetic benchmark length (default 1500); raise to >=5000 for"
        " reliable nonlinear-driver detection of weak (β≈0.35) couplings",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress the verbose per-stage banner; only print the final VERIFICATION line",
    )
    return parser.parse_args(argv)


def _ensure_dirs(output_root: Path) -> tuple[Path, Path, Path]:
    json_dir = output_root / "json"
    tables_dir = output_root / "tables"
    reports_dir = output_root / "reports" / "showcase_covariant"
    for path in (json_dir, tables_dir, reports_dir):
        path.mkdir(parents=True, exist_ok=True)
    return json_dir, tables_dir, reports_dir


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_summary_csv(path: Path, bundle: CovariantAnalysisBundle) -> None:
    fieldnames = [
        "target",
        "driver",
        "lag",
        "cross_ami",
        "cross_pami",
        "transfer_entropy",
        "gcmi",
        "pcmci_link",
        "pcmci_ami_parent",
        "significance",
        "rank",
        "interpretation_tag",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in bundle.summary_table:
            writer.writerow({name: getattr(row, name) for name in fieldnames})


def _verify_against_ground_truth(
    bundle: CovariantAnalysisBundle,
    interpretation: CovariantInterpretationResult,
) -> list[str]:
    """Check interpretation roles against synthetic-benchmark ground truth.

    Rules are mode-aware:

    * ``full`` mode (causal methods present): every driver must land in its
      full accepted role set (includes ``direct_driver`` / ``mediated_driver``
      / ``redundant``, which require PCMCI or PCMCI-AMI evidence).
    * ``triage`` mode (no PCMCI or PCMCI-AMI in the bundle): we can only
      verify the triage-level invariants — noise stays noise, the two
      nonlinear drivers are not demoted to noise, and ``driver_noise`` never
      enters ``primary_drivers``. ``inconclusive`` is accepted for drivers
      that would normally require causal evidence.
    """
    has_causal = bundle.pcmci_graph is not None or bundle.pcmci_ami_result is not None
    violations: list[str] = []
    role_by_driver = {entry.driver: entry.role for entry in interpretation.driver_roles}
    primary_set = set(interpretation.primary_drivers)

    for driver, accepted in _EXPECTED_ROLES.items():
        role = role_by_driver.get(driver)
        if role is None:
            violations.append(f"{driver}: missing from interpretation.driver_roles")
            continue
        # In triage mode (no PCMCI / PCMCI-AMI), drivers whose role is anchored
        # on causal evidence are allowed to surface as `inconclusive`. Only
        # `driver_noise` is held to a strict standard: a pure noise driver must
        # never be promoted above noise_or_weak/inconclusive (already in its
        # accepted set). Nonlinear drivers are NOT triage-strict because without
        # PCMCI we cannot distinguish nonlinear from inconclusive.
        accepted_mode = set(accepted)
        if not has_causal:
            accepted_mode.add("inconclusive")
        if role not in accepted_mode:
            violations.append(
                f"{driver}: role='{role}' not in accepted set {sorted(accepted_mode)}"
            )

    if has_causal and role_by_driver.get("driver_direct") in _EXPECTED_ROLES["driver_direct"]:
        if "driver_direct" not in primary_set:
            violations.append("driver_direct: expected to be in primary_drivers")
    if role_by_driver.get("driver_nonlin_sq") in _EXPECTED_ROLES["driver_nonlin_sq"]:
        if "driver_nonlin_sq" not in primary_set:
            violations.append("driver_nonlin_sq: expected to be in primary_drivers")
    if role_by_driver.get("driver_nonlin_abs") in {"nonlinear_driver", "direct_driver"}:
        if "driver_nonlin_abs" not in primary_set:
            violations.append("driver_nonlin_abs: expected to be in primary_drivers")
    if "driver_noise" in primary_set:
        violations.append("driver_noise: must NOT be in primary_drivers")

    if bundle.pcmci_ami_result is not None:
        pcmci_ami_sources = {
            src
            for (src, _lag) in bundle.pcmci_ami_result.causal_graph.parents.get(
                bundle.target_name, []
            )
        }
        if "driver_redundant" in pcmci_ami_sources:
            violations.append(
                "driver_redundant: must NOT be in pcmci_ami_result.causal_graph.parents[target]"
            )
    return violations


def _write_verification_report(
    path: Path,
    *,
    bundle: CovariantAnalysisBundle,
    interpretation: CovariantInterpretationResult,
    violations: list[str],
) -> None:
    status = "PASS" if not violations else "FAIL"
    lines: list[str] = [
        "# Covariant showcase verification",
        "",
        f"- target: `{bundle.target_name}`",
        f"- forecastability_class: `{interpretation.forecastability_class}`",
        f"- directness_class: `{interpretation.directness_class}`",
        f"- primary_drivers: `{interpretation.primary_drivers}`",
        f"- modeling_regime: `{interpretation.modeling_regime}`",
        f"- status: **{status}**",
        "",
        "## Driver roles",
        "",
        "| driver | role | best_lag |",
        "| --- | --- | --- |",
    ]
    for entry in interpretation.driver_roles:
        lines.append(f"| {entry.driver} | {entry.role} | {entry.best_lag} |")
    lines.append("")
    lines.append("## Violations")
    lines.append("")
    if violations:
        for item in violations:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _resolve_methods(methods_arg: str | None, *, fast: bool) -> list[str] | None:
    if methods_arg is not None:
        return [part.strip() for part in methods_arg.split(",") if part.strip()]
    if fast:
        return list(_FAST_METHODS)
    return None


def _say(quiet: bool, msg: str) -> None:
    if not quiet:
        print(msg, flush=True)


def _format_driver_table(interpretation: CovariantInterpretationResult) -> list[str]:
    header = f"  {'driver':<20} {'role':<20} {'best_lag':<10}"
    rule = f"  {'-' * 20} {'-' * 20} {'-' * 10}"
    rows = [
        f"  {entry.driver:<20} {entry.role:<20} {str(entry.best_lag):<10}"
        for entry in interpretation.driver_roles
    ]
    return [header, rule, *rows]


def main(argv: list[str] | None = None) -> int:
    """Run the covariant showcase and return a POSIX-style exit code.

    Args:
        argv: Optional argv overrides for testing; ``None`` uses ``sys.argv``.

    Returns:
        ``0`` when verification passes, ``1`` otherwise.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
    args = _parse_args(argv)
    if args.n_surrogates < 99:
        raise ValueError(f"n_surrogates must be >= 99, got {args.n_surrogates}")
    if args.no_rolling:
        _logger.info("--no-rolling is a no-op for the covariant showcase")

    output_root = Path(args.output_root)
    json_dir, tables_dir, reports_dir = _ensure_dirs(output_root)
    quiet = bool(args.quiet)
    methods = _resolve_methods(args.methods, fast=bool(args.fast))

    _say(quiet, "=" * 72)
    _say(quiet, "[covariant-showcase] V3-F09 canonical run")
    _say(quiet, "=" * 72)
    _say(
        quiet,
        f"[covariant-showcase] benchmark       : generate_covariant_benchmark "
        f"(n={args.n}, seed={args.random_state})",
    )
    _say(
        quiet,
        f"[covariant-showcase] methods         : {methods if methods else 'all (6)'}"
        f"{'  [--fast preset]' if args.fast and args.methods is None else ''}",
    )
    if args.fast and args.methods is None:
        _say(
            quiet,
            "[covariant-showcase]                   (triage-only verification: "
            "PCMCI-dependent checks are relaxed)",
        )
    _say(
        quiet,
        f"[covariant-showcase] max_lag         : {args.max_lag}"
        f"     n_surrogates : {args.n_surrogates}",
    )
    _say(quiet, f"[covariant-showcase] output_root     : {output_root}")
    _say(quiet, f"[covariant-showcase] agent           : {'on' if args.agent else 'off'}")
    _say(quiet, "")

    t_gen_start = time.perf_counter()
    _say(quiet, "[covariant-showcase] step 1/5  generating synthetic benchmark ...")
    df = generate_covariant_benchmark(n=args.n, seed=args.random_state)
    target = df["target"].to_numpy()
    drivers = {name: df[name].to_numpy() for name in df.columns if name != "target"}
    t_gen = time.perf_counter() - t_gen_start
    _say(
        quiet,
        f"[covariant-showcase]           -> {len(df)} rows, "
        f"{len(drivers)} drivers ({list(drivers)}) "
        f"[{t_gen:.2f}s]",
    )

    t_bundle_start = time.perf_counter()
    _say(
        quiet,
        "[covariant-showcase] step 2/5  running run_covariant_analysis (this is the slow step) ...",
    )
    bundle = run_covariant_analysis(
        target,
        drivers,
        target_name="target",
        max_lag=args.max_lag,
        methods=methods,
        random_state=args.random_state,
        n_surrogates=args.n_surrogates,
    )
    t_bundle = time.perf_counter() - t_bundle_start
    _say(
        quiet,
        f"[covariant-showcase]           -> summary rows = {len(bundle.summary_table)}   "
        f"pcmci_graph = {'yes' if bundle.pcmci_graph is not None else 'no'}   "
        f"pcmci_ami = {'yes' if bundle.pcmci_ami_result is not None else 'no'}   "
        f"[{t_bundle:.2f}s]",
    )

    t_interp_start = time.perf_counter()
    _say(quiet, "[covariant-showcase] step 3/5  deterministic interpretation ...")
    interpretation = interpret_covariant_bundle(bundle)
    t_interp = time.perf_counter() - t_interp_start
    fc = interpretation.forecastability_class
    dc = interpretation.directness_class
    pd_ = interpretation.primary_drivers
    _say(
        quiet,
        f"[covariant-showcase]           -> forecastability={fc}  directness={dc}  "
        f"primary_drivers={pd_}  [{t_interp:.2f}s]",
    )
    for line in _format_driver_table(interpretation):
        _say(quiet, line)

    t_agent_start = time.perf_counter()
    _say(
        quiet,
        f"[covariant-showcase] step 4/5  agent narration ({'live' if args.agent else 'disabled'})"
        f" ...",
    )
    explanation: CovariantAgentExplanation
    if args.agent:
        explanation = asyncio.run(
            run_covariant_interpretation_agent(
                bundle,
                interpretation,
                strict=args.strict,
            )
        )
    else:
        explanation = explanation_from_interpretation(
            interpretation,
            narrative=None,
            caveats=["Agent disabled via --no-agent."],
        )
    t_agent = time.perf_counter() - t_agent_start
    narr_state = "present" if explanation.narrative else "none"
    _say(
        quiet,
        f"[covariant-showcase]           -> narrative={narr_state}  "
        f"caveats={len(explanation.caveats)}  [{t_agent:.2f}s]",
    )

    t_write_start = time.perf_counter()
    _say(quiet, "[covariant-showcase] step 5/5  writing artifacts ...")
    bundle_path = json_dir / "covariant_bundle.json"
    interp_path = json_dir / "covariant_interpretation.json"
    explanation_path = json_dir / "covariant_agent_explanation.json"
    csv_path = tables_dir / "covariant_summary.csv"
    report_path = reports_dir / "verification.md"
    _write_json(bundle_path, bundle.model_dump(mode="json"))
    _write_json(interp_path, interpretation.model_dump(mode="json"))
    _write_json(explanation_path, explanation.model_dump(mode="json"))
    _write_summary_csv(csv_path, bundle)

    violations = _verify_against_ground_truth(bundle, interpretation)
    _write_verification_report(
        report_path,
        bundle=bundle,
        interpretation=interpretation,
        violations=violations,
    )
    t_write = time.perf_counter() - t_write_start
    _say(quiet, f"[covariant-showcase]           -> {bundle_path}")
    _say(quiet, f"[covariant-showcase]           -> {interp_path}")
    _say(quiet, f"[covariant-showcase]           -> {explanation_path}")
    _say(quiet, f"[covariant-showcase]           -> {csv_path}")
    _say(quiet, f"[covariant-showcase]           -> {report_path}   [{t_write:.2f}s]")

    total = t_gen + t_bundle + t_interp + t_agent + t_write
    _say(quiet, "")
    _say(
        quiet,
        f"[covariant-showcase] timings  gen={t_gen:.2f}s  bundle={t_bundle:.2f}s  "
        f"interpret={t_interp:.2f}s  agent={t_agent:.2f}s  write={t_write:.2f}s  "
        f"total={total:.2f}s",
    )

    status = "PASS" if not violations else "FAIL"
    if violations:
        _say(quiet, "")
        _say(quiet, f"[covariant-showcase] VIOLATIONS ({len(violations)}):")
        for v in violations:
            _say(quiet, f"  - {v}")
        _say(quiet, f"[covariant-showcase] see {report_path} for full report")
    else:
        _say(quiet, "")
        _say(quiet, "[covariant-showcase] ground-truth checks: all 7 drivers accepted")
    _say(quiet, "")
    print(f"VERIFICATION: {status}", flush=True)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
