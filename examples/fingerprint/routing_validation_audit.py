"""Minimal routing validation audit example (plan v0.3.3 V3_4-F05).

Runs ``run_routing_validation()`` over the full §6.1 synthetic archetype panel
and prints a per-case audit table together with a pass/fail/downgrade/abstain
summary. No real-panel path is needed — the example is self-contained.

Outputs::

    outputs/json/routing_validation_audit.json

Usage::

    uv run python examples/fingerprint/routing_validation_audit.py
"""

from __future__ import annotations

import json
from pathlib import Path

from forecastability import run_routing_validation
from forecastability.utils.types import RoutingPolicyAuditConfig, RoutingValidationBundle

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

N_PER_ARCHETYPE: int = 600
RANDOM_STATE: int = 42
OUTPUT_JSON = Path("outputs/json/routing_validation_audit.json")

# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

_OUTCOME_SYMBOL: dict[str, str] = {
    "pass": "✓",
    "fail": "✗",
    "downgrade": "↓",
    "abstain": "○",
}


def _print_case_table(bundle: RoutingValidationBundle) -> None:
    """Print a compact per-case audit table."""
    header = f"{'Case':<40} {'Out':<10} {'Conf':<8} {'Stab':>6}  Expected → Observed"
    print(header)
    print("-" * 100)
    for case in bundle.cases:
        symbol = _OUTCOME_SYMBOL.get(case.outcome, "?")
        observed_str = ", ".join(case.observed_primary_families)
        expected_str = ", ".join(case.expected_primary_families)
        stability = f"{case.rule_stability:.2f}" if case.rule_stability is not None else "n/a"
        print(
            f"{case.case_name:<40} {symbol} {case.outcome:<8} {case.confidence_label:<8}"
            f" {stability:>6}  [{expected_str}] → [{observed_str}]"
        )


def _print_summary(bundle: RoutingValidationBundle) -> None:
    """Print a one-line audit summary."""
    a = bundle.audit
    print()
    print(
        f"Summary: {a.total_cases} cases — "
        f"pass={a.passed_cases}  fail={a.failed_cases}  "
        f"downgrade={a.downgraded_cases}  abstain={a.abstained_cases}"
    )


# ---------------------------------------------------------------------------
# JSON serialisation
# ---------------------------------------------------------------------------


def _bundle_to_dict(bundle: RoutingValidationBundle) -> dict[str, object]:
    """Serialise the validation bundle to a JSON-safe dict."""
    return {
        "metadata": bundle.metadata,
        "audit": {
            "total_cases": bundle.audit.total_cases,
            "passed_cases": bundle.audit.passed_cases,
            "failed_cases": bundle.audit.failed_cases,
            "downgraded_cases": bundle.audit.downgraded_cases,
            "abstained_cases": bundle.audit.abstained_cases,
        },
        "cases": [
            {
                "case_name": c.case_name,
                "source_kind": c.source_kind,
                "outcome": c.outcome,
                "confidence_label": c.confidence_label,
                "rule_stability": c.rule_stability,
                "threshold_margin": c.threshold_margin,
                "expected_primary_families": c.expected_primary_families,
                "observed_primary_families": c.observed_primary_families,
                "notes": list(c.notes),
            }
            for c in bundle.cases
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the routing validation audit and print results."""
    print("=" * 100)
    print("Routing Validation Audit — Synthetic Panel")
    print(f"n_per_archetype={N_PER_ARCHETYPE}  random_state={RANDOM_STATE}")
    print("=" * 100)
    print()

    bundle = run_routing_validation(
        n_per_archetype=N_PER_ARCHETYPE,
        random_state=RANDOM_STATE,
        config=RoutingPolicyAuditConfig(),
    )

    _print_case_table(bundle)
    _print_summary(bundle)

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(_bundle_to_dict(bundle), indent=2))
    print(f"\nJSON written to {OUTPUT_JSON}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()
