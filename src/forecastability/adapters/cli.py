"""CLI transport adapter for the forecastability triage pipeline (AGT-009).

Provides a ``forecastability`` command with three subcommands:

- ``triage`` — run forecastability triage on a time series (CSV or JSON).
- ``triage-batch`` — run deterministic batch screening from a JSON payload.
- ``list-scorers`` — list all registered dependence scorers.

Usage examples::

    forecastability triage --csv data.csv --format json
    forecastability triage --csv data.csv --col value --format markdown
    forecastability triage --series '[0.1, -0.5, 0.3, ...]'
    forecastability triage-batch --batch-json configs/batch_payload.json
    forecastability list-scorers
    forecastability list-scorers --format markdown

Entry point is registered in ``pyproject.toml``::

    [project.scripts]
    forecastability = "forecastability.adapters.cli:main"
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from pydantic import ValidationError

from forecastability.adapters.triage_presenter import present_triage_result
from forecastability.metrics.scorers import default_registry
from forecastability.triage.batch_models import (
    FAILURE_TABLE_COLUMNS,
    SUMMARY_TABLE_COLUMNS,
    BatchTriageRequest,
    BatchTriageResponse,
)
from forecastability.triage.extended_forecastability import (
    ExtendedForecastabilityAnalysisResult,
)
from forecastability.triage.models import AnalysisGoal, TriageRequest, TriageResult
from forecastability.use_cases.run_batch_triage import run_batch_triage
from forecastability.use_cases.run_extended_forecastability_analysis import (
    run_extended_forecastability_analysis,
)
from forecastability.use_cases.run_triage import run_triage

# ---------------------------------------------------------------------------
# Series loading helpers
# ---------------------------------------------------------------------------


def _series_from_csv(csv_path: Path, col: str | None) -> np.ndarray:
    """Load a 1-D numeric series from a CSV file.

    Args:
        csv_path: Path to the CSV file.
        col: Column name to read.  If ``None``, the first numeric column is used.

    Returns:
        1-D float64 numpy array.

    Raises:
        SystemExit: When the file does not exist or the requested column is absent.
    """
    import pandas as pd  # pandas is a core dependency — always available

    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}", file=sys.stderr)
        raise SystemExit(1)

    df = pd.read_csv(csv_path)

    if col is not None:
        if col not in df.columns:
            print(
                f"Error: column '{col}' not found. Available: {list(df.columns)}",
                file=sys.stderr,
            )
            raise SystemExit(1)
        return df[col].to_numpy(dtype=np.float64)

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        print("Error: no numeric columns found in CSV file.", file=sys.stderr)
        raise SystemExit(1)

    return df[numeric_cols[0]].to_numpy(dtype=np.float64)


def _series_from_json(json_str: str) -> np.ndarray:
    """Parse a JSON array string into a 1-D numpy array.

    Args:
        json_str: JSON-encoded list of numbers, e.g. ``'[1.2, 3.4, -0.5]'``.

    Returns:
        1-D float64 numpy array.

    Raises:
        SystemExit: When the JSON is invalid or not a list.
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in --series: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    if not isinstance(data, list):
        print("Error: --series must be a JSON array, e.g. '[1.2, 3.4]'", file=sys.stderr)
        raise SystemExit(1)

    return np.asarray(data, dtype=np.float64)


def _batch_request_from_json_file(json_path: Path) -> BatchTriageRequest:
    """Load and validate a batch triage request from a JSON file.

    Args:
        json_path: Path to the JSON payload.

    Returns:
        Validated :class:`BatchTriageRequest`.

    Raises:
        SystemExit: When the file is missing, unreadable, malformed, or invalid.
    """
    if not json_path.exists():
        print(f"Error: batch JSON file not found: {json_path}", file=sys.stderr)
        raise SystemExit(1)

    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"Error: unable to read batch JSON file: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in batch payload: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    if not isinstance(payload, dict):
        print("Error: batch JSON payload must be an object.", file=sys.stderr)
        raise SystemExit(1)

    try:
        return BatchTriageRequest.model_validate(payload)
    except ValidationError as exc:
        print(f"Error: invalid batch payload: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def _write_table_csv(
    csv_path: Path,
    *,
    columns: tuple[str, ...],
    rows: list[dict[str, object]],
) -> None:
    """Write a flat table to CSV with a deterministic column order."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in columns})


# ---------------------------------------------------------------------------
# Result serialisation helpers
# ---------------------------------------------------------------------------


def _triage_result_to_dict(result: TriageResult) -> dict[str, Any]:
    """Serialise a ``TriageResult`` to a JSON-safe dict.

    Args:
        result: ``TriageResult`` returned by ``run_triage()``.

    Returns:
        Plain dict suitable for ``json.dumps``.
    """
    view = present_triage_result(result)
    out: dict[str, Any] = {
        "blocked": view.blocked,
        "readiness": {
            "status": view.readiness_status,
            "warnings": view.readiness_warnings,
        },
    }

    if view.route is not None:
        out["method_plan"] = {
            "route": view.route,
            "compute_surrogates": view.compute_surrogates,
            "rationale": view.method_plan_rationale,
            "assumptions": view.method_plan_assumptions,
        }

    if view.method is not None:
        out["analyze_summary"] = {
            "method": view.method,
            "recommendation": view.recommendation,
            "n_sig_raw_lags": view.n_sig_raw_lags,
            "n_sig_partial_lags": view.n_sig_partial_lags,
        }

    if view.forecastability_class is not None:
        out["interpretation"] = {
            "forecastability_class": view.forecastability_class,
            "directness_class": view.directness_class,
            "modeling_regime": view.modeling_regime,
            "primary_lags": view.primary_lags,
            "pattern_class": view.pattern_class,
        }

    if view.recommendation is not None:
        out["recommendation"] = view.recommendation

    return out


def _batch_result_to_dict(result: BatchTriageResponse) -> dict[str, object]:
    """Serialise a batch triage response to a JSON-safe dictionary."""
    return {
        "n_items": len(result.items),
        "n_failed": len(result.failure_table),
        "items": [item.model_dump(mode="json") for item in result.items],
        "summary_table": [row.model_dump(mode="json") for row in result.summary_table],
        "failure_table": [row.model_dump(mode="json") for row in result.failure_table],
    }


def _extended_result_to_dict(
    result: ExtendedForecastabilityAnalysisResult,
) -> dict[str, object]:
    """Serialise an extended analysis result to a JSON-safe dictionary."""
    return result.model_dump(mode="json")


def _render_markdown(data: dict[str, Any]) -> str:
    """Render a triage result dict as Markdown text.

    Args:
        data: Dict produced by :func:`_triage_result_to_dict`.

    Returns:
        Markdown string ready for stdout.
    """
    lines: list[str] = ["# Forecastability Triage Result", ""]

    readiness = data.get("readiness", {})
    lines.append(f"**Readiness status:** `{readiness.get('status', 'unknown')}`")

    warnings = readiness.get("warnings", [])
    if warnings:
        lines.append("")
        lines.append("**Warnings:**")
        for w in warnings:
            lines.append(f"- `{w['code']}`: {w['message']}")

    blocked = data.get("blocked", False)
    if blocked:
        lines.extend(
            [
                "",
                "> [!IMPORTANT]",
                "> Series is blocked. Resolve warnings before analysis.",
            ]
        )
        return "\n".join(lines)

    method_plan = data.get("method_plan", {})
    if method_plan:
        lines.extend(
            [
                "",
                "## Method Plan",
                "",
                f"**Route:** `{method_plan.get('route', '—')}`",
                f"**Compute surrogates:** {method_plan.get('compute_surrogates', False)}",
                f"**Rationale:** {method_plan.get('rationale', '—')}",
            ]
        )

    interp = data.get("interpretation", {})
    if interp:
        lines.extend(
            [
                "",
                "## Interpretation",
                "",
                f"**Forecastability:** {interp.get('forecastability_class', '—')}",
                f"**Directness:** {interp.get('directness_class', '—')}",
                f"**Modeling regime:** {interp.get('modeling_regime', '—')}",
            ]
        )
        primary = interp.get("primary_lags", [])
        if primary:
            lines.append(f"**Primary lags:** {primary}")

    rec = data.get("recommendation")
    if rec:
        lines.extend(["", "## Recommendation", "", rec])

    return "\n".join(lines)


def _render_scorers_markdown(scorers: list[dict[str, str]]) -> str:
    """Render scorer list as a Markdown table.

    Args:
        scorers: List of scorer dicts with ``name``, ``family``, ``description``.

    Returns:
        Markdown string ready for stdout.
    """
    lines = [
        "# Available Scorers",
        "",
        "| Name | Family | Description |",
        "|------|--------|-------------|",
    ]
    for info in scorers:
        lines.append(f"| `{info['name']}` | {info['family']} | {info['description']} |")
    return "\n".join(lines)


def _render_extended_markdown(data: dict[str, object]) -> str:
    """Render an extended forecastability result as an executive-style brief."""
    profile = data.get("profile")
    typed_profile = (
        {str(key): value for key, value in profile.items()} if isinstance(profile, dict) else {}
    )
    sources_obj = typed_profile.get("predictability_sources")
    recommended_obj = typed_profile.get("recommended_model_families")
    avoid_obj = typed_profile.get("avoid_model_families")
    explanation_obj = typed_profile.get("explanation")
    signal_strength_obj = typed_profile.get("signal_strength")
    noise_risk_obj = typed_profile.get("noise_risk")

    sources = sources_obj if isinstance(sources_obj, list) else []
    recommended = recommended_obj if isinstance(recommended_obj, list) else []
    avoid = avoid_obj if isinstance(avoid_obj, list) else []
    explanation = explanation_obj if isinstance(explanation_obj, list) else []
    signal_strength = signal_strength_obj if isinstance(signal_strength_obj, str) else "unclear"
    noise_risk = noise_risk_obj if isinstance(noise_risk_obj, str) else "unclear"
    lines: list[str] = ["# Extended Forecastability Brief", ""]
    lines.append(f"**Forecastability profile:** {signal_strength}")
    lines.append(f"**Noise risk:** {noise_risk}")

    if isinstance(sources, list) and len(sources) > 0:
        lines.extend(["", "Detected sources:"])
        for source in sources:
            lines.append(f"- {source}")

    if isinstance(recommended, list) and len(recommended) > 0:
        lines.extend(["", "Suggested families:"])
        for family in recommended:
            lines.append(f"- {family}")

    if isinstance(avoid, list) and len(avoid) > 0:
        lines.extend(["", "Avoid:"])
        for family in avoid:
            lines.append(f"- {family}")

    if isinstance(explanation, list) and len(explanation) > 0:
        lines.extend(["", "Why:"])
        for line in explanation:
            lines.append(f"- {line}")

    return "\n".join(lines)


def _render_batch_markdown(data: dict[str, object]) -> str:
    """Render a batch triage payload as Markdown text."""
    lines: list[str] = ["# Forecastability Batch Triage Results", ""]

    n_items = data.get("n_items", 0)
    n_failed = data.get("n_failed", 0)
    lines.append(f"**Series screened:** {n_items}")
    lines.append(f"**Failed items:** {n_failed}")

    summary_obj = data.get("summary_table")
    if not isinstance(summary_obj, list) or len(summary_obj) == 0:
        return "\n".join(lines)

    lines.extend(
        [
            "",
            (
                "| Rank | Series | Outcome | Readiness | Forecastability | "
                "Directness ratio | Exogenous usefulness | Next action |"
            ),
            (
                "|------|--------|---------|-----------|-----------------|"
                "------------------|----------------------|-------------|"
            ),
        ]
    )

    for entry in summary_obj:
        if not isinstance(entry, dict):
            continue
        entry_dict = {str(key): value for key, value in entry.items()}

        directness = entry_dict.get("directness_ratio")
        directness_text = "—"
        if isinstance(directness, int | float):
            directness_text = f"{float(directness):.4f}"

        line_template = (
            "| {rank} | {series_id} | {outcome} | {readiness_status} | "
            "{forecastability_class} | {directness} | "
            "{exogenous_usefulness} | {next_action} |"
        )
        lines.append(
            line_template.format(
                rank=entry_dict.get("rank", "—"),
                series_id=entry_dict.get("series_id", "—"),
                outcome=entry_dict.get("outcome", "—"),
                readiness_status=entry_dict.get("readiness_status", "—"),
                forecastability_class=entry_dict.get("forecastability_class", "—"),
                directness=directness_text,
                exogenous_usefulness=entry_dict.get("exogenous_usefulness", "—"),
                next_action=entry_dict.get("recommended_next_action", "—"),
            )
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def cmd_triage(args: argparse.Namespace) -> int:
    """Execute the ``triage`` subcommand.

    Args:
        args: Parsed CLI arguments from :func:`build_parser`.

    Returns:
        Exit code (``0`` = success, ``1`` = error).
    """
    if args.csv is not None:
        series = _series_from_csv(Path(args.csv), args.col)
    else:
        series = _series_from_json(args.series)

    try:
        goal = AnalysisGoal(args.goal)
    except ValueError:
        print(
            f"Error: unknown goal '{args.goal}'. Valid: {[g.value for g in AnalysisGoal]}",
            file=sys.stderr,
        )
        return 1

    exog: np.ndarray | None = None
    if args.exog_csv is not None:
        exog = _series_from_csv(Path(args.exog_csv), args.exog_col)

    request = TriageRequest(
        series=series,
        exog=exog,
        goal=goal,
        max_lag=args.max_lag,
        n_surrogates=args.n_surrogates,
        random_state=args.random_state,
    )

    result = run_triage(request)
    data = _triage_result_to_dict(result)

    if args.format == "json":
        print(json.dumps(data, indent=2, default=str))
    else:
        print(_render_markdown(data))

    return 0


def cmd_triage_batch(args: argparse.Namespace) -> int:
    """Execute the ``triage-batch`` subcommand.

    Args:
        args: Parsed CLI arguments from :func:`build_parser`.

    Returns:
        Exit code (``0`` = success).
    """
    request = _batch_request_from_json_file(Path(args.batch_json))
    result = run_batch_triage(request)
    data = _batch_result_to_dict(result)

    if args.export_summary_csv is not None:
        summary_rows = [row.model_dump(mode="json") for row in result.summary_table]
        _write_table_csv(
            Path(args.export_summary_csv),
            columns=SUMMARY_TABLE_COLUMNS,
            rows=summary_rows,
        )

    if args.export_failures_csv is not None:
        failure_rows = [row.model_dump(mode="json") for row in result.failure_table]
        _write_table_csv(
            Path(args.export_failures_csv),
            columns=FAILURE_TABLE_COLUMNS,
            rows=failure_rows,
        )

    if args.format == "json":
        print(json.dumps(data, indent=2, default=str))
    else:
        print(_render_batch_markdown(data))

    return 0


def cmd_extended(args: argparse.Namespace) -> int:
    """Execute the ``extended`` subcommand.

    Args:
        args: Parsed CLI arguments from :func:`build_parser`.

    Returns:
        Exit code (``0`` = success, ``1`` = validation error).
    """
    if args.csv is not None:
        series = _series_from_csv(Path(args.csv), args.col)
    else:
        series = _series_from_json(args.series)

    try:
        result = run_extended_forecastability_analysis(
            series,
            name=args.name,
            max_lag=args.max_lag,
            period=args.period,
            include_ami_geometry=args.include_ami_geometry,
            include_spectral=args.include_spectral,
            include_ordinal=args.include_ordinal,
            include_classical=args.include_classical,
            include_memory=args.include_memory,
            ordinal_embedding_dimension=args.ordinal_embedding_dimension,
            ordinal_delay=args.ordinal_delay,
            memory_min_scale=args.memory_min_scale,
            memory_max_scale=args.memory_max_scale,
        )
    except (ValidationError, ValueError) as exc:
        print(f"Error: invalid extended analysis input: {exc}", file=sys.stderr)
        return 1

    data = _extended_result_to_dict(result)
    if args.format == "json":
        print(json.dumps(data, indent=2))
    else:
        print(_render_extended_markdown(data))
    return 0


def cmd_list_scorers(args: argparse.Namespace) -> int:
    """Execute the ``list-scorers`` subcommand.

    Args:
        args: Parsed CLI arguments from :func:`build_parser`.

    Returns:
        Exit code (``0`` = success).
    """
    registry = default_registry()
    scorers = [
        {"name": info.name, "family": info.family, "description": info.description}
        for info in registry.list_scorers()
    ]

    if args.format == "json":
        print(json.dumps(scorers, indent=2))
    else:
        print(_render_scorers_markdown(scorers))

    return 0


# ---------------------------------------------------------------------------
# Parser builder (public for testing)
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser.

    Returns:
        Configured :class:`argparse.ArgumentParser` with ``triage``,
        ``triage-batch``, and ``list-scorers`` subparsers.
    """
    parser = argparse.ArgumentParser(
        prog="forecastability",
        description="Forecastability triage CLI — deterministic AMI/pAMI analysis.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ------------------------------------------------------------------
    # triage subcommand
    # ------------------------------------------------------------------
    triage_p = subparsers.add_parser(
        "triage",
        help="Run forecastability triage on a time series.",
    )
    source_grp = triage_p.add_mutually_exclusive_group(required=True)
    source_grp.add_argument("--csv", metavar="PATH", help="Path to CSV file.")
    source_grp.add_argument("--series", metavar="JSON", help="Series as JSON array string.")
    triage_p.add_argument("--col", metavar="COL", default=None, help="CSV column name.")
    triage_p.add_argument(
        "--exog-csv",
        dest="exog_csv",
        metavar="PATH",
        default=None,
        help="Optional exogenous CSV file.",
    )
    triage_p.add_argument(
        "--exog-col",
        dest="exog_col",
        metavar="COL",
        default=None,
        help="Column name in exog CSV.",
    )
    triage_p.add_argument(
        "--goal",
        default="univariate",
        choices=[g.value for g in AnalysisGoal],
        help="Analysis goal (default: univariate).",
    )
    triage_p.add_argument(
        "--max-lag",
        dest="max_lag",
        type=int,
        default=40,
        metavar="N",
        help="Maximum lag to evaluate (default: 40).",
    )
    triage_p.add_argument(
        "--n-surrogates",
        dest="n_surrogates",
        type=int,
        default=99,
        metavar="N",
        help="Number of surrogates for significance (default: 99).",
    )
    triage_p.add_argument(
        "--random-state",
        dest="random_state",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42).",
    )
    triage_p.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format (default: json).",
    )
    triage_p.set_defaults(func=cmd_triage)

    # ------------------------------------------------------------------
    # extended subcommand
    # ------------------------------------------------------------------
    extended_p = subparsers.add_parser(
        "extended",
        help="Run the AMI-first extended forecastability analysis.",
    )
    extended_source = extended_p.add_mutually_exclusive_group(required=True)
    extended_source.add_argument("--csv", metavar="PATH", help="Path to CSV file.")
    extended_source.add_argument("--series", metavar="JSON", help="Series as JSON array.")
    extended_p.add_argument(
        "--col",
        "--value-col",
        dest="col",
        default=None,
        metavar="COL",
        help="CSV column name.",
    )
    extended_p.add_argument("--name", default=None, help="Optional series identifier.")
    extended_p.add_argument(
        "--max-lag",
        dest="max_lag",
        type=int,
        default=40,
        metavar="N",
        help="Maximum lag to evaluate (default: 40).",
    )
    extended_p.add_argument(
        "--period",
        type=int,
        default=None,
        metavar="N",
        help="Optional seasonal period.",
    )
    extended_p.add_argument(
        "--ordinal-embedding-dimension",
        dest="ordinal_embedding_dimension",
        type=int,
        default=3,
        metavar="N",
        help="Ordinal embedding dimension (default: 3).",
    )
    extended_p.add_argument(
        "--ordinal-delay",
        dest="ordinal_delay",
        type=int,
        default=1,
        metavar="N",
        help="Ordinal delay (default: 1).",
    )
    extended_p.add_argument(
        "--memory-min-scale",
        dest="memory_min_scale",
        type=int,
        default=None,
        metavar="N",
        help="Optional minimum DFA scale.",
    )
    extended_p.add_argument(
        "--memory-max-scale",
        dest="memory_max_scale",
        type=int,
        default=None,
        metavar="N",
        help="Optional maximum DFA scale.",
    )
    extended_p.add_argument(
        "--without-ami-geometry",
        dest="include_ami_geometry",
        action="store_false",
        help="Disable the AMI geometry block.",
    )
    extended_p.add_argument(
        "--without-spectral",
        dest="include_spectral",
        action="store_false",
        help="Disable the spectral diagnostics block.",
    )
    extended_p.add_argument(
        "--without-ordinal",
        dest="include_ordinal",
        action="store_false",
        help="Disable the ordinal diagnostics block.",
    )
    extended_p.add_argument(
        "--without-classical",
        dest="include_classical",
        action="store_false",
        help="Disable the classical diagnostics block.",
    )
    extended_p.add_argument(
        "--without-memory",
        dest="include_memory",
        action="store_false",
        help="Disable the memory diagnostics block.",
    )
    extended_p.add_argument(
        "--format",
        choices=["json", "markdown", "brief"],
        default="json",
        help="Output format (default: json).",
    )
    extended_p.set_defaults(
        func=cmd_extended,
        include_ami_geometry=True,
        include_spectral=True,
        include_ordinal=True,
        include_classical=True,
        include_memory=True,
    )

    # ------------------------------------------------------------------
    # triage-batch subcommand
    # ------------------------------------------------------------------
    batch_p = subparsers.add_parser(
        "triage-batch",
        help="Run deterministic batch screening on multiple series.",
    )
    batch_p.add_argument(
        "--batch-json",
        dest="batch_json",
        metavar="PATH",
        required=True,
        help="Path to a batch triage JSON payload.",
    )
    batch_p.add_argument(
        "--export-summary-csv",
        dest="export_summary_csv",
        metavar="PATH",
        default=None,
        help="Optional path for exporting the ranked summary table CSV.",
    )
    batch_p.add_argument(
        "--export-failures-csv",
        dest="export_failures_csv",
        metavar="PATH",
        default=None,
        help="Optional path for exporting the failed-series table CSV.",
    )
    batch_p.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format (default: json).",
    )
    batch_p.set_defaults(func=cmd_triage_batch)

    # ------------------------------------------------------------------
    # list-scorers subcommand
    # ------------------------------------------------------------------
    scorers_p = subparsers.add_parser(
        "list-scorers",
        help="List all registered dependence scorers.",
    )
    scorers_p.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format (default: json).",
    )
    scorers_p.set_defaults(func=cmd_list_scorers)

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for the ``forecastability`` CLI command."""
    parser = build_parser()
    args = parser.parse_args()
    exit_code = args.func(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
