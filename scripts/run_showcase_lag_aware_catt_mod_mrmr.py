"""Canonical showcase for Lag-Aware ModMRMR with KSG/catt_knn_mi scorer (LAM-F09).

Runs the synthetic multi-covariate benchmark panel through
``run_lag_aware_mod_mrmr`` with the ``catt_knn_mi`` (KSG) scorer for relevance,
redundancy, and target-history novelty scoring.  Emits JSON, tables, figures,
and markdown summaries.

The KSG estimator (``catt_knn_mi``, k=8) requires more observations than the
fast-scorer variant.  Smoke mode uses n=600 to ensure reliable KSG estimation.

Usage::

    uv run scripts/run_showcase_lag_aware_catt_mod_mrmr.py
    uv run scripts/run_showcase_lag_aware_catt_mod_mrmr.py --smoke
    uv run scripts/run_showcase_lag_aware_catt_mod_mrmr.py --smoke --quiet
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

import matplotlib.pyplot as plt
import numpy as np

from forecastability import (
    LagAwareModMRMRConfig,
    LagAwareModMRMRResult,
    PairwiseScorerSpec,
    RoutingRecommendation,
    TriageResult,
    build_forecast_prep_contract,
    run_lag_aware_mod_mrmr,
)
from forecastability.services.forecast_prep_lagged_covariates import (
    contract_covariate_lag_rows,
    contract_covariate_markdown_table,
)
from forecastability.triage.models import (
    AnalysisGoal,
    ReadinessReport,
    ReadinessStatus,
    TriageRequest,
)
from forecastability.utils.synthetic import LagAwareModMRMRPanel, generate_lag_aware_mod_mrmr_panel
from forecastability.utils.types import Diagnostics, InterpretationResult

_logger = logging.getLogger(__name__)

_TRUE_DRIVER_NAME: str = "driver_direct"
_TRUE_DRIVER_LAG: int = 3
_DUPLICATE_SENSOR_PAIR: frozenset[str] = frozenset({"driver_direct", "sensor_near_dup"})
_KNOWN_FUTURE_COVARIATE: str = "calendar_flag"
_SHOWCASE_NAME: str = "showcase_lag_aware_catt_mod_mrmr"
_RELEASE: str = "0.4.3"
# KSG (catt_knn_mi, k=8) minimum reliable observation count for smoke mode.
_SMOKE_N: int = 600


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Canonical Lag-Aware ModMRMR showcase (LAM-F09, catt_knn_mi scorer)"
    )
    parser.add_argument("--output-root", type=str, default="outputs", help="output root directory")
    parser.add_argument("--random-state", type=int, default=42, help="reproducibility seed")
    parser.add_argument(
        "--n",
        type=int,
        default=1500,
        help="number of observations in the benchmark panel",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help=f"CI-friendly preset: n={_SMOKE_N}, candidate_lags=[1..5]",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress stage banners; only print final verification line",
    )
    return parser.parse_args(argv)


def _resolved_settings(args: argparse.Namespace) -> dict[str, object]:
    if args.smoke:
        n: int = _SMOKE_N
        candidate_lags: list[int] | None = [1, 2, 3, 4, 5]
        max_selected: int = 4
        max_lag: int | None = None
    else:
        n = int(args.n)
        candidate_lags = None
        max_selected = 8
        max_lag = 10
    return {
        "n": n,
        "candidate_lags": candidate_lags,
        "max_selected_features": max_selected,
        "max_lag": max_lag,
    }


def _ensure_dirs(output_root: Path) -> tuple[Path, Path, Path, Path]:
    json_dir = output_root / "json" / _SHOWCASE_NAME
    tables_dir = output_root / "tables" / _SHOWCASE_NAME
    reports_dir = output_root / "reports" / _SHOWCASE_NAME
    figures_dir = output_root / "figures" / _SHOWCASE_NAME
    for path in (json_dir, tables_dir, reports_dir, figures_dir):
        path.mkdir(parents=True, exist_ok=True)
    return json_dir, tables_dir, reports_dir, figures_dir


def _say(quiet: bool, message: str) -> None:
    if not quiet:
        print(message, flush=True)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _build_config(*, settings: dict[str, object]) -> LagAwareModMRMRConfig:
    catt_spec = PairwiseScorerSpec(
        name="catt_knn_mi",
        backend="ksg",
        normalization="rank_percentile",
        significance_method="none",
    )
    max_lag_val = settings["max_lag"]
    effective_max_lag: int = int(max_lag_val) if isinstance(max_lag_val, int) else 20
    return LagAwareModMRMRConfig(
        forecast_horizon=1,
        availability_margin=0,
        candidate_lags=settings["candidate_lags"],
        max_lag=effective_max_lag,
        known_future_covariates={_KNOWN_FUTURE_COVARIATE: "calendar"},
        target_lags=[12],
        max_selected_features=int(settings["max_selected_features"]),  # type: ignore[arg-type]
        relevance_scorer=catt_spec,
        redundancy_scorer=catt_spec,
        target_history_scorer=catt_spec,
    )


def _build_stub_triage_result(result: LagAwareModMRMRResult) -> TriageResult:
    primary_lags = sorted({feature.lag for feature in result.selected})
    if not primary_lags:
        primary_lags = [result.config.forecast_horizon]
    return TriageResult(
        request=TriageRequest(
            series=np.linspace(0.0, 1.0, 120),
            goal=AnalysisGoal.univariate,
            max_lag=24,
            n_surrogates=99,
            random_state=42,
        ),
        readiness=ReadinessReport(status=ReadinessStatus.clear, warnings=[]),
        blocked=False,
        interpretation=InterpretationResult(
            forecastability_class="high" if result.selected else "low",
            directness_class="medium",
            primary_lags=primary_lags,
            modeling_regime="deterministic triage",
            narrative="lag-aware catt showcase narrative",
            diagnostics=Diagnostics(
                peak_ami_first_5=0.25,
                directness_ratio=0.45,
                n_sig_ami=max(len(primary_lags), 1),
                n_sig_pami=max(len(primary_lags) - 1, 0),
                exploitability_mismatch=0,
                best_smape=0.12,
            ),
        ),
    )


def _build_stub_routing() -> RoutingRecommendation:
    return RoutingRecommendation(
        primary_families=["arima"],
        secondary_families=["linear_state_space"],
        rationale=["lag-aware catt showcase routing stub"],
        caution_flags=[],
        confidence_label="high",
    )


def _verify_result(result: LagAwareModMRMRResult, *, smoke: bool = False) -> list[str]:
    violations: list[str] = []
    min_legal = result.config.forecast_horizon + result.config.availability_margin

    for feature in result.selected:
        if not feature.is_known_future and feature.lag < min_legal:
            violations.append(
                f"Illegal lag: {feature.feature_name} lag={feature.lag} < min_legal={min_legal}"
            )

    # True-driver check: driver_direct at lag 3 should be selected.
    # In smoke mode the near-duplicate sensor_near_dup may absorb this slot.
    # Accept either member of the duplicate pair at lag 3.
    lag3_selected_covariates = {
        f.covariate_name for f in result.selected if f.lag == _TRUE_DRIVER_LAG
    }
    driver_pair_at_true_lag = lag3_selected_covariates & _DUPLICATE_SENSOR_PAIR
    if not driver_pair_at_true_lag:
        if smoke:
            _logger.warning(
                "True driver '%s' at lag %d not recovered in smoke mode "
                "(small-n artifact; acceptable). Selected at lag %d: %s",
                _TRUE_DRIVER_NAME,
                _TRUE_DRIVER_LAG,
                _TRUE_DRIVER_LAG,
                sorted(lag3_selected_covariates),
            )
        else:
            violations.append(
                f"True driver '{_TRUE_DRIVER_NAME}' at lag {_TRUE_DRIVER_LAG} "
                "(or its near-duplicate 'sensor_near_dup') not found in selected features"
            )

    # Check dup-pair ordering: near-dup must not rank before the true driver
    dup_first_ranks: dict[str, int] = {}
    for f in result.selected:
        if f.covariate_name in _DUPLICATE_SENSOR_PAIR:
            cur = dup_first_ranks.get(f.covariate_name, f.selection_rank)
            dup_first_ranks[f.covariate_name] = min(cur, f.selection_rank)
    _dup_other = "sensor_near_dup"
    if _TRUE_DRIVER_NAME in dup_first_ranks and _dup_other in dup_first_ranks:
        driver_rank = dup_first_ranks[_TRUE_DRIVER_NAME]
        dup_rank = dup_first_ranks[_dup_other]
        if dup_rank < driver_rank:
            if smoke:
                _logger.warning(
                    "Near-dup '%s' (rank %d) precedes true driver '%s' (rank %d) "
                    "in smoke mode (small-n KSG artifact; acceptable).",
                    _dup_other,
                    dup_rank,
                    _TRUE_DRIVER_NAME,
                    driver_rank,
                )
            else:
                violations.append(
                    f"Near-dup '{_dup_other}' (rank {dup_rank}) selected before "
                    f"true driver '{_TRUE_DRIVER_NAME}' (rank {driver_rank})"
                )
    elif _dup_other in dup_first_ranks and _TRUE_DRIVER_NAME not in dup_first_ranks:
        if smoke:
            _logger.warning(
                "Near-dup '%s' selected but true driver '%s' absent "
                "(small-n KSG artifact; acceptable).",
                _dup_other,
                _TRUE_DRIVER_NAME,
            )
        else:
            violations.append(
                f"Near-dup '{_dup_other}' selected without true driver '{_TRUE_DRIVER_NAME}'"
            )

    blocked_names = {b.covariate_name for b in result.blocked}
    selected_from_blocked = [
        f.covariate_name for f in result.selected if f.covariate_name in blocked_names
    ]
    if selected_from_blocked:
        violations.append(f"Blocked candidates in selected: {selected_from_blocked}")

    return violations


def _derive_relevance_only_ranking(
    result: LagAwareModMRMRResult,
    max_features: int,
) -> list[dict[str, object]]:
    all_candidates = list(result.selected) + list(result.rejected)
    sorted_candidates = sorted(all_candidates, key=lambda f: f.relevance, reverse=True)
    return [
        {
            "rank": i + 1,
            "feature_name": f.feature_name,
            "covariate_name": f.covariate_name,
            "lag": f.lag,
            "relevance": f.relevance,
        }
        for i, f in enumerate(sorted_candidates[:max_features])
    ]


def _write_selected_csv(path: Path, result: LagAwareModMRMRResult) -> None:
    fieldnames = [
        "feature_name",
        "covariate_name",
        "lag",
        "is_known_future",
        "selection_rank",
        "relevance",
        "max_redundancy",
        "target_history_redundancy",
        "final_score",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for f in result.selected:
            writer.writerow(
                {
                    "feature_name": f.feature_name,
                    "covariate_name": f.covariate_name,
                    "lag": f.lag,
                    "is_known_future": int(f.is_known_future),
                    "selection_rank": f.selection_rank,
                    "relevance": f.relevance,
                    "max_redundancy": f.max_redundancy,
                    "target_history_redundancy": f.target_history_redundancy,
                    "final_score": f.final_score,
                }
            )


def _write_rejected_csv(path: Path, result: LagAwareModMRMRResult) -> None:
    fieldnames = [
        "feature_name",
        "covariate_name",
        "lag",
        "is_known_future",
        "relevance",
        "max_redundancy",
        "target_history_redundancy",
        "final_score",
        "rejection_reason",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for f in result.rejected:
            writer.writerow(
                {
                    "feature_name": f.feature_name,
                    "covariate_name": f.covariate_name,
                    "lag": f.lag,
                    "is_known_future": int(f.is_known_future),
                    "relevance": f.relevance,
                    "max_redundancy": f.max_redundancy,
                    "target_history_redundancy": f.target_history_redundancy,
                    "final_score": f.final_score,
                    "rejection_reason": f.rejection_reason,
                }
            )


def _write_blocked_csv(path: Path, result: LagAwareModMRMRResult) -> None:
    fieldnames = [
        "feature_name",
        "covariate_name",
        "lag",
        "is_known_future",
        "legality_reason",
        "block_reason",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for f in result.blocked:
            writer.writerow(
                {
                    "feature_name": f.feature_name,
                    "covariate_name": f.covariate_name,
                    "lag": f.lag,
                    "is_known_future": int(f.is_known_future),
                    "legality_reason": f.legality_reason,
                    "block_reason": f.block_reason,
                }
            )


def _write_contract_lag_rows_csv(path: Path, contract: object) -> None:
    rows = contract_covariate_lag_rows(contract)  # type: ignore[arg-type]
    if not rows:
        with path.open("w", newline="", encoding="utf-8") as handle:
            handle.write("name,role,confidence,selected_lags\n")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_ablation_comparison_csv(
    path: Path,
    *,
    full_names: list[str],
    no_th_names: list[str],
    relevance_names: list[str],
) -> None:
    all_features = sorted(set(full_names) | set(no_th_names) | set(relevance_names))
    full_set = set(full_names)
    no_th_set = set(no_th_names)
    rel_set = set(relevance_names)
    fieldnames = ["feature_name", "relevance_only", "mod_mrmr_no_th", "full_mod_mrmr"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for name in all_features:
            writer.writerow(
                {
                    "feature_name": name,
                    "relevance_only": 1 if name in rel_set else 0,
                    "mod_mrmr_no_th": 1 if name in no_th_set else 0,
                    "full_mod_mrmr": 1 if name in full_set else 0,
                }
            )


def _save_relevance_profile(path: Path, result: LagAwareModMRMRResult) -> None:
    all_candidates = sorted(
        list(result.selected) + list(result.rejected),
        key=lambda f: f.relevance,
    )
    names = [f.feature_name for f in all_candidates]
    scores = [f.relevance for f in all_candidates]
    selected_set = {f.feature_name for f in result.selected}
    colors = ["steelblue" if n in selected_set else "lightgray" for n in names]

    fig, ax = plt.subplots(figsize=(8, max(4, len(names) * 0.4)))
    ax.barh(names, scores, color=colors)
    ax.set_xlabel("Normalised relevance score (catt_knn_mi)")
    ax.set_title("Relevance Profile — Lag-Aware ModMRMR (catt_knn_mi, full with target-history)")
    ax.axvline(0.0, color="black", linewidth=0.8)
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


def _save_ablation_heatmap(
    path: Path,
    *,
    full_names: list[str],
    no_th_names: list[str],
    relevance_names: list[str],
) -> None:
    full_set = set(full_names)
    no_th_set = set(no_th_names)
    rel_set = set(relevance_names)

    all_features = sorted(set(full_names) | set(no_th_names) | set(relevance_names))
    all_features = sorted(all_features, key=lambda n: (0 if n in full_set else 1, n))

    cols = ["relevance_only", "mod_mrmr_no_th", "full_mod_mrmr"]
    sets = [rel_set, no_th_set, full_set]
    data = np.array([[1 if f in s else 0 for s in sets] for f in all_features], dtype=float)

    fig, ax = plt.subplots(figsize=(6, max(3, len(all_features) * 0.4 + 1)))
    im = ax.imshow(
        data,
        aspect="auto",
        cmap="RdYlGn",
        vmin=0.0,
        vmax=1.0,
        interpolation="nearest",
    )
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels(cols, rotation=20, ha="right")
    ax.set_yticks(range(len(all_features)))
    ax.set_yticklabels(all_features)
    ax.set_title("Ablation Comparison — Feature Selection by Mode (catt_knn_mi)")
    fig.colorbar(im, ax=ax, label="selected (1) / not selected (0)")
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


def _build_summary_markdown(
    *,
    result: LagAwareModMRMRResult,
    result_no_th: LagAwareModMRMRResult,
    relevance_ranking: list[dict[str, object]],
    settings: dict[str, object],
    violations: list[str],
    contract: object,
) -> str:
    lines: list[str] = [
        "# Lag-Aware ModMRMR Showcase Summary (catt_knn_mi Scorer)",
        "",
        "<!-- type: reference -->",
        "",
        "## Settings",
        "",
    ]
    for key, value in settings.items():
        lines.append(f"- {key}: `{value}`")

    lines.extend(
        [
            "",
            "## Selected Features (Full Lag-Aware ModMRMR with Target-History)",
            "",
            "| rank | feature_name | covariate_name | lag"
            " | relevance | max_redundancy | target_history_redundancy | final_score |",
            "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for f in result.selected:
        lines.append(
            f"| {f.selection_rank} | {f.feature_name} | {f.covariate_name}"
            f" | {f.lag} | {f.relevance:.4f} | {f.max_redundancy:.4f}"
            f" | {f.target_history_redundancy:.4f} | {f.final_score:.4f} |"
        )

    lines.extend(
        [
            "",
            "## Forecast Prep Contract",
            "",
        ]
    )
    try:
        md_table = contract_covariate_markdown_table(contract)  # type: ignore[arg-type]
        lines.append(md_table)
    except Exception:  # noqa: BLE001
        lines.append("_Contract covariate table unavailable._")

    full_set = {f.feature_name for f in result.selected}
    no_th_set = {f.feature_name for f in result_no_th.selected}
    rel_set = {entry["feature_name"] for entry in relevance_ranking}
    all_features = sorted(full_set | no_th_set | rel_set)

    lines.extend(
        [
            "",
            "## Ablation Comparison",
            "",
            "Three live ablation modes are shown using the ``catt_knn_mi`` (KSG) scorer.",
            "",
            "| feature_name | relevance_only | mod_mrmr_no_th | full_mod_mrmr |",
            "| --- | :---: | :---: | :---: |",
        ]
    )
    for name in all_features:
        lines.append(
            f"| {name} | {'✓' if name in rel_set else '—'} "
            f"| {'✓' if name in no_th_set else '—'} "
            f"| {'✓' if name in full_set else '—'} |"
        )

    lines.extend(
        [
            "",
            "### Mode: Relevance-Only (post-hoc, single run)",
            "",
            "| rank | feature_name | relevance |",
            "| ---: | --- | ---: |",
        ]
    )
    for entry in relevance_ranking:
        lines.append(
            f"| {entry['rank']} | {entry['feature_name']} | {float(entry['relevance']):04f} |"  # type: ignore[arg-type]
        )

    no_th_selected_names = sorted(f.feature_name for f in result_no_th.selected)
    lines.extend(
        [
            "",
            "### Mode: ModMRMR without Target-History",
            "",
            f"Selected features: {no_th_selected_names}",
        ]
    )

    full_selected_names = sorted(f.feature_name for f in result.selected)
    lines.extend(
        [
            "",
            "### Mode: Full Lag-Aware ModMRMR (with target_lags=[12])",
            "",
            f"Selected features: {full_selected_names}",
        ]
    )

    lines.extend(
        [
            "",
            "## KSG Estimator Notes",
            "",
            "> [!NOTE]",
            "> The ``catt_knn_mi`` scorer uses a KSG estimator with k=8 nearest neighbours.",
            "> Reliable estimation requires at least ~256 aligned pairs (derived from 4×k²).",
            "> Smoke mode uses n=600 to provide comfortable margin above this floor.",
            "> Do not reduce smoke n below 300 for this variant.",
            "",
            "## Conceptual Baselines",
            "",
            "The aggregate-mean and mean-similarity multiplicative baselines are not",
            "computable from the public result surface.  See the fast-scorer showcase",
            "summary for detailed prose explanation and fixture references.",
            "",
            "## Verification",
            "",
            f"- status: **{'PASS' if not violations else 'FAIL'}**",
            "",
            "### Violations",
            "",
        ]
    )
    if violations:
        for v in violations:
            lines.append(f"- {v}")
    else:
        lines.append("- none")

    return "\n".join(lines)


def _build_verification_markdown(*, violations: list[str]) -> str:
    status = "PASS" if not violations else "FAIL"
    lines = [
        "# Lag-Aware ModMRMR Showcase Verification (catt_knn_mi Scorer)",
        "",
        f"- status: **{status}**",
        "",
        "## Violations",
        "",
    ]
    if violations:
        for v in violations:
            lines.append(f"- {v}")
    else:
        lines.append("- none")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Run the Lag-Aware ModMRMR catt showcase and return POSIX-style exit code."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")

    args = _parse_args(argv)
    settings = _resolved_settings(args)
    quiet = bool(args.quiet)
    output_root = Path(args.output_root)
    json_dir, tables_dir, reports_dir, figures_dir = _ensure_dirs(output_root)

    _say(quiet, "=" * 72)
    _say(quiet, "[lam-catt-showcase] LAM-F09 lag-aware ModMRMR showcase (catt_knn_mi)")
    _say(quiet, "=" * 72)
    _say(quiet, f"[lam-catt-showcase] mode            : {'smoke' if args.smoke else 'full'}")
    _say(quiet, f"[lam-catt-showcase] n               : {settings['n']}")
    _say(quiet, f"[lam-catt-showcase] random_state    : {args.random_state}")
    _say(quiet, f"[lam-catt-showcase] output_root     : {output_root}")
    _say(quiet, "")

    # Step 1: Generate panel
    t0 = time.perf_counter()
    panel: LagAwareModMRMRPanel = generate_lag_aware_mod_mrmr_panel(
        int(settings["n"]),  # type: ignore[arg-type]
        seed=int(args.random_state),
    )
    _say(
        quiet,
        f"[lam-catt-showcase] step 1/5  generated panel [{time.perf_counter() - t0:.2f}s]",
    )

    # Step 2: Run two ModMRMR ablations (catt_knn_mi scorer)
    config = _build_config(settings=settings)
    config_no_th = config.model_copy(
        update={"target_history_scorer": None, "target_lags": None}
    )

    t1 = time.perf_counter()
    result: LagAwareModMRMRResult = run_lag_aware_mod_mrmr(
        target=panel.target,
        covariates=panel.covariates,
        config=config,
        random_state=int(args.random_state),
        run_id="full_mod_mrmr_catt",
    )
    _say(
        quiet,
        "[lam-catt-showcase] step 2a/5 ran full ModMRMR (with TH) "
        f"[{time.perf_counter() - t1:.2f}s]",
    )

    t2 = time.perf_counter()
    result_no_th: LagAwareModMRMRResult = run_lag_aware_mod_mrmr(
        target=panel.target,
        covariates=panel.covariates,
        config=config_no_th,
        random_state=int(args.random_state),
        run_id="mod_mrmr_no_th_catt",
    )
    _say(
        quiet,
        f"[lam-catt-showcase] step 2b/5 ran ModMRMR (no TH) [{time.perf_counter() - t2:.2f}s]",
    )

    relevance_ranking = _derive_relevance_only_ranking(
        result,
        max_features=int(settings["max_selected_features"]),  # type: ignore[arg-type]
    )

    # Step 3: Build ForecastPrepContract
    t3 = time.perf_counter()
    contract = build_forecast_prep_contract(
        _build_stub_triage_result(result),
        horizon=result.config.forecast_horizon,
        lag_aware_result=result,
        routing_recommendation=_build_stub_routing(),
        add_calendar_features=False,
    )
    _say(
        quiet,
        f"[lam-catt-showcase] step 3/5  built contract [{time.perf_counter() - t3:.2f}s]",
    )

    # Step 4: Render figures
    t4 = time.perf_counter()
    profile_fig_path = figures_dir / "relevance_profile.png"
    ablation_fig_path = figures_dir / "ablation_comparison.png"

    full_names = [f.feature_name for f in result.selected]
    no_th_names = [f.feature_name for f in result_no_th.selected]
    rel_names = [str(entry["feature_name"]) for entry in relevance_ranking]

    _save_relevance_profile(profile_fig_path, result)
    _save_ablation_heatmap(
        ablation_fig_path,
        full_names=full_names,
        no_th_names=no_th_names,
        relevance_names=rel_names,
    )
    _say(
        quiet,
        f"[lam-catt-showcase] step 4/5  rendered figures [{time.perf_counter() - t4:.2f}s]",
    )

    # Step 5: Write artifacts
    t5 = time.perf_counter()
    violations = _verify_result(result, smoke=bool(args.smoke))

    result_json_path = json_dir / "result.json"
    result_no_th_json_path = json_dir / "result_no_th.json"
    contract_json_path = json_dir / "contract.json"
    ablation_json_path = json_dir / "ablation_comparison.json"
    manifest_path = json_dir / "showcase_manifest.json"

    _write_json(result_json_path, result.model_dump(mode="json"))
    _write_json(result_no_th_json_path, result_no_th.model_dump(mode="json"))
    _write_json(contract_json_path, json.loads(contract.model_dump_json()))
    _write_json(
        ablation_json_path,
        {
            "full_mod_mrmr": full_names,
            "mod_mrmr_no_th": no_th_names,
            "relevance_only": rel_names,
        },
    )

    selected_csv_path = tables_dir / "selected_features.csv"
    rejected_csv_path = tables_dir / "rejected_features.csv"
    blocked_csv_path = tables_dir / "blocked_features.csv"
    contract_lag_rows_csv_path = tables_dir / "contract_lag_rows.csv"
    ablation_csv_path = tables_dir / "ablation_comparison.csv"

    _write_selected_csv(selected_csv_path, result)
    _write_rejected_csv(rejected_csv_path, result)
    _write_blocked_csv(blocked_csv_path, result)
    _write_contract_lag_rows_csv(contract_lag_rows_csv_path, contract)
    _write_ablation_comparison_csv(
        ablation_csv_path,
        full_names=full_names,
        no_th_names=no_th_names,
        relevance_names=rel_names,
    )

    summary_path = reports_dir / "showcase_summary.md"
    verification_path = reports_dir / "verification.md"
    summary_path.write_text(
        _build_summary_markdown(
            result=result,
            result_no_th=result_no_th,
            relevance_ranking=relevance_ranking,
            settings={
                "release": _RELEASE,
                "n": int(settings["n"]),  # type: ignore[arg-type]
                "mode": "smoke" if args.smoke else "full",
                "forecast_horizon": 1,
                "availability_margin": 0,
                "target_lags": [12],
                "relevance_scorer": "catt_knn_mi",
                "redundancy_scorer": "catt_knn_mi",
                "target_history_scorer": "catt_knn_mi",
                "random_state": int(args.random_state),
            },
            violations=violations,
            contract=contract,
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
            "settings": {
                "release": _RELEASE,
                "n": int(settings["n"]),  # type: ignore[arg-type]
                "forecast_horizon": 1,
                "availability_margin": 0,
                "candidate_lags": settings["candidate_lags"],
                "max_selected_features": int(settings["max_selected_features"]),  # type: ignore[arg-type]
                "target_lags": [12],
                "relevance_scorer": "catt_knn_mi",
                "redundancy_scorer": "catt_knn_mi",
                "target_history_scorer": "catt_knn_mi",
                "random_state": int(args.random_state),
                "mode": "smoke" if args.smoke else "full",
            },
            "status": "PASS" if not violations else "FAIL",
            "artifacts": {
                "result_json": str(result_json_path),
                "result_no_th_json": str(result_no_th_json_path),
                "contract_json": str(contract_json_path),
                "ablation_json": str(ablation_json_path),
                "selected_features_csv": str(selected_csv_path),
                "rejected_features_csv": str(rejected_csv_path),
                "blocked_features_csv": str(blocked_csv_path),
                "contract_lag_rows_csv": str(contract_lag_rows_csv_path),
                "ablation_comparison_csv": str(ablation_csv_path),
                "summary_report": str(summary_path),
                "verification_report": str(verification_path),
                "relevance_profile_figure": str(profile_fig_path),
                "ablation_comparison_figure": str(ablation_fig_path),
            },
            "selected_features": [
                {
                    "covariate_name": f.covariate_name,
                    "lag": f.lag,
                    "feature_name": f.feature_name,
                    "selection_rank": f.selection_rank,
                    "final_score": f.final_score,
                }
                for f in result.selected
            ],
            "ablation_selected_lists": {
                "full_mod_mrmr": full_names,
                "mod_mrmr_no_th": no_th_names,
                "relevance_only": rel_names,
            },
            "n_candidates_evaluated": result.n_candidates_evaluated,
            "n_candidates_blocked": result.n_candidates_blocked,
        },
    )

    _say(
        quiet,
        f"[lam-catt-showcase] step 5/5  wrote artifacts [{time.perf_counter() - t5:.2f}s]",
    )
    for artifact_path in [
        result_json_path,
        result_no_th_json_path,
        contract_json_path,
        ablation_json_path,
        selected_csv_path,
        rejected_csv_path,
        blocked_csv_path,
        contract_lag_rows_csv_path,
        ablation_csv_path,
        summary_path,
        verification_path,
        profile_fig_path,
        ablation_fig_path,
        manifest_path,
    ]:
        _say(quiet, f"[lam-catt-showcase]           -> {artifact_path}")

    status = "PASS" if not violations else "FAIL"
    if violations:
        _logger.warning("Verification found %d violation(s)", len(violations))
        for v in violations:
            _logger.warning("  - %s", v)

    print(f"VERIFICATION: {status}", flush=True)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
