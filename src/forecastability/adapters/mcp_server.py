"""MCP server transport adapter for the forecastability triage pipeline (AGT-011).

Exposes deterministic forecastability capabilities as MCP tools and resources,
enabling IDE / assistant interop through the Model Context Protocol.

**Tools**

- ``validate_series`` — run the readiness gate and return a structured report.
- ``run_triage_tool`` — execute the complete triage pipeline.
- ``list_scorers_tool`` — list all registered dependence scorers.

**Resources**

- ``scorers://catalog`` — full scorer catalog as JSON.
- ``schema://triage-request`` — annotated JSON schema example for a triage request.

The ``mcp`` module-level object is ``None`` when the ``mcp`` package is not
installed; the helper functions (``_build_triage_request``, etc.) are always
importable for testing without a running MCP server.

Usage (requires ``transport`` optional group)::

    uv sync --extra transport

    # stdio transport (default — suitable for IDE MCP clients)
    python -m forecastability.adapters.mcp_server

    # streamable-HTTP transport (for network access)
    python -m forecastability.adapters.mcp_server --http --port 8001
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np

try:
    from mcp.server.fastmcp import FastMCP

    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False

from forecastability.adapters.triage_presenter import present_triage_result
from forecastability.scorers import default_registry
from forecastability.triage.models import AnalysisGoal, ReadinessReport, TriageRequest, TriageResult
from forecastability.triage.readiness import assess_readiness
from forecastability.use_cases.run_triage import run_triage

# ---------------------------------------------------------------------------
# Pure helper functions (testable without MCP runtime)
# ---------------------------------------------------------------------------


def _build_triage_request(
    series: list[float],
    *,
    exog: list[float] | None = None,
    goal: str = "univariate",
    max_lag: int = 40,
    n_surrogates: int = 99,
    random_state: int = 42,
) -> TriageRequest:
    """Construct a :class:`~forecastability.triage.models.TriageRequest` from
    JSON-safe tool arguments.

    Args:
        series: Target time series as a list of floats.
        exog: Optional exogenous series (must match ``series`` length).
        goal: Analysis goal string (``"univariate"`` or ``"exogenous"``).
        max_lag: Maximum lag to evaluate.
        n_surrogates: Number of surrogates for significance estimation.
        random_state: Seed for deterministic execution.

    Returns:
        Frozen :class:`~forecastability.triage.models.TriageRequest`.

    Raises:
        ValueError: When ``goal`` is not a valid
            :class:`~forecastability.triage.models.AnalysisGoal` member.
    """
    return TriageRequest(
        series=np.asarray(series, dtype=np.float64),
        exog=np.asarray(exog, dtype=np.float64) if exog is not None else None,
        goal=AnalysisGoal(goal),
        max_lag=max_lag,
        n_surrogates=n_surrogates,
        random_state=random_state,
    )


def _readiness_to_json(report: ReadinessReport) -> str:
    """Serialise a ``ReadinessReport`` to a compact JSON string.

    Args:
        report: ``ReadinessReport`` from ``assess_readiness()``.

    Returns:
        Indented JSON string with ``status`` and ``warnings``.
    """
    return json.dumps(
        {
            "status": report.status.value,
            "warnings": [{"code": w.code, "message": w.message} for w in report.warnings],
        },
        indent=2,
    )


def _triage_result_to_json(result: TriageResult) -> str:
    """Serialise a ``TriageResult`` to a compact JSON string.

    Large numpy arrays are excluded; summary statistics are returned instead.

    Args:
        result: ``TriageResult`` from ``run_triage()``.

    Returns:
        Indented JSON string with analysis summary.
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
        }

    if view.recommendation is not None:
        out["recommendation"] = view.recommendation

    return json.dumps(out, indent=2)


# ---------------------------------------------------------------------------
# MCP server (only created when `mcp` is installed)
# ---------------------------------------------------------------------------

if _MCP_AVAILABLE:
    mcp = FastMCP("Forecastability")

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    @mcp.tool()
    def validate_series(
        series: list[float],
        max_lag: int = 40,
        n_surrogates: int = 99,
    ) -> str:
        """Check if a time series is ready for forecastability analysis.

        Runs the deterministic readiness gate and returns a structured JSON
        report indicating whether the series is ``clear``, ``warning``, or
        ``blocked`` for the requested analysis parameters.

        Args:
            series: Target time series as a list of floats.
            max_lag: Maximum lag to evaluate (used for lag feasibility check).
            n_surrogates: Number of surrogates (used for significance
                feasibility check).

        Returns:
            JSON string with ``status`` (``"clear"``, ``"warning"``, or
            ``"blocked"``) and a ``warnings`` list.
        """
        request = TriageRequest(
            series=np.asarray(series, dtype=np.float64),
            max_lag=max_lag,
            n_surrogates=n_surrogates,
        )
        report = assess_readiness(request)
        return _readiness_to_json(report)

    @mcp.tool()
    def run_triage_tool(
        series: list[float],
        goal: str = "univariate",
        max_lag: int = 40,
        n_surrogates: int = 99,
        random_state: int = 42,
        exog: list[float] | None = None,
    ) -> str:
        """Run the complete forecastability triage pipeline.

        Executes: readiness gate → method routing → AMI/pAMI compute →
        interpretation → recommendation.  All steps are deterministic; no LLM.

        Args:
            series: Target time series as a list of floats.
            goal: ``"univariate"`` or ``"exogenous"``.
            max_lag: Maximum lag to evaluate.
            n_surrogates: Number of surrogates for significance estimation.
            random_state: Seed for reproducibility.
            exog: Optional exogenous series (must match ``series`` length).

        Returns:
            JSON string with triage results, including ``blocked`` flag,
            readiness, method plan, analysis summary, interpretation
            (forecastability class, modeling regime), and recommendation.
        """
        request = _build_triage_request(
            series,
            exog=exog,
            goal=goal,
            max_lag=max_lag,
            n_surrogates=n_surrogates,
            random_state=random_state,
        )
        result = run_triage(request)
        return _triage_result_to_json(result)

    @mcp.tool()
    def list_scorers_tool() -> str:
        """List all available dependence scorers in the registry.

        Returns:
            JSON array listing scorer ``name``, ``family``, and
            ``description`` for every registered scorer.
        """
        registry = default_registry()
        scorers = [
            {"name": info.name, "family": info.family, "description": info.description}
            for info in registry.list_scorers()
        ]
        return json.dumps(scorers, indent=2)

    # ------------------------------------------------------------------
    # Resources
    # ------------------------------------------------------------------

    @mcp.resource("scorers://catalog")
    def scorer_catalog() -> str:
        """Return the full scorer catalog as JSON.

        Returns:
            JSON string with all registered scorer metadata (name, family,
            description).
        """
        registry = default_registry()
        scorers = [
            {"name": info.name, "family": info.family, "description": info.description}
            for info in registry.list_scorers()
        ]
        return json.dumps(scorers, indent=2)

    @mcp.resource("schema://triage-request")
    def triage_request_schema() -> str:
        """Return an annotated example showing all accepted triage request fields.

        Returns:
            JSON string documenting the ``run_triage_tool`` argument schema
            with type annotations and default values.
        """
        schema = {
            "series": {
                "type": "array[float]",
                "required": True,
                "description": "Target time series",
            },
            "exog": {
                "type": "array[float] | null",
                "required": False,
                "default": None,
                "description": "Optional exogenous series",
            },
            "goal": {
                "type": "string",
                "required": False,
                "default": "univariate",
                "enum": ["univariate", "exogenous"],
            },
            "max_lag": {"type": "integer", "required": False, "default": 40},
            "n_surrogates": {"type": "integer", "required": False, "default": 99},
            "random_state": {"type": "integer", "required": False, "default": 42},
        }
        return json.dumps(schema, indent=2)

else:
    mcp = None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the MCP server.

    Defaults to stdio transport (suitable for IDE MCP clients).
    Pass ``--http`` to use the streamable-HTTP transport instead.
    """
    import argparse
    import sys

    if not _MCP_AVAILABLE or mcp is None:
        print(
            "mcp package not found. Install with: uv sync --extra transport",
            file=sys.stderr,
        )
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Forecastability MCP server.")
    parser.add_argument("--http", action="store_true", help="Use streamable-HTTP transport.")
    args = parser.parse_args()

    if args.http:
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
