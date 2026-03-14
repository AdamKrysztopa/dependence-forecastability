"""Run the fixed exogenous benchmark slice and save diagnostic artifacts."""

from __future__ import annotations

import logging

from forecastability.exog_benchmark import run_benchmark_exog_panel


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run_benchmark_exog_panel()


if __name__ == "__main__":
    main()
