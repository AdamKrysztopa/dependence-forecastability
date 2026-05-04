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

## How To Read The Result

1. Start with `fingerprint.information_geometry` when it is present, because it remains the primary lagged-information evidence.
2. Read `spectral`, `ordinal`, `classical`, and `memory` as additive explanations for why forecastability may exist.
3. If `routing_metadata["descriptive_only"]` is `True`, treat the result as intentionally diagnostic-only. That means AMI geometry was disabled or unavailable, so routing-grade family recommendations were withheld.
4. Use `profile.predictability_sources` and `profile.explanation` as deterministic starting guidance after triage, not as model fitting instructions.

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
- [../theory/classical_structure.md](../theory/classical_structure.md)
- [../theory/memory_structure.md](../theory/memory_structure.md)

Richer walkthroughs and notebooks for this surface belong in the sibling
`forecastability-examples` repository rather than in this core repo.
