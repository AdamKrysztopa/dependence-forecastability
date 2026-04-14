<!-- type: reference -->
# HTTP API Contract

Reference for the FastAPI application exposed at `forecastability.adapters.api:app`.

_Last verified for release 0.2.0 consolidation on 2026-04-14._

> [!IMPORTANT]
> The HTTP API is deterministic-first. A blocked readiness outcome is returned as a successful transport response with `blocked: true`.

## Source Of Truth

- Runtime adapter: [../src/forecastability/adapters/api.py](../src/forecastability/adapters/api.py)
- SSE event emitter: [../src/forecastability/adapters/event_emitter.py](../src/forecastability/adapters/event_emitter.py)
- Contract tests: [../tests/test_api.py](../tests/test_api.py)
- Stability policy: [versioning.md](versioning.md)

## Endpoints

| Method | Path | Purpose | Success codes |
| --- | --- | --- | --- |
| `GET` | `/health` | Liveness probe | `200` |
| `GET` | `/scorers` | Registered dependence scorers | `200` |
| `POST` | `/triage` | Deterministic triage request | `200` |
| `GET` | `/triage/stream` | Server-Sent Events progress stream | `200`, `503` when disabled |

## `POST /triage`

### Request body

```json
{
  "series": [0.12, -0.30, 0.88],
  "exog": [0.01, 0.00, 0.12],
  "goal": "univariate",
  "max_lag": 40,
  "n_surrogates": 99,
  "random_state": 42
}
```

| Field | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `series` | `array[number]` | Yes | None | Must be non-empty |
| `exog` | `array[number] \| null` | No | `null` | Optional exogenous series |
| `goal` | `string` | No | `"univariate"` | Allowed values: `"univariate"`, `"exogenous"` |
| `max_lag` | `integer` | No | `40` | Passed through to deterministic triage |
| `n_surrogates` | `integer` | No | `99` | Must be `>= 99` at the HTTP boundary |
| `random_state` | `integer` | No | `42` | Deterministic seed |

### Response body

```json
{
  "blocked": false,
  "readiness_status": "warning",
  "readiness_warnings": [],
  "route": "univariate_with_significance",
  "compute_surrogates": true,
  "recommendation": "Compact structured models are justified.",
  "forecastability_class": "high",
  "directness_class": "medium",
  "modeling_regime": "compact_structured_models",
  "primary_lags": [1, 2],
  "n_sig_raw_lags": 2,
  "n_sig_partial_lags": 1
}
```

| Field | Type | Meaning |
| --- | --- | --- |
| `blocked` | `boolean` | Readiness blocked the request |
| `readiness_status` | `"clear" \| "warning" \| "blocked"` | Readiness outcome |
| `readiness_warnings` | `array[{code: string, message: string}]` | Machine-readable warning list |
| `route` | `string \| null` | Selected compute route, or `null` when blocked |
| `compute_surrogates` | `boolean \| null` | Whether surrogate significance was actually computed |
| `recommendation` | `string \| null` | Deterministic recommendation |
| `forecastability_class` | `string \| null` | Interpretation class |
| `directness_class` | `string \| null` | Directness label |
| `modeling_regime` | `string \| null` | Suggested modeling regime |
| `primary_lags` | `array[integer]` | Primary lags, empty when blocked or none found |
| `n_sig_raw_lags` | `integer \| null` | Count of significant raw lags |
| `n_sig_partial_lags` | `integer \| null` | Count of significant partial lags |

> [!NOTE]
> `compute_surrogates` is the field that distinguishes “significance was skipped” from “significance was computed.” If `compute_surrogates` is `false`, `n_sig_*_lags` should not be read as evidence that no lags were significant.

### Validation failures

`POST /triage` returns `422` for malformed JSON, invalid enum values, empty series, or `n_surrogates < 99`.

### Transport vs business outcome

- `200` means the request was accepted and the deterministic workflow ran to completion, even if the business outcome is blocked.
- `422` means the request body could not be accepted as valid input.

## `GET /triage/stream`

This endpoint streams stage progress as Server-Sent Events.

| Query parameter | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `series` | `string` | Yes | None | JSON-encoded list of floats |
| `goal` | `string` | No | `"univariate"` | Allowed values: `"univariate"`, `"exogenous"` |
| `max_lag` | `integer` | No | `40` | Maximum lag |
| `n_surrogates` | `integer` | No | `99` | Passed through to triage |
| `random_state` | `integer` | No | `42` | Deterministic seed |

> [!CAUTION]
> The streaming endpoint does not expose an `exog` query parameter today. Use `POST /triage` for exogenous requests. If you request `goal=exogenous` over the stream endpoint without exogenous data, the underlying readiness logic may block the run.

### Stream semantics

- Media type: `text/event-stream`
- Each event is emitted as `data: {...}\n\n`
- The stream ends with `data: {"event_type": "done"}`
- Streaming requires `triage_enable_streaming=true` in infrastructure settings

### Event types

| `event_type` | Fields |
| --- | --- |
| `stage_started` | `stage`, `timestamp` |
| `stage_completed` | `stage`, `duration_ms`, `result_summary` |
| `stage_error` | `stage`, `error` |
| `done` | No payload fields |

### Status codes

- `200` when the stream is enabled and starts successfully
- `422` for invalid JSON or invalid query parameters
- `503` when streaming is disabled in settings

## Minimal Startup

```bash
uv sync --extra transport
uv run uvicorn forecastability.adapters.api:app --host 127.0.0.1 --port 8000
```
