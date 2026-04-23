"""Routing validation regression fixture generation, rebuild, and verification.

Generates deterministic routing validation bundles for the ten canonical synthetic
archetypes, serialises per-case outcomes, confidence labels, and the aggregate audit
summary to JSON, and verifies rebuilt outputs against frozen expected files.

Fixture files written by ``rebuild_fixtures``:

- ``docs/fixtures/routing_validation_regression/expected/synthetic_panel.json``
  Per-case discrete and numeric fields (outcome, confidence_label, families,
  threshold_margin, rule_stability, fingerprint_penalty_count).

- ``docs/fixtures/routing_validation_regression/expected/audit_summary.json``
  Aggregate audit counts (total, passed, failed, downgraded, abstained).

- ``docs/fixtures/routing_validation_regression/expected/confidence_labels.json``
  Flat mapping from case_name → confidence_label.

- ``docs/fixtures/routing_validation_regression/expected/calibration.json``
  Written exclusively by ``calibrate_near_threshold_amplitude``; consumed by
  ``rebuild_fixtures`` when present to pass the pinned amplitude through to the
  ``weak_seasonal_near_threshold`` archetype generator.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

import numpy as np

from forecastability.services.routing_policy_audit_service import (
    _compute_threshold_margin,
    build_routing_threshold_vector,
)
from forecastability.use_cases.run_forecastability_fingerprint import (
    run_forecastability_fingerprint,
)
from forecastability.use_cases.run_routing_validation import run_routing_validation
from forecastability.utils.synthetic import (
    generate_weak_seasonal_near_threshold_archetype,
)
from forecastability.utils.types import (
    RoutingPolicyAuditConfig,
    RoutingValidationBundle,
)

_logger = logging.getLogger(__name__)

# Tolerance for cross-platform float comparison (per repo memory note).
# The weak-seasonal pinned calibration is intentionally close to the audit
# margin boundary, so Linux/macOS numeric kernels can drift by a few ppm while
# leaving the routed outcome and confidence unchanged.
_ATOL = 1e-5
_RTOL = 1e-4

# Canonical rebuild parameters (seed, n_per_archetype).
_REBUILD_SEED = 42
_REBUILD_N = 600

# Calibration sweep parameters (plan §6.3).
# Range [0.80, 2.00]: for this additive sinusoid + unit-variance noise archetype,
# the AMI framework first detects seasonal structure at amplitude ≈ 0.85;
# amplitudes below 0.80 produce information_mass = 0.0 and d_theta is stuck at
# low_mass_max = 0.03, which is above the target band.
_CALIBRATION_SEED = 42
_CALIBRATION_N = 600
_SWEEP_AMPLITUDES = np.linspace(0.80, 2.00, 61)  # step ≈ 0.02

_EXPECTED_SUBDIR = Path("docs/fixtures/routing_validation_regression/expected")

# Fixture file names.
_SYNTHETIC_PANEL_FILE = "synthetic_panel.json"
_AUDIT_SUMMARY_FILE = "audit_summary.json"
_CONFIDENCE_LABELS_FILE = "confidence_labels.json"
_CALIBRATION_FILE = "calibration.json"


# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------


def _build_synthetic_panel_payload(bundle: RoutingValidationBundle) -> list[dict[str, Any]]:
    """Serialise per-case validation results to a compact regression payload.

    Discrete fields (outcome, confidence_label, family lists) are serialised
    exactly; float fields (threshold_margin, rule_stability) are rounded to 10
    decimal places to keep fixture diffs readable while preserving enough
    precision for cross-platform float comparison.
    """
    rows: list[dict[str, Any]] = []
    for case in bundle.cases:
        rows.append(
            {
                "case_name": case.case_name,
                "source_kind": case.source_kind,
                "outcome": case.outcome,
                "confidence_label": case.confidence_label,
                "expected_primary_families": sorted(case.expected_primary_families),
                "observed_primary_families": sorted(case.observed_primary_families),
                "threshold_margin": case.threshold_margin,
                "rule_stability": case.rule_stability,
                "fingerprint_penalty_count": case.fingerprint_penalty_count,
            }
        )
    return rows


def _build_audit_summary_payload(bundle: RoutingValidationBundle) -> dict[str, Any]:
    """Serialise the aggregate audit to a compact regression payload."""
    return {
        "total_cases": bundle.audit.total_cases,
        "passed_cases": bundle.audit.passed_cases,
        "failed_cases": bundle.audit.failed_cases,
        "downgraded_cases": bundle.audit.downgraded_cases,
        "abstained_cases": bundle.audit.abstained_cases,
    }


def _build_confidence_labels_payload(bundle: RoutingValidationBundle) -> dict[str, str]:
    """Serialise per-case confidence labels to a flat name→label mapping."""
    return {case.case_name: case.confidence_label for case in bundle.cases}


# ---------------------------------------------------------------------------
# Calibration sweep
# ---------------------------------------------------------------------------


def calibrate_near_threshold_amplitude(
    *,
    sweep_seed: int = _CALIBRATION_SEED,
    sweep_n: int = _CALIBRATION_N,
    config: RoutingPolicyAuditConfig | None = None,
) -> dict[str, Any]:
    """Sweep sinusoid amplitude for the weak_seasonal_near_threshold archetype.

    Sweeps amplitude over ``[0.80, 2.00]`` at 61 steps (≈ 0.02 per step),
    fingerprints each candidate series, and selects the amplitude whose
    normalised threshold-distance ``d_theta(f)`` lies in
    ``[0.5 * tau_margin_medium, 0.5 * tau_margin]`` (plan §6.3).

    When multiple amplitudes satisfy the target band, the one whose margin
    is closest to the band centre is selected.

    Args:
        sweep_seed: Integer seed for the archetype generator and surrogate computation.
        sweep_n: Number of observations in each candidate series.
        config: Audit config providing tau scalars; defaults to
            ``RoutingPolicyAuditConfig()`` (v0.3.3 conservative defaults).

    Returns:
        Dict suitable for writing to ``calibration.json``, containing:
        - ``calibrated_amplitude``: the selected float value
        - ``threshold_margin_at_calibration``: d_theta(f) at the chosen amplitude
        - ``target_range_low`` / ``target_range_high``: the target band
        - ``tau_margin``, ``tau_margin_medium``: config scalars used
        - ``sweep_seed``, ``sweep_n``: the parameters used

    Raises:
        RuntimeError: If no amplitude in the sweep lands inside the target band.
    """
    cfg = config if config is not None else RoutingPolicyAuditConfig()
    target_low = 0.5 * cfg.tau_margin_medium
    target_high = 0.5 * cfg.tau_margin
    band_centre = 0.5 * (target_low + target_high)

    _logger.info(
        "Calibration sweep: amplitudes [0.80, 2.00] × %d steps; target d_theta band [%.4f, %.4f]",
        len(_SWEEP_AMPLITUDES),
        target_low,
        target_high,
    )

    candidates: list[tuple[float, float]] = []  # (amplitude, d_theta)

    for amplitude in _SWEEP_AMPLITUDES:
        amp = float(amplitude)
        series, _ = generate_weak_seasonal_near_threshold_archetype(
            sweep_n,
            sweep_seed + 3,  # same seed offset as generate_routing_validation_archetypes
            amplitude=amp,
        )
        max_lag = min(24, max(4, sweep_n // 20))
        try:
            fp_bundle = run_forecastability_fingerprint(
                series,
                target_name="weak_seasonal_near_threshold",
                max_lag=max_lag,
                n_surrogates=99,
                random_state=sweep_seed,
            )
        except Exception:
            _logger.debug("Fingerprint failed for amplitude=%.4f; skipping.", amp)
            continue

        threshold_vector = build_routing_threshold_vector(fp_bundle.fingerprint)
        margin = _compute_threshold_margin(fp_bundle.fingerprint, threshold_vector, config=cfg)
        _logger.debug("  amplitude=%.4f → d_theta=%.6f", amp, margin)

        if target_low <= margin <= target_high:
            candidates.append((amp, margin))

    if not candidates:
        raise RuntimeError(
            f"Calibration sweep found no amplitude in [0.80, 2.00] whose "
            f"d_theta(f) lands in [{target_low:.4f}, {target_high:.4f}]. "
            f"Inspect logs for per-amplitude d_theta values. "
            f"Consider widening the sweep range or relaxing the target band."
        )

    # Select the amplitude closest to the band centre.
    best_amp, best_margin = min(candidates, key=lambda t: abs(t[1] - band_centre))
    _logger.info(
        "Calibration result: amplitude=%.4f → d_theta=%.6f (band centre=%.4f)",
        best_amp,
        best_margin,
        band_centre,
    )

    return {
        "calibrated_amplitude": best_amp,
        "threshold_margin_at_calibration": best_margin,
        "target_range_low": target_low,
        "target_range_high": target_high,
        "tau_margin": cfg.tau_margin,
        "tau_margin_medium": cfg.tau_margin_medium,
        "sweep_seed": sweep_seed,
        "sweep_n": sweep_n,
    }


# ---------------------------------------------------------------------------
# Rebuild and verify
# ---------------------------------------------------------------------------


def _load_calibration(expected_dir: Path) -> float | None:
    """Load the pinned weak_seasonal amplitude from calibration.json if present."""
    cal_path = expected_dir / _CALIBRATION_FILE
    if not cal_path.exists():
        return None
    payload = json.loads(cal_path.read_text(encoding="utf-8"))
    amplitude = payload.get("calibrated_amplitude")
    if amplitude is None:
        return None
    return float(amplitude)


def load_pinned_weak_seasonal_amplitude(repo_root: Path) -> float | None:
    """Load the pinned weak-seasonal amplitude from the repository fixture path."""
    return _load_calibration(repo_root / _EXPECTED_SUBDIR)


def _run_validation_bundle(
    *,
    weak_seasonal_amplitude: float | None,
) -> RoutingValidationBundle:
    """Run routing validation via the public use case with an optional calibration."""
    if weak_seasonal_amplitude is not None:
        _logger.info("Using calibrated weak_seasonal amplitude: %.4f", weak_seasonal_amplitude)
    return run_routing_validation(
        real_panel_path=None,
        n_per_archetype=_REBUILD_N,
        random_state=_REBUILD_SEED,
        weak_seasonal_amplitude=weak_seasonal_amplitude,
        config=RoutingPolicyAuditConfig(),
    )


def rebuild_fixtures(repo_root: Path) -> int:
    """Build and write routing validation regression fixtures.

    Reads ``calibration.json`` from the expected directory (if present) and
    uses the pinned amplitude for the ``weak_seasonal_near_threshold`` archetype.

    Args:
        repo_root: Absolute path to the repository root.

    Returns:
        0 on success, non-zero on error.
    """
    expected_dir = repo_root / _EXPECTED_SUBDIR
    expected_dir.mkdir(parents=True, exist_ok=True)

    weak_seasonal_amplitude = load_pinned_weak_seasonal_amplitude(repo_root)
    if weak_seasonal_amplitude is not None:
        _logger.info(
            "Loaded calibrated amplitude from %s: %.4f",
            expected_dir / _CALIBRATION_FILE,
            weak_seasonal_amplitude,
        )
    else:
        _logger.info(
            "No calibration.json found; using default weak_seasonal amplitude (0.18). "
            "Run --calibrate-near-threshold first to pin a calibrated amplitude."
        )

    _logger.info(
        "Building routing validation bundle (n=%d, seed=%d) …",
        _REBUILD_N,
        _REBUILD_SEED,
    )
    bundle = _run_validation_bundle(weak_seasonal_amplitude=weak_seasonal_amplitude)

    _logger.info("Writing %d fixture files …", 3)

    panel_path = expected_dir / _SYNTHETIC_PANEL_FILE
    panel_path.write_text(
        json.dumps(_build_synthetic_panel_payload(bundle), indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    _logger.info("  wrote %s", panel_path)

    audit_path = expected_dir / _AUDIT_SUMMARY_FILE
    audit_path.write_text(
        json.dumps(_build_audit_summary_payload(bundle), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _logger.info("  wrote %s", audit_path)

    labels_path = expected_dir / _CONFIDENCE_LABELS_FILE
    labels_path.write_text(
        json.dumps(_build_confidence_labels_payload(bundle), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _logger.info("  wrote %s", labels_path)

    _logger.info("Rebuild complete.")
    return 0


# ---------------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------------


def _compare_value(
    actual: Any,
    expected: Any,
    *,
    field_path: str,
) -> list[str]:
    """Compare one possibly nested value; return human-readable mismatches."""
    errors: list[str] = []

    if isinstance(expected, dict) and isinstance(actual, dict):
        for key, exp_value in expected.items():
            if key not in actual:
                errors.append(f"{field_path}: missing key '{key}'")
                continue
            errors.extend(_compare_value(actual[key], exp_value, field_path=f"{field_path}/{key}"))
        return errors

    if isinstance(expected, list) and isinstance(actual, list):
        if len(actual) != len(expected):
            errors.append(
                f"{field_path}: length mismatch (actual={len(actual)}, expected={len(expected)})"
            )
            return errors
        for idx, (a_item, e_item) in enumerate(zip(actual, expected, strict=True)):
            errors.extend(_compare_value(a_item, e_item, field_path=f"{field_path}[{idx}]"))
        return errors

    # Float fields: cross-platform tolerance (per repo memory note).
    if isinstance(expected, float) and isinstance(actual, float):
        if not math.isclose(actual, expected, rel_tol=_RTOL, abs_tol=_ATOL):
            errors.append(
                f"{field_path}: float mismatch "
                f"(actual={actual}, expected={expected}, atol={_ATOL}, rtol={_RTOL})"
            )
        return errors

    # Discrete fields: exact comparison.
    if actual != expected:
        errors.append(f"{field_path}: mismatch (actual={actual!r}, expected={expected!r})")
    return errors


def verify_fixtures(repo_root: Path) -> int:
    """Verify that rebuilding the validation fixtures matches the frozen expected files.

    Builds a fresh bundle from scratch (using the calibrated amplitude if
    ``calibration.json`` is present) and compares each fixture file against the
    corresponding frozen expected file.

    Args:
        repo_root: Absolute path to the repository root.

    Returns:
        0 if all fixtures match, 2 on any drift or missing file.
    """
    expected_dir = repo_root / _EXPECTED_SUBDIR

    required_files = [_SYNTHETIC_PANEL_FILE, _AUDIT_SUMMARY_FILE, _CONFIDENCE_LABELS_FILE]
    for fname in required_files:
        if not (expected_dir / fname).exists():
            _logger.error(
                "Expected fixture file missing: %s. Run without --verify to rebuild.",
                expected_dir / fname,
            )
            return 2

    weak_seasonal_amplitude = load_pinned_weak_seasonal_amplitude(repo_root)
    bundle = _run_validation_bundle(weak_seasonal_amplitude=weak_seasonal_amplitude)

    errors: list[str] = []

    # Verify synthetic_panel.json
    expected_panel = json.loads((expected_dir / _SYNTHETIC_PANEL_FILE).read_text(encoding="utf-8"))
    actual_panel = _build_synthetic_panel_payload(bundle)
    errors.extend(_compare_value(actual_panel, expected_panel, field_path=_SYNTHETIC_PANEL_FILE))

    # Verify audit_summary.json
    expected_audit = json.loads((expected_dir / _AUDIT_SUMMARY_FILE).read_text(encoding="utf-8"))
    actual_audit = _build_audit_summary_payload(bundle)
    errors.extend(_compare_value(actual_audit, expected_audit, field_path=_AUDIT_SUMMARY_FILE))

    # Verify confidence_labels.json
    expected_labels = json.loads(
        (expected_dir / _CONFIDENCE_LABELS_FILE).read_text(encoding="utf-8")
    )
    actual_labels = _build_confidence_labels_payload(bundle)
    errors.extend(
        _compare_value(actual_labels, expected_labels, field_path=_CONFIDENCE_LABELS_FILE)
    )

    if errors:
        error_block = "\n".join(f"  - {e}" for e in errors)
        _logger.error("Routing validation fixture verification FAILED:\n%s", error_block)
        return 2

    _logger.info("Routing validation fixture verification passed — all outputs match.")
    return 0


__all__ = [
    "calibrate_near_threshold_amplitude",
    "rebuild_fixtures",
    "verify_fixtures",
]
