"""Exporter end-to-end walkthrough for ForecastPrepContract.

Demonstrates all three serialisation helpers for a ForecastPrepContract:

    1. JSON via ``contract.model_dump_json``
    2. Markdown via ``forecast_prep_contract_to_markdown``
    3. CSV lag table via ``forecast_prep_contract_to_lag_table``

All three outputs are written under ``outputs/examples/forecast_prep/``.
No forecasting framework is imported. Only stdlib, plus ``forecastability``.
"""

from __future__ import annotations

import csv
from pathlib import Path

from forecastability import (
    TriageRequest,
    build_forecast_prep_contract,
    forecast_prep_contract_to_lag_table,
    forecast_prep_contract_to_markdown,
    generate_ar1,
    run_triage,
)
from forecastability.triage import AnalysisGoal

_OUTPUT_DIR = Path("outputs/examples/forecast_prep")


def main() -> None:
    """Run triage, build a contract, and write JSON / Markdown / CSV outputs."""
    series = generate_ar1(n_samples=300, phi=0.8, random_state=42)

    triage_result = run_triage(
        TriageRequest(
            series=series,
            goal=AnalysisGoal.univariate,
            max_lag=20,
            n_surrogates=99,
            random_state=42,
        )
    )

    contract = build_forecast_prep_contract(
        triage_result,
        horizon=12,
        target_frequency="D",
        add_calendar_features=False,
    )

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- JSON ---
    json_path = _OUTPUT_DIR / "contract.json"
    json_path.write_text(contract.model_dump_json(indent=2), encoding="utf-8")
    print(f"Written: {json_path}")

    # --- Markdown ---
    md_path = _OUTPUT_DIR / "contract.md"
    md_path.write_text(forecast_prep_contract_to_markdown(contract), encoding="utf-8")
    print(f"Written: {md_path}")

    # --- CSV lag table ---
    csv_path = _OUTPUT_DIR / "lag_table.csv"
    rows = forecast_prep_contract_to_lag_table(contract)
    if rows:
        fieldnames = list(rows[0].keys())
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    else:
        csv_path.write_text("", encoding="utf-8")
    print(f"Written: {csv_path}")


if __name__ == "__main__":
    main()
