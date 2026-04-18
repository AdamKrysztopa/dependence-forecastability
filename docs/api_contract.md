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

---

## Python Compute Functions

The functions below are importable directly and do not require the HTTP transport layer.
They are part of the v0.3.0 covariant-informative extension.

### Transfer Entropy (V3-F01)

All TE functions live in `src/forecastability/diagnostics/transfer_entropy.py`
(re-exported by `src/forecastability/services/transfer_entropy_service.py`).

| Function | Signature | Returns |
|---|---|---|
| `compute_transfer_entropy` | `(source, target, *, lag, min_pairs=50) -> float` | TE in bits |
| `compute_transfer_entropy_curve` | `(source, target, *, max_lag, min_pairs=50) -> np.ndarray` | Per-lag TE curve, shape `(max_lag,)` |
| `te_scorer` | `(*, lag=1, min_pairs=50) -> DependenceScorer` | Factory — returns a `DependenceScorer` registered as `"te"` |

`TeResult` model fields:

| Field | Type | Notes |
|---|---|---|
| `source` | `str` | Source series identifier |
| `target` | `str` | Target series identifier |
| `lag` | `int` | Lag at which TE was computed |
| `te_value` | `float` | TE estimate in bits |
| `p_value` | `float \| None` | Surrogate p-value if computed |
| `significant` | `bool \| None` | Significance flag |

> [!NOTE]
> TE uses kNN MI estimation with conditioning vectors. Minimum pairs requirement
> is `min_pairs=50` due to conditioning dimensionality.

### Gaussian Copula MI (V3-F02)

All GCMI functions live in `src/forecastability/diagnostics/gcmi.py`
(re-exported by `src/forecastability/services/gcmi_service.py`).

| Function | Signature | Returns |
|---|---|---|
| `compute_gcmi` | `(x, y, *, min_pairs=30) -> float` | GCMI in bits |
| `compute_gcmi_at_lag` | `(source, target, *, lag, min_pairs=30) -> float` | GCMI at a single lag, in bits |
| `compute_gcmi_curve` | `(source, target, *, max_lag, min_pairs=30) -> np.ndarray` | Per-lag GCMI curve, shape `(max_lag,)`, index 0 = lag 1 |
| `gcmi_scorer` | `(*, lag=1, min_pairs=30) -> DependenceScorer` | Factory — returns a `DependenceScorer` registered as `"gcmi"` |

`GcmiResult` model fields:

| Field | Type | Notes |
|---|---|---|
| `source` | `str` | Source series identifier |
| `target` | `str` | Target series identifier |
| `lag` | `int` | Lag at which GCMI was computed |
| `gcmi_value` | `float` | GCMI estimate in bits |

> [!NOTE]
> GCMI is fully deterministic — it has no random state. The `random_state` argument
> accepted by `DependenceScorer.__call__` is accepted but ignored.

See [theory/gcmi.md](theory/gcmi.md) for the algorithm, properties, and GCMI vs TE comparison.
