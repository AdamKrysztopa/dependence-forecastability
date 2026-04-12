"""Interface-level contract tests for adapter behavior (backlog item #11)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from forecastability.adapters.checkpoint import (
    FilesystemCheckpointAdapter,
    NoopCheckpointAdapter,
)
from forecastability.adapters.event_emitter import (
    CollectingEventEmitter,
    StreamingEventEmitter,
)
from forecastability.adapters.settings import InfraSettings
from forecastability.ports import CheckpointPort, EventEmitterPort, SettingsPort
from forecastability.triage.events import TriageStageCompleted, TriageStageStarted
from forecastability.triage.models import TriageRequest
from forecastability.triage.run_triage import run_triage


def _event_signature(emitter: CollectingEventEmitter) -> list[tuple[str, str]]:
    signature: list[tuple[str, str]] = []
    for event in emitter.events:
        if isinstance(event, TriageStageStarted):
            signature.append(("start", event.stage))
        if isinstance(event, TriageStageCompleted):
            signature.append(("complete", event.stage))
    return signature


def test_settings_adapter_honors_settings_port_contract() -> None:
    settings = InfraSettings(openai_model="gpt-4o-mini", mcp_port=9100)
    assert isinstance(settings, SettingsPort)
    assert settings.get_openai_model() == "gpt-4o-mini"
    assert settings.get_mcp_port() == 9100


def test_noop_checkpoint_adapter_honors_checkpoint_port_contract() -> None:
    adapter = NoopCheckpointAdapter()
    assert isinstance(adapter, CheckpointPort)
    adapter.save_checkpoint("run-1", "readiness", {"status": "clear"})
    assert adapter.load_checkpoint("run-1") is None


def test_filesystem_checkpoint_adapter_honors_checkpoint_port_contract() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        adapter = FilesystemCheckpointAdapter(Path(tmp_dir))
        assert isinstance(adapter, CheckpointPort)

        adapter.save_checkpoint(
            "run-1",
            "routing",
            {
                "readiness": {
                    "status": "warning",
                    "warnings": [],
                }
            },
        )

        checkpoint = adapter.load_checkpoint("run-1")
        assert checkpoint is not None
        assert checkpoint["stage"] == "routing"
        assert checkpoint["data"]["readiness"]["status"] == "warning"


def test_event_emitter_honors_port_and_full_pipeline_ordering(
    deterministic_triage_request: TriageRequest,
) -> None:
    emitter = CollectingEventEmitter()
    assert isinstance(emitter, EventEmitterPort)

    result = run_triage(deterministic_triage_request, event_emitter=emitter)
    assert result.blocked is False

    assert _event_signature(emitter) == [
        ("start", "readiness"),
        ("complete", "readiness"),
        ("start", "routing"),
        ("complete", "routing"),
        ("start", "compute"),
        ("complete", "compute"),
        ("start", "interpretation"),
        ("complete", "interpretation"),
    ]


def test_event_ordering_for_blocked_request_is_short_circuited(
    deterministic_blocked_request: TriageRequest,
) -> None:
    emitter = CollectingEventEmitter()
    assert isinstance(emitter, EventEmitterPort)

    result = run_triage(deterministic_blocked_request, event_emitter=emitter)
    assert result.blocked is True

    assert _event_signature(emitter) == [
        ("start", "readiness"),
        ("complete", "readiness"),
    ]


def test_streaming_event_emitter_honors_sse_contract() -> None:
    emitter = StreamingEventEmitter()
    assert isinstance(emitter, EventEmitterPort)

    emitter.emit(TriageStageStarted(stage="readiness"))
    emitter.emit(
        TriageStageCompleted(
            stage="readiness",
            duration_ms=1.5,
            result_summary="status=warning",
        )
    )
    emitter.close()

    chunks = list(emitter.sse_stream(timeout=0.1))
    payloads = [json.loads(chunk[len("data: ") :].strip()) for chunk in chunks]

    assert [payload["event_type"] for payload in payloads] == [
        "stage_started",
        "stage_completed",
        "done",
    ]
    assert payloads[0]["stage"] == "readiness"
    assert payloads[1]["stage"] == "readiness"
