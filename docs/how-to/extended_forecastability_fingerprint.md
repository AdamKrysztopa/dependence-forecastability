<!-- type: how-to -->
# Extended Forecastability Fingerprint

Use this page when you want to run the implemented AMI-first extended analysis
surfaces and read their outputs conservatively.

> [!IMPORTANT]
> The extended surface is AMI-first. The spectral, ordinal, classical, and
> memory blocks add explanatory context around lagged-information evidence;
> they do not replace AMI geometry and they do not perform model fitting.

## What Is Shipped Now

The live repository now exposes the full Phase 2 public surface:

- `run_extended_forecastability_analysis(...)` on `forecastability` and `forecastability.triage`
- additive `run_triage(..., include_extended_fingerprint=True)` with `TriageResult.extended_forecastability_analysis`
- `forecastability extended` CLI with `json`, `markdown`, and `brief` output

The underlying AMI geometry, spectral, ordinal, classical, and memory blocks
remain the same additive fingerprint inputs. Phase 2 adds the deterministic
router, the public use case, and the CLI adapter on top of that fingerprint.

## Purpose

Use the extended surface when you want one deterministic, explanation-oriented
bundle that keeps AMI geometry at the center while adding cheap secondary
structure signals around it.

## Public Result Map

`run_extended_forecastability_analysis(...)` returns one
`ExtendedForecastabilityAnalysisResult`.

| Field | Meaning | Where to read more |
| --- | --- | --- |
| `series_name` | Optional stable identifier echoed back in the result | This page |
| `n_observations` | Number of validated observations used by the analysis | This page |
| `max_lag` | Public lag horizon requested for lag-aware diagnostics | This page |
| `period` | Optional seasonal period supplied by the caller | [../theory/classical_structure_features.md](../theory/classical_structure_features.md) |
| `fingerprint` | Composite AMI-first diagnostic bundle | Tables below and theory links below |
| `profile` | Deterministic `ExtendedForecastabilityProfile` built from the fingerprint | [../explanation/extended_forecastability_profile.md](../explanation/extended_forecastability_profile.md) |
| `routing_metadata` | JSON-safe provenance and routing-state metadata | Tables below |

The `fingerprint` container keeps each diagnostic block explicit.

| `result.fingerprint` field | Meaning | Canonical theory page |
| --- | --- | --- |
| `information_geometry` | Existing AMI geometry block reused by the extended surface | [../theory/ami_information_geometry.md](../theory/ami_information_geometry.md) |
| `spectral` | Frequency-domain concentration and periodicity summary | [../theory/spectral_forecastability.md](../theory/spectral_forecastability.md) |
| `ordinal` | Rank-pattern entropy and redundancy summary | [../theory/ordinal_complexity.md](../theory/ordinal_complexity.md) |
| `classical` | Trend, optional seasonality, and autocorrelation summary | [../theory/classical_structure_features.md](../theory/classical_structure_features.md) |
| `memory` | DFA-based persistence and scale summary | [../theory/memory_diagnostics.md](../theory/memory_diagnostics.md) |

When a block is disabled, its field stays `None` instead of being replaced with
an invented placeholder.

## Pick The Right Entry Point

- Use `run_extended_forecastability_analysis(...)` when you want the direct
  univariate extended result.
- Use `run_triage(..., include_extended_fingerprint=True)` when you want the
  normal triage result plus the additive extended bundle in one object.
- Use `forecastability extended` when you need adapter-owned CLI output without
  writing Python glue.
- Stay on the exogenous surfaces for exogenous requests; the triage opt-in is
  intentionally suppressed there because this repository does not yet ship an
  exogenous-aware extended analysis.

## Direct Python Use

```python
from forecastability import generate_ar1, run_extended_forecastability_analysis

series = generate_ar1(n_samples=300, phi=0.8, random_state=42)
result = run_extended_forecastability_analysis(series, max_lag=24)

print(result.profile.predictability_sources)
print(result.routing_metadata["descriptive_only"])
```

If you want a compact JSON-safe record for inspection, `model_dump()` keeps the
field names visible:

```python
payload = result.model_dump(exclude_none=True)
print(sorted(payload.keys()))
```

## Triage Opt-In

```python
from forecastability import TriageRequest, generate_ar1, run_triage

series = generate_ar1(n_samples=300, phi=0.8, random_state=42)
triage = run_triage(
    TriageRequest(series=series, max_lag=24, random_state=42),
    include_extended_fingerprint=True,
)

extended = triage.extended_forecastability_analysis
```

When the request is blocked or routed as exogenous, `extended` stays `None` and
the field is omitted from serialized presenter output.

## CLI Use

```bash
forecastability extended --csv data.csv --col value --max-lag 24 --format brief
```

> [!NOTE]
> The current non-JSON CLI renderer is the same executive-style brief for
> `markdown` and `brief`.

## Routing Metadata Keys

The router keeps public provenance in `result.routing_metadata`.

Always-present routing keys:

| Key | Meaning |
| --- | --- |
| `policy_version` | Deterministic router policy identifier |
| `ami_geometry_requested` | Whether the router was asked to use AMI geometry |
| `ami_geometry_available` | Whether AMI geometry was present in the fingerprint |
| `descriptive_only` | `True` when routing-grade family recommendations were intentionally withheld |
| `predictability_source_count` | Count of distinct entries in `profile.predictability_sources` |
| `has_nonlinear_followup` | `True` when the router sees a nonlinear follow-up case and AMI routing is active |
| `signal_strength` | Echo of `profile.signal_strength` for JSON-first consumers |
| `noise_risk` | Echo of `profile.noise_risk` for JSON-first consumers |
| `include_ami_geometry` | Request echo for the AMI geometry block |
| `include_spectral` | Request echo for the spectral block |
| `include_ordinal` | Request echo for the ordinal block |
| `include_classical` | Request echo for the classical block |
| `include_memory` | Request echo for the memory block |
| `ordinal_embedding_dimension` | Request echo for ordinal embedding size |
| `ordinal_delay` | Request echo for ordinal embedding delay |

Conditionally present routing keys:

| Key | When present | Meaning |
| --- | --- | --- |
| `period_supplied` | A positive `period` was passed | Signals that the classical seasonal path was eligible |
| `memory_min_scale` | The caller overrode the lower DFA scale bound | Records the explicit public override |
| `memory_max_scale` | The caller overrode the upper DFA scale bound | Records the explicit public override |
| `random_state_contract` | `random_state` was passed | Records that Phase 2 remains deterministic and ignores that value |

## How To Read The Result

1. Start with `fingerprint.information_geometry` when it is present, because it remains the primary lagged-information evidence.
2. Read `spectral`, `ordinal`, `classical`, and `memory` as additive explanations for why forecastability may exist.
3. If `routing_metadata["descriptive_only"]` is `True`, treat the result as intentionally diagnostic-only. That means AMI geometry was disabled or unavailable, so routing-grade family recommendations were withheld.
4. Use `profile.predictability_sources` and `profile.explanation` as deterministic starting guidance after triage, not as model fitting instructions.

> [!TIP]
> The fastest read is: `information_geometry` first, `profile` second,
> `routing_metadata` third, and then the block-specific theory pages only for
> the blocks that materially shaped the profile.

## Validation And Block Gating

- shared validation requires a finite one-dimensional input series
- `max_lag` is validated before optional lag-aware blocks run
- `period` is validated before the classical block runs, even if that block is later disabled
- `seasonal_strength` is only computed when `period` is supplied
- disabling a block preserves `None` in the corresponding fingerprint field instead of fabricating a placeholder result

## Non-Goals

- skipping straight to downstream fitting or benchmark comparisons
- treating the extended surface as a replacement for `run_triage()` or the exogenous workflows
- pretending the secondary diagnostics alone justify routing-grade family recommendations
- expecting notebook-first showcase material in this repository

## Theory Cross-References

- [../theory/spectral_forecastability.md](../theory/spectral_forecastability.md)
- [../theory/ordinal_complexity.md](../theory/ordinal_complexity.md)
- [../theory/classical_structure_features.md](../theory/classical_structure_features.md)
- [../theory/memory_diagnostics.md](../theory/memory_diagnostics.md)

Richer walkthroughs and notebooks for this surface belong in the sibling
`forecastability-examples` repository rather than in this core repo.
