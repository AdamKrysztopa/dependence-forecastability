"""Release-review report generator for routing validation (plan v0.3.3 V3_4-F07).

Runs the deterministic routing-validation workflow, writes a markdown release
review, freezes the full bundle and a compact manifest to JSON, and saves a
small set of summary figures.

Usage::

    uv run python scripts/run_routing_validation_report.py
    uv run python scripts/run_routing_validation_report.py --smoke
    uv run python scripts/run_routing_validation_report.py --smoke --no-real-panel
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
from pydantic import BaseModel, ConfigDict

from forecastability import (
    RoutingPolicyAuditConfig,
    RoutingValidationBundle,
    RoutingValidationCase,
    run_routing_validation,
)
from forecastability.diagnostics.routing_validation_regression import (
    load_pinned_weak_seasonal_amplitude,
)

_logger = logging.getLogger(__name__)

_OUTCOME_COLORS: dict[str, str] = {
    "pass": "#2e8b57",
    "downgrade": "#e69f00",
    "fail": "#d55e00",
    "abstain": "#7a7a7a",
}
_CONFIDENCE_COLORS: dict[str, str] = {
    "high": "#2e8b57",
    "medium": "#e69f00",
    "low": "#d55e00",
    "abstain": "#7a7a7a",
}
_OUTCOME_ORDER: tuple[str, ...] = ("pass", "downgrade", "fail", "abstain")
_CONFIDENCE_ORDER: tuple[str, ...] = ("high", "medium", "low", "abstain")


class _CaseRow(BaseModel):
    """Typed per-case summary row for markdown and manifest rendering."""

    model_config = ConfigDict(frozen=True)

    case_name: str
    source_kind: str
    outcome: str
    confidence_label: str
    threshold_margin: float
    rule_stability: float
    review_flag: str
    expected_primary_families: list[str]
    observed_primary_families: list[str]


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse command-line arguments for the report generator.

    Args:
        argv: Optional argv list for testability.

    Returns:
        Parsed namespace.
    """
    parser = argparse.ArgumentParser(
        description="Build markdown, JSON, and plots for routing-validation release review"
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default="outputs",
        help="Root output directory (defaults to outputs/)",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Deterministic seed passed to run_routing_validation()",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Fast synthetic-only run with n_per_archetype=200",
    )
    parser.add_argument(
        "--no-real-panel",
        action="store_true",
        help="Skip the real-series panel even when the manifest exists",
    )
    return parser.parse_args(argv)


def _ensure_dirs(output_root: Path) -> tuple[Path, Path, Path]:
    """Create routing-validation output directories.

    Args:
        output_root: Base output directory.

    Returns:
        Tuple of (json_dir, reports_dir, figures_dir).
    """
    json_dir = output_root / "json" / "routing_validation"
    reports_dir = output_root / "reports" / "routing_validation"
    figures_dir = output_root / "figures" / "routing_validation"
    for path in (json_dir, reports_dir, figures_dir):
        path.mkdir(parents=True, exist_ok=True)
    return json_dir, reports_dir, figures_dir


def _resolve_real_panel_path(*, smoke: bool, no_real_panel: bool) -> Path | None:
    """Resolve the real-panel manifest path for the current run mode.

    Args:
        smoke: Whether the script is running in smoke mode.
        no_real_panel: Whether the caller explicitly disabled the real panel.

    Returns:
        Manifest path when enabled and present, otherwise ``None``.
    """
    if smoke or no_real_panel:
        return None
    manifest_path = Path("configs/routing_validation_real_panel.yaml")
    if not manifest_path.exists():
        _logger.info("Real-panel manifest not found at %s; synthetic-only run.", manifest_path)
        return None
    return manifest_path


def _resolve_repo_root() -> Path:
    """Resolve the repository root from the script location."""
    return Path(__file__).resolve().parents[1]


def _resolve_weak_seasonal_amplitude() -> float | None:
    """Load the pinned weak-seasonal amplitude when the calibration fixture exists."""
    amplitude = load_pinned_weak_seasonal_amplitude(_resolve_repo_root())
    if amplitude is not None:
        _logger.info("Using pinned weak-seasonal amplitude %.4f for routing validation.", amplitude)
    return amplitude


def _escape_cell(value: str) -> str:
    """Escape pipe characters for markdown tables.

    Args:
        value: Raw string value.

    Returns:
        Escaped string safe for markdown tables.
    """
    return value.replace("|", "\\|")


def _review_flag(case: RoutingValidationCase) -> str:
    """Build a concise review flag for one validation case.

    Args:
        case: Routing validation case.

    Returns:
        Stable review flag string.
    """
    tokens: list[str] = []
    if case.outcome == "fail":
        tokens.append("FAIL")
    elif case.outcome == "abstain":
        tokens.append("ABSTAIN")
    elif case.outcome == "downgrade":
        tokens.append("DOWNGRADE")

    if case.confidence_label in {"low", "abstain"}:
        tokens.append("LOW-CONF")

    if not tokens:
        return "OK"
    return ", ".join(tokens)


def _case_rows(bundle: RoutingValidationBundle) -> list[_CaseRow]:
    """Build compact per-case dictionaries for markdown and JSON outputs.

    Args:
        bundle: Deterministic routing-validation bundle.

    Returns:
        Ordered list of JSON-safe per-case rows.
    """
    rows: list[_CaseRow] = []
    for case in bundle.cases:
        rows.append(
            _CaseRow(
                case_name=case.case_name,
                source_kind=case.source_kind,
                outcome=case.outcome,
                confidence_label=case.confidence_label,
                threshold_margin=case.threshold_margin,
                rule_stability=case.rule_stability,
                review_flag=_review_flag(case),
                expected_primary_families=list(case.expected_primary_families),
                observed_primary_families=list(case.observed_primary_families),
            )
        )
    return rows


def _build_manifest_payload(
    bundle: RoutingValidationBundle,
    *,
    case_rows: list[_CaseRow],
    settings: dict[str, object],
    artifacts: dict[str, str],
) -> dict[str, object]:
    """Build the compact JSON manifest for release review.

    Args:
        bundle: Deterministic routing-validation bundle.
        case_rows: Compact per-case summaries.
        settings: Run configuration used by the script.
        artifacts: Written artifact paths.

    Returns:
        JSON-safe manifest payload.
    """
    flagged_rows = [row.model_dump(mode="json") for row in case_rows if row.review_flag != "OK"]
    return {
        "settings": settings,
        "audit": bundle.audit.model_dump(mode="json"),
        "metadata": dict(bundle.metadata),
        "flagged_cases": flagged_rows,
        "artifacts": artifacts,
    }


def _render_markdown(
    bundle: RoutingValidationBundle,
    *,
    case_rows: list[_CaseRow],
    settings: dict[str, object],
    artifacts: dict[str, str],
) -> str:
    """Render the routing-validation markdown report.

    Args:
        bundle: Deterministic routing-validation bundle.
        case_rows: Compact per-case summaries.
        settings: Run configuration used by the script.
        artifacts: Paths to generated figures and JSON files.

    Returns:
        Markdown report text.
    """
    outcome_counts = bundle.audit.model_dump(mode="json")
    synthetic_count = sum(1 for case in bundle.cases if case.source_kind == "synthetic")
    real_count = sum(1 for case in bundle.cases if case.source_kind == "real")
    flagged = [row for row in case_rows if row.review_flag != "OK"]

    lines = ["# Routing Validation Report", ""]
    lines.append("## Run Settings")
    lines.append("")
    for key, value in settings.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Overall Counts")
    lines.append("")
    lines.append(f"- Total cases: {bundle.audit.total_cases}")
    lines.append(f"- Passed: {bundle.audit.passed_cases}")
    lines.append(f"- Downgraded: {bundle.audit.downgraded_cases}")
    lines.append(f"- Failed: {bundle.audit.failed_cases}")
    lines.append(f"- Abstained: {bundle.audit.abstained_cases}")
    lines.append(f"- Synthetic cases: {synthetic_count}")
    lines.append(f"- Real cases: {real_count}")
    lines.append("")
    lines.append("## Review Flags")
    lines.append("")
    if flagged:
        for row in flagged:
            lines.append(
                "- "
                f"{row.case_name}: {row.review_flag} "
                f"(outcome={row.outcome}, confidence={row.confidence_label}, "
                f"threshold_margin={row.threshold_margin:.4f}, "
                f"rule_stability={row.rule_stability:.4f})"
            )
    else:
        lines.append("- No flagged cases.")
    lines.append("")
    lines.append("## Per-Case Outcomes")
    lines.append("")
    lines.append(
        "| Case | Source | Outcome | Confidence | Margin | Stability | "
        "Review Flag | Expected | Observed |"
    )
    lines.append("| --- | --- | --- | --- | ---: | ---: | --- | --- | --- |")
    for row in case_rows:
        expected = ", ".join(row.expected_primary_families)
        observed = ", ".join(row.observed_primary_families)
        lines.append(
            "| "
            f"{_escape_cell(row.case_name)} | "
            f"{row.source_kind} | "
            f"{row.outcome} | "
            f"{row.confidence_label} | "
            f"{row.threshold_margin:.4f} | "
            f"{row.rule_stability:.4f} | "
            f"{row.review_flag} | "
            f"{_escape_cell(expected)} | "
            f"{_escape_cell(observed)} |"
        )
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    for label, artifact_path in artifacts.items():
        lines.append(f"- {label}: {artifact_path}")
    lines.append("")
    lines.append("## Audit Snapshot")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(outcome_counts, indent=2, sort_keys=True))
    lines.append("```")
    return "\n".join(lines) + "\n"


def _save_outcome_overview(bundle: RoutingValidationBundle, *, output_path: Path) -> None:
    """Save a bar chart of outcome counts.

    Args:
        bundle: Deterministic routing-validation bundle.
        output_path: Output PNG path.
    """
    labels = list(_OUTCOME_ORDER)
    values = [sum(1 for case in bundle.cases if case.outcome == label) for label in labels]
    colors = [_OUTCOME_COLORS[label] for label in labels]

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(labels, values, color=colors)
    ax.set_title("Routing validation outcomes")
    ax.set_ylabel("Case count")
    for idx, value in enumerate(values):
        ax.text(idx, value + 0.05, str(value), ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def _save_threshold_margin_histogram(
    bundle: RoutingValidationBundle,
    *,
    output_path: Path,
) -> None:
    """Save a threshold-margin histogram with flagged cases highlighted.

    Args:
        bundle: Deterministic routing-validation bundle.
        output_path: Output PNG path.
    """
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for outcome in _OUTCOME_ORDER:
        values = [case.threshold_margin for case in bundle.cases if case.outcome == outcome]
        if not values:
            continue
        ax.hist(
            values,
            bins=min(8, max(3, len(bundle.cases))),
            alpha=0.55,
            color=_OUTCOME_COLORS[outcome],
            label=outcome,
        )

    low_conf_cases = [case for case in bundle.cases if case.confidence_label in {"low", "abstain"}]
    for idx, case in enumerate(low_conf_cases):
        label = "low-confidence marker" if idx == 0 else None
        ax.axvline(
            case.threshold_margin,
            color="black",
            linestyle="--",
            linewidth=1.2,
            label=label,
        )

    ax.set_title("Threshold margin distribution")
    ax.set_xlabel("threshold_margin")
    ax.set_ylabel("Count")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def _save_margin_stability_scatter(
    bundle: RoutingValidationBundle,
    *,
    output_path: Path,
) -> None:
    """Save a threshold-margin vs rule-stability scatter plot.

    Args:
        bundle: Deterministic routing-validation bundle.
        output_path: Output PNG path.
    """
    fig, ax = plt.subplots(figsize=(8, 5))
    for outcome in _OUTCOME_ORDER:
        outcome_cases = [case for case in bundle.cases if case.outcome == outcome]
        if not outcome_cases:
            continue
        x_values = [case.threshold_margin for case in outcome_cases]
        y_values = [case.rule_stability for case in outcome_cases]
        edge_colors = [
            "black" if case.confidence_label in {"low", "abstain"} else "white"
            for case in outcome_cases
        ]
        ax.scatter(
            x_values,
            y_values,
            s=70,
            color=_OUTCOME_COLORS[outcome],
            edgecolors=edge_colors,
            linewidths=1.1,
            label=outcome,
        )
        for case in outcome_cases:
            if case.outcome in {"fail", "abstain"} or case.confidence_label in {"low", "abstain"}:
                ax.annotate(
                    case.case_name,
                    (case.threshold_margin, case.rule_stability),
                    fontsize=8,
                    xytext=(4, 4),
                    textcoords="offset points",
                )

    ax.set_title("Threshold margin vs. rule stability")
    ax.set_xlabel("threshold_margin")
    ax.set_ylabel("rule_stability")
    ax.set_ylim(-0.02, 1.02)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def _save_confidence_overview(bundle: RoutingValidationBundle, *, output_path: Path) -> None:
    """Save a bar chart of confidence-label counts.

    Args:
        bundle: Deterministic routing-validation bundle.
        output_path: Output PNG path.
    """
    labels = list(_CONFIDENCE_ORDER)
    values = [sum(1 for case in bundle.cases if case.confidence_label == label) for label in labels]
    colors = [_CONFIDENCE_COLORS[label] for label in labels]

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(labels, values, color=colors)
    ax.set_title("Confidence label counts")
    ax.set_ylabel("Case count")
    for idx, value in enumerate(values):
        ax.text(idx, value + 0.05, str(value), ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    """Run the routing-validation report generator.

    Args:
        argv: Optional argv list for testability.

    Returns:
        POSIX-style exit code.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
    args = _parse_args(argv)

    output_root = Path(args.output_root)
    json_dir, reports_dir, figures_dir = _ensure_dirs(output_root)
    config = RoutingPolicyAuditConfig()
    n_per_archetype = 200 if args.smoke else 600
    real_panel_path = _resolve_real_panel_path(smoke=args.smoke, no_real_panel=args.no_real_panel)
    weak_seasonal_amplitude = _resolve_weak_seasonal_amplitude()

    bundle = run_routing_validation(
        n_per_archetype=n_per_archetype,
        random_state=args.random_state,
        real_panel_path=real_panel_path,
        weak_seasonal_amplitude=weak_seasonal_amplitude,
        config=config,
    )

    bundle_path = json_dir / "routing_validation_bundle.json"
    manifest_path = json_dir / "routing_validation_report_manifest.json"
    report_path = reports_dir / "report.md"
    outcome_path = figures_dir / "routing_validation_outcomes.png"
    confidence_path = figures_dir / "routing_validation_confidence.png"
    margin_hist_path = figures_dir / "routing_validation_threshold_margin_histogram.png"
    scatter_path = figures_dir / "routing_validation_margin_stability.png"

    _save_outcome_overview(bundle, output_path=outcome_path)
    _save_confidence_overview(bundle, output_path=confidence_path)
    _save_threshold_margin_histogram(bundle, output_path=margin_hist_path)
    _save_margin_stability_scatter(bundle, output_path=scatter_path)

    settings: dict[str, object] = {
        "smoke": args.smoke,
        "random_state": args.random_state,
        "n_per_archetype": n_per_archetype,
        "real_panel_enabled": real_panel_path is not None,
        "real_panel_path": (
            str(real_panel_path) if real_panel_path is not None else "synthetic-only"
        ),
        "weak_seasonal_amplitude": weak_seasonal_amplitude,
    }
    artifacts: dict[str, str] = {
        "bundle_json": str(bundle_path),
        "manifest_json": str(manifest_path),
        "report_markdown": str(report_path),
        "outcome_plot": str(outcome_path),
        "confidence_plot": str(confidence_path),
        "threshold_margin_histogram": str(margin_hist_path),
        "margin_stability_scatter": str(scatter_path),
    }
    case_rows = _case_rows(bundle)

    bundle_path.write_text(
        json.dumps(bundle.model_dump(mode="json"), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(
            _build_manifest_payload(
                bundle,
                case_rows=case_rows,
                settings=settings,
                artifacts=artifacts,
            ),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    report_path.write_text(
        _render_markdown(
            bundle,
            case_rows=case_rows,
            settings=settings,
            artifacts=artifacts,
        ),
        encoding="utf-8",
    )

    print(f"Routing validation report written to {report_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
