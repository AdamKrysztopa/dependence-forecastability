"""Tests for RVH-F08 — routing-confidence calibration.

Verifies:
1. The calibration script module is importable and has the expected constants.
2. _generate_series produces valid arrays for every archetype.
3. _extract_confidence_label correctly parses recommendation strings.
4. _compute_precision returns values in [0, 1].
5. RoutingConfidenceCalibrationAudit model validates a plausible audit dict.
6. The "calibrated" word is absent from recommendation_service.py docstrings.
7. The calibration docs file exists.

The full 1000-run suite is NOT executed in CI — it is reserved for the
release-engineering step (scripts/run_routing_confidence_calibration.py).
"""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# 1. Script importability and constants
# ---------------------------------------------------------------------------


class TestScriptStructure:
    """Calibration script must be importable and have correct constants."""

    def test_script_is_importable(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "run_routing_confidence_calibration",
            ROOT / "scripts" / "run_routing_confidence_calibration.py",
        )
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)

    def test_constants_exist(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "run_routing_confidence_calibration",
            ROOT / "scripts" / "run_routing_confidence_calibration.py",
        )
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)

        assert mod.N_REPLICATES >= 100
        assert mod.TARGET_PRECISION_HIGH == pytest.approx(0.90)
        assert mod.TARGET_PRECISION_MEDIUM == pytest.approx(0.75)
        assert mod.SERIES_LENGTH > 0
        assert len(mod.ARCHETYPES) == 10

    def test_archetypes_have_valid_ground_truth(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "run_routing_confidence_calibration",
            ROOT / "scripts" / "run_routing_confidence_calibration.py",
        )
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)

        valid_labels = {"HIGH", "MEDIUM", "LOW"}
        for archetype in mod.ARCHETYPES:
            assert archetype.ground_truth_family in valid_labels, (
                f"Archetype {archetype.name!r} has invalid ground truth "
                f"{archetype.ground_truth_family!r}"
            )


# ---------------------------------------------------------------------------
# 2. Series generation
# ---------------------------------------------------------------------------


class TestSeriesGeneration:
    """_generate_series must produce valid arrays for every archetype."""

    def _load_mod(self) -> object:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "run_routing_confidence_calibration",
            ROOT / "scripts" / "run_routing_confidence_calibration.py",
        )
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    def test_all_archetypes_generate_valid_series(self) -> None:
        mod = self._load_mod()
        rng = np.random.default_rng(0)
        for archetype in mod.ARCHETYPES:  # type: ignore[attr-defined]
            series = mod._generate_series(archetype, rng)  # type: ignore[attr-defined]
            assert isinstance(series, np.ndarray), f"Archetype {archetype.name}: expected ndarray"
            assert series.shape == (mod.SERIES_LENGTH,), (  # type: ignore[attr-defined]
                f"Archetype {archetype.name}: expected shape ({mod.SERIES_LENGTH},), "  # type: ignore[attr-defined]
                f"got {series.shape}"
            )
            assert np.isfinite(series).all(), (
                f"Archetype {archetype.name}: series contains non-finite values"
            )

    def test_replicates_differ(self) -> None:
        """Different rng seeds must produce different series."""
        mod = self._load_mod()
        archetype = mod.ARCHETYPES[2]  # type: ignore[attr-defined]  # ar1_strong
        rng1 = np.random.default_rng(1)
        rng2 = np.random.default_rng(2)
        s1 = mod._generate_series(archetype, rng1)  # type: ignore[attr-defined]
        s2 = mod._generate_series(archetype, rng2)  # type: ignore[attr-defined]
        assert not np.allclose(s1, s2), "Different seeds must produce different series"


# ---------------------------------------------------------------------------
# 3. Label extraction
# ---------------------------------------------------------------------------


class TestLabelExtraction:
    """_extract_confidence_label must correctly parse recommendation strings."""

    def _load_mod(self) -> object:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "run_routing_confidence_calibration",
            ROOT / "scripts" / "run_routing_confidence_calibration.py",
        )
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    @pytest.mark.parametrize(
        "recommendation, expected",
        [
            ("HIGH -> Complex structured models (deep AR, nonlinear, LSTM)", "HIGH"),
            ("MEDIUM -> Seasonal ARIMA / LightGBM", "MEDIUM"),
            ("LOW -> Naive or seasonal naive only", "LOW"),
            ("high -> some text", "HIGH"),
            ("medium -> something", "MEDIUM"),
            ("low -> something", "LOW"),
        ],
    )
    def test_label_extraction(self, recommendation: str, expected: str) -> None:
        mod = self._load_mod()
        result = mod._extract_confidence_label(recommendation)  # type: ignore[attr-defined]
        assert result == expected


# ---------------------------------------------------------------------------
# 4. Precision computation
# ---------------------------------------------------------------------------


class TestPrecisionComputation:
    """_compute_precision must return values in [0, 1]."""

    def _load_mod(self) -> object:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "run_routing_confidence_calibration",
            ROOT / "scripts" / "run_routing_confidence_calibration.py",
        )
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    def test_precision_in_range(self) -> None:
        mod = self._load_mod()
        # Synthetic results: 3 archetypes, 2 reps each
        fake_results = {
            "white_noise": ["LOW", "LOW"],
            "ar1_strong": ["HIGH", "HIGH"],
            "ar1_weak": ["MEDIUM", "HIGH"],
        }
        # Monkeypatch ARCHETYPES
        from types import SimpleNamespace

        original = mod.ARCHETYPES  # type: ignore[attr-defined]
        mod.ARCHETYPES = [  # type: ignore[attr-defined]
            SimpleNamespace(name="white_noise", ground_truth_family="LOW"),
            SimpleNamespace(name="ar1_strong", ground_truth_family="HIGH"),
            SimpleNamespace(name="ar1_weak", ground_truth_family="MEDIUM"),
        ]
        try:
            for label in ("HIGH", "MEDIUM", "LOW"):
                precision = mod._compute_precision(fake_results, label=label)  # type: ignore[attr-defined]
                assert 0.0 <= precision <= 1.0, (
                    f"Precision for {label} must be in [0, 1]; got {precision}"
                )
        finally:
            mod.ARCHETYPES = original  # type: ignore[attr-defined]

    def test_perfect_precision(self) -> None:
        mod = self._load_mod()
        from types import SimpleNamespace

        original = mod.ARCHETYPES  # type: ignore[attr-defined]
        mod.ARCHETYPES = [  # type: ignore[attr-defined]
            SimpleNamespace(name="ar1_strong", ground_truth_family="HIGH"),
        ]
        try:
            fake_results = {"ar1_strong": ["HIGH", "HIGH", "HIGH"]}
            p = mod._compute_precision(fake_results, label="HIGH")  # type: ignore[attr-defined]
            assert p == pytest.approx(1.0)
        finally:
            mod.ARCHETYPES = original  # type: ignore[attr-defined]

    def test_zero_precision_all_wrong(self) -> None:
        mod = self._load_mod()
        from types import SimpleNamespace

        original = mod.ARCHETYPES  # type: ignore[attr-defined]
        mod.ARCHETYPES = [  # type: ignore[attr-defined]
            SimpleNamespace(name="white_noise", ground_truth_family="LOW"),
        ]
        try:
            # All predicted HIGH but ground truth is LOW
            fake_results = {"white_noise": ["HIGH", "HIGH"]}
            p = mod._compute_precision(fake_results, label="HIGH")  # type: ignore[attr-defined]
            assert p == pytest.approx(0.0)
        finally:
            mod.ARCHETYPES = original  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# 5. RoutingConfidenceCalibrationAudit model
# ---------------------------------------------------------------------------


class TestCalibrationAuditModel:
    """RoutingConfidenceCalibrationAudit must validate a plausible audit dict."""

    def test_valid_audit_validates(self) -> None:
        from forecastability.domain.results.calibration_audit import (
            RoutingConfidenceCalibrationAudit,
            ThresholdEntry,
        )

        audit = RoutingConfidenceCalibrationAudit(
            version="0.5.0",
            n_archetypes=10,
            n_noise_replicates=100,
            thresholds=[
                ThresholdEntry(
                    label="high",
                    threshold=0.15,
                    achieved_precision=0.88,
                    target_precision=0.90,
                    n_samples=500,
                ),
                ThresholdEntry(
                    label="medium",
                    threshold=0.05,
                    achieved_precision=0.72,
                    target_precision=0.75,
                    n_samples=200,
                ),
                ThresholdEntry(
                    label="low",
                    threshold=0.05,
                    achieved_precision=0.95,
                    target_precision=0.0,
                    n_samples=300,
                ),
            ],
            audit_timestamp="2026-05-24T18:00:00+00:00",
            notes="Test audit",
        )
        assert audit.version == "0.5.0"
        assert audit.n_archetypes == 10
        assert len(audit.thresholds) == 3

    def test_model_is_frozen(self) -> None:
        from forecastability.domain.results.calibration_audit import (
            RoutingConfidenceCalibrationAudit,
        )

        audit = RoutingConfidenceCalibrationAudit(
            version="0.5.0",
            n_archetypes=10,
            n_noise_replicates=100,
            thresholds=[],
            audit_timestamp="2026-05-24T18:00:00+00:00",
        )
        # frozen Pydantic raises ValidationError (a ValueError subclass) or AttributeError
        with pytest.raises((ValueError, AttributeError)):
            audit.version = "0.6.0"


# ---------------------------------------------------------------------------
# 6. "calibrated" word removed from docstrings where not warranted
# ---------------------------------------------------------------------------


class TestCalibratedWordRemoved:
    """The word 'calibrated' must not appear in recommendation_service.py docstrings."""

    def test_calibrated_absent_from_recommendation_service_docstrings(self) -> None:
        path = ROOT / "src/forecastability/services/recommendation_service.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))

        violations: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
                docstring = ast.get_docstring(node)
                if docstring and "calibrated" in docstring.lower():
                    name = getattr(node, "name", "<module>")
                    violations.append(f"  '{name}' docstring contains 'calibrated'")

        assert not violations, (
            "recommendation_service.py docstrings must not use 'calibrated' for "
            "hand-picked thresholds:\n" + "\n".join(violations)
        )


# ---------------------------------------------------------------------------
# 7. Calibration docs file exists
# ---------------------------------------------------------------------------


class TestCalibrationDocsExist:
    """Calibration documentation files must exist."""

    def test_methodology_doc_exists(self) -> None:
        path = ROOT / "docs" / "calibration" / "v0_5_0_routing_confidence.md"
        assert path.exists(), f"Missing calibration doc: {path}"
        content = path.read_text(encoding="utf-8")
        assert "calibrated" in content.lower(), (
            "Calibration doc should explain what 'calibrated' means in this context"
        )
        assert "precision" in content.lower(), "Calibration doc should explain the precision target"
