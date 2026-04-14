# 22. Interpretation Algorithm

- [x] Implement deterministic interpretation logic consuming:
  - [ ] AMI curve
  - [ ] pAMI curve
  - [ ] significance bands
  - [ ] summary descriptors
  - [ ] optional rolling-origin results

```python
from __future__ import annotations

import numpy as np

from forecastability.utils.aggregation import summarize_canonical_result
from forecastability.utils.types import CanonicalExampleResult, InterpretationResult


def interpret_canonical_result(
    result: CanonicalExampleResult,
) -> InterpretationResult:
    """Interpret AMI and pAMI behavior."""
    summary = summarize_canonical_result(result)

    mean_ami_first_20 = float(np.mean(result.ami.values[: min(20, result.ami.values.size)]))
    directness_ratio = float(summary["directness_ratio"])
    n_sig_ami = int(summary["n_sig_ami"])
    n_sig_pami = int(summary["n_sig_pami"])

    if mean_ami_first_20 > 0.8:
        forecastability_class = "high"
    elif mean_ami_first_20 > 0.3:
        forecastability_class = "medium"
    else:
        forecastability_class = "low"

    if directness_ratio > 0.7 and n_sig_pami >= max(2, n_sig_ami // 2):
        directness_class = "high"
    elif directness_ratio > 0.35:
        directness_class = "medium"
    else:
        directness_class = "low"

    sig_lags = result.pami.significant_lags
    primary_lags = sig_lags.tolist()[:5] if sig_lags is not None else []

    if forecastability_class == "high" and directness_class == "high":
        modeling_regime = "rich_models_with_structured_memory"
    elif forecastability_class == "high" and directness_class in {"medium", "low"}:
        modeling_regime = "compact_structured_models"
    elif forecastability_class == "medium":
        modeling_regime = "seasonal_or_regularized_models"
    else:
        modeling_regime = "baseline_or_robust_decision_design"

    if directness_class == "low":
        narrative = (
            "The series shows more total dependence than direct dependence. "
            "Much of the long-lag AMI structure appears mediated through shorter lags."
        )
    elif directness_class == "medium":
        narrative = (
            "The series contains meaningful direct structure, but pAMI is notably sparser than AMI. "
            "A compact lag design is likely sufficient."
        )
    else:
        narrative = (
            "Direct dependence remains strong after conditioning on shorter lags. "
            "Richer structured models may be justified."
        )

    diagnostics = {
        "mean_ami_first_20": mean_ami_first_20,
        "directness_ratio": directness_ratio,
        "n_sig_ami": n_sig_ami,
        "n_sig_pami": n_sig_pami,
    }

    return InterpretationResult(
        forecastability_class=forecastability_class,
        directness_class=directness_class,
        primary_lags=primary_lags,
        modeling_regime=modeling_regime,
        narrative=narrative,
        diagnostics=diagnostics,
    )
```
