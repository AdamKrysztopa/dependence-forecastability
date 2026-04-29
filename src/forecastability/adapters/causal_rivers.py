"""Causal-rivers data loading and deterministic analysis helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from forecastability.extensions import TargetBaselineCurves
from forecastability.pipeline import run_exogenous_rolling_origin_evaluation
from forecastability.utils.config import RollingOriginConfig

CausalRiversRole = Literal["positive", "negative"]


class CausalRiversDataConfig(BaseModel):
    """Input dataset paths and resampling parameters.

    Attributes:
        raw_dir: Directory containing the raw East Germany subset files.
        ts_file: CSV file with the station time series.
        graph_file: Pickle file with the benchmark graph.
        meta_file: CSV file with station metadata.
        resample_freq: Pandas offset alias used for resampling.
    """

    model_config = ConfigDict(frozen=True)

    raw_dir: Path
    ts_file: str
    graph_file: str
    meta_file: str
    resample_freq: str = "6h"


class CausalRiversStationSelectionConfig(BaseModel):
    """Target and driver station ids for the deterministic slice.

    Attributes:
        target_id: Downstream target station id.
        positive_upstream: Graph-verified upstream tributaries.
        negative_control: Unrelated-basin negative controls.
    """

    model_config = ConfigDict(frozen=True)

    target_id: int
    positive_upstream: list[int] = Field(default_factory=list)
    negative_control: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_station_sets(self) -> CausalRiversStationSelectionConfig:
        if not self.positive_upstream:
            raise ValueError("positive_upstream must be non-empty")
        if not self.negative_control:
            raise ValueError("negative_control must be non-empty")
        return self


class CausalRiversMetricConfig(BaseModel):
    """Metric and seed settings for the causal-rivers slice.

    Attributes:
        n_neighbors: MI neighborhood size; fixed at 8 by repo invariant.
        random_state: Deterministic seed.
        n_surrogates: Surrogate count carried into the analyzer.
        min_pairs_raw: Minimum pair count for raw cross-MI.
        min_pairs_partial: Minimum pair count for conditioned cross-MI.
    """

    model_config = ConfigDict(frozen=True)

    n_neighbors: int = Field(default=8, ge=1)
    random_state: int = 42
    n_surrogates: int = Field(default=99, ge=99)
    min_pairs_raw: int = Field(default=30, ge=2)
    min_pairs_partial: int = Field(default=50, ge=2)


class CausalRiversAnalysisConfig(BaseModel):
    """Typed configuration for the deterministic causal-rivers analysis.

    Attributes:
        data: Raw-data path settings.
        station_selection: Target and driver station ids.
        rolling_origin: Rolling-origin horizons and origin count.
        metric: MI estimator settings.
        analysis_scope: Disclosure label mirrored into result metadata.
        project_extension: Disclosure flag for project-only behavior.
    """

    model_config = ConfigDict(frozen=True)

    data: CausalRiversDataConfig
    station_selection: CausalRiversStationSelectionConfig
    rolling_origin: RollingOriginConfig
    metric: CausalRiversMetricConfig
    analysis_scope: Literal["descriptive", "guidance", "both"] = "both"
    project_extension: bool = True

    @model_validator(mode="after")
    def _validate_repo_invariants(self) -> CausalRiversAnalysisConfig:
        if self.metric.n_neighbors != 8:
            raise ValueError("causal-rivers analysis requires n_neighbors=8")
        return self


class CausalRiversPairSummary(BaseModel):
    """Deterministic summary for one target-driver evaluation pair.

    Attributes:
        case_id: Stable case identifier.
        station_id: Driver station id.
        station_label: Human-readable driver label.
        role: Positive or negative-control label.
        n_obs: Number of aligned observations used.
        mean_raw_cross_mi: Mean raw cross-MI across evaluated horizons.
        mean_conditioned_cross_mi: Mean conditioned cross-MI across horizons.
        mean_directness_ratio: Mean directness ratio across horizons.
        raw_cross_mi_by_horizon: Raw cross-MI keyed by horizon.
        conditioned_cross_mi_by_horizon: Conditioned cross-MI keyed by horizon.
        directness_ratio_by_horizon: Directness ratio keyed by horizon.
        warning_horizons: Horizons where directness exceeded 1.0.
    """

    model_config = ConfigDict(frozen=True)

    case_id: str
    station_id: int
    station_label: str
    role: CausalRiversRole
    n_obs: int
    mean_raw_cross_mi: float
    mean_conditioned_cross_mi: float
    mean_directness_ratio: float
    raw_cross_mi_by_horizon: dict[int, float]
    conditioned_cross_mi_by_horizon: dict[int, float]
    directness_ratio_by_horizon: dict[int, float]
    warning_horizons: list[int] = Field(default_factory=list)


class CausalRiversAnalysisBundle(BaseModel):
    """Serializable bundle emitted by the causal-rivers run script.

    Attributes:
        target_id: Downstream target station id.
        target_label: Human-readable target label.
        resample_freq: Resampling frequency used for analysis.
        horizons: Evaluated forecast horizons.
        target_baseline: Target-only rolling-origin baseline curves.
        pairs: Driver-pair summaries.
    """

    model_config = ConfigDict(frozen=True)

    target_id: int
    target_label: str
    resample_freq: str
    horizons: list[int]
    target_baseline: TargetBaselineCurves
    pairs: list[CausalRiversPairSummary]


def load_causal_rivers_config(path: Path) -> CausalRiversAnalysisConfig:
    """Load the typed causal-rivers analysis configuration.

    Args:
        path: YAML config path.

    Returns:
        Parsed and validated config model.
    """
    payload: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    return CausalRiversAnalysisConfig.model_validate(payload)


def load_resampled_causal_rivers_frame(config: CausalRiversAnalysisConfig) -> pd.DataFrame:
    """Load and resample the East Germany time-series slice.

    Args:
        config: Parsed causal-rivers analysis config.

    Returns:
        Data frame indexed by timestamp with integer station-id columns.
    """
    raw_dir = config.data.raw_dir
    required_paths = [
        raw_dir / config.data.ts_file,
        raw_dir / config.data.graph_file,
        raw_dir / config.data.meta_file,
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise ValueError(f"Missing causal-rivers inputs: {missing}")

    ts_path = raw_dir / config.data.ts_file
    frame = pd.read_csv(ts_path, index_col=0, parse_dates=True)
    resampled = frame.resample(config.data.resample_freq).mean()
    resampled.columns = [int(column) for column in resampled.columns]
    return resampled


def extract_station_series(frame: pd.DataFrame, station_id: int) -> np.ndarray:
    """Extract one station series with bounded forward filling.

    Args:
        frame: Resampled station frame.
        station_id: Station identifier.

    Returns:
        Cleaned float array for the requested station.
    """
    series = _prepare_station_series(frame, station_id).dropna()
    return series.to_numpy(dtype=float)


def extract_aligned_station_pair(
    frame: pd.DataFrame,
    target_station_id: int,
    driver_station_id: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Extract one target-driver pair on shared timestamps.

    Args:
        frame: Resampled station frame.
        target_station_id: Target station identifier.
        driver_station_id: Driver station identifier.

    Returns:
        Target and driver arrays aligned on the same timestamp index.
    """
    aligned = pd.concat(
        [
            _prepare_station_series(frame, target_station_id).rename("target"),
            _prepare_station_series(frame, driver_station_id).rename("driver"),
        ],
        axis=1,
    ).dropna()
    if aligned.empty:
        raise ValueError("target and driver do not share any timestamps after bounded forward fill")
    return (
        aligned["target"].to_numpy(dtype=float),
        aligned["driver"].to_numpy(dtype=float),
    )


def _prepare_station_series(frame: pd.DataFrame, station_id: int) -> pd.Series:
    """Return one station series after bounded forward fill, preserving timestamps."""
    if station_id not in frame.columns:
        raise ValueError(f"Station {station_id} is not present in the resampled frame")

    return frame[station_id].copy().ffill(limit=4)


def evaluate_causal_rivers_pair(
    *,
    config: CausalRiversAnalysisConfig,
    target: np.ndarray,
    driver: np.ndarray,
    station_id: int,
    role: CausalRiversRole,
) -> CausalRiversPairSummary:
    """Evaluate one configured target-driver pair.

    Args:
        config: Parsed causal-rivers analysis config.
        target: Target station series.
        driver: Candidate driver series.
        station_id: Driver station id.
        role: Positive or negative-control label.

    Returns:
        Serializable pair summary with per-horizon diagnostics.
    """
    if target.size != driver.size:
        raise ValueError("target and driver must be aligned to shared timestamps before evaluation")
    if target.size == 0:
        raise ValueError("aligned target-driver pair must contain at least one observation")

    n_obs = target.size
    result = run_exogenous_rolling_origin_evaluation(
        target,
        driver,
        case_id=f"station_{config.station_selection.target_id}_vs_station_{station_id}",
        target_name=f"station_{config.station_selection.target_id}",
        exog_name=f"station_{station_id}",
        horizons=config.rolling_origin.horizons,
        n_origins=config.rolling_origin.n_origins,
        random_state=config.metric.random_state,
        n_surrogates=config.metric.n_surrogates,
        min_pairs_raw=config.metric.min_pairs_raw,
        min_pairs_partial=config.metric.min_pairs_partial,
        analysis_scope=config.analysis_scope,
        project_extension=config.project_extension,
    )
    return CausalRiversPairSummary(
        case_id=result.case_id,
        station_id=station_id,
        station_label=f"station_{station_id}",
        role=role,
        n_obs=n_obs,
        mean_raw_cross_mi=_mean_metric(result.raw_cross_mi_by_horizon),
        mean_conditioned_cross_mi=_mean_metric(result.conditioned_cross_mi_by_horizon),
        mean_directness_ratio=_mean_metric(result.directness_ratio_by_horizon),
        raw_cross_mi_by_horizon=result.raw_cross_mi_by_horizon,
        conditioned_cross_mi_by_horizon=result.conditioned_cross_mi_by_horizon,
        directness_ratio_by_horizon=result.directness_ratio_by_horizon,
        warning_horizons=result.warning_horizons,
    )


def build_pair_summary_table(pairs: list[CausalRiversPairSummary]) -> pd.DataFrame:
    """Build one summary row per evaluated driver.

    Args:
        pairs: Evaluated driver summaries.

    Returns:
        Summary table suitable for CSV export.
    """
    rows = [
        {
            "case_id": pair.case_id,
            "station_id": pair.station_id,
            "station_label": pair.station_label,
            "role": pair.role,
            "n_obs": pair.n_obs,
            "mean_raw_cross_mi": pair.mean_raw_cross_mi,
            "mean_conditioned_cross_mi": pair.mean_conditioned_cross_mi,
            "mean_directness_ratio": pair.mean_directness_ratio,
            "warning_horizon_count": len(pair.warning_horizons),
        }
        for pair in pairs
    ]
    return pd.DataFrame(rows)


def build_pair_horizon_table(pairs: list[CausalRiversPairSummary]) -> pd.DataFrame:
    """Build one row per evaluated driver and horizon.

    Args:
        pairs: Evaluated driver summaries.

    Returns:
        Long-form horizon table suitable for CSV export.
    """
    rows: list[dict[str, str | int | float]] = []
    for pair in pairs:
        for horizon in sorted(pair.raw_cross_mi_by_horizon):
            rows.append(
                {
                    "case_id": pair.case_id,
                    "station_id": pair.station_id,
                    "station_label": pair.station_label,
                    "role": pair.role,
                    "horizon": horizon,
                    "raw_cross_mi": pair.raw_cross_mi_by_horizon[horizon],
                    "conditioned_cross_mi": pair.conditioned_cross_mi_by_horizon[horizon],
                    "directness_ratio": pair.directness_ratio_by_horizon[horizon],
                }
            )
    return pd.DataFrame(rows)


def _mean_metric(values_by_horizon: dict[int, float]) -> float:
    """Return the deterministic mean across per-horizon float values."""
    values = list(values_by_horizon.values())
    if not values:
        return float("nan")
    return float(np.mean(values))
