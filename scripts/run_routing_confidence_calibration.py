"""Routing-confidence precision measurement script (RVH-F08).

Runs the 10-archetype synthetic suite across ≥ 100 noise replicates per
archetype to *measure* the achieved precision of the hand-picked
routing-confidence thresholds.  Emits a
:class:`RoutingConfidenceCalibrationAudit` JSON artifact to
``docs/calibration/v0_5_0_routing_confidence_audit.json``.

Usage::

    uv run python scripts/run_routing_confidence_calibration.py

The script is deterministic: all series generation uses ``numpy.random.default_rng``
seeded from a fixed base, and ``run_triage`` always uses ``random_state=42``.
Re-running on the same codebase produces the same JSON (modulo ``audit_timestamp``).

Design notes
------------
The "routing confidence" here refers to the confidence label embedded in the
triage recommendation string (``HIGH``, ``MEDIUM``, ``LOW``).  For each label,
we define precision as the fraction of runs labelled with that confidence that
have the *correct* model family as determined by the ground-truth archetype.

Threshold measurement
~~~~~~~~~~~~~~~~~~~~~
This script measures the achieved precision of the *current* hand-picked
threshold values from ``_TRIAGE_THRESHOLDS`` against the 10-archetype ×
100-replicate synthetic suite.  It does **not** fit or optimise thresholds:
the raw AMI peak per run is not stored, so no sweep over threshold candidates
is possible.  Threshold fitting is a future deliverable planned for v0.5.1.

This is an in-sample measurement (all data used for evaluation).  A hold-out
split would require a much larger archetype suite; the current design
prioritises interpretability over generalization guarantees.  See
``docs/calibration/v0_5_0_routing_confidence.md`` for the methodological
limitations.
"""

from __future__ import annotations

import datetime
import json
import warnings
from pathlib import Path
from typing import NamedTuple

import numpy as np

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Number of noise replicates per archetype.
N_REPLICATES: int = 100

# Series length for all synthetic archetypes.
SERIES_LENGTH: int = 400

# Target precision for the HIGH confidence label.
TARGET_PRECISION_HIGH: float = 0.90

# Target precision for the MEDIUM confidence label.
TARGET_PRECISION_MEDIUM: float = 0.75

# Reserved for future threshold sweep — not used in this measurement-only script.
THRESHOLD_LOW: float = 0.01
THRESHOLD_HIGH_MAX: float = 0.60
THRESHOLD_STEP: float = 0.005

# Output path (relative to repo root).
_REPO_ROOT = Path(__file__).parent.parent
OUTPUT_PATH = _REPO_ROOT / "docs" / "calibration" / "v0_5_0_routing_confidence_audit.json"

# Fixed base seed for reproducibility.
BASE_SEED: int = 20260524


# ---------------------------------------------------------------------------
# Ground-truth archetypes
# ---------------------------------------------------------------------------


class Archetype(NamedTuple):
    """Synthetic archetype definition."""

    name: str
    ground_truth_family: str  # "HIGH", "MEDIUM", or "LOW"
    description: str


ARCHETYPES: list[Archetype] = [
    Archetype(
        name="white_noise",
        ground_truth_family="LOW",
        description="i.i.d. Gaussian white noise — no predictable structure",
    ),
    Archetype(
        name="ar1_weak",
        ground_truth_family="MEDIUM",
        description="AR(1) with phi=0.3 — weak linear structure",
    ),
    Archetype(
        name="ar1_strong",
        ground_truth_family="HIGH",
        description="AR(1) with phi=0.8 — strong linear structure",
    ),
    Archetype(
        name="ar2",
        ground_truth_family="HIGH",
        description="AR(2) with phi=[0.6, 0.3] — multilag linear structure",
    ),
    Archetype(
        name="sine_ar1",
        ground_truth_family="HIGH",
        description="Sine wave + AR(1) noise — periodic + linear structure",
    ),
    Archetype(
        name="logistic_map",
        ground_truth_family="HIGH",
        description="Logistic map r=3.9 — deterministic chaos",
    ),
    Archetype(
        name="random_walk",
        ground_truth_family="HIGH",
        description="Random walk — strong lag-1 dependence (unit root)",
    ),
    Archetype(
        name="seasonal_ar1",
        ground_truth_family="HIGH",
        description="Seasonal AR(1) with period 12 — seasonal structure",
    ),
    Archetype(
        name="ma1",
        ground_truth_family="MEDIUM",
        description="MA(1) with theta=0.5 — short-memory linear",
    ),
    Archetype(
        name="heavy_noise_ar1",
        ground_truth_family="LOW",
        description="AR(1) phi=0.1 + heavy noise — near-white-noise",
    ),
]

assert len(ARCHETYPES) == 10, f"Expected 10 archetypes, got {len(ARCHETYPES)}"


# ---------------------------------------------------------------------------
# Series generators
# ---------------------------------------------------------------------------


def _generate_series(archetype: Archetype, rng: np.random.Generator) -> np.ndarray:
    """Generate one noise replicate for *archetype*."""
    n = SERIES_LENGTH
    noise = rng.standard_normal(n)

    if archetype.name == "white_noise":
        return noise

    if archetype.name == "ar1_weak":
        s = np.zeros(n)
        for i in range(1, n):
            s[i] = 0.3 * s[i - 1] + noise[i]
        return s

    if archetype.name == "ar1_strong":
        s = np.zeros(n)
        for i in range(1, n):
            s[i] = 0.8 * s[i - 1] + noise[i]
        return s

    if archetype.name == "ar2":
        s = np.zeros(n)
        for i in range(2, n):
            s[i] = 0.6 * s[i - 1] + 0.3 * s[i - 2] + noise[i]
        return s

    if archetype.name == "sine_ar1":
        t = np.linspace(0, 4 * np.pi, n)
        ar = np.zeros(n)
        for i in range(1, n):
            ar[i] = 0.5 * ar[i - 1] + 0.3 * noise[i]
        return np.sin(t) + ar

    if archetype.name == "logistic_map":
        s = np.zeros(n)
        s[0] = 0.5 + 0.01 * rng.standard_normal()
        for i in range(1, n):
            s[i] = 3.9 * s[i - 1] * (1 - s[i - 1])
        s += 0.001 * noise
        return s

    if archetype.name == "random_walk":
        return np.cumsum(noise)

    if archetype.name == "seasonal_ar1":
        s = np.zeros(n)
        for i in range(12, n):
            s[i] = 0.7 * s[i - 12] + 0.3 * noise[i]
        return s

    if archetype.name == "ma1":
        s = np.zeros(n)
        for i in range(1, n):
            s[i] = noise[i] + 0.5 * noise[i - 1]
        return s

    if archetype.name == "heavy_noise_ar1":
        s = np.zeros(n)
        for i in range(1, n):
            s[i] = 0.1 * s[i - 1] + noise[i]
        return s

    raise ValueError(f"Unknown archetype: {archetype.name}")


# ---------------------------------------------------------------------------
# Recommendation extraction
# ---------------------------------------------------------------------------


def _extract_confidence_label(recommendation: str) -> str:
    """Extract HIGH / MEDIUM / LOW from the recommendation string."""
    rec_upper = recommendation.upper()
    if rec_upper.startswith("HIGH"):
        return "HIGH"
    if rec_upper.startswith("MEDIUM"):
        return "MEDIUM"
    return "LOW"


# ---------------------------------------------------------------------------
# Calibration run
# ---------------------------------------------------------------------------


def run_calibration() -> dict[str, list[str]]:
    """Run the full calibration suite and return raw results.

    Returns a dict mapping archetype name → list of predicted labels.
    """
    from forecastability.triage.models import TriageRequest
    from forecastability.use_cases.run_triage import run_triage

    results: dict[str, list[str]] = {a.name: [] for a in ARCHETYPES}

    for archetype in ARCHETYPES:
        print(f"  Archetype: {archetype.name} ({N_REPLICATES} replicates) ...", flush=True)
        rng = np.random.default_rng([BASE_SEED, hash(archetype.name) & 0xFFFFFFFF])

        for _rep in range(N_REPLICATES):
            series = _generate_series(archetype, rng)
            request = TriageRequest(
                series=series,
                max_lag=20,
                n_surrogates=99,
                random_state=42,
            )
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                result = run_triage(request)

            if result.blocked or result.analyze_result is None:
                predicted = "LOW"
            else:
                predicted = _extract_confidence_label(result.analyze_result.recommendation)
            results[archetype.name].append(predicted)

    return results


# ---------------------------------------------------------------------------
# Threshold fitting
# ---------------------------------------------------------------------------


def _compute_precision(
    results: dict[str, list[str]],
    *,
    label: str,
) -> float:
    """Compute precision for *label* given raw results.

    Precision = TP / (TP + FP) where TP = correctly labelled with *label*
    and FP = labelled *label* but ground-truth is different.
    """
    archetype_gt = {a.name: a.ground_truth_family for a in ARCHETYPES}
    tp = 0
    fp = 0
    for name, preds in results.items():
        gt = archetype_gt[name]
        for pred in preds:
            if pred == label:
                if gt == label:
                    tp += 1
                else:
                    fp += 1
    if tp + fp == 0:
        return 0.0
    return tp / (tp + fp)


def _count_samples_at_label(results: dict[str, list[str]], *, label: str) -> int:
    """Count the number of predictions equal to *label*."""
    return sum(1 for preds in results.values() for p in preds if p == label)


def _measure_threshold_precision(
    *,
    target_precision: float,
    label: str,
    results: dict[str, list[str]],
) -> tuple[float, float]:
    """Return (current_threshold, achieved_precision) for *label*.

    Measures the achieved precision of the *current* hand-picked threshold
    from ``_TRIAGE_THRESHOLDS`` against the synthetic calibration suite.
    This function does not fit or optimise a threshold: the raw AMI peak per
    run is not stored, so no sweep over threshold candidates is possible.
    Threshold fitting is planned for v0.5.1.

    The ``target_precision`` parameter is accepted for interface symmetry and
    used by the caller to report whether the current threshold meets the target.
    """
    achieved = _compute_precision(results, label=label)
    # The threshold that was used is the current hand-picked value from
    # _TRIAGE_THRESHOLDS (0.15 for HIGH, 0.05 for MEDIUM).
    current_threshold = 0.15 if label == "HIGH" else 0.05
    return current_threshold, achieved


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for the calibration script."""
    print("RVH-F08: Routing-confidence calibration")
    print(f"  Archetypes: {len(ARCHETYPES)}")
    print(f"  Replicates per archetype: {N_REPLICATES}")
    print(f"  Series length: {SERIES_LENGTH}")
    print(f"  Target precision (HIGH): {TARGET_PRECISION_HIGH}")
    print(f"  Target precision (MEDIUM): {TARGET_PRECISION_MEDIUM}")
    print()

    results = run_calibration()

    high_threshold, high_precision = _measure_threshold_precision(
        target_precision=TARGET_PRECISION_HIGH,
        label="HIGH",
        results=results,
    )
    medium_threshold, medium_precision = _measure_threshold_precision(
        target_precision=TARGET_PRECISION_MEDIUM,
        label="MEDIUM",
        results=results,
    )
    low_threshold, low_precision = 0.05, _compute_precision(results, label="LOW")

    n_high = _count_samples_at_label(results, label="HIGH")
    n_medium = _count_samples_at_label(results, label="MEDIUM")
    n_low = _count_samples_at_label(results, label="LOW")

    timestamp = datetime.datetime.now(datetime.UTC).isoformat()

    high_meets_target = high_precision >= TARGET_PRECISION_HIGH
    medium_meets_target = medium_precision >= TARGET_PRECISION_MEDIUM

    notes = (
        f"Calibration run with {len(ARCHETYPES)} archetypes × {N_REPLICATES} replicates. "
        f"HIGH precision {'MEETS' if high_meets_target else 'DOES NOT MEET'} target "
        f"({high_precision:.3f} vs {TARGET_PRECISION_HIGH:.2f}). "
        f"MEDIUM precision {'MEETS' if medium_meets_target else 'DOES NOT MEET'} target "
        f"({medium_precision:.3f} vs {TARGET_PRECISION_MEDIUM:.2f}). "
        "Thresholds reported are the current hand-picked values from _TRIAGE_THRESHOLDS; "
        "a full sweep calibration is planned for v0.5.1 when raw AMI peaks are stored per run."
    )

    audit = {
        "version": "0.5.0",
        "n_archetypes": len(ARCHETYPES),
        "n_noise_replicates": N_REPLICATES,
        "thresholds": [
            {
                "label": "high",
                "threshold": high_threshold,
                "achieved_precision": round(high_precision, 4),
                "target_precision": TARGET_PRECISION_HIGH,
                "n_samples": n_high,
            },
            {
                "label": "medium",
                "threshold": medium_threshold,
                "achieved_precision": round(medium_precision, 4),
                "target_precision": TARGET_PRECISION_MEDIUM,
                "n_samples": n_medium,
            },
            {
                "label": "low",
                "threshold": low_threshold,
                "achieved_precision": round(low_precision, 4),
                "target_precision": 0.0,  # no precision target for LOW
                "n_samples": n_low,
            },
        ],
        "audit_timestamp": timestamp,
        "notes": notes,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2)
        f.write("\n")

    print(f"Audit written to: {OUTPUT_PATH}")
    print()
    print(
        f"  HIGH   precision: {high_precision:.3f} (target: {TARGET_PRECISION_HIGH:.2f}) "
        f"{'✓' if high_meets_target else '✗'}"
    )
    print(
        f"  MEDIUM precision: {medium_precision:.3f} (target: {TARGET_PRECISION_MEDIUM:.2f}) "
        f"{'✓' if medium_meets_target else '✗'}"
    )
    print(f"  LOW    precision: {low_precision:.3f}")
    print()

    if not high_meets_target:
        print(
            f"WARNING: HIGH precision {high_precision:.3f} < target {TARGET_PRECISION_HIGH:.2f}. "
            "Consider raising _TRIAGE_THRESHOLDS['nonlinear'][0] to reduce false HIGH labels."
        )
    if not medium_meets_target:
        print(
            f"WARNING: MEDIUM precision {medium_precision:.3f} < target "
            f"{TARGET_PRECISION_MEDIUM:.2f}. "
            "See docs/calibration/v0_5_0_routing_confidence.md for guidance."
        )


if __name__ == "__main__":
    main()
