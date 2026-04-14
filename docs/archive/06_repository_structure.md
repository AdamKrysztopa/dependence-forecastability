# 6. Repository Structure

- [x] Use exactly this structure:

```text
project/
├─ pyproject.toml
├─ README.md
├─ configs/
│  ├─ canonical_examples.yaml
│  ├─ benchmark_panel.yaml
│  └─ interpretation_rules.yaml
├─ data/
│  ├─ raw/
│  ├─ interim/
│  └─ processed/
├─ outputs/
│  ├─ figures/
│  ├─ tables/
│  ├─ json/
│  └─ reports/
├─ src/
│  └─ forecastability/
│     ├─ __init__.py
│     ├─ config.py
│     ├─ types.py
│     ├─ validation.py
│     ├─ datasets.py
│     ├─ metrics.py
│     ├─ surrogates.py
│     ├─ rolling_origin.py
│     ├─ models.py
│     ├─ aggregation.py
│     ├─ interpretation.py
│     ├─ plots.py
│     ├─ reporting.py
│     └─ pipeline.py
├─ scripts/
│  ├─ run_canonical_triage.py
│  ├─ run_benchmark_panel.py
│  └─ build_report_artifacts.py
└─ tests/
   ├─ test_validation.py
   ├─ test_metrics.py
   ├─ test_surrogates.py
   ├─ test_rolling_origin.py
   ├─ test_interpretation.py
   └─ test_pipeline.py
```

- [x] Keep this layout as the canonical target for implementation planning and verification.
