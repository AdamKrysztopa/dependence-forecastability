# 25. Canonical Examples Runner

- [x] `scripts/run_canonical_triage.py` must:
  - [ ] run all four canonical examples
  - [ ] save figures
  - [ ] save JSON summaries
  - [ ] save markdown snippets

```python
from __future__ import annotations

from pathlib import Path

from forecastability.utils.aggregation import summarize_canonical_result
from forecastability.utils.datasets import (
    generate_henon_map,
    generate_simulated_stock_returns,
    generate_sine_wave,
    load_air_passengers,
)
from forecastability.reporting.interpretation import interpret_canonical_result
from forecastability.pipeline import run_canonical_example
from forecastability.utils.plots import plot_canonical_result
from forecastability.reporting import save_canonical_result_json


def main() -> None:
    """Run canonical example analysis."""
    output_root = Path("outputs")
    figures_dir = output_root / "figures" / "canonical"
    json_dir = output_root / "json" / "canonical"

    datasets = {
        "sine_wave": generate_sine_wave(),
        "air_passengers": load_air_passengers(),
        "henon_map": generate_henon_map(),
        "simulated_stock_returns": generate_simulated_stock_returns(),
    }

    for name, ts in datasets.items():
        result = run_canonical_example(
            name,
            ts,
            max_lag_ami=60,
            max_lag_pami=40,
            n_neighbors=8,
            n_surrogates=99,
            alpha=0.05,
            random_state=42,
        )

        plot_canonical_result(
            result,
            save_path=figures_dir / f"{name}.png",
        )
        save_canonical_result_json(
            result,
            output_path=json_dir / f"{name}.json",
        )

        summary = summarize_canonical_result(result)
        interpretation = interpret_canonical_result(result)

        print(f"=== {name} ===")
        print(summary)
        print(interpretation)


if __name__ == "__main__":
    main()
```
