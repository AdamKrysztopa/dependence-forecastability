# 24. Reporting Module

- [x] Create markdown and JSON outputs.
- [x] Implement canonical JSON output.
- [x] Implement canonical markdown summary.

```python
from __future__ import annotations

import json
from pathlib import Path

from forecastability.utils.aggregation import summarize_canonical_result
from forecastability.reporting.interpretation import interpret_canonical_result
from forecastability.utils.types import CanonicalExampleResult


def save_canonical_result_json(
    result: CanonicalExampleResult,
    *,
    output_path: Path,
) -> None:
    """Save canonical result summary to JSON."""
    summary = summarize_canonical_result(result)
    interpretation = interpret_canonical_result(result)

    payload = {
        "series_name": result.series_name,
        "summary": summary,
        "interpretation": {
            "forecastability_class": interpretation.forecastability_class,
            "directness_class": interpretation.directness_class,
            "primary_lags": interpretation.primary_lags,
            "modeling_regime": interpretation.modeling_regime,
            "narrative": interpretation.narrative,
            "diagnostics": interpretation.diagnostics,
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_canonical_markdown(
    result: CanonicalExampleResult,
) -> str:
    """Build markdown summary for one canonical example."""
    summary = summarize_canonical_result(result)
    interpretation = interpret_canonical_result(result)

    return f"""# {result.series_name}

## Summary
- n_sig_ami: {summary['n_sig_ami']}
- n_sig_pami: {summary['n_sig_pami']}
- peak_lag_ami: {summary['peak_lag_ami']}
- peak_lag_pami: {summary['peak_lag_pami']}
- auc_ami: {summary['auc_ami']:.4f}
- auc_pami: {summary['auc_pami']:.4f}
- directness_ratio: {summary['directness_ratio']:.4f}

## Interpretation
- forecastability_class: {interpretation.forecastability_class}
- directness_class: {interpretation.directness_class}
- primary_lags: {interpretation.primary_lags}
- modeling_regime: {interpretation.modeling_regime}

## Narrative
{interpretation.narrative}
"""
```
