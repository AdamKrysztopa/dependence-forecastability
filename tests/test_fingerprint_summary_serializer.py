"""Unit tests for the fingerprint summary serialiser (V3_1-F05.1 — A2 layer)."""

from __future__ import annotations

import json

from forecastability.adapters.agents.fingerprint_agent_payload_models import (
    FingerprintAgentPayload,
    fingerprint_agent_payload,
)
from forecastability.adapters.agents.fingerprint_summary_serializer import (
    SerialisedFingerprintSummary,
    serialise_fingerprint_payload,
    serialise_fingerprint_to_json,
)
from forecastability.utils.types import (
    AmiGeometryCurvePoint,
    AmiInformationGeometry,
    FingerprintBundle,
    ForecastabilityFingerprint,
    RoutingRecommendation,
)


def _make_payload(
    *,
    structure: str = "monotonic",
    mass: float = 0.12,
    horizon: int = 8,
    nonlinear_share: float = 0.05,
    signal_to_noise: float = 0.33,
    primary_families: list[str] | None = None,
    confidence_label: str = "high",
    narrative: str | None = None,
) -> FingerprintAgentPayload:
    """Build a minimal :class:`FingerprintAgentPayload` for testing."""
    geometry = AmiInformationGeometry(
        signal_to_noise=signal_to_noise,
        information_horizon=horizon,
        information_structure=structure,  # type: ignore[arg-type]
        informative_horizons=[1, 2, 3, horizon],
        curve=[
            AmiGeometryCurvePoint(
                horizon=item,
                ami_raw=0.18,
                ami_bias=0.04,
                ami_corrected=0.14,
                tau=0.03,
                accepted=True,
                valid=True,
            )
            for item in range(1, horizon + 1)
        ],
    )
    fp = ForecastabilityFingerprint(
        information_mass=mass,
        information_horizon=horizon,
        information_structure=structure,  # type: ignore[arg-type]
        nonlinear_share=nonlinear_share,
        signal_to_noise=signal_to_noise,
        directness_ratio=0.72,
        informative_horizons=[1, 2, 3, horizon],
    )
    rec = RoutingRecommendation(
        primary_families=primary_families or ["arima"],  # type: ignore[list-item]
        secondary_families=["ets"],
        confidence_label=confidence_label,  # type: ignore[arg-type]
        rationale=["monotonic decay with high directness"],
    )
    bundle = FingerprintBundle(
        target_name="serialiser_test",
        geometry=geometry,
        fingerprint=fp,
        recommendation=rec,
        profile_summary={"n_sig_lags": 3},
    )
    return fingerprint_agent_payload(bundle, narrative=narrative)


class TestSerialisedFingerprintSummaryEnvelope:
    """Test versioned envelope structure."""

    def test_envelope_has_schema_version(self) -> None:
        payload = _make_payload()
        summary = serialise_fingerprint_payload(payload)

        assert summary.schema_version == "1"

    def test_envelope_has_payload_type(self) -> None:
        payload = _make_payload()
        summary = serialise_fingerprint_payload(payload)

        assert summary.payload_type == "FingerprintAgentPayload"

    def test_envelope_has_serialised_at(self) -> None:
        payload = _make_payload()
        summary = serialise_fingerprint_payload(payload)

        assert summary.serialised_at is not None
        assert "T" in summary.serialised_at  # ISO-8601 format

    def test_envelope_payload_contains_fingerprint_fields(self) -> None:
        payload = _make_payload(mass=0.20, horizon=5, structure="periodic")
        summary = serialise_fingerprint_payload(payload)

        inner = summary.payload
        assert inner["information_mass"] == 0.20
        assert inner["information_horizon"] == 5
        assert inner["information_structure"] == "periodic"

    def test_envelope_payload_contains_geometry_fields(self) -> None:
        payload = _make_payload(signal_to_noise=0.44)
        summary = serialise_fingerprint_payload(payload)

        inner = summary.payload
        assert inner["geometry_method"] == "ksg2_shuffle_surrogate"
        assert inner["signal_to_noise"] == 0.44
        assert inner["geometry_information_horizon"] == 8

    def test_envelope_payload_contains_routing_fields(self) -> None:
        payload = _make_payload(primary_families=["tbats"], confidence_label="medium")
        summary = serialise_fingerprint_payload(payload)

        inner = summary.payload
        assert inner["primary_families"] == ["tbats"]
        assert inner["confidence_label"] == "medium"


class TestSerialisedFingerprintSummaryJson:
    """Test JSON serialisation output."""

    def test_json_output_is_valid(self) -> None:
        payload = _make_payload()
        json_str = serialise_fingerprint_to_json(payload)

        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_json_contains_payload_type(self) -> None:
        payload = _make_payload()
        json_str = serialise_fingerprint_to_json(payload)

        parsed = json.loads(json_str)
        assert parsed["payload_type"] == "FingerprintAgentPayload"

    def test_json_contains_four_fingerprint_fields(self) -> None:
        payload = _make_payload(mass=0.15, horizon=10, structure="mixed")
        json_str = serialise_fingerprint_to_json(payload)

        parsed = json.loads(json_str)
        inner = parsed["payload"]
        assert "information_mass" in inner
        assert "information_horizon" in inner
        assert "information_structure" in inner
        assert "nonlinear_share" in inner

    def test_json_narrative_none_serialised(self) -> None:
        payload = _make_payload(narrative=None)
        json_str = serialise_fingerprint_to_json(payload)

        parsed = json.loads(json_str)
        assert parsed["payload"]["narrative"] is None

    def test_json_roundtrip_summary(self) -> None:
        payload = _make_payload(narrative="test narrative")
        summary = serialise_fingerprint_payload(payload)

        json_str = json.dumps(summary.model_dump())
        reconstructed = SerialisedFingerprintSummary.model_validate(json.loads(json_str))

        assert reconstructed.schema_version == summary.schema_version
        assert reconstructed.payload_type == summary.payload_type
        assert reconstructed.payload["information_mass"] == summary.payload["information_mass"]

    def test_json_is_pretty_printed(self) -> None:
        payload = _make_payload()
        json_str = serialise_fingerprint_to_json(payload)

        # Pretty-printed JSON has newlines.
        assert "\n" in json_str
