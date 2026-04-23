"""Focused tests for routing-validation agent payloads, serializer, and example."""

from __future__ import annotations

import asyncio
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from forecastability.adapters.agents.routing_validation_agent_payload_models import (
    RoutingValidationAgentPayload,
    routing_validation_agent_payload,
)
from forecastability.adapters.agents.routing_validation_summary_serializer import (
    serialise_routing_validation_payload,
    serialise_routing_validation_to_json,
)
from forecastability.adapters.llm import routing_validation_agent as agent_module
from forecastability.adapters.llm.routing_validation_agent import (
    RoutingValidationNarrative,
    run_routing_validation_agent,
)
from forecastability.adapters.settings import InfraSettings
from forecastability.utils.types import (
    RoutingPolicyAudit,
    RoutingPolicyAuditConfig,
    RoutingValidationBundle,
    RoutingValidationCase,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE_PATH = (
    _REPO_ROOT / "examples" / "univariate" / "agents" / "routing_validation_agent_review.py"
)


def _make_bundle() -> RoutingValidationBundle:
    cases = [
        RoutingValidationCase(
            case_name="seasonal_pass_case",
            source_kind="synthetic",
            expected_primary_families=["seasonal_naive"],
            observed_primary_families=["seasonal_naive"],
            outcome="pass",
            confidence_label="high",
            threshold_margin=0.073,
            rule_stability=0.98,
            fingerprint_penalty_count=0,
            notes=["stable seasonal case"],
            metadata={"panel": "synthetic"},
        ),
        RoutingValidationCase(
            case_name="borderline_real_case",
            source_kind="real",
            expected_primary_families=["arima"],
            observed_primary_families=["arima"],
            outcome="downgrade",
            confidence_label="low",
            threshold_margin=0.011,
            rule_stability=0.64,
            fingerprint_penalty_count=2,
            notes=["borderline threshold margin"],
            metadata={"panel": "real"},
        ),
        RoutingValidationCase(
            case_name="mismatch_case",
            source_kind="synthetic",
            expected_primary_families=["tree_on_lags"],
            observed_primary_families=["naive"],
            outcome="fail",
            confidence_label="medium",
            threshold_margin=0.049,
            rule_stability=0.79,
            fingerprint_penalty_count=1,
            notes=["engineered mismatch"],
            metadata={"panel": "synthetic"},
        ),
    ]
    audit = RoutingPolicyAudit(
        total_cases=3,
        passed_cases=1,
        failed_cases=1,
        downgraded_cases=1,
        abstained_cases=0,
    )
    return RoutingValidationBundle(
        cases=cases,
        audit=audit,
        config=RoutingPolicyAuditConfig(),
        metadata={"panel_version": "test"},
    )


def _settings_without_key() -> InfraSettings:
    return InfraSettings.model_construct(openai_api_key=None)


def _openai_settings() -> InfraSettings:
    return InfraSettings.model_construct(openai_api_key="pretend")


def _anthropic_settings() -> InfraSettings:
    return InfraSettings.model_construct(
        openai_api_key=None,
        anthropic_api_key="pretend",
    )


def _load_example_module():
    spec = importlib.util.spec_from_file_location(
        "routing_validation_agent_review_under_test",
        _EXAMPLE_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_routing_validation_agent_payload_preserves_bundle_fields() -> None:
    bundle = _make_bundle()
    payload = routing_validation_agent_payload(bundle)

    assert isinstance(payload, RoutingValidationAgentPayload)
    assert payload.bundle_audit == bundle.audit
    assert payload.case_summaries == bundle.cases
    assert payload.headline_findings
    assert any("Low-confidence" in finding for finding in payload.headline_findings)
    assert any("mismatch_case" in finding for finding in payload.headline_findings)
    assert payload.caveats == [
        "Primary families are family-level guidance, not optimal-model claims.",
        "Abstain means no opinion, not failure.",
        "Downgrade means borderline-confident, not wrong.",
        (
            "threshold_margin and rule_stability are policy fragility signals, "
            "not forecasting-quality signals."
        ),
    ]


def test_routing_validation_summary_serializer_wraps_payload() -> None:
    payload = routing_validation_agent_payload(_make_bundle())
    summary = serialise_routing_validation_payload(payload)
    json_str = serialise_routing_validation_to_json(payload)
    parsed = json.loads(json_str)

    assert summary.payload_type == "RoutingValidationAgentPayload"
    assert parsed["payload"]["bundle_audit"]["total_cases"] == 3
    assert parsed["payload"]["case_summaries"][1]["case_name"] == "borderline_real_case"


def test_run_routing_validation_agent_strict_returns_narrative_none() -> None:
    explanation = asyncio.run(
        run_routing_validation_agent(
            _make_bundle(),
            settings=_settings_without_key(),
            strict=True,
        )
    )

    assert explanation.narrative is None
    assert explanation.bundle_audit.total_cases == 3
    assert explanation.case_summaries[0].case_name == "seasonal_pass_case"


def test_run_routing_validation_agent_appends_missing_caveats(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _make_bundle()
    payload = routing_validation_agent_payload(bundle)

    @dataclass
    class _FakeRunResult:
        output: RoutingValidationNarrative

    class _FakeAgent:
        async def run(self, prompt: str, deps: object) -> _FakeRunResult:
            del prompt, deps
            return _FakeRunResult(
                output=RoutingValidationNarrative(
                    narrative="Release review: one case failed and one real case was downgraded."
                )
            )

    def _fake_create_agent(
        *,
        model: str | None = None,
        settings: InfraSettings | None = None,
    ) -> _FakeAgent:
        del model, settings
        return _FakeAgent()

    monkeypatch.setattr(agent_module, "_PYDANTIC_AI_AVAILABLE", True)
    monkeypatch.setattr(agent_module, "create_routing_validation_agent", _fake_create_agent)

    explanation = asyncio.run(
        run_routing_validation_agent(
            bundle,
            settings=_openai_settings(),
            strict=False,
        )
    )

    assert explanation.narrative is not None
    for caveat in payload.caveats:
        assert caveat in explanation.narrative


def test_run_routing_validation_agent_uses_selected_provider_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @dataclass
    class _FakeRunResult:
        output: RoutingValidationNarrative

    class _FakeAgent:
        async def run(self, prompt: str, deps: object) -> _FakeRunResult:
            del prompt, deps
            return _FakeRunResult(
                output=RoutingValidationNarrative(narrative="Anthropic provider path used.")
            )

    def _fake_create_agent(
        *,
        model: str | None = None,
        settings: InfraSettings | None = None,
    ) -> _FakeAgent:
        del model, settings
        return _FakeAgent()

    monkeypatch.setattr(agent_module, "_PYDANTIC_AI_AVAILABLE", True)
    monkeypatch.setattr(agent_module, "create_routing_validation_agent", _fake_create_agent)

    explanation = asyncio.run(
        run_routing_validation_agent(
            _make_bundle(),
            model="anthropic:claude-sonnet-4-5",
            settings=_anthropic_settings(),
            strict=False,
        )
    )

    assert explanation.narrative is not None
    assert "Anthropic provider path used." in explanation.narrative


def test_routing_validation_agent_review_example_prints_deterministic_payload(
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_example_module()

    exit_code = module.main(["--smoke"])

    assert exit_code == 0
    output = capsys.readouterr().out
    parsed = json.loads(output)
    assert parsed["bundle_audit"]["total_cases"] > 0
    assert parsed["case_summaries"]
    assert parsed["headline_findings"]
    assert parsed["caveats"]
