"""Script-facing helpers for the Phase 3 extended fingerprint showcase."""

from __future__ import annotations

from math import ceil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict

from forecastability.triage.extended_forecastability import (
    ExtendedForecastabilityAnalysisResult,
)
from forecastability.utils.synthetic import ExtendedFingerprintShowcaseCase

_CANONICAL_SERIES: tuple[str, ...] = (
    "white_noise",
    "clean_sine_wave",
    "seasonal_plus_noise",
    "ar1",
    "trend_plus_noise",
    "long_memory_candidate",
    "henon_map",
)


class ExtendedFingerprintShowcaseRecord(BaseModel):
    """One extended-showcase item plus its deterministic analysis result."""

    model_config = ConfigDict(frozen=True)

    series_name: str
    description: str
    generator: str
    period: int | None
    expected_story: str
    analysis: ExtendedForecastabilityAnalysisResult


class ShowcaseSemanticSnapshot(BaseModel):
    """Coarse semantic snapshot used by the showcase verifier."""

    model_config = ConfigDict(frozen=True)

    series_name: str
    signal_to_noise: float | None
    information_horizon: int
    predictability_sources: tuple[str, ...]
    ordinal_redundancy: float | None
    complexity_class: str | None
    dfa_alpha: float | None
    memory_type: str | None
    trend_strength: float | None
    seasonal_strength: float | None


def build_extended_fingerprint_showcase_record(
    *,
    case: ExtendedFingerprintShowcaseCase,
    analysis: ExtendedForecastabilityAnalysisResult,
) -> ExtendedFingerprintShowcaseRecord:
    """Package one showcase case with its extended analysis result."""
    return ExtendedFingerprintShowcaseRecord(
        series_name=case.series_name,
        description=case.description,
        generator=case.generator,
        period=case.period,
        expected_story=case.expected_story,
        analysis=analysis,
    )


def _format_optional_float(value: float | None, *, digits: int = 4) -> str:
    if value is None:
        return "N/A"
    return f"{value:.{digits}f}"


def _joined(values: list[str] | tuple[str, ...]) -> str:
    return ", ".join(values) if values else "-"


def _semantic_snapshot(record: ExtendedFingerprintShowcaseRecord) -> ShowcaseSemanticSnapshot:
    """Extract the coarse semantic fields used by the showcase verifier."""
    fingerprint = record.analysis.fingerprint
    geometry = fingerprint.information_geometry
    ordinal = fingerprint.ordinal
    memory = fingerprint.memory
    classical = fingerprint.classical
    return ShowcaseSemanticSnapshot(
        series_name=record.series_name,
        signal_to_noise=None if geometry is None else geometry.signal_to_noise,
        information_horizon=0 if geometry is None else geometry.information_horizon,
        predictability_sources=tuple(record.analysis.profile.predictability_sources),
        ordinal_redundancy=None if ordinal is None else ordinal.ordinal_redundancy,
        complexity_class=None if ordinal is None else ordinal.complexity_class,
        dfa_alpha=None if memory is None else memory.dfa_alpha,
        memory_type=None if memory is None else memory.memory_type,
        trend_strength=None if classical is None else classical.trend_strength,
        seasonal_strength=None if classical is None else classical.seasonal_strength,
    )


def _geometry_metrics(
    record: ExtendedFingerprintShowcaseRecord,
) -> tuple[float, int | float, str]:
    geometry = record.analysis.fingerprint.information_geometry
    if geometry is None:
        return np.nan, np.nan, "unavailable"
    return geometry.signal_to_noise, geometry.information_horizon, geometry.information_structure


def extended_profile_frame(record: ExtendedFingerprintShowcaseRecord) -> pd.DataFrame:
    """Return one AMI-profile frame for plotting the extended showcase."""
    geometry = record.analysis.fingerprint.information_geometry
    if geometry is None:
        return pd.DataFrame(
            columns=["target_name", "horizon", "ami_corrected", "tau", "accepted", "valid"]
        )

    rows: list[dict[str, object]] = []
    for point in geometry.curve:
        rows.append(
            {
                "target_name": record.series_name,
                "horizon": point.horizon,
                "ami_corrected": point.ami_corrected,
                "tau": point.tau,
                "accepted": point.accepted,
                "valid": point.valid,
            }
        )
    return pd.DataFrame(rows)


def showcase_summary_frame(records: list[ExtendedFingerprintShowcaseRecord]) -> pd.DataFrame:
    """Build the compact summary table for the extended showcase."""
    rows: list[dict[str, object]] = []
    for record in records:
        analysis = record.analysis
        fingerprint = analysis.fingerprint
        profile = analysis.profile
        signal_to_noise, information_horizon, information_structure = _geometry_metrics(record)
        rows.append(
            {
                "target_name": record.series_name,
                "generator": record.generator,
                "period": record.period if record.period is not None else np.nan,
                "signal_to_noise": (
                    round(signal_to_noise, 6) if not np.isnan(signal_to_noise) else np.nan
                ),
                "information_horizon": information_horizon,
                "information_structure": information_structure,
                "spectral_predictability": (
                    round(fingerprint.spectral.spectral_predictability, 6)
                    if fingerprint.spectral is not None
                    else np.nan
                ),
                "spectral_concentration": (
                    round(fingerprint.spectral.spectral_concentration, 6)
                    if fingerprint.spectral is not None
                    else np.nan
                ),
                "ordinal_redundancy": (
                    round(fingerprint.ordinal.ordinal_redundancy, 6)
                    if fingerprint.ordinal is not None
                    else np.nan
                ),
                "trend_strength": (
                    round(fingerprint.classical.trend_strength, 6)
                    if fingerprint.classical is not None
                    and fingerprint.classical.trend_strength is not None
                    else np.nan
                ),
                "seasonal_strength": (
                    round(fingerprint.classical.seasonal_strength, 6)
                    if fingerprint.classical is not None
                    and fingerprint.classical.seasonal_strength is not None
                    else np.nan
                ),
                "dfa_alpha": (
                    round(fingerprint.memory.dfa_alpha, 6)
                    if fingerprint.memory is not None and fingerprint.memory.dfa_alpha is not None
                    else np.nan
                ),
                "signal_strength": profile.signal_strength,
                "predictability_sources": _joined(profile.predictability_sources),
                "recommended_model_families": _joined(profile.recommended_model_families),
            }
        )
    return pd.DataFrame(rows)


def routing_table_frame(records: list[ExtendedFingerprintShowcaseRecord]) -> pd.DataFrame:
    """Build the routing-focused comparison table for the extended showcase."""
    rows: list[dict[str, object]] = []
    for record in records:
        profile = record.analysis.profile
        rows.append(
            {
                "target_name": record.series_name,
                "expected_story": record.expected_story,
                "signal_strength": profile.signal_strength,
                "noise_risk": profile.noise_risk,
                "predictability_sources": _joined(profile.predictability_sources),
                "recommended_model_families": _joined(profile.recommended_model_families),
                "avoid_model_families": _joined(profile.avoid_model_families),
                "summary": profile.summary,
                "model_now": profile.model_now,
                "explanation": " | ".join(profile.explanation),
            }
        )
    return pd.DataFrame(rows)


def write_frame_csv(frame: pd.DataFrame, *, output_path: Path) -> None:
    """Write a stable CSV artifact for the extended showcase."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)


def _verification_issues_for_record(record: ExtendedFingerprintShowcaseRecord) -> list[str]:
    """Return metadata and round-trip verification issues for one showcase record."""
    issues: list[str] = []
    analysis = record.analysis
    prefix = record.series_name
    payload = analysis.model_dump(mode="json")
    reconstructed = ExtendedForecastabilityAnalysisResult.model_validate(payload)

    if analysis.series_name != record.series_name:
        issues.append(f"{prefix}: result series_name diverges from showcase case name")
    if analysis.period != record.period:
        issues.append(f"{prefix}: result period diverges from showcase case period")
    if analysis.fingerprint.information_geometry is None:
        issues.append(f"{prefix}: AMI-first geometry should be available for the showcase")
    if analysis.routing_metadata.get("policy_version") != "v0.4.2":
        issues.append(f"{prefix}: routing metadata is missing the expected policy version")
    if analysis.routing_metadata.get("ami_geometry_requested") is not True:
        issues.append(f"{prefix}: routing metadata should record AMI geometry as requested")
    if analysis.routing_metadata.get("ami_geometry_available") is not True:
        issues.append(f"{prefix}: routing metadata should record AMI geometry as available")
    if analysis.routing_metadata.get("descriptive_only") is not False:
        issues.append(f"{prefix}: showcase routing should not fall back to descriptive-only")
    if analysis.routing_metadata.get("signal_strength") != analysis.profile.signal_strength:
        issues.append(f"{prefix}: signal_strength diverges between profile and metadata")
    if analysis.routing_metadata.get("noise_risk") != analysis.profile.noise_risk:
        issues.append(f"{prefix}: noise_risk diverges between profile and metadata")
    if record.period is not None and analysis.routing_metadata.get("period_supplied") is not True:
        issues.append(f"{prefix}: period-aware showcase case did not preserve period metadata")
    if not analysis.profile.recommended_model_families:
        issues.append(f"{prefix}: routing should emit a non-empty family shortlist")
    if reconstructed.model_dump(mode="json") != payload:
        issues.append(f"{prefix}: JSON payload does not round-trip through the result model")
    return issues


def _require_snapshot(
    lookup: dict[str, ShowcaseSemanticSnapshot],
    series_name: str,
    *,
    issues: list[str],
) -> ShowcaseSemanticSnapshot | None:
    """Return the semantic snapshot for one series or record a missing-series issue."""
    snapshot = lookup.get(series_name)
    if snapshot is None:
        issues.append(f"{series_name}: missing from coarse semantic verification")
    return snapshot


def _append_required_sources(
    issues: list[str],
    *,
    snapshot: ShowcaseSemanticSnapshot,
    required_sources: tuple[str, ...],
) -> None:
    """Record any missing predictability sources for one snapshot."""
    for source in required_sources:
        if source not in snapshot.predictability_sources:
            issues.append(
                f"{snapshot.series_name}: expected source '{source}' in "
                f"{list(snapshot.predictability_sources)!r}"
            )


def _append_forbidden_sources(
    issues: list[str],
    *,
    snapshot: ShowcaseSemanticSnapshot,
    forbidden_sources: tuple[str, ...],
) -> None:
    """Record any disallowed predictability sources for one snapshot."""
    for source in forbidden_sources:
        if source in snapshot.predictability_sources:
            issues.append(
                f"{snapshot.series_name}: source '{source}' should stay absent from the "
                f"coarse semantic snapshot {list(snapshot.predictability_sources)!r}"
            )


def _append_minimum_float_issue(
    issues: list[str],
    *,
    series_name: str,
    metric_name: str,
    value: float | None,
    minimum: float,
) -> None:
    """Record a float-valued metric falling below a required floor."""
    if value is None:
        issues.append(f"{series_name}: {metric_name} is unavailable")
        return
    if value < minimum:
        issues.append(f"{series_name}: {metric_name}={value:.4f} should be >= {minimum:.4f}")


def _append_minimum_int_issue(
    issues: list[str],
    *,
    series_name: str,
    metric_name: str,
    value: int,
    minimum: int,
) -> None:
    """Record an integer-valued metric falling below a required floor."""
    if value < minimum:
        issues.append(f"{series_name}: {metric_name}={value} should be >= {minimum}")


def _append_maximum_float_issue(
    issues: list[str],
    *,
    series_name: str,
    metric_name: str,
    value: float | None,
    maximum: float,
) -> None:
    """Record a float-valued metric exceeding a required ceiling."""
    if value is None:
        issues.append(f"{series_name}: {metric_name} is unavailable")
        return
    if value > maximum:
        issues.append(f"{series_name}: {metric_name}={value:.4f} should be <= {maximum:.4f}")


def _append_strictly_greater_issue(
    issues: list[str],
    *,
    left_name: str,
    left_metric: float | None,
    right_name: str,
    right_metric: float | None,
    metric_name: str,
) -> None:
    """Record a failed strict-greater cross-series comparison."""
    if left_metric is None or right_metric is None:
        issues.append(
            f"{left_name}: cannot compare {metric_name} against {right_name} because one "
            "value is unavailable"
        )
        return
    if left_metric <= right_metric:
        issues.append(
            f"{left_name}: {metric_name}={left_metric:.4f} should exceed "
            f"{right_name} {metric_name}={right_metric:.4f}"
        )


def _append_strictly_less_issue(
    issues: list[str],
    *,
    left_name: str,
    left_metric: float | None,
    right_name: str,
    right_metric: float | None,
    metric_name: str,
) -> None:
    """Record a failed strict-less cross-series comparison."""
    if left_metric is None or right_metric is None:
        issues.append(
            f"{left_name}: cannot compare {metric_name} against {right_name} because one "
            "value is unavailable"
        )
        return
    if left_metric >= right_metric:
        issues.append(
            f"{left_name}: {metric_name}={left_metric:.4f} should stay below "
            f"{right_name} {metric_name}={right_metric:.4f}"
        )


def _semantic_issues(records: list[ExtendedFingerprintShowcaseRecord]) -> list[str]:
    """Verify the coarse per-series semantics for the deterministic showcase."""
    issues: list[str] = []
    lookup = {record.series_name: _semantic_snapshot(record) for record in records}

    white_noise = _require_snapshot(lookup, "white_noise", issues=issues)
    clean_sine_wave = _require_snapshot(lookup, "clean_sine_wave", issues=issues)
    seasonal_plus_noise = _require_snapshot(lookup, "seasonal_plus_noise", issues=issues)
    ar1 = _require_snapshot(lookup, "ar1", issues=issues)
    trend_plus_noise = _require_snapshot(lookup, "trend_plus_noise", issues=issues)
    long_memory_candidate = _require_snapshot(lookup, "long_memory_candidate", issues=issues)
    henon_map = _require_snapshot(lookup, "henon_map", issues=issues)

    if white_noise is not None:
        _append_forbidden_sources(
            issues,
            snapshot=white_noise,
            forbidden_sources=(
                "lag_dependence",
                "spectral_concentration",
                "seasonality",
                "trend",
                "ordinal_redundancy",
                "long_memory",
            ),
        )
        if white_noise.information_horizon != 0:
            issues.append(
                "white_noise: information_horizon="
                f"{white_noise.information_horizon} should stay at 0"
            )
        _append_maximum_float_issue(
            issues,
            series_name="white_noise",
            metric_name="signal_to_noise",
            value=white_noise.signal_to_noise,
            maximum=0.30,
        )

    if clean_sine_wave is not None:
        _append_required_sources(
            issues,
            snapshot=clean_sine_wave,
            required_sources=("lag_dependence", "spectral_concentration", "seasonality"),
        )
        _append_minimum_int_issue(
            issues,
            series_name="clean_sine_wave",
            metric_name="information_horizon",
            value=clean_sine_wave.information_horizon,
            minimum=8,
        )
        _append_minimum_float_issue(
            issues,
            series_name="clean_sine_wave",
            metric_name="seasonal_strength",
            value=clean_sine_wave.seasonal_strength,
            minimum=0.95,
        )

    if seasonal_plus_noise is not None:
        _append_required_sources(
            issues,
            snapshot=seasonal_plus_noise,
            required_sources=("lag_dependence", "seasonality"),
        )
        _append_minimum_float_issue(
            issues,
            series_name="seasonal_plus_noise",
            metric_name="seasonal_strength",
            value=seasonal_plus_noise.seasonal_strength,
            minimum=0.60,
        )

    if ar1 is not None:
        _append_required_sources(
            issues,
            snapshot=ar1,
            required_sources=("lag_dependence",),
        )
        _append_forbidden_sources(
            issues,
            snapshot=ar1,
            forbidden_sources=(
                "spectral_concentration",
                "seasonality",
                "trend",
                "ordinal_redundancy",
                "long_memory",
            ),
        )
        _append_minimum_int_issue(
            issues,
            series_name="ar1",
            metric_name="information_horizon",
            value=ar1.information_horizon,
            minimum=3,
        )
        _append_minimum_float_issue(
            issues,
            series_name="ar1",
            metric_name="signal_to_noise",
            value=ar1.signal_to_noise,
            minimum=0.55,
        )

    if trend_plus_noise is not None:
        _append_required_sources(
            issues,
            snapshot=trend_plus_noise,
            required_sources=("lag_dependence", "trend"),
        )
        _append_minimum_float_issue(
            issues,
            series_name="trend_plus_noise",
            metric_name="trend_strength",
            value=trend_plus_noise.trend_strength,
            minimum=0.80,
        )

    if long_memory_candidate is not None:
        _append_required_sources(
            issues,
            snapshot=long_memory_candidate,
            required_sources=("lag_dependence", "long_memory"),
        )
        _append_forbidden_sources(
            issues,
            snapshot=long_memory_candidate,
            forbidden_sources=("seasonality", "trend", "ordinal_redundancy"),
        )
        _append_minimum_int_issue(
            issues,
            series_name="long_memory_candidate",
            metric_name="information_horizon",
            value=long_memory_candidate.information_horizon,
            minimum=3,
        )
        _append_minimum_float_issue(
            issues,
            series_name="long_memory_candidate",
            metric_name="signal_to_noise",
            value=long_memory_candidate.signal_to_noise,
            minimum=0.45,
        )
        _append_minimum_float_issue(
            issues,
            series_name="long_memory_candidate",
            metric_name="dfa_alpha",
            value=long_memory_candidate.dfa_alpha,
            minimum=0.90,
        )

    if henon_map is not None:
        _append_required_sources(
            issues,
            snapshot=henon_map,
            required_sources=("lag_dependence", "ordinal_redundancy"),
        )
        _append_forbidden_sources(
            issues,
            snapshot=henon_map,
            forbidden_sources=("seasonality", "trend"),
        )
        _append_minimum_float_issue(
            issues,
            series_name="henon_map",
            metric_name="ordinal_redundancy",
            value=henon_map.ordinal_redundancy,
            minimum=0.35,
        )
        if henon_map.complexity_class not in {
            "complex_but_redundant",
            "structured_nonlinear",
        }:
            issues.append(
                "henon_map: complexity_class should support the nonlinear cue, got "
                f"{henon_map.complexity_class!r}"
            )

    if clean_sine_wave is not None and seasonal_plus_noise is not None:
        _append_strictly_less_issue(
            issues,
            left_name="seasonal_plus_noise",
            left_metric=seasonal_plus_noise.seasonal_strength,
            right_name="clean_sine_wave",
            right_metric=clean_sine_wave.seasonal_strength,
            metric_name="seasonal_strength",
        )

    if clean_sine_wave is not None and henon_map is not None:
        _append_strictly_greater_issue(
            issues,
            left_name="henon_map",
            left_metric=henon_map.ordinal_redundancy,
            right_name="clean_sine_wave",
            right_metric=clean_sine_wave.ordinal_redundancy,
            metric_name="ordinal_redundancy",
        )

    return issues


def _semantic_snapshot_lines(records: list[ExtendedFingerprintShowcaseRecord]) -> list[str]:
    """Summarize the realized per-series semantics for the verification report."""
    lookup = {record.series_name: _semantic_snapshot(record) for record in records}
    lines: list[str] = []
    for series_name in _CANONICAL_SERIES:
        snapshot = lookup.get(series_name)
        if snapshot is None:
            lines.append(f"- `{series_name}`: missing from semantic snapshot")
            continue
        lines.append(
            f"- `{series_name}`: sources={_joined(snapshot.predictability_sources)}; "
            f"signal_to_noise={_format_optional_float(snapshot.signal_to_noise)}; "
            f"information_horizon={snapshot.information_horizon}; "
            f"ordinal_redundancy={_format_optional_float(snapshot.ordinal_redundancy)}; "
            f"seasonal_strength={_format_optional_float(snapshot.seasonal_strength)}; "
            f"trend_strength={_format_optional_float(snapshot.trend_strength)}; "
            f"dfa_alpha={_format_optional_float(snapshot.dfa_alpha)}"
        )
    return lines


def verify_showcase_records(records: list[ExtendedFingerprintShowcaseRecord]) -> list[str]:
    """Verify deterministic ordering, metadata, and coarse showcase semantics."""
    issues: list[str] = []
    names = [record.series_name for record in records]
    if names != list(_CANONICAL_SERIES):
        issues.append(
            f"panel order mismatch: actual={names!r} expected={list(_CANONICAL_SERIES)!r}"
        )

    for record in records:
        issues.extend(_verification_issues_for_record(record))

    issues.extend(_semantic_issues(records))

    return issues


def save_showcase_profile_grid(
    records: list[ExtendedFingerprintShowcaseRecord],
    *,
    output_path: Path,
) -> pd.DataFrame:
    """Save the AMI-first profile figure grid for the extended showcase."""
    n_columns = 3
    n_rows = int(ceil(len(records) / n_columns))
    fig, axes = plt.subplots(n_rows, n_columns, figsize=(15, 4.3 * n_rows), sharex=False)
    flat_axes = np.atleast_1d(axes).ravel()
    combined = pd.concat([extended_profile_frame(record) for record in records], ignore_index=True)

    for axis, record in zip(flat_axes, records, strict=False):
        frame = extended_profile_frame(record)
        accepted = frame[frame["accepted"]]
        profile = record.analysis.profile
        geometry = record.analysis.fingerprint.information_geometry
        if geometry is None or frame.empty:
            axis.set_visible(False)
            continue

        axis.plot(
            frame["horizon"],
            frame["ami_corrected"],
            color="tab:blue",
            linewidth=2.0,
            marker="o",
            markersize=3.0,
            label="corrected AMI",
        )
        axis.plot(
            frame["horizon"],
            frame["tau"],
            color="tab:red",
            linewidth=1.4,
            linestyle="--",
            label="tau",
        )
        if not accepted.empty:
            axis.scatter(
                accepted["horizon"],
                accepted["ami_corrected"],
                color="black",
                s=24,
                zorder=4,
                label="accepted horizons",
            )

        first_family = (
            profile.recommended_model_families[0] if profile.recommended_model_families else "-"
        )
        sources = _joined(profile.predictability_sources)
        axis.set_title(
            (
                f"{record.series_name}\n"
                f"SNR={geometry.signal_to_noise:.2f}, "
                f"sources={sources}, route={first_family}"
            ),
            fontsize=9,
        )
        axis.set_xlabel("Horizon")
        axis.set_ylabel("Corrected AMI")
        axis.grid(alpha=0.3)

    for axis in flat_axes[len(records) :]:
        axis.set_visible(False)

    handles, labels = flat_axes[0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False)
    fig.suptitle(
        "Extended forecastability showcase: AMI-first lag geometry across the deterministic panel",
        fontsize=12,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return combined


def _annotate_bar(axis: plt.Axes, index: int, plotted_value: float, raw_value: float) -> None:
    if np.isnan(raw_value):
        axis.text(index, max(plotted_value, 0.0), "N/A", ha="center", va="bottom", fontsize=8)
        return
    axis.text(index, plotted_value, f"{raw_value:.2f}", ha="center", va="bottom", fontsize=8)


def save_metric_overview(
    records: list[ExtendedFingerprintShowcaseRecord],
    *,
    output_path: Path,
) -> pd.DataFrame:
    """Save a compact multi-metric overview figure for the extended showcase."""
    frame = showcase_summary_frame(records)
    labels = frame["target_name"].tolist()
    x = np.arange(len(labels))

    fig, axes = plt.subplots(2, 3, figsize=(16, 8.5))
    metric_specs = [
        ("signal_to_noise", "AMI signal-to-noise", "tab:blue"),
        ("information_horizon", "AMI information horizon", "tab:orange"),
        ("spectral_predictability", "Spectral predictability", "tab:green"),
        ("ordinal_redundancy", "Ordinal redundancy", "tab:red"),
        ("trend_strength", "Trend strength", "tab:purple"),
        ("dfa_alpha", "DFA alpha", "tab:brown"),
    ]

    for axis, (column, title, color) in zip(axes.ravel(), metric_specs, strict=True):
        raw_values = frame[column].to_numpy(dtype=float)
        plotted_values = np.nan_to_num(raw_values, nan=0.0)
        axis.bar(x, plotted_values, color=color, alpha=0.85)
        axis.set_title(title)
        axis.set_xticks(x, labels=labels, rotation=20, ha="right")
        axis.grid(axis="y", alpha=0.3)
        value_pairs = zip(plotted_values, raw_values, strict=True)
        for index, (plotted_value, raw_value) in enumerate(value_pairs):
            _annotate_bar(axis, index, plotted_value, raw_value)

    fig.suptitle(
        "Extended forecastability showcase: AMI-first metrics plus additive structure diagnostics",
        fontsize=12,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return frame


def _markdown_table_cell(value: object) -> str:
    if isinstance(value, float):
        text = "N/A" if np.isnan(value) else f"{value:.6f}"
    else:
        text = str(value)
    return text.replace("\r\n", "<br>").replace("\n", "<br>").replace("|", "\\|")


def _markdown_table(frame: pd.DataFrame) -> str:
    columns = [_markdown_table_cell(column) for column in frame.columns]
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    rows = [header, divider]
    for row in frame.itertuples(index=False, name=None):
        values = [_markdown_table_cell(value) for value in row]
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)


def _math_line(record: ExtendedFingerprintShowcaseRecord) -> str:
    analysis = record.analysis
    profile = analysis.profile
    geometry = analysis.fingerprint.information_geometry
    signal_to_noise = geometry.signal_to_noise if geometry is not None else 0.0
    information_horizon = geometry.information_horizon if geometry is not None else 0
    sources = _joined(profile.predictability_sources)
    route = _joined(profile.recommended_model_families)

    if len(profile.predictability_sources) == 0:
        return (
            f"- `{record.series_name}`: the AMI-first gate stays near the noise floor "
            f"(signal_to_noise={signal_to_noise:.3f}), so the additive blocks are treated as "
            f"confirmation of a simple baseline route `{route}` rather than a reason to escalate."
        )
    if "trend" in profile.predictability_sources:
        return (
            f"- `{record.series_name}`: AMI keeps lagged signal alive out to horizon "
            f"{information_horizon}, and the classical block explains that the structure is "
            f"trend-dominated; sources={sources}, route `{route}`."
        )
    if "long_memory" in profile.predictability_sources:
        return (
            f"- `{record.series_name}`: AMI still gates the signal story, but the memory block "
            f"adds a persistence-across-scales cue; sources={sources}, route `{route}`."
        )
    if "ordinal_redundancy" in profile.predictability_sources:
        return (
            f"- `{record.series_name}`: AMI establishes usable lagged information and the ordinal "
            f"diagnostic adds a nonlinear-structure cue, so the fingerprint stays AMI-first while "
            f"routing toward `{route}`."
        )
    return (
        f"- `{record.series_name}`: AMI signal survives to horizon {information_horizon} and the "
        f"supporting diagnostics explain the source as `{sources}`, keeping the route at `{route}`."
    )


def build_plain_language_math_summary(records: list[ExtendedFingerprintShowcaseRecord]) -> str:
    """Explain the extended showcase mathematics in plain language."""
    lines = [
        "The showcase stays AMI-first from start to finish:",
        "",
        (
            "1. Use AMI information geometry to answer the first question: "
            "is there lagged information worth modeling at all?"
        ),
        (
            "2. Only after that AMI gate passes do the spectral, ordinal, "
            "classical, and memory blocks explain where the structure seems to come from."
        ),
        (
            "3. Convert those additive diagnostics into transparent "
            "predictability sources and conservative model-family directions."
        ),
        (
            "4. Stop at the triage boundary: this report does not fit "
            "downstream forecasting models or claim a winner."
        ),
        "",
        "Applied to the deterministic seven-series panel:",
    ]
    lines.extend(_math_line(record) for record in records)
    lines.extend(
        [
            "",
            (
                "This remains a forecastability triage surface. AMI decides "
                "whether the series looks forecastable at all; the additive "
                "diagnostics explain why that signal may be there."
            ),
        ]
    )
    return "\n".join(lines)


def _informative_horizons_text(record: ExtendedFingerprintShowcaseRecord) -> str:
    geometry = record.analysis.fingerprint.information_geometry
    if geometry is None or len(geometry.informative_horizons) == 0:
        return "none"
    horizons = geometry.informative_horizons
    if len(horizons) > 10:
        return ", ".join(str(horizon) for horizon in horizons[:10]) + ", ..."
    return ", ".join(str(horizon) for horizon in horizons)


def _notes_lines(record: ExtendedFingerprintShowcaseRecord) -> list[str]:
    fingerprint = record.analysis.fingerprint
    note_groups = [
        fingerprint.spectral.notes if fingerprint.spectral is not None else [],
        fingerprint.ordinal.notes if fingerprint.ordinal is not None else [],
        fingerprint.classical.notes if fingerprint.classical is not None else [],
        fingerprint.memory.notes if fingerprint.memory is not None else [],
    ]
    notes: list[str] = []
    for group in note_groups:
        notes.extend(group)
    if not notes:
        return ["- notes: none"]
    return [f"- notes: {' | '.join(notes)}"]


def _series_section(record: ExtendedFingerprintShowcaseRecord) -> str:
    analysis = record.analysis
    fingerprint = analysis.fingerprint
    profile = analysis.profile
    geometry = fingerprint.information_geometry
    spectral_predictability = (
        fingerprint.spectral.spectral_predictability if fingerprint.spectral is not None else None
    )
    spectral_concentration = (
        fingerprint.spectral.spectral_concentration if fingerprint.spectral is not None else None
    )
    ordinal_redundancy = (
        fingerprint.ordinal.ordinal_redundancy if fingerprint.ordinal is not None else None
    )
    seasonal_strength = (
        fingerprint.classical.seasonal_strength if fingerprint.classical is not None else None
    )
    trend_strength = (
        fingerprint.classical.trend_strength if fingerprint.classical is not None else None
    )
    dfa_alpha = fingerprint.memory.dfa_alpha if fingerprint.memory is not None else None
    ami_signal_to_noise = geometry.signal_to_noise if geometry is not None else None
    ami_information_horizon = geometry.information_horizon if geometry is not None else "N/A"

    lines = [
        f"## {record.series_name}",
        "",
        f"- description: {record.description}",
        f"- generator: `{record.generator}`",
        f"- expected_story: {record.expected_story}",
        f"- signal_strength: `{profile.signal_strength}`",
        f"- noise_risk: `{profile.noise_risk}`",
        f"- predictability_sources: {_joined(profile.predictability_sources)}",
        f"- recommended_model_families: {_joined(profile.recommended_model_families)}",
        f"- avoid_model_families: {_joined(profile.avoid_model_families)}",
        f"- ami_signal_to_noise: {_format_optional_float(ami_signal_to_noise)}",
        f"- ami_information_horizon: {ami_information_horizon}",
        f"- ami_informative_horizons: {_informative_horizons_text(record)}",
        f"- spectral_predictability: {_format_optional_float(spectral_predictability)}",
        f"- spectral_concentration: {_format_optional_float(spectral_concentration)}",
        f"- ordinal_redundancy: {_format_optional_float(ordinal_redundancy)}",
        f"- seasonal_strength: {_format_optional_float(seasonal_strength)}",
        f"- trend_strength: {_format_optional_float(trend_strength)}",
        f"- dfa_alpha: {_format_optional_float(dfa_alpha)}",
        f"- summary: {profile.summary}",
        f"- model_now: {profile.model_now}",
        "",
        "### Explanation",
    ]
    lines.extend(f"- {item}" for item in profile.explanation)
    lines.extend(["", "### Notes"])
    lines.extend(_notes_lines(record))
    return "\n".join(lines)


def build_showcase_brief(
    records: list[ExtendedFingerprintShowcaseRecord],
    *,
    settings: dict[str, str | int | float],
) -> str:
    """Build a README-sized markdown brief for the extended showcase."""
    lines = [
        "# Extended Forecastability Brief",
        "",
        (
            "AMI-first deterministic showcase over seven synthetic archetypes. "
            "The lag-geometry block decides whether there is durable signal to model; "
            "spectral, ordinal, classical, and memory diagnostics then explain "
            "where that signal seems to come from."
        ),
        "",
        "## Run settings",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in settings.items())
    lines.extend(["", "## Panel at a glance"])
    for record in records:
        profile = record.analysis.profile
        sources = _joined(profile.predictability_sources)
        route = _joined(profile.recommended_model_families)
        lines.append(f"- {record.series_name}: sources={sources}, route={route}")
    return "\n".join(lines)


def build_showcase_report(
    records: list[ExtendedFingerprintShowcaseRecord],
    *,
    settings: dict[str, str | int | float],
    verification_issues: list[str],
) -> str:
    """Build the canonical markdown report for the extended showcase."""
    summary_md = _markdown_table(showcase_summary_frame(records))
    routing_md = _markdown_table(routing_table_frame(records))
    status = "PASS" if not verification_issues else "FAIL"

    lines: list[str] = [
        "# Extended forecastability fingerprint showcase",
        "",
        (
            "Core-repo Phase 3 showcase for the AMI-first v0.4.2 extended "
            "fingerprint. The panel is deterministic, univariate-first, and "
            "stops at routing-grade diagnostics rather than downstream model fitting."
        ),
        "",
        "## Run settings",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in settings.items())
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
            "## Verification status",
            "",
            f"- status: **{status}**",
            f"- issues: `{len(verification_issues)}`",
        ]
    )
    if verification_issues:
        lines.extend(f"- {issue}" for issue in verification_issues)
    else:
        lines.append(
            "- all seven showcase payloads preserve AMI-first routing, "
            "stable ordering, JSON round-trip integrity, and the intended coarse semantic "
            "snapshot"
        )

    for record in records:
        lines.extend(["", _series_section(record)])

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
    records: list[ExtendedFingerprintShowcaseRecord],
    *,
    verification_issues: list[str],
) -> str:
    """Build the deterministic verification report for the extended showcase."""
    status = "PASS" if not verification_issues else "FAIL"
    lines = [
        "# Extended fingerprint showcase verification",
        "",
        f"- status: **{status}**",
        f"- canonical_series_count: `{len(records)}`",
        "",
        "## Deterministic checks",
        "",
        "- Panel order matches the published seven-series showcase contract.",
        "- Every payload preserves AMI geometry and avoids descriptive-only fallback.",
        (
            "- Every per-series JSON payload round-trips through "
            "ExtendedForecastabilityAnalysisResult."
        ),
        (
            "- Routing metadata remains aligned with the profile-level "
            "signal-strength and noise-risk labels."
        ),
        (
            "- Every series clears a coarse AMI-first semantic check, so PASS means the "
            "published coarse semantic expectations hold for this deterministic panel."
        ),
        "",
        "## Coarse semantic snapshots",
        "",
    ]
    lines.extend(_semantic_snapshot_lines(records))
    lines.extend(
        [
            "",
            "## Included series",
            "",
        ]
    )
    lines.extend(f"- `{record.series_name}`" for record in records)
    lines.extend(["", "## Issues", ""])
    if verification_issues:
        lines.extend(f"- {issue}" for issue in verification_issues)
    else:
        lines.append("- none")
    return "\n".join(lines)
