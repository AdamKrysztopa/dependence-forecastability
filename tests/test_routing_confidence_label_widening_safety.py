"""Safety tests for additive RoutingConfidenceLabel widening (phase 0)."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import get_args

from forecastability.use_cases.run_batch_forecastability_workbench import _next_step_from_bundle
from forecastability.utils.types import (
    AmiInformationGeometry,
    FingerprintBundle,
    ForecastabilityFingerprint,
    RoutingConfidenceLabel,
    RoutingRecommendation,
)


def test_routing_confidence_label_contains_abstain_literal() -> None:
    """The widened alias must include abstain additively."""
    assert "abstain" in get_args(RoutingConfidenceLabel)


def test_batch_workbench_treats_abstain_as_non_usable() -> None:
    """Abstain confidence must never route into active benchmark actions."""
    bundle = FingerprintBundle(
        target_name="case",
        geometry=AmiInformationGeometry(
            signal_to_noise=0.3,
            information_horizon=12,
            information_structure="periodic",
            informative_horizons=[1, 2, 3, 12],
        ),
        fingerprint=ForecastabilityFingerprint(
            information_mass=0.2,
            information_horizon=12,
            information_structure="periodic",
            nonlinear_share=0.1,
            signal_to_noise=0.3,
            informative_horizons=[1, 2, 3, 12],
        ),
        recommendation=RoutingRecommendation(
            primary_families=["tbats"],
            confidence_label="abstain",
            rationale=["synthetic abstain guard"],
        ),
        profile_summary={"n_sig_lags": 4},
    )

    next_step = _next_step_from_bundle(series_id="case", bundle=bundle)
    assert next_step.action in {"hybrid_review", "baseline_monitoring"}
    assert next_step.action not in {
        "seasonal_benchmark",
        "linear_benchmark",
        "nonlinear_benchmark",
    }


def test_no_open_eq_or_neq_confidence_label_string_checks() -> None:
    """Guard against open confidence-label equality checks after widening."""
    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / "src" / "forecastability"

    disallowed: list[str] = []
    for path in src_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            if len(node.ops) != 1 or len(node.comparators) != 1:
                continue
            op = node.ops[0]
            if not isinstance(op, (ast.Eq, ast.NotEq)):
                continue

            left = node.left
            right = node.comparators[0]
            left_attr = isinstance(left, ast.Attribute) and left.attr == "confidence_label"
            right_attr = isinstance(right, ast.Attribute) and right.attr == "confidence_label"
            left_str = isinstance(left, ast.Constant) and isinstance(left.value, str)
            right_str = isinstance(right, ast.Constant) and isinstance(right.value, str)

            if (left_attr and right_str) or (right_attr and left_str):
                rel = path.relative_to(repo_root)
                disallowed.append(f"{rel}:{node.lineno}")

    assert not disallowed, (
        "Open confidence_label string comparisons are forbidden after widening; "
        "use closed-set membership instead. Found: " + ", ".join(sorted(disallowed))
    )
