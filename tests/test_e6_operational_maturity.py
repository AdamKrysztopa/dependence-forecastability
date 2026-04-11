"""Tests for E6 — Operational Maturity (AGT-012, AGT-013, AGT-014)."""

from __future__ import annotations

import tempfile
from datetime import UTC
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from forecastability.triage.models import TriageRequest
from forecastability.triage.run_triage import run_triage

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _small_ar1(n: int = 150, phi: float = 0.85, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    ts = np.zeros(n)
    ts[0] = rng.standard_normal()
    for i in range(1, n):
        ts[i] = phi * ts[i - 1] + rng.standard_normal()
    return ts


def _make_request(n: int = 150) -> TriageRequest:
    return TriageRequest(series=_small_ar1(n=n), max_lag=20, random_state=42)


# ---------------------------------------------------------------------------
# AGT-012: Event model unit tests
# ---------------------------------------------------------------------------


class TestTriageEvents:
    def test_stage_started_has_utc_timestamp(self) -> None:

        from forecastability.triage.events import TriageStageStarted

        ev = TriageStageStarted(stage="readiness")
        assert ev.timestamp.tzinfo is not None
        assert ev.timestamp.tzinfo == UTC

    def test_stage_completed_fields(self) -> None:
        from forecastability.triage.events import TriageStageCompleted

        ev = TriageStageCompleted(stage="compute", duration_ms=120.5, result_summary="ok")
        assert ev.stage == "compute"
        assert ev.duration_ms == pytest.approx(120.5)
        assert ev.result_summary == "ok"

    def test_triage_error_fields(self) -> None:
        from forecastability.triage.events import TriageError

        ev = TriageError(stage="routing", error="oops")
        assert ev.stage == "routing"
        assert ev.error == "oops"

    def test_events_are_frozen(self) -> None:
        from forecastability.triage.events import TriageStageStarted

        ev = TriageStageStarted(stage="x")
        with pytest.raises(ValidationError):
            ev.stage = "y"  # type: ignore[misc]

    def test_events_are_pydantic_serialisable(self) -> None:
        from forecastability.triage.events import TriageStageCompleted

        ev = TriageStageCompleted(stage="s", duration_ms=1.0, result_summary="ok")
        data = ev.model_dump()
        assert data["stage"] == "s"
        assert data["duration_ms"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# AGT-012: EventEmitterPort adapters
# ---------------------------------------------------------------------------


class TestEventEmitters:
    def test_noop_emitter_does_not_raise(self) -> None:
        from forecastability.adapters.event_emitter import NoopEventEmitter
        from forecastability.triage.events import TriageStageStarted

        emitter = NoopEventEmitter()
        emitter.emit(TriageStageStarted(stage="test"))  # must not raise

    def test_collecting_emitter_accumulates_events(self) -> None:
        from forecastability.adapters.event_emitter import CollectingEventEmitter
        from forecastability.triage.events import (
            TriageStageCompleted,
            TriageStageStarted,
        )

        emitter = CollectingEventEmitter()
        emitter.emit(TriageStageStarted(stage="a"))
        emitter.emit(TriageStageCompleted(stage="a", duration_ms=5.0, result_summary="ok"))
        assert len(emitter.events) == 2

    def test_logging_emitter_does_not_raise(self) -> None:
        from forecastability.adapters.event_emitter import LoggingEventEmitter
        from forecastability.triage.events import (
            TriageError,
            TriageStageCompleted,
            TriageStageStarted,
        )

        emitter = LoggingEventEmitter()
        emitter.emit(TriageStageStarted(stage="s"))
        emitter.emit(TriageStageCompleted(stage="s", duration_ms=1.0, result_summary="ok"))
        emitter.emit(TriageError(stage="s", error="kaboom"))

    def test_collecting_emitter_protocol_compliance(self) -> None:
        from forecastability.adapters.event_emitter import CollectingEventEmitter
        from forecastability.ports import EventEmitterPort

        emitter = CollectingEventEmitter()
        assert isinstance(emitter, EventEmitterPort)

    def test_logging_emitter_protocol_compliance(self) -> None:
        from forecastability.adapters.event_emitter import LoggingEventEmitter
        from forecastability.ports import EventEmitterPort

        emitter = LoggingEventEmitter()
        assert isinstance(emitter, EventEmitterPort)

    def test_noop_emitter_protocol_compliance(self) -> None:
        from forecastability.adapters.event_emitter import NoopEventEmitter
        from forecastability.ports import EventEmitterPort

        emitter = NoopEventEmitter()
        assert isinstance(emitter, EventEmitterPort)


# ---------------------------------------------------------------------------
# AGT-013: Timing instrumentation in run_triage
# ---------------------------------------------------------------------------


class TestTimingInstrumentation:
    def test_timing_dict_populated_when_emitter_provided(self) -> None:
        from forecastability.adapters.event_emitter import CollectingEventEmitter

        emitter = CollectingEventEmitter()
        req = _make_request()
        result = run_triage(req, event_emitter=emitter)

        assert result.timing is not None
        assert "readiness" in result.timing
        assert "routing" in result.timing
        assert "compute" in result.timing
        assert "interpretation" in result.timing

    def test_all_stage_durations_are_positive(self) -> None:
        from forecastability.adapters.event_emitter import CollectingEventEmitter

        emitter = CollectingEventEmitter()
        req = _make_request()
        result = run_triage(req, event_emitter=emitter)

        assert result.timing is not None
        for stage, ms in result.timing.items():
            assert ms >= 0, f"Stage {stage!r} has non-positive duration {ms}"

    def test_events_fired_in_pipeline_order(self) -> None:
        from forecastability.adapters.event_emitter import CollectingEventEmitter
        from forecastability.triage.events import TriageStageStarted

        emitter = CollectingEventEmitter()
        req = _make_request()
        run_triage(req, event_emitter=emitter)

        started = [e for e in emitter.events if isinstance(e, TriageStageStarted)]
        stages = [e.stage for e in started]
        assert stages == ["readiness", "routing", "compute", "interpretation"]

    def test_completed_events_pair_with_started(self) -> None:
        from forecastability.adapters.event_emitter import CollectingEventEmitter
        from forecastability.triage.events import TriageStageCompleted, TriageStageStarted

        emitter = CollectingEventEmitter()
        req = _make_request()
        run_triage(req, event_emitter=emitter)

        started_stages = {e.stage for e in emitter.events if isinstance(e, TriageStageStarted)}
        completed_stages = {e.stage for e in emitter.events if isinstance(e, TriageStageCompleted)}
        assert started_stages == completed_stages

    def test_timing_is_none_without_emitter(self) -> None:
        req = _make_request()
        result = run_triage(req)
        assert result.timing is None

    def test_blocked_result_has_timing_when_emitter_provided(self) -> None:
        from forecastability.adapters.event_emitter import CollectingEventEmitter

        emitter = CollectingEventEmitter()
        rng = np.random.default_rng(0)
        req = TriageRequest(series=rng.standard_normal(30), max_lag=40)
        result = run_triage(req, event_emitter=emitter)

        assert result.blocked is True
        assert result.timing is not None
        assert "readiness" in result.timing


# ---------------------------------------------------------------------------
# AGT-014: Checkpoint adapters unit tests
# ---------------------------------------------------------------------------


class TestCheckpointAdapters:
    def test_noop_load_returns_none(self) -> None:
        from forecastability.adapters.checkpoint import NoopCheckpointAdapter

        adapter = NoopCheckpointAdapter()
        assert adapter.load_checkpoint("any-key") is None

    def test_noop_save_does_not_raise(self) -> None:
        from forecastability.adapters.checkpoint import NoopCheckpointAdapter

        adapter = NoopCheckpointAdapter()
        adapter.save_checkpoint("k", "readiness", {"x": 1})

    def test_filesystem_roundtrip(self) -> None:
        from forecastability.adapters.checkpoint import FilesystemCheckpointAdapter

        with tempfile.TemporaryDirectory() as tmp:
            adapter = FilesystemCheckpointAdapter(Path(tmp))
            adapter.save_checkpoint("run1", "readiness", {"status": "clear", "warnings": []})
            ckpt = adapter.load_checkpoint("run1")
            assert ckpt is not None
            assert ckpt["stage"] == "readiness"
            assert ckpt["data"]["status"] == "clear"

    def test_filesystem_missing_key_returns_none(self) -> None:
        from forecastability.adapters.checkpoint import FilesystemCheckpointAdapter

        with tempfile.TemporaryDirectory() as tmp:
            adapter = FilesystemCheckpointAdapter(Path(tmp))
            assert adapter.load_checkpoint("nonexistent") is None

    def test_filesystem_overwrites_previous_checkpoint(self) -> None:
        from forecastability.adapters.checkpoint import FilesystemCheckpointAdapter

        with tempfile.TemporaryDirectory() as tmp:
            adapter = FilesystemCheckpointAdapter(Path(tmp))
            adapter.save_checkpoint("r", "readiness", {"x": 1})
            adapter.save_checkpoint("r", "routing", {"x": 2})
            ckpt = adapter.load_checkpoint("r")
            assert ckpt is not None
            assert ckpt["stage"] == "routing"

    def test_filesystem_creates_directory_on_first_save(self) -> None:
        from forecastability.adapters.checkpoint import FilesystemCheckpointAdapter

        with tempfile.TemporaryDirectory() as tmp:
            nested = Path(tmp) / "deep" / "nested"
            adapter = FilesystemCheckpointAdapter(nested)
            adapter.save_checkpoint("r", "readiness", {"status": "clear", "warnings": []})
            assert nested.exists()

    def test_filesystem_protocol_compliance(self) -> None:
        from forecastability.adapters.checkpoint import FilesystemCheckpointAdapter
        from forecastability.ports import CheckpointPort

        with tempfile.TemporaryDirectory() as tmp:
            adapter = FilesystemCheckpointAdapter(Path(tmp))
            assert isinstance(adapter, CheckpointPort)

    def test_noop_protocol_compliance(self) -> None:
        from forecastability.adapters.checkpoint import NoopCheckpointAdapter
        from forecastability.ports import CheckpointPort

        adapter = NoopCheckpointAdapter()
        assert isinstance(adapter, CheckpointPort)


# ---------------------------------------------------------------------------
# AGT-014: Durable execution — checkpoint save/resume in run_triage
# ---------------------------------------------------------------------------


class TestDurableExecution:
    def test_checkpoint_saves_after_readiness(self) -> None:
        from forecastability.adapters.checkpoint import FilesystemCheckpointAdapter

        with tempfile.TemporaryDirectory() as tmp:
            adapter = FilesystemCheckpointAdapter(Path(tmp))
            req = _make_request()
            run_triage(req, checkpoint=adapter, checkpoint_key="ckpt-test")

            ckpt = adapter.load_checkpoint("ckpt-test")
            assert ckpt is not None
            # Final stage saved is "interpretation"
            assert ckpt["stage"] == "interpretation"

    def test_checkpoint_resume_skips_completed_stages(self) -> None:
        """Manually inject a checkpoint at 'routing' so readiness is skipped."""
        from forecastability.adapters.checkpoint import FilesystemCheckpointAdapter

        with tempfile.TemporaryDirectory() as tmp:
            adapter = FilesystemCheckpointAdapter(Path(tmp))
            # Pre-seed a routing checkpoint
            adapter.save_checkpoint(
                "resume-test",
                "routing",
                {
                    "readiness": {"status": "clear", "warnings": []},
                    "method_plan": {
                        "route": "univariate_no_significance",
                        "compute_surrogates": False,
                        "assumptions": ["resumed"],
                        "rationale": "test resume",
                    },
                },
            )

            readiness_call_count = 0

            def counting_gate(r: TriageRequest):  # type: ignore[return]
                nonlocal readiness_call_count
                readiness_call_count += 1
                from forecastability.triage.models import ReadinessReport, ReadinessStatus

                return ReadinessReport(status=ReadinessStatus.clear, warnings=[])

            req = _make_request()
            result = run_triage(
                req,
                readiness_gate=counting_gate,
                checkpoint=adapter,
                checkpoint_key="resume-test",
            )
            # readiness_gate should NOT have been called because checkpoint had "routing"
            assert readiness_call_count == 0
            assert result.blocked is False

    def test_run_with_noop_checkpoint_produces_correct_result(self) -> None:
        from forecastability.adapters.checkpoint import NoopCheckpointAdapter

        adapter = NoopCheckpointAdapter()
        req = _make_request()
        result = run_triage(req, checkpoint=adapter, checkpoint_key="k")

        assert result.blocked is False
        assert result.interpretation is not None

    def test_collect_events_and_checkpoint_together(self) -> None:
        from forecastability.adapters.checkpoint import FilesystemCheckpointAdapter
        from forecastability.adapters.event_emitter import CollectingEventEmitter
        from forecastability.triage.events import TriageStageCompleted

        with tempfile.TemporaryDirectory() as tmp:
            emitter = CollectingEventEmitter()
            adapter = FilesystemCheckpointAdapter(Path(tmp))

            req = _make_request()
            result = run_triage(
                req,
                event_emitter=emitter,
                checkpoint=adapter,
                checkpoint_key="combo",
            )

            assert result.timing is not None
            completed = [e for e in emitter.events if isinstance(e, TriageStageCompleted)]
            assert len(completed) == 4
            final_ckpt = adapter.load_checkpoint("combo")
            assert final_ckpt is not None
            assert final_ckpt["stage"] == "interpretation"
