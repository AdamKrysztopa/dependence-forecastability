"""Tests for persisted triage result bundles and provenance hashing."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from forecastability.triage.models import TriageRequest
from forecastability.triage.result_bundle import (
    TriageResultBundle,
    build_triage_result_bundle,
    load_result_bundle,
    save_result_bundle,
)
from forecastability.triage.run_triage import run_triage


def _make_result_bundle() -> tuple[np.ndarray, TriageResultBundle]:
    rng = np.random.default_rng(17)
    series = rng.standard_normal(180)
    request = TriageRequest(series=series, max_lag=20, random_state=17)
    result = run_triage(request)
    bundle = build_triage_result_bundle(
        result,
        run_id="run-017",
        series_name="synthetic_gaussian",
        metadata={"source": "unit-test", "backlog_item": 17},
    )
    return series, bundle


def test_result_bundle_roundtrip_save_load(tmp_path: Path) -> None:
    _, bundle = _make_result_bundle()
    output_path = tmp_path / "triage_result_bundle.json"

    save_result_bundle(bundle, path=output_path)
    loaded_bundle = load_result_bundle(output_path)

    assert loaded_bundle == bundle
    assert loaded_bundle.input_metadata.series_name == "synthetic_gaussian"
    assert loaded_bundle.verify_content_hash()


def test_result_bundle_content_hash_is_stable_and_detects_mutation() -> None:
    series, bundle = _make_result_bundle()

    expected_hash = bundle.compute_content_hash()
    assert bundle.provenance.content_sha256 == expected_hash
    assert bundle.verify_content_hash()

    rebuilt_bundle = bundle.with_content_hash()
    assert rebuilt_bundle.provenance.content_sha256 == expected_hash

    tampered_bundle = bundle.model_copy(update={"recommendation": "tampered"})
    assert not tampered_bundle.verify_content_hash()

    assert bundle.provenance.input_series_sha256 != ""
    assert series.size == bundle.input_metadata.series_length
