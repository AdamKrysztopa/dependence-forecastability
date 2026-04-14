from __future__ import annotations

import json
from pathlib import Path

from forecastability.utils.io_models import CanonicalPayload, CanonicalSummaryBundle, ExogCaseRecord
from forecastability.utils.types import CanonicalSummary, Diagnostics, InterpretationResult


def test_canonical_payload_from_summary_interpretation_excludes_narrative_when_disabled() -> None:
    summary = CanonicalSummary(
        series_name="sine_wave",
        n_sig_ami=6,
        n_sig_pami=4,
        peak_lag_ami=1,
        peak_lag_pami=1,
        peak_ami=0.45,
        peak_pami=0.21,
        auc_ami=2.8,
        auc_pami=1.4,
        directness_ratio=0.5,
        pami_to_ami_sig_ratio=0.66,
        first_sig_ami=1,
        first_sig_pami=1,
        last_sig_ami=8,
        last_sig_pami=6,
    )
    interpretation = InterpretationResult(
        forecastability_class="high",
        directness_class="medium",
        primary_lags=[1, 2, 3],
        modeling_regime="seasonal_linear",
        narrative="Narrative text.",
        diagnostics=Diagnostics(
            peak_ami_first_5=0.2,
            directness_ratio=0.5,
            n_sig_ami=6,
            n_sig_pami=4,
            exploitability_mismatch=0,
            best_smape=0.1,
        ),
    )

    payload = CanonicalPayload.from_summary_and_interpretation(
        series_name="sine_wave",
        summary=summary,
        interpretation=interpretation,
        include_narrative=False,
    )

    dumped = payload.model_dump(exclude_none=True)
    assert dumped["series_name"] == "sine_wave"
    assert dumped["summary"]["n_sig_ami"] == 6
    assert "narrative" not in dumped["interpretation"]


def test_canonical_payload_from_json_file_allows_extra_keys(tmp_path: Path) -> None:
    payload = {
        "series_name": "sine_wave",
        "summary": {
            "n_sig_ami": 5,
            "n_sig_pami": 3,
            "directness_ratio": 0.6,
            "auc_ami": 2.1,
            "auc_pami": 1.3,
            "peak_lag_ami": 1,
            "peak_lag_pami": 1,
            "extra_metric": 123,
        },
        "interpretation": {
            "forecastability_class": "high",
            "directness_class": "medium",
            "modeling_regime": "seasonal_linear",
            "primary_lags": [1, 2],
            "narrative": "ok",
            "diagnostics": {"unused": True},
        },
        "analysis_agent_answers": {"ignored": True},
    }
    path = tmp_path / "sine_wave.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    model = CanonicalPayload.from_json_file(path)
    assert model.series_name == "sine_wave"
    assert model.interpretation.primary_lags == [1, 2]


def test_summary_bundle_and_exog_record_roundtrip(tmp_path: Path) -> None:
    bundle = CanonicalSummaryBundle(
        examples=[
            CanonicalPayload.model_validate(
                {
                    "series_name": "series_a",
                    "summary": {
                        "n_sig_ami": 1,
                        "n_sig_pami": 1,
                        "directness_ratio": 0.9,
                        "auc_ami": 0.2,
                        "auc_pami": 0.18,
                        "peak_lag_ami": 1,
                        "peak_lag_pami": 1,
                    },
                    "interpretation": {
                        "forecastability_class": "low",
                        "directness_class": "low",
                        "modeling_regime": "baseline",
                        "primary_lags": [1],
                    },
                }
            )
        ]
    )
    bundle_path = tmp_path / "bundle.json"
    bundle.to_json_file(bundle_path, exclude_none=True)
    loaded_bundle = CanonicalSummaryBundle.from_json_file(bundle_path)
    assert loaded_bundle.examples[0].series_name == "series_a"

    exog = ExogCaseRecord.from_fields(
        case_name="btc_noise",
        description="desc",
        method="mi",
        max_lag=40,
        recommendation="DROP",
        n_sig_raw_lags=0,
        n_sig_partial_lags=0,
        sig_raw_lags=[],
        sig_partial_lags=[],
        mean_raw_20=0.0,
        mode="cross",
        target_name="btc",
        exog_name="noise",
        n_target=10,
        n_exog=10,
        raw_curve=[0.0, 0.1],
        partial_curve=[0.0, 0.0],
        auc_raw=0.1,
        auc_partial=0.0,
        peak_raw_lag=2,
        peak_raw_value=0.1,
        peak_partial_lag=1,
        peak_partial_value=0.0,
        mean_partial_20=0.0,
        directness_ratio=0.0,
        recommended_lags=[1],
        compute_surrogates=False,
    )
    exog_path = tmp_path / "exog.json"
    exog.to_json_file(exog_path)
    loaded_exog = ExogCaseRecord.from_json_file(exog_path)
    assert loaded_exog.case_name == "btc_noise"
