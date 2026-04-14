# 16. Plotting

- [x] Implement these figures:
  - [ ] AMI with surrogate band
  - [ ] pAMI with surrogate band
  - [ ] AMI vs pAMI overlay
  - [ ] canonical multi-panel figure with series segment + AMI + pAMI
  - [ ] optional AMI-pAMI difference plot

```python
from __future__ import annotations

from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

from forecastability.utils.types import CanonicalExampleResult


def plot_canonical_result(
    result: CanonicalExampleResult,
    *,
    save_path: Path,
) -> None:
    """Plot canonical example with series, AMI, and pAMI."""
    fig, axs = plt.subplots(3, 1, figsize=(11, 10))

    axs[0].plot(result.series, lw=1.5)
    axs[0].set_title(f"{result.series_name} — representative series")

    lags_ami = np.arange(1, result.ami.values.size + 1)
    axs[1].plot(lags_ami, result.ami.values, lw=2, label="AMI(h)")
    if result.ami.lower_band is not None and result.ami.upper_band is not None:
        axs[1].fill_between(
            lags_ami,
            result.ami.lower_band,
            result.ami.upper_band,
            alpha=0.2,
            label="95% surrogate band",
        )
    axs[1].set_title("AMI — nonlinear ACF interpretation")
    axs[1].legend()
    axs[1].grid(alpha=0.3)

    lags_pami = np.arange(1, result.pami.values.size + 1)
    axs[2].plot(lags_pami, result.pami.values, lw=2, label="pAMI(h)")
    if result.pami.lower_band is not None and result.pami.upper_band is not None:
        axs[2].fill_between(
            lags_pami,
            result.pami.lower_band,
            result.pami.upper_band,
            alpha=0.2,
            label="95% surrogate band",
        )
    axs[2].set_title("pAMI — nonlinear PACF interpretation")
    axs[2].legend()
    axs[2].grid(alpha=0.3)

    plt.tight_layout()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
```
