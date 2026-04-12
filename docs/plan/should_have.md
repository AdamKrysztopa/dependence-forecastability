<!-- type: reference -->
# Should Have

These items are important and high-value, but they do not outrank paper-baseline parity or the core extension studies.

## 1. Frequency-wise extension report ✅

**Status: Complete.**

Implementation: `src/forecastability/reporting.py` includes `build_frequency_panel_markdown()`.

## 2. Extension ablation pack ✅

**Status: Complete.**

Implementation: `src/forecastability/extensions.py` provides `compute_k_sensitivity()` and `bootstrap_descriptor_uncertainty()` for ablation studies.

## 3. SOLID Refactor (Compatibility-Preserving) ✅

**Status: Complete.** All 12 tickets implemented.

Implemented modules:
- `services/` — raw_curve, partial_curve, significance, recommendation, plot, exog variants
- `use_cases/` — rolling-origin evaluation, exogenous evaluation, request/response DTOs  
- `assemblers/` — summary and report payload assembly
- `ports/` — 9 Protocol interfaces
- `bootstrap/` — output directory management
- `state.py` — explicit analyzer state

Verification gates (all passing):

```bash
uv run pytest -q -ra
uv run ruff check .
uv run ty check
```
