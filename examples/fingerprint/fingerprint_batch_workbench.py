"""Batch triage + fingerprint routing + executive report example.

This example demonstrates the v0.3.1 batch workbench path:

1. Batch triage for portfolio-level prioritization.
2. Geometry-backed fingerprint routing for each analyzable series.
3. Deterministic next-step forecasting plans.
4. Technical and executive markdown reports.
5. A1 -> A3 agent handoff for batch narratives.

Usage::

    uv run python examples/fingerprint/fingerprint_batch_workbench.py
"""

from __future__ import annotations

from pathlib import Path

from forecastability import (
    build_batch_forecastability_executive_markdown,
    build_batch_forecastability_markdown,
    generate_fingerprint_archetypes,
    generate_mediated_directness_drop,
    run_batch_forecastability_workbench,
)
from forecastability.adapters.agents.fingerprint_agent_interpretation_adapter import (
    interpret_fingerprint_batch,
)
from forecastability.adapters.agents.fingerprint_agent_payload_models import (
    FingerprintAgentPayload,
    fingerprint_agent_payload,
)
from forecastability.adapters.agents.fingerprint_summary_serializer import (
    SerialisedFingerprintSummary,
)
from forecastability.triage import BatchSeriesRequest, BatchTriageRequest

N_SAMPLES = 600
MAX_LAG = 24
N_SURROGATES = 99
RANDOM_STATE = 42

OUTPUT_REPORTS_DIR = Path("outputs/reports")


def _build_request() -> BatchTriageRequest:
    """Build a deterministic synthetic portfolio request."""
    series_map = generate_fingerprint_archetypes(n=N_SAMPLES, seed=RANDOM_STATE)
    series_map["mediated_directness_drop"] = generate_mediated_directness_drop(
        N_SAMPLES,
        seed=RANDOM_STATE,
    )[1]
    items = [
        BatchSeriesRequest(series_id=name, series=series.tolist())
        for name, series in series_map.items()
    ]
    return BatchTriageRequest(
        items=items,
        max_lag=MAX_LAG,
        n_surrogates=N_SURROGATES,
        random_state=RANDOM_STATE,
    )


def main() -> None:
    """Run the batch workbench and print report artifacts."""
    request = _build_request()
    result = run_batch_forecastability_workbench(request, top_n=3)

    technical_md = build_batch_forecastability_markdown(result)
    executive_md = build_batch_forecastability_executive_markdown(result)

    OUTPUT_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    technical_path = OUTPUT_REPORTS_DIR / "fingerprint_batch_workbench.md"
    executive_path = OUTPUT_REPORTS_DIR / "fingerprint_batch_executive_brief.md"
    technical_path.write_text(technical_md, encoding="utf-8")
    executive_path.write_text(executive_md, encoding="utf-8")

    payloads: list[FingerprintAgentPayload | SerialisedFingerprintSummary] = [
        fingerprint_agent_payload(item.fingerprint_bundle)
        for item in result.items
        if item.fingerprint_bundle is not None
    ]
    interpretations = interpret_fingerprint_batch(payloads)

    print("=" * 72)
    print("Batch Forecastability Workbench")
    print("=" * 72)
    print(result.summary.technical_summary)
    print()
    print("Per-series next steps:")
    for item in result.items:
        print(
            f"  - {item.series_id}: action={item.next_step.action}, "
            f"priority={item.next_step.priority_tier}, "
            f"families={item.next_step.recommended_model_families}"
        )

    print("\nA3 deterministic agent summaries:")
    for interpretation in interpretations:
        print(f"  - {interpretation.deterministic_summary}")
        if interpretation.cautionary_narrative:
            print(f"    caution: {interpretation.cautionary_narrative}")
        if interpretation.rich_signal_narrative:
            print(f"    signal: {interpretation.rich_signal_narrative}")

    print("\nArtifacts:")
    print(f"  - technical report: {technical_path}")
    print(f"  - executive brief: {executive_path}")


if __name__ == "__main__":
    main()
