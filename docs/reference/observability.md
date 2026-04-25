<!-- type: reference -->
# Observability and Auditability Guide

Operational reference for stage-level events, checkpoint replay boundaries,
and minimum audit evidence for deterministic triage runs.

> [!IMPORTANT]
> Deterministic triage outputs are the source of truth. Observability layers
> (SSE events, logs, checkpoints, narrative adapters) must describe execution,
> not change numeric outcomes.

## Source of truth

- Runtime event models: [src/forecastability/triage/events.py](../src/forecastability/triage/events.py)
- Event adapter encoders: [src/forecastability/adapters/event_emitter.py](../src/forecastability/adapters/event_emitter.py)
- Orchestration and checkpoint behavior: [src/forecastability/triage/run_triage.py](../src/forecastability/triage/run_triage.py)
- Checkpoint adapter persistence: [src/forecastability/adapters/checkpoint.py](../src/forecastability/adapters/checkpoint.py)
- HTTP + SSE transport contract: [api_contract.md](api_contract.md)
- Architecture semantics (AGT-023, AGT-024): [architecture.md](architecture.md)

## Standard event payload fields

### Stream envelope

SSE events are emitted as `data: {...}\n\n` and terminated by the sentinel:

```json
{"event_type": "done"}
```

Every payload must include `event_type`.

### Event contract by type

| `event_type` | Required fields | Field semantics |
|---|---|---|
| `stage_started` | `stage`, `timestamp` | Stage entry marker with UTC wall-clock timestamp (`ISO 8601`). |
| `stage_completed` | `stage`, `duration_ms`, `result_summary` | Successful stage exit marker with elapsed wall-clock duration and compact outcome summary. |
| `stage_error` | `stage`, `error` | Stage failure marker. `error` is a string representation of the raised exception. |
| `done` | none | Terminal sentinel emitted after stream close (including error paths). |

### Stage naming convention

Current deterministic stage names are:

- `readiness`
- `routing`
- `compute`
- `interpretation`

These names should be treated as compatibility-sensitive by clients that
aggregate stage-level metrics.

## Checkpoint semantics and resumability boundaries

Checkpoints implement orchestration-state replay, not full-artifact resume.

### Persisted state model

- Keyed by `checkpoint_key`.
- Saved as one JSON file per key for `FilesystemCheckpointAdapter`.
- Overwritten after each completed stage.
- Envelope shape: `{ "stage": "<last_completed_stage>", "data": {...} }`.

### What is persisted vs not persisted

| Persisted | Not persisted |
|---|---|
| Readiness report (`status`, warning codes/messages) | Full `AnalyzeResult` arrays (`raw`, `partial`, significance arrays) |
| Method plan (`route`, `compute_surrogates`, assumptions, rationale) | Full `InterpretationResult` object |
| Compute summary metadata (`method`, recommendation, lag count) | In-memory emitter queues and open stream state |
| Interpretation summary metadata (`forecastability_class`, `directness_class`) | Any exactly-once delivery guarantee |

### Resume boundary rules

| Last checkpoint stage | Stages skipped on resume | Stages re-executed |
|---|---|---|
| `readiness` | none | `routing`, `compute`, `interpretation` |
| `routing` | `readiness`, `routing` | `compute`, `interpretation` |
| `compute` | `readiness`, `routing` | `compute`, `interpretation` |
| `interpretation` | `readiness`, `routing` | `compute`, `interpretation` |

`compute` always re-runs by design because numerical arrays are not checkpointed
as JSON payloads.

> [!WARNING]
> Using `checkpoint_key="default"` with an active checkpoint adapter can cause
> cross-run collisions. Use a unique per-run key (for example UUIDv4).

## Minimal audit trail schema for triage runs

The following schema is intentionally small while preserving reproducibility,
readiness traceability, and outcome accountability.

```json
{
  "run_id": "4c0a9c24-6f20-4d31-8cc8-0af739f3c7d6",
  "started_at_utc": "2026-04-12T14:07:31.028Z",
  "finished_at_utc": "2026-04-12T14:07:31.944Z",
  "request": {
    "goal": "univariate",
    "max_lag": 40,
    "n_surrogates": 99,
    "random_state": 42,
    "series_length": 500,
    "exog_length": null
  },
  "checkpoint": {
    "enabled": true,
    "checkpoint_key": "run-20260412-140731-4c0a9c24",
    "last_stage": "interpretation"
  },
  "readiness": {
    "status": "warning",
    "warnings": [
      {
        "code": "SIGNIFICANCE_FEASIBILITY",
        "message": "Series length (150) < 200. Surrogate significance bands may be unstable; interpret p-values with caution."
      }
    ]
  },
  "method_plan": {
    "route": "univariate_no_significance",
    "compute_surrogates": false
  },
  "timing_ms": {
    "readiness": 0.6,
    "routing": 0.3,
    "compute": 818.2,
    "interpretation": 2.1
  },
  "outcome": {
    "blocked": false,
    "forecastability_class": "high",
    "directness_class": "medium",
    "modeling_regime": "compact_structured_models",
    "primary_lags": [1],
    "n_sig_raw_lags": 0,
    "n_sig_partial_lags": 0,
    "recommendation": "HIGH -> Complex structured models (deep AR, nonlinear, LSTM)"
  },
  "stream": {
    "saw_done": true,
    "had_stage_error": false,
    "last_event_type": "done"
  },
  "error": null
}
```

Minimum retention guidance:

- Keep one immutable audit record per run.
- Store warning codes/messages exactly as emitted.
- Record `random_state` and effective route for replayability.

## Recommended logging fields for industrial usage

Use structured logs (JSON lines preferred) with one event per stage boundary.

| Category | Recommended fields |
|---|---|
| Correlation | `run_id`, `checkpoint_key`, `service`, `environment`, `host`, `process_id` |
| Request footprint | `goal`, `max_lag`, `n_surrogates`, `random_state`, `series_length`, `exog_length` |
| Stage lifecycle | `event_type`, `stage`, `timestamp`, `duration_ms`, `result_summary` |
| Routing and readiness | `readiness_status`, `readiness_warning_codes`, `route`, `compute_surrogates`, `blocked` |
| Deterministic outcome | `forecastability_class`, `directness_class`, `modeling_regime`, `primary_lags`, `n_sig_raw_lags`, `n_sig_partial_lags` |
| Error diagnostics | `error_class`, `error_message`, `stage_error`, `saw_done`, `http_status` |

> [!CAUTION]
> Do not log raw series values by default in shared industrial environments.
> Log compact lineage identifiers (dataset key, series ID, window bounds,
> checksum/hash) unless policy explicitly requires full payload retention.

## Practical failure triage workflow

1. Classify by transport outcome.
2. Validate stream terminal behavior.
3. Isolate failing stage and map to likely cause.
4. Check checkpoint replay position.
5. Re-run deterministically with the same request and `random_state`.
6. Produce closure evidence in the audit record.

### 1) Classify by transport outcome

- `422`: malformed or invalid request input.
- `503` on `/triage/stream`: streaming disabled by settings.
- `200` with `blocked=true`: readiness blocked by scientific constraints.
- `200` with `stage_error`: runtime failure in a pipeline stage.

### 2) Validate stream terminal behavior

- Confirm every payload has `event_type`.
- Confirm terminal sentinel `{ "event_type": "done" }` is present.
- If `done` is missing, treat as transport interruption and investigate network
  path or server cancellation before interpreting stage-level data.

### 3) Isolate failing stage and map to likely cause

| Stage | Typical symptom | First operational action |
|---|---|---|
| `readiness` | `blocked=true` or readiness warnings | Adjust `max_lag`, data length, or significance mode policy; record warning codes. |
| `routing` | Missing/invalid route assumptions | Verify `goal` and exogenous inputs are aligned with request contract. |
| `compute` | `stage_error` with estimator/runtime message | Re-run with identical seed and capture method plan + request footprint. |
| `interpretation` | `stage_error` after compute success | Validate compute outputs were produced and interpretation thresholds/config are available. |

### 4) Check checkpoint replay position

- Inspect checkpoint `stage` and `data` snapshot.
- Resume only when replay boundary is understood.
- If state is stale or key collisions are suspected, issue a new `checkpoint_key`
  and run from scratch.

### 5) Re-run deterministically

- Keep `series`, `goal`, `max_lag`, `n_surrogates`, and `random_state` fixed.
- Compare stage durations and warnings across runs.
- Escalate only if deterministic replay reproduces unexpected failures.

### 6) Produce closure evidence

Record in the audit artifact:

- final classification (`resolved`, `mitigated`, or `open`),
- remediation applied,
- run IDs and checkpoint keys used,
- before/after readiness and outcome snapshots.

## Cross-references

- SSE request/response details: [api_contract.md](api_contract.md)
- Replay semantics rationale: [architecture.md](architecture.md)
- Stability policy for adapters: [versioning.md](versioning.md)
- Production boundaries and non-goals: [production_readiness.md](production_readiness.md)

## Triage Extension Diagnostics in Observability

Triage extension diagnostics (F1–F6) produce structured Pydantic result
payloads that are included in the event and checkpoint trail alongside the
core triage output. When a diagnostic is computed, its result model is
serialised into the same `stage_completed` event for the `compute` stage
and persisted in the checkpoint summary.

The agent payload adapters (A1–A3) serialise all diagnostic outputs to
schema-versioned Pydantic models for observability and downstream consumption:

- **A1** (`triage_agent_payload_models.py`) — 9 typed payload models, one per diagnostic family.
- **A2** (`triage_summary_serializer.py`) — serialisation envelope with `schema_version` for forward compatibility.
- **A3** (`triage_agent_interpretation_adapter.py`) — deterministic interpretation with experimental and warning flags.

Experimental diagnostics (e.g. F5 Lyapunov exponent) are explicitly tagged
with `experimental=True` in the serialised payload so that observability
pipelines can filter or annotate accordingly.