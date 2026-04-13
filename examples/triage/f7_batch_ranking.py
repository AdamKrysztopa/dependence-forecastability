"""F7 example: deterministic batch triage ranking with export artifacts.

This example evaluates 11 synthetic signals, prints a ranked table with
individual diagnostic columns, and exports CSV/JSON outputs.

Usage:
    uv run python examples/triage/f7_batch_ranking.py
"""

from __future__ import annotations

import csv
import os
from pathlib import Path

import numpy as np

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt

from forecastability.triage.batch_models import (
    SUMMARY_TABLE_COLUMNS,
    BatchSeriesRequest,
    BatchTriageRequest,
)
from forecastability.use_cases.run_batch_triage import run_batch_triage

_N_SAMPLES = 420


def _make_white_noise(*, n_samples: int, random_state: int) -> np.ndarray:
    rng = np.random.default_rng(random_state)
    return rng.standard_normal(n_samples)


def _make_ar1(*, n_samples: int, phi: float, random_state: int) -> np.ndarray:
    rng = np.random.default_rng(random_state)
    series = np.zeros(n_samples, dtype=float)
    series[0] = rng.standard_normal()
    for index in range(1, n_samples):
        series[index] = phi * series[index - 1] + rng.standard_normal()
    return series


def _make_seasonal(*, n_samples: int, period: float, random_state: int) -> np.ndarray:
    rng = np.random.default_rng(random_state)
    time_index = np.arange(n_samples, dtype=float)
    series = np.sin(2.0 * np.pi * time_index / period) + 0.35 * np.sin(
        2.0 * np.pi * time_index / (period / 2.0)
    )
    return series + 0.25 * rng.standard_normal(n_samples)


def _make_random_walk(*, n_samples: int, random_state: int) -> np.ndarray:
    rng = np.random.default_rng(random_state)
    return np.cumsum(rng.standard_normal(n_samples))


def _make_sawtooth(*, n_samples: int, period: float) -> np.ndarray:
    time_index = np.arange(n_samples, dtype=float)
    return (time_index % period) / period


def _make_logistic(*, n_samples: int, r: float = 3.8) -> np.ndarray:
    series = np.empty(n_samples, dtype=float)
    series[0] = 0.5
    for index in range(1, n_samples):
        series[index] = r * series[index - 1] * (1.0 - series[index - 1])
    return series


def _make_trend_plus_season(*, n_samples: int, random_state: int) -> np.ndarray:
    rng = np.random.default_rng(random_state)
    time_index = np.arange(n_samples, dtype=float)
    trend = 0.01 * time_index
    seasonal = 0.9 * np.sin(2.0 * np.pi * time_index / 24.0)
    return trend + seasonal + 0.4 * rng.standard_normal(n_samples)


def _make_bursty_process(*, n_samples: int, random_state: int) -> np.ndarray:
    rng = np.random.default_rng(random_state)
    baseline = rng.standard_normal(n_samples)
    spikes = np.zeros(n_samples, dtype=float)
    spike_positions = np.arange(20, n_samples, 50)
    spikes[spike_positions] = rng.normal(loc=4.0, scale=0.3, size=spike_positions.size)
    return baseline + spikes


def _build_signal_bank() -> list[tuple[str, np.ndarray]]:
    return [
        ("white_noise", _make_white_noise(n_samples=_N_SAMPLES, random_state=101)),
        ("ar1_phi02", _make_ar1(n_samples=_N_SAMPLES, phi=0.2, random_state=102)),
        ("ar1_phi08", _make_ar1(n_samples=_N_SAMPLES, phi=0.8, random_state=103)),
        (
            "seasonal_period12",
            _make_seasonal(n_samples=_N_SAMPLES, period=12.0, random_state=104),
        ),
        (
            "seasonal_period24",
            _make_seasonal(n_samples=_N_SAMPLES, period=24.0, random_state=105),
        ),
        ("random_walk", _make_random_walk(n_samples=_N_SAMPLES, random_state=106)),
        ("sawtooth_period18", _make_sawtooth(n_samples=_N_SAMPLES, period=18.0)),
        ("logistic_r38", _make_logistic(n_samples=_N_SAMPLES, r=3.8)),
        (
            "trend_plus_season",
            _make_trend_plus_season(n_samples=_N_SAMPLES, random_state=107),
        ),
        (
            "bursty_noise",
            _make_bursty_process(n_samples=_N_SAMPLES, random_state=108),
        ),
        (
            "ar1_phi05",
            _make_ar1(n_samples=_N_SAMPLES, phi=0.5, random_state=109),
        ),
    ]


def _write_csv(
    *,
    csv_path: Path,
    rows: list[dict[str, object]],
    columns: tuple[str, ...],
) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in columns})


def _get_float(row: dict[str, object], key: str) -> float:
    """Safely extract a float from a dict[str, object] value."""
    val = row.get(key)
    return float(val) if isinstance(val, (int, float)) else 0.0


def _plot_diagnostic_heatmap(
    *,
    summary_rows: list[dict[str, object]],
    output_path: Path,
) -> None:
    ordered = sorted(summary_rows, key=lambda row: int(row.get("rank") or 10_000))

    forecastability_map = {"high": 1.0, "medium": 0.5, "low": 0.0}
    complexity_map = {"high": 1.0, "medium": 0.5, "low": 0.0}

    matrix = np.array(
        [
            [
                _get_float(row, "spectral_predictability"),
                _get_float(row, "permutation_entropy"),
                _get_float(row, "directness_ratio"),
                forecastability_map.get(str(row.get("forecastability_class") or ""), 0.0),
                complexity_map.get(str(row.get("complexity_band_label") or ""), 0.0),
            ]
            for row in ordered
        ],
        dtype=float,
    )

    fig, ax = plt.subplots(figsize=(11, max(5, 0.45 * len(ordered) + 2.0)))
    image = ax.imshow(matrix, aspect="auto", cmap="YlGnBu", vmin=0.0, vmax=1.0)
    ax.set_xticks(np.arange(5))
    ax.set_xticklabels(
        [
            "spectral_predictability",
            "permutation_entropy",
            "directness_ratio",
            "forecastability_class",
            "complexity_band_label",
        ],
        rotation=20,
        ha="right",
    )
    ax.set_yticks(np.arange(len(ordered)))
    ax.set_yticklabels(
        [f"#{row.get('rank')} {row.get('series_id')}" for row in ordered],
        fontsize=9,
    )

    for row_index, row in enumerate(ordered):
        for col_index in range(5):
            if col_index == 0:
                text = f"{_get_float(row, 'spectral_predictability'):.2f}"
            elif col_index == 1:
                text = f"{_get_float(row, 'permutation_entropy'):.2f}"
            elif col_index == 2:
                value = row.get("directness_ratio")
                text = f"{float(value):.2f}" if isinstance(value, int | float) else "-"
            elif col_index == 3:
                text = str(row.get("forecastability_class") or "-")
            else:
                text = str(row.get("complexity_band_label") or "-")
            ax.text(col_index, row_index, text, ha="center", va="center", fontsize=8)

    ax.set_title("F7 Batch ranking: per-signal diagnostics (not composite rank only)")
    fig.colorbar(image, ax=ax, label="normalized diagnostic encoding")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main() -> None:
    """Run the F7 example and export ranking artifacts."""
    signal_bank = _build_signal_bank()
    request = BatchTriageRequest(
        items=[
            BatchSeriesRequest(series_id=signal_name, series=series.tolist())
            for signal_name, series in signal_bank
        ],
        max_lag=24,
        n_surrogates=99,
        random_state=314,
    )
    response = run_batch_triage(request)

    summary_rows = [row.model_dump(mode="json") for row in response.summary_table]
    failure_rows = [row.model_dump(mode="json") for row in response.failure_table]

    print("\n=== F7 Batch Multi-Signal Ranking ===")
    print(f"n_signals: {len(signal_bank)}")
    print("\nRanking table (key diagnostic columns):")
    print(
        f"{'Rank':<6} {'Series ID':<20} {'Forecast.':<10} "
        f"{'Omega':<7} {'PE':<7} {'Directness':<10} {'Band':<8} {'Next action'}"
    )
    print("-" * 100)

    ordered_rows = sorted(summary_rows, key=lambda row: int(row.get("rank") or 10_000))
    for row in ordered_rows:
        directness_value = row.get("directness_ratio")
        directness_text = (
            f"{float(directness_value):.3f}" if isinstance(directness_value, int | float) else "-"
        )
        print(
            f"{int(row.get('rank') or 0):<6} {str(row.get('series_id')):<20} "
            f"{str(row.get('forecastability_class') or '-'): <10} "
            f"{float(row.get('spectral_predictability') or 0.0):<7.3f} "
            f"{float(row.get('permutation_entropy') or 0.0):<7.3f} "
            f"{directness_text:<10} "
            f"{str(row.get('complexity_band_label') or '-'):<8} "
            f"{str(row.get('recommended_next_action') or '-')}"
        )

    tables_dir = Path("outputs/tables/examples/triage")
    json_dir = Path("outputs/json/examples/triage")
    figure_path = Path("outputs/figures/examples/triage/f7_batch_ranking_heatmap.png")

    summary_csv = tables_dir / "f7_batch_ranking_summary.csv"
    failures_csv = tables_dir / "f7_batch_ranking_failures.csv"
    response_json = json_dir / "f7_batch_ranking_response.json"

    _write_csv(csv_path=summary_csv, rows=summary_rows, columns=SUMMARY_TABLE_COLUMNS)
    _write_csv(
        csv_path=failures_csv,
        rows=failure_rows,
        columns=("series_id", "error_code", "error_message"),
    )

    response_json.parent.mkdir(parents=True, exist_ok=True)
    response_json.write_text(response.model_dump_json(indent=2), encoding="utf-8")

    _plot_diagnostic_heatmap(summary_rows=summary_rows, output_path=figure_path)

    print("\nSaved artifacts:")
    print(f"- {summary_csv}")
    print(f"- {failures_csv}")
    print(f"- {response_json}")
    print(f"- {figure_path}")


if __name__ == "__main__":
    main()
