# 15. Summary Descriptors to Quantify What pAMI Adds

- [x] Implement derived descriptors for each canonical result:
  - [ ] `n_sig_ami`
  - [ ] `n_sig_pami`
  - [ ] `peak_lag_ami`
  - [ ] `peak_lag_pami`
  - [ ] `peak_ami`
  - [ ] `peak_pami`
  - [ ] `auc_ami`
  - [ ] `auc_pami`
  - [ ] `directness_ratio = auc_pami / max(auc_ami, eps)`
  - [ ] `pami_to_ami_sig_ratio`
  - [ ] `first_sig_ami`
  - [ ] `first_sig_pami`
  - [ ] `last_sig_ami`
  - [ ] `last_sig_pami`

```python
from __future__ import annotations

import numpy as np

from forecastability.types import CanonicalExampleResult


def summarize_canonical_result(
    result: CanonicalExampleResult,
) -> dict[str, float | int | str]:
    """Summarize AMI and pAMI result."""
    eps = 1e-12

    ami = result.ami.values
    pami = result.pami.values
    sig_ami = result.ami.significant_lags if result.ami.significant_lags is not None else np.array([])
    sig_pami = result.pami.significant_lags if result.pami.significant_lags is not None else np.array([])

    summary: dict[str, float | int | str] = {
        "series_name": result.series_name,
        "n_sig_ami": int(sig_ami.size),
        "n_sig_pami": int(sig_pami.size),
        "peak_lag_ami": int(np.argmax(ami) + 1),
        "peak_lag_pami": int(np.argmax(pami) + 1),
        "peak_ami": float(np.max(ami)),
        "peak_pami": float(np.max(pami)),
        "auc_ami": float(np.trapezoid(ami)),
        "auc_pami": float(np.trapezoid(pami)),
        "directness_ratio": float(np.trapezoid(pami) / max(np.trapezoid(ami), eps)),
        "pami_to_ami_sig_ratio": float(sig_pami.size / max(sig_ami.size, 1)),
        "first_sig_ami": int(sig_ami[0]) if sig_ami.size else 0,
        "first_sig_pami": int(sig_pami[0]) if sig_pami.size else 0,
        "last_sig_ami": int(sig_ami[-1]) if sig_ami.size else 0,
        "last_sig_pami": int(sig_pami[-1]) if sig_pami.size else 0,
    }
    return summary
```
