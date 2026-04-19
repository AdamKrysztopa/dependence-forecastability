"""Notebook- and script-facing helpers for the fingerprint showcase surface.

This module reshapes already-computed deterministic fingerprint outputs into
stable tables, figures, and markdown reports. It also owns the strict A1/A2/A3
agent-surface verification used by the fingerprint showcase script and
walkthrough notebook.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict

from forecastability.adapters.agents.fingerprint_agent_interpretation_adapter import (
    FingerprintAgentInterpretation,
    interpret_fingerprint_payload,
)
from forecastability.adapters.agents.fingerprint_agent_payload_models import (
    FingerprintAgentPayload,
    fingerprint_agent_payload,
)
from forecastability.adapters.agents.fingerprint_summary_serializer import (
    SerialisedFingerprintSummary,
    serialise_fingerprint_payload,
)
from forecastability.reporting.fingerprint_reporting import build_fingerprint_markdown
from forecastability.services.linear_information_service import LinearInformationCurve
from forecastability.utils.types import FingerprintBundle

_CANONICAL_SERIES: tuple[str, ...] = (
    "white_noise",
    "ar1_monotonic",
    "seasonal_periodic",
    "nonlinear_mixed",
)


class FingerprintShowcaseRecord(BaseModel):
    """One deterministic showcase item plus its agent-facing derivatives."""

    model_config = ConfigDict(frozen=True)

    bundle: FingerprintBundle
    baseline: LinearInformationCurve
    payload: FingerprintAgentPayload
    serialised_payload: SerialisedFingerprintSummary
    interpretation: FingerprintAgentInterpretation


def build_fingerprint_showcase_record(
    *,
    bundle: FingerprintBundle,
    baseline: LinearInformationCurve,
) -> FingerprintShowcaseRecord:
    """Build the strict showcase record for one deterministic bundle."""
    payload = fingerprint_agent_payload(bundle, narrative=None)
    serialised_payload = serialise_fingerprint_payload(payload)
    interpretation = interpret_fingerprint_payload(payload)
    return FingerprintShowcaseRecord(
        bundle=bundle,
        baseline=baseline,
        payload=payload,
        serialised_payload=serialised_payload,
        interpretation=interpretation,
    )


def fingerprint_profile_frame(record: FingerprintShowcaseRecord) -> pd.DataFrame:
    """Return one notebook-friendly profile frame for plotting and inspection."""
    baseline_map = {point.horizon: point for point in record.baseline.points}
    rows: list[dict[str, object]] = []
    for point in record.bundle.geometry.curve:
        baseline_point = baseline_map.get(point.horizon)
        rows.append(
            {
                "target_name": record.bundle.target_name,
                "horizon": point.horizon,
                "ami_corrected": point.ami_corrected,
                "tau": point.tau,
                "accepted": point.accepted,
                "valid": point.valid,
                "gaussian_information": (
                    baseline_point.gaussian_information
                    if baseline_point is not None and baseline_point.valid
                    else np.nan
                ),
            }
        )
    return pd.DataFrame(rows)


def showcase_summary_frame(records: list[FingerprintShowcaseRecord]) -> pd.DataFrame:
    """Return the compact fingerprint-showcase summary table."""
    rows: list[dict[str, object]] = []
    for record in records:
        bundle = record.bundle
        payload = record.payload
        recommendation = bundle.recommendation
        rows.append(
            {
                "target_name": bundle.target_name,
                "signal_to_noise": round(bundle.geometry.signal_to_noise, 6),
                "information_mass": round(bundle.fingerprint.information_mass, 6),
                "information_horizon": bundle.fingerprint.information_horizon,
                "information_structure": bundle.fingerprint.information_structure,
                "nonlinear_share": round(bundle.fingerprint.nonlinear_share, 6),
                "directness_ratio": (
                    round(bundle.fingerprint.directness_ratio, 6)
                    if bundle.fingerprint.directness_ratio is not None
                    else np.nan
                ),
                "primary_families": ", ".join(recommendation.primary_families) or "-",
                "confidence_label": recommendation.confidence_label,
                "caution_flags": ", ".join(recommendation.caution_flags) or "-",
                "agent_summary": payload.target_name
                and record.interpretation.deterministic_summary,
            }
        )
    return pd.DataFrame(rows)


def routing_table_frame(records: list[FingerprintShowcaseRecord]) -> pd.DataFrame:
    """Return the routing-focused comparison table."""
    rows: list[dict[str, object]] = []
    for record in records:
        recommendation = record.bundle.recommendation
        interpretation = record.interpretation
        rows.append(
            {
                "target_name": record.bundle.target_name,
                "primary_families": ", ".join(recommendation.primary_families) or "-",
                "secondary_families": ", ".join(recommendation.secondary_families) or "-",
                "confidence_label": recommendation.confidence_label,
                "caution_flags": ", ".join(recommendation.caution_flags) or "-",
                "rich_signal_narrative": interpretation.rich_signal_narrative or "-",
                "cautionary_narrative": interpretation.cautionary_narrative or "-",
            }
        )
    return pd.DataFrame(rows)


def write_frame_csv(frame: pd.DataFrame, *, output_path: Path) -> None:
    """Write a DataFrame to CSV with stable defaults."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)


def verify_showcase_records(records: list[FingerprintShowcaseRecord]) -> list[str]:
    """Verify A1/A2/A3 outputs against the deterministic bundle contract."""
    issues: list[str] = []
    names = [record.bundle.target_name for record in records]
    if names != list(_CANONICAL_SERIES):
        issues.append(
            f"panel order mismatch: actual={names!r} expected={list(_CANONICAL_SERIES)!r}"
        )

    for record in records:
        bundle = record.bundle
        payload = record.payload
        interpretation = record.interpretation
        reconstructed_payload = FingerprintAgentPayload.model_validate(
            record.serialised_payload.payload
        )
        prefix = bundle.target_name

        if payload.narrative is not None:
            issues.append(f"{prefix}: strict showcase payload must keep narrative=None")
        if reconstructed_payload != payload:
            issues.append(f"{prefix}: A2 envelope does not round-trip to the A1 payload")

        if payload.target_name != bundle.target_name:
            issues.append(f"{prefix}: payload target_name diverges from bundle target_name")
        if payload.geometry_method != bundle.geometry.method:
            issues.append(f"{prefix}: payload geometry_method diverges from deterministic bundle")
        if payload.signal_to_noise != bundle.geometry.signal_to_noise:
            issues.append(f"{prefix}: payload signal_to_noise diverges from geometry output")
        if payload.information_mass != bundle.fingerprint.information_mass:
            issues.append(f"{prefix}: payload information_mass diverges from fingerprint output")
        if payload.information_horizon != bundle.fingerprint.information_horizon:
            issues.append(f"{prefix}: payload information_horizon diverges from fingerprint output")
        if payload.information_structure != bundle.fingerprint.information_structure:
            issues.append(
                f"{prefix}: payload information_structure diverges from fingerprint output"
            )
        if payload.nonlinear_share != bundle.fingerprint.nonlinear_share:
            issues.append(f"{prefix}: payload nonlinear_share diverges from fingerprint output")
        if payload.primary_families != bundle.recommendation.primary_families:
            issues.append(f"{prefix}: payload primary_families diverge from routing recommendation")
        if payload.confidence_label != bundle.recommendation.confidence_label:
            issues.append(f"{prefix}: payload confidence_label diverges from routing output")

        if interpretation.source_target_name != payload.target_name:
            issues.append(f"{prefix}: A3 target_name diverges from A1 payload")
        if interpretation.structure_bucket != payload.information_structure:
            issues.append(f"{prefix}: A3 structure bucket diverges from A1 payload")
        if interpretation.primary_families != payload.primary_families:
            issues.append(f"{prefix}: A3 primary_families diverge from A1 payload")
        if interpretation.secondary_families != payload.secondary_families:
            issues.append(f"{prefix}: A3 secondary_families diverge from A1 payload")
        if interpretation.confidence_label != payload.confidence_label:
            issues.append(f"{prefix}: A3 confidence_label diverges from A1 payload")
        if interpretation.caution_flags != payload.caution_flags:
            issues.append(f"{prefix}: A3 caution_flags diverge from A1 payload")
        if interpretation.rationale != payload.rationale:
            issues.append(f"{prefix}: A3 rationale diverges from A1 payload")
        if (
            payload.information_structure == "none"
            and interpretation.rich_signal_narrative is not None
        ):
            issues.append(f"{prefix}: A3 rich_signal_narrative should be absent for none-structure")

    return issues


def save_showcase_profile_grid(
    records: list[FingerprintShowcaseRecord],
    *,
    output_path: Path,
) -> pd.DataFrame:
    """Save the canonical 2x2 corrected-profile showcase figure."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 8), sharex=False, sharey=False)
    combined = pd.concat(
        [fingerprint_profile_frame(record) for record in records],
        ignore_index=True,
    )

    for ax, record in zip(axes.flatten(), records, strict=True):
        frame = fingerprint_profile_frame(record)
        bundle = record.bundle
        recommendation = bundle.recommendation
        accepted = frame[frame["accepted"]]

        ax.plot(
            frame["horizon"],
            frame["ami_corrected"],
            color="tab:blue",
            linewidth=2.0,
            marker="o",
            markersize=3.5,
            label="corrected AMI",
        )
        ax.plot(
            frame["horizon"],
            frame["tau"],
            color="tab:red",
            linewidth=1.5,
            linestyle="--",
            label="tau",
        )
        ax.plot(
            frame["horizon"],
            frame["gaussian_information"],
            color="tab:green",
            linewidth=1.5,
            linestyle="-.",
            label="Gaussian baseline",
        )
        if not accepted.empty:
            ax.scatter(
                accepted["horizon"],
                accepted["ami_corrected"],
                color="black",
                s=28,
                zorder=4,
                label="accepted horizons",
            )
            ax.bar(
                accepted["horizon"],
                accepted["ami_corrected"],
                color="tab:blue",
                alpha=0.12,
                width=0.9,
            )

        first_route = recommendation.primary_families[0] if recommendation.primary_families else "-"
        ax.set_title(
            (
                f"{bundle.target_name}\n"
                f"{bundle.fingerprint.information_structure}, "
                f"mass={bundle.fingerprint.information_mass:.3f}, "
                f"route={first_route}"
            ),
            fontsize=10,
        )
        ax.set_xlabel("Horizon")
        ax.set_ylabel("Information (nats)")
        ax.grid(alpha=0.3)

    handles, labels = axes.flatten()[0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False)
    fig.suptitle(
        "Forecastability fingerprint showcase: corrected AMI, surrogate "
        "threshold, and linear baseline",
        fontsize=12,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return combined


def save_metric_overview(
    records: list[FingerprintShowcaseRecord],
    *,
    output_path: Path,
) -> pd.DataFrame:
    """Save a compact multi-metric overview figure across the canonical series."""
    frame = showcase_summary_frame(records)
    labels = frame["target_name"].tolist()
    x = np.arange(len(labels))

    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    metric_specs = [
        ("signal_to_noise", "Signal-to-noise", "tab:blue"),
        ("information_mass", "Information mass", "tab:orange"),
        ("information_horizon", "Information horizon", "tab:green"),
        ("nonlinear_share", "Nonlinear share", "tab:red"),
    ]

    for ax, (column, title, color) in zip(axes.flatten(), metric_specs, strict=True):
        values = frame[column].to_numpy(dtype=float)
        ax.bar(x, values, color=color, alpha=0.85)
        ax.set_title(title)
        ax.set_xticks(x, labels=labels, rotation=20, ha="right")
        ax.grid(axis="y", alpha=0.3)
        for idx, value in enumerate(values):
            ax.text(idx, value, f"{value:.2f}", ha="center", va="bottom", fontsize=8)

    fig.suptitle("Fingerprint metrics across the canonical 0.3.1 archetypes", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return frame


def _markdown_table(frame: pd.DataFrame) -> str:
    columns = [str(column) for column in frame.columns]
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    rows = [header, divider]
    for row in frame.itertuples(index=False, name=None):
        values = []
        for value in row:
            if isinstance(value, float):
                if np.isnan(value):
                    values.append("N/A")
                else:
                    values.append(f"{value:.6f}")
            else:
                values.append(str(value))
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)


def _math_line(record: FingerprintShowcaseRecord) -> str:
    bundle = record.bundle
    fingerprint = bundle.fingerprint
    recommendation = bundle.recommendation
    route = ", ".join(recommendation.primary_families) or "no primary route"
    if fingerprint.information_structure == "none":
        return (
            f"- `{bundle.target_name}`: after surrogate correction no horizon "
            "cleared the acceptance threshold, so the math says there is no "
            "durable lag structure to exploit and the route "
            f"falls back to `{route}`."
        )
    if fingerprint.information_structure == "periodic":
        return (
            f"- `{bundle.target_name}`: repeated accepted peaks survive out to horizon "
            f"{fingerprint.information_horizon}, which reads like recurring seasonal signal; "
            f"nonlinear_share={fingerprint.nonlinear_share:.3f}, so the route stays with `{route}`."
        )
    if fingerprint.nonlinear_share >= 0.25:
        return (
            f"- `{bundle.target_name}`: usable signal survives to horizon "
            f"{fingerprint.information_horizon}, and a meaningful share of it "
            "sits above the linear Gaussian baseline "
            f"(nonlinear_share={fingerprint.nonlinear_share:.3f}); that is why "
            "the "
            f"route escalates toward `{route}`."
        )
    return (
        f"- `{bundle.target_name}`: the accepted profile decays without strong "
        "periodic repetition, so the main questions are how much signal "
        "remains "
        f"(information_mass={fingerprint.information_mass:.3f}) and how far it "
        "lasts "
        f"(information_horizon={fingerprint.information_horizon}); the route "
        "therefore "
        f"stays with `{route}`."
    )


def build_plain_language_math_summary(records: list[FingerprintShowcaseRecord]) -> str:
    """Explain the showcase mathematics in human language."""
    lines = [
        "The same deterministic chain is applied to every synthetic series:",
        "",
        "1. Estimate horizon-wise AMI and subtract the shuffle-surrogate "
        "background so only corrected signal remains.",
        "2. Keep only horizons where corrected AMI rises clearly above the threshold `tau`.",
        "3. Compress the accepted profile into four human-usable fields: how "
        "much signal survived (`information_mass`), how far it survived "
        "(`information_horizon`), what shape it formed "
        "(`information_structure`), and how much exceeded a linear "
        "autocorrelation baseline (`nonlinear_share`).",
        "4. Route those fields to model families and pass the result through "
        "the strict deterministic A3 agent adapter, which is allowed to "
        "explain but not allowed to change the numbers.",
        "",
        "Applied to the four canonical archetypes:",
    ]
    lines.extend(_math_line(record) for record in records)
    lines.extend(
        [
            "",
            "This showcase remains univariate-first and AMI-first. It does not "
            "claim to identify one true optimal model, and it does not "
            "introduce multivariate or conditional-MI routing semantics into "
            "the fingerprint surface.",
        ]
    )
    return "\n".join(lines)


def build_showcase_report(
    records: list[FingerprintShowcaseRecord],
    *,
    settings: dict[str, str | int | float],
    verification_issues: list[str],
) -> str:
    """Build the canonical markdown report for the fingerprint showcase."""
    summary_md = _markdown_table(showcase_summary_frame(records))
    routing_md = _markdown_table(routing_table_frame(records))
    status = "PASS" if not verification_issues else "FAIL"

    lines: list[str] = [
        "# Forecastability fingerprint showcase",
        "",
        "Canonical deterministic v0.3.1 showcase over the prepared synthetic archetype panel.",
        "",
        "## Run settings",
        "",
    ]
    for key, value in settings.items():
        lines.append(f"- {key}: `{value}`")

    lines.extend(
        [
            "",
            "## Summary table",
            "",
            summary_md,
            "",
            "## Routing comparison",
            "",
            routing_md,
            "",
            "## Agent verification status",
            "",
            f"- status: **{status}**",
            f"- issues: `{len(verification_issues)}`",
        ]
    )
    if verification_issues:
        lines.extend(f"- {issue}" for issue in verification_issues)
    else:
        lines.append("- strict A1/A2/A3 outputs remain aligned with the deterministic bundles")

    for record in records:
        lines.extend(
            [
                "",
                f"## {record.bundle.target_name}",
                "",
                build_fingerprint_markdown(record.bundle),
                "### A3 deterministic interpretation",
                f"- summary: {record.interpretation.deterministic_summary}",
                f"- rich_signal_narrative: {record.interpretation.rich_signal_narrative or 'none'}",
                f"- cautionary_narrative: {record.interpretation.cautionary_narrative or 'none'}",
            ]
        )

    lines.extend(
        [
            "",
            "## Plain-language summary of the mathematics",
            "",
            build_plain_language_math_summary(records),
            "",
        ]
    )
    return "\n".join(lines)


def build_verification_markdown(
    records: list[FingerprintShowcaseRecord],
    *,
    verification_issues: list[str],
) -> str:
    """Build the strict verification report for the showcase artifacts."""
    status = "PASS" if not verification_issues else "FAIL"
    lines = [
        "# Fingerprint showcase verification",
        "",
        f"- status: **{status}**",
        f"- canonical_series_count: `{len(records)}`",
        "",
        "## Deterministic alignment checks",
        "",
        "- A1 payload mirrors geometry, fingerprint, and routing outputs exactly.",
        "- A2 envelope round-trips back to the A1 payload.",
        "- A3 interpretation preserves route families, confidence, cautions, and target identity.",
        "",
        "## Included series",
        "",
    ]
    lines.extend(f"- `{record.bundle.target_name}`" for record in records)
    lines.extend(["", "## Issues", ""])
    if verification_issues:
        lines.extend(f"- {issue}" for issue in verification_issues)
    else:
        lines.append("- none")
    return "\n".join(lines)
