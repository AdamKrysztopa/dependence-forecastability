"""AMI Information Geometry service for v0.3.1.

This module is the deterministic geometry engine that sits beneath the
forecastability fingerprint and routing layers. It owns:

* horizon-wise KSG-II AMI estimation,
* shuffle-surrogate bias correction,
* corrected profile and threshold semantics,
* geometry-derived information horizon and structure classification.

No plotting, file I/O, agent orchestration, or routing logic belongs here.
"""

from __future__ import annotations

import math

import numpy as np
from joblib import Parallel, delayed
from pydantic import BaseModel, ConfigDict, Field, field_validator
from scipy.special import digamma
from sklearn.neighbors import NearestNeighbors

from forecastability.utils.types import (
    AmiGeometryCurvePoint,
    AmiInformationGeometry,
    FingerprintStructure,
)
from forecastability.utils.validation import validate_time_series

_INSUFFICIENT_PAIRS_CAUTION = "insufficient_pairs_for_ksg2"
_GEOMETRY_METHOD = "ksg2_shuffle_surrogate"
_CLASSIFIER_TIEBREAK_METADATA = "classifier_used_tiebreak"
_GEOMETRY_BORDERLINE_METADATA = "geometry_threshold_borderline"
_DEFAULT_BORDERLINE_MARGIN = 0.01


class AmiInformationGeometryConfig(BaseModel):
    """Versioned threshold and estimator settings for geometry semantics."""

    model_config = ConfigDict(frozen=True)

    k_list: tuple[int, ...] = (3, 5, 8)
    n_surrogates: int = Field(default=200, ge=99)
    max_lag_frac: float = Field(default=0.33, gt=0.0, le=1.0)
    max_horizon: int | None = Field(default=None, ge=1)
    min_n: int = Field(default=80, ge=16)
    peak_prominence_abs: float = Field(default=0.10, ge=0.0)
    peak_spacing: int = Field(default=2, ge=1)
    signal_to_noise_none_threshold: float = Field(default=0.05, ge=0.0, le=1.0)
    horizon_multiplier_threshold: float = Field(default=3.0, gt=0.0)
    epsilon: float = Field(default=1e-8, gt=0.0)
    jitter_scale: float = Field(default=1e-7, gt=0.0)
    n_jobs: int = 1

    @field_validator("k_list")
    @classmethod
    def _validate_k_list(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        """Require a non-empty, positive, strictly increasing k-list."""
        if not value:
            raise ValueError("k_list must not be empty")
        if any(k <= 0 for k in value):
            raise ValueError("k_list entries must be positive")
        if tuple(sorted(set(value))) != value:
            raise ValueError("k_list must be strictly increasing without duplicates")
        return value


def _resolve_max_horizon(n: int, config: AmiInformationGeometryConfig) -> int:
    """Resolve evaluated horizon count.

    Explicit ``max_horizon`` takes precedence and is treated as a hard cap.
    ``max_lag_frac`` is only applied when ``max_horizon`` is not provided.

    PBE-F07: the resolved horizon is also capped by the largest horizon ``h``
    for which ``n - h >= _guard_pairs_required(config)``. Beyond that cap the
    per-horizon ``n_pairs < min_pairs`` guard inside ``_compute_raw_profile``
    would skip every entry while still paying the full surrogate cost. To
    avoid surfacing an empty curve when even the first horizon is infeasible,
    the cap is floored at ``1`` and the per-horizon guard remains in place
    defensively.
    """
    if config.max_horizon is not None:
        resolved = min(config.max_horizon, n - 1)
    else:
        frac_horizon = max(1, int(math.floor(n * config.max_lag_frac)))
        resolved = min(frac_horizon, n - 1)
    max_feasible = n - _guard_pairs_required(config)
    if max_feasible < 1:
        return max(1, resolved)
    return min(resolved, max_feasible)


def _guard_pairs_required(config: AmiInformationGeometryConfig) -> int:
    """Return the minimum pair count required for stable KSG-II estimation."""
    return 5 * max(config.k_list)


def _apply_one_shot_jitter(
    series: np.ndarray,
    *,
    jitter_scale: float,
    random_state: int,
) -> np.ndarray:
    """Apply the release-aligned one-shot tiny jitter used for tie handling."""
    rng = np.random.default_rng(random_state)
    std = float(np.std(series))
    scale = max(std * jitter_scale, jitter_scale)
    return series + rng.normal(0.0, scale, size=series.size)


def _ksg2_single_k(
    x: np.ndarray,
    y: np.ndarray,
    *,
    k: int,
    neighbor_indices: np.ndarray,
    x_sorted: np.ndarray,
    y_sorted: np.ndarray,
) -> float:
    """Compute the KSG-II mutual-information estimate for one k value."""
    eps_x = np.max(np.abs(x[neighbor_indices] - x[:, None]), axis=1)
    eps_y = np.max(np.abs(y[neighbor_indices] - y[:, None]), axis=1)

    nx = (
        np.searchsorted(x_sorted, x + eps_x, side="right")
        - np.searchsorted(x_sorted, x - eps_x, side="left")
        - 1
    )
    ny = (
        np.searchsorted(y_sorted, y + eps_y, side="right")
        - np.searchsorted(y_sorted, y - eps_y, side="left")
        - 1
    )
    return float(digamma(k) - 1.0 / k + digamma(len(x)) - np.mean(digamma(nx) + digamma(ny)))


def _ksg2_median_profile_value(
    x: np.ndarray,
    y: np.ndarray,
    *,
    config: AmiInformationGeometryConfig,
) -> float:
    """Estimate one horizon's raw AMI via KSG-II and median aggregation over k_list."""
    xy = np.column_stack((x, y))
    k_max = max(config.k_list)
    neighbors = NearestNeighbors(n_neighbors=k_max + 1, metric="chebyshev")
    neighbors.fit(xy)
    _, indices = neighbors.kneighbors(xy)

    x_sorted = np.sort(x)
    y_sorted = np.sort(y)
    values = [
        _ksg2_single_k(
            x,
            y,
            k=k,
            neighbor_indices=indices[:, 1 : k + 1],
            x_sorted=x_sorted,
            y_sorted=y_sorted,
        )
        for k in config.k_list
    ]
    return float(np.median(values))


def _compute_raw_profile(
    series: np.ndarray,
    *,
    max_horizon: int,
    config: AmiInformationGeometryConfig,
    random_state: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute the raw KSG-II AMI profile and the valid-horizon mask."""
    jittered = _apply_one_shot_jitter(
        series,
        jitter_scale=config.jitter_scale,
        random_state=random_state,
    )
    raw = np.full(max_horizon, np.nan, dtype=float)
    valid_mask = np.zeros(max_horizon, dtype=bool)
    min_pairs = _guard_pairs_required(config)

    for zero_based_horizon in range(max_horizon):
        horizon = zero_based_horizon + 1
        n_pairs = jittered.size - horizon
        if n_pairs < min_pairs:
            continue
        raw[zero_based_horizon] = _ksg2_median_profile_value(
            jittered[:n_pairs],
            jittered[horizon:],
            config=config,
        )
        valid_mask[zero_based_horizon] = True

    return raw, valid_mask


def _shuffle_profile(
    series: np.ndarray,
    *,
    max_horizon: int,
    config: AmiInformationGeometryConfig,
    random_state: int,
) -> np.ndarray:
    """Compute one shuffle-surrogate raw profile."""
    rng = np.random.default_rng(random_state)
    shuffled = rng.permutation(series)
    raw, _ = _compute_raw_profile(
        shuffled,
        max_horizon=max_horizon,
        config=config,
        random_state=random_state + 1,
    )
    return raw


def _compute_shuffle_matrix(
    series: np.ndarray,
    *,
    max_horizon: int,
    config: AmiInformationGeometryConfig,
    random_state: int,
) -> np.ndarray:
    """Compute the matrix of shuffle-surrogate raw profiles."""
    seed_sequence = np.random.SeedSequence(random_state)
    seeds = [int(child.generate_state(1)[0]) for child in seed_sequence.spawn(config.n_surrogates)]

    if config.n_jobs == 1:
        rows = [
            _shuffle_profile(
                series,
                max_horizon=max_horizon,
                config=config,
                random_state=seed,
            )
            for seed in seeds
        ]
    else:
        rows = Parallel(n_jobs=config.n_jobs)(
            delayed(_shuffle_profile)(
                series,
                max_horizon=max_horizon,
                config=config,
                random_state=seed,
            )
            for seed in seeds
        )
    return np.vstack(rows)


def _stable_spacing(
    peaks: list[int],
    *,
    spacing_tolerance: int,
) -> bool:
    """Return True when inter-peak spacings cluster around one dominant spacing."""
    if len(peaks) < 2:
        return False
    spacings = np.diff(peaks)
    dominant_spacing = float(np.median(spacings))
    return bool(np.all(np.abs(spacings - dominant_spacing) <= spacing_tolerance))


def _periodic_shift_match(
    corrected: np.ndarray,
    accepted: np.ndarray,
    *,
    min_period: int,
    correlation_threshold: float = 0.60,
) -> bool:
    """Detect repeated accepted structure when local-peak spacing is too brittle.

    This fallback is aimed at seasonal profiles where the first short-memory peak
    distorts the spacing sequence, but a later accepted segment still repeats at
    a materially non-trivial lag.
    """
    if corrected.size < 2 * min_period or min_period <= 0:
        return False

    candidate_horizon = int(np.argmax(corrected[1:]) + 2)
    if candidate_horizon < min_period or candidate_horizon >= corrected.size:
        return False

    head = corrected[:-candidate_horizon]
    tail = corrected[candidate_horizon:]
    mask = accepted[:-candidate_horizon] & accepted[candidate_horizon:]
    if int(np.sum(mask)) < 4:
        return False

    head = head[mask]
    tail = tail[mask]
    if np.allclose(head, head[0]) or np.allclose(tail, tail[0]):
        return False

    return bool(np.corrcoef(head, tail)[0, 1] >= correlation_threshold)


def _extract_peak_candidates(
    corrected: np.ndarray,
    accepted: np.ndarray,
    *,
    prominence_abs: float,
    peak_spacing: int,
) -> list[int]:
    """Return accepted local-maximum horizon indices for structure classification."""
    n = corrected.size
    if n == 0:
        return []

    candidates: list[int] = []
    if n >= 2 and accepted[0] and corrected[0] > corrected[1]:
        if corrected[0] - corrected[1] >= prominence_abs:
            candidates.append(0)

    for idx in range(1, n - 1):
        if not accepted[idx]:
            continue
        left = corrected[idx - 1]
        center = corrected[idx]
        right = corrected[idx + 1]
        prominence = center - max(left, right)
        if center > left and center > right and prominence >= prominence_abs:
            candidates.append(idx)

    merged: list[int] = []
    for idx in candidates:
        if not merged:
            merged.append(idx)
            continue
        if idx - merged[-1] >= peak_spacing:
            merged.append(idx)
            continue
        if corrected[idx] > corrected[merged[-1]]:
            merged[-1] = idx
    return merged


def _classify_information_structure(
    corrected: np.ndarray,
    accepted: np.ndarray,
    *,
    signal_to_noise: float,
    information_horizon: int,
    config: AmiInformationGeometryConfig,
) -> tuple[FingerprintStructure, bool]:
    """Classify the corrected AMI profile into the public fingerprint taxonomy."""
    if (
        signal_to_noise < config.signal_to_noise_none_threshold
        or information_horizon == 0
        or not np.any(accepted)
    ):
        return "none", False

    peaks = _extract_peak_candidates(
        corrected,
        accepted,
        prominence_abs=config.peak_prominence_abs,
        peak_spacing=config.peak_spacing,
    )
    if len(peaks) >= 2 and _stable_spacing(peaks, spacing_tolerance=config.peak_spacing):
        return "periodic", False
    if _periodic_shift_match(
        corrected,
        accepted,
        min_period=max(6, 2 * config.peak_spacing + 1),
    ):
        return "periodic", True

    accepted_horizons = np.flatnonzero(accepted)
    early_peak_cutoff = max(4, int(math.ceil(accepted_horizons.size / 4)))
    if not peaks:
        return "monotonic", False
    if len(peaks) == 1 and (peaks[0] + 1) <= early_peak_cutoff:
        return "monotonic", True
    return "mixed", False


def compute_ami_information_geometry(
    series: np.ndarray,
    *,
    config: AmiInformationGeometryConfig | None = None,
    random_state: int = 42,
) -> AmiInformationGeometry:
    """Compute the deterministic AMI Information Geometry outputs for one series."""
    resolved_config = config if config is not None else AmiInformationGeometryConfig()
    values = validate_time_series(series, min_length=resolved_config.min_n)

    max_horizon = _resolve_max_horizon(values.size, resolved_config)
    raw, valid_mask = _compute_raw_profile(
        values,
        max_horizon=max_horizon,
        config=resolved_config,
        random_state=random_state,
    )
    shuffle_matrix = _compute_shuffle_matrix(
        values,
        max_horizon=max_horizon,
        config=resolved_config,
        random_state=random_state,
    )

    bias = np.nanmean(shuffle_matrix, axis=0)
    tau = np.nanpercentile(shuffle_matrix, 90.0, axis=0)
    corrected = np.where(valid_mask, np.maximum(raw - bias, 0.0), np.nan)
    accepted = (
        valid_mask
        & np.isfinite(corrected)
        & np.isfinite(tau)
        & (corrected > resolved_config.horizon_multiplier_threshold * tau)
    )

    signal_numerator = np.nansum(np.maximum(corrected - tau, 0.0))
    signal_denominator = np.nansum(corrected)
    if signal_denominator <= resolved_config.epsilon:
        signal_to_noise = 0.0
    else:
        signal_to_noise = float(
            np.clip(signal_numerator / (signal_denominator + resolved_config.epsilon), 0.0, 1.0)
        )

    informative_horizons = [int(idx + 1) for idx in np.flatnonzero(accepted)]
    information_horizon = max(informative_horizons, default=0)
    information_structure, used_tiebreak = _classify_information_structure(
        np.nan_to_num(corrected, nan=0.0),
        accepted,
        signal_to_noise=signal_to_noise,
        information_horizon=information_horizon,
        config=resolved_config,
    )

    threshold_profile = resolved_config.horizon_multiplier_threshold * tau
    geometry_threshold_borderline = int(
        bool(
            np.any(
                valid_mask
                & np.isfinite(corrected)
                & np.isfinite(threshold_profile)
                & (np.abs(corrected - threshold_profile) <= _DEFAULT_BORDERLINE_MARGIN)
            )
        )
    )

    curve: list[AmiGeometryCurvePoint] = []
    for zero_based_horizon in range(max_horizon):
        horizon = zero_based_horizon + 1
        if not valid_mask[zero_based_horizon]:
            curve.append(
                AmiGeometryCurvePoint(
                    horizon=horizon,
                    valid=False,
                    accepted=False,
                    caution=_INSUFFICIENT_PAIRS_CAUTION,
                )
            )
            continue
        curve.append(
            AmiGeometryCurvePoint(
                horizon=horizon,
                ami_raw=float(raw[zero_based_horizon]),
                ami_bias=float(bias[zero_based_horizon]),
                ami_corrected=float(corrected[zero_based_horizon]),
                tau=float(tau[zero_based_horizon]),
                accepted=bool(accepted[zero_based_horizon]),
                valid=True,
                caution=None,
            )
        )

    return AmiInformationGeometry(
        method=_GEOMETRY_METHOD,
        signal_to_noise=signal_to_noise,
        information_horizon=information_horizon,
        information_structure=information_structure,
        informative_horizons=informative_horizons,
        curve=curve,
        metadata={
            "n_observations": int(values.size),
            "max_horizon": int(max_horizon),
            "n_surrogates": int(resolved_config.n_surrogates),
            "k_list": ",".join(str(item) for item in resolved_config.k_list),
            "random_state": int(random_state),
            _CLASSIFIER_TIEBREAK_METADATA: int(used_tiebreak),
            _GEOMETRY_BORDERLINE_METADATA: geometry_threshold_borderline,
        },
    )
