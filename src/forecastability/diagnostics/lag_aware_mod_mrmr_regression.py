"""Lag-Aware ModMRMR regression fixture generation and verification."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import cast

import numpy as np

from forecastability.services.forecast_prep_export import (
    forecast_prep_contract_to_lag_table,
    forecast_prep_contract_to_markdown,
)
from forecastability.services.lag_aware_mod_mrmr_domain import build_aligned_pair
from forecastability.services.lag_aware_mod_mrmr_scorers import (
    PairwiseDependenceScorer,
    build_scorer,
)
from forecastability.triage.lag_aware_mod_mrmr import (
    BlockedLagAwareFeature,
    LagAwareModMRMRConfig,
    LagAwareModMRMRResult,
    PairwiseScorerSpec,
    RejectedLagAwareFeature,
    SelectedLagAwareFeature,
)
from forecastability.triage.models import (
    AnalysisGoal,
    ReadinessReport,
    ReadinessStatus,
    TriageRequest,
    TriageResult,
)
from forecastability.use_cases.build_forecast_prep_contract import build_forecast_prep_contract
from forecastability.use_cases.lag_aware_mod_mrmr import run_lag_aware_mod_mrmr
from forecastability.utils.types import Diagnostics, InterpretationResult, RoutingRecommendation

_ATOL = 1e-6
_RTOL = 1e-2
_DEFAULT_LENGTH = 240
_PRIMARY_LAG = 4

LAG_AWARE_MOD_MRMR_FIXTURE_CASES: tuple[str, ...] = (
    "known_synthetic_lag_driver",
    "duplicate_sensor_suppression",
    "lag_neighbour_duplicate_suppression",
    "target_history_proxy_suppression",
    "forecast_horizon_legality",
    "known_future_bypass",
    "aggregate_redundancy_vs_maximum",
)


def _raw_spearman_spec() -> PairwiseScorerSpec:
    """Return the deterministic raw Spearman scorer spec used in fixtures."""
    return PairwiseScorerSpec(
        name="spearman_abs",
        backend="scipy",
        normalization="none",
        significance_method="none",
    )


def _make_white_noise(*, n: int, seed: int) -> np.ndarray:
    """Return deterministic white noise."""
    return np.random.default_rng(seed).standard_normal(n)


def _make_ar1(*, n: int, phi: float, seed: int) -> np.ndarray:
    """Return deterministic AR(1) series."""
    rng = np.random.default_rng(seed)
    series = np.zeros(n)
    for index in range(1, n):
        series[index] = phi * series[index - 1] + rng.standard_normal()
    return series


def _lead_covariate(
    series: np.ndarray,
    *,
    lag: int,
    seed: int,
    noise_scale: float = 0.0,
) -> np.ndarray:
    """Return a leading covariate so lag ``k`` aligns with the target."""
    rng = np.random.default_rng(seed)
    head = series[lag:] + noise_scale * rng.standard_normal(series.size - lag)
    tail = rng.standard_normal(lag)
    return np.concatenate([head, tail])


def _routing() -> RoutingRecommendation:
    """Return deterministic routing used by fixture contract payloads."""
    return RoutingRecommendation(
        primary_families=["arima"],
        secondary_families=["linear_state_space"],
        rationale=["deterministic lag-aware regression fixture route"],
        caution_flags=[],
        confidence_label="high",
    )


def _triage_result(*, result: LagAwareModMRMRResult) -> TriageResult:
    """Build a minimal deterministic triage result for contract export."""
    primary_lags = sorted({feature.lag for feature in result.selected})
    if not primary_lags:
        primary_lags = [result.config.forecast_horizon]

    return TriageResult(
        request=TriageRequest(
            series=np.linspace(0.0, 1.0, 120),
            goal=AnalysisGoal.univariate,
            max_lag=24,
            n_surrogates=99,
            random_state=42,
        ),
        readiness=ReadinessReport(status=ReadinessStatus.clear, warnings=[]),
        blocked=False,
        interpretation=InterpretationResult(
            forecastability_class="high" if result.selected else "low",
            directness_class="medium",
            primary_lags=primary_lags,
            modeling_regime="deterministic triage",
            narrative="lag-aware regression fixture narrative",
            diagnostics=Diagnostics(
                peak_ami_first_5=0.25,
                directness_ratio=0.45,
                n_sig_ami=max(len(primary_lags), 1),
                n_sig_pami=max(len(primary_lags) - 1, 0),
                exploitability_mismatch=0,
                best_smape=0.12,
            ),
        ),
    )


def _compact_selected(feature: SelectedLagAwareFeature) -> dict[str, object]:
    """Return a compact selected-feature payload."""
    return {
        "covariate_name": feature.covariate_name,
        "lag": feature.lag,
        "feature_name": feature.feature_name,
        "is_known_future": feature.is_known_future,
        "known_future_provenance": feature.known_future_provenance,
        "selection_rank": feature.selection_rank,
        "relevance": feature.relevance,
        "max_redundancy": feature.max_redundancy,
        "target_history_redundancy": feature.target_history_redundancy,
        "final_score": feature.final_score,
    }


def _compact_rejected(feature: RejectedLagAwareFeature) -> dict[str, object]:
    """Return a compact rejected-feature payload."""
    return {
        "covariate_name": feature.covariate_name,
        "lag": feature.lag,
        "feature_name": feature.feature_name,
        "is_known_future": feature.is_known_future,
        "known_future_provenance": feature.known_future_provenance,
        "relevance": feature.relevance,
        "max_redundancy": feature.max_redundancy,
        "target_history_redundancy": feature.target_history_redundancy,
        "final_score": feature.final_score,
        "rejection_reason": feature.rejection_reason,
    }


def _compact_blocked(feature: BlockedLagAwareFeature) -> dict[str, object]:
    """Return a compact blocked-feature payload."""
    return {
        "covariate_name": feature.covariate_name,
        "lag": feature.lag,
        "feature_name": feature.feature_name,
        "is_known_future": feature.is_known_future,
        "known_future_provenance": feature.known_future_provenance,
        "legality_reason": feature.legality_reason,
        "block_reason": feature.block_reason,
    }


def _result_payload(
    *,
    case_name: str,
    result: LagAwareModMRMRResult,
    include_contract: bool = True,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build the deterministic payload for one regression case."""
    payload: dict[str, object] = {
        "case_name": case_name,
        "config": {
            "forecast_horizon": result.config.forecast_horizon,
            "availability_margin": result.config.availability_margin,
            "candidate_lags": list(result.config.candidate_lags or []),
            "max_selected_features": result.config.max_selected_features,
            "known_future_covariates": dict(result.config.known_future_covariates),
            "target_lags": list(result.config.target_lags or []),
        },
        "selected_feature_names": [feature.feature_name for feature in result.selected],
        "selected": [_compact_selected(feature) for feature in result.selected],
        "rejected": [_compact_rejected(feature) for feature in result.rejected],
        "blocked": [_compact_blocked(feature) for feature in result.blocked],
        "n_candidates_evaluated": result.n_candidates_evaluated,
        "n_candidates_blocked": result.n_candidates_blocked,
        "notes": list(result.notes),
    }

    if include_contract:
        contract = build_forecast_prep_contract(
            _triage_result(result=result),
            horizon=result.config.forecast_horizon,
            lag_aware_result=result,
            routing_recommendation=_routing(),
            add_calendar_features=False,
        )
        contract_obj: object = json.loads(contract.model_dump_json())
        if not isinstance(contract_obj, dict):
            raise TypeError("Expected ForecastPrepContract JSON payload to decode to an object")
        payload["contract"] = cast(dict[str, object], contract_obj)
        payload["lag_table"] = forecast_prep_contract_to_lag_table(contract)
        payload["markdown_length"] = len(forecast_prep_contract_to_markdown(contract))

    if extra is not None:
        payload.update(extra)
    return payload


def _build_known_synthetic_lag_driver_case() -> dict[str, object]:
    """Build fixture for a clean known synthetic lead-lag driver."""
    target = _make_white_noise(n=_DEFAULT_LENGTH, seed=11)
    covariates = {
        "driver_signal": _lead_covariate(target, lag=_PRIMARY_LAG, seed=12, noise_scale=0.01),
        "noise": _make_white_noise(n=_DEFAULT_LENGTH, seed=13),
    }
    config = LagAwareModMRMRConfig(
        forecast_horizon=1,
        availability_margin=0,
        candidate_lags=[2, 4, 6],
        relevance_scorer=_raw_spearman_spec(),
        redundancy_scorer=_raw_spearman_spec(),
        max_selected_features=2,
    )
    result = run_lag_aware_mod_mrmr(target=target, covariates=covariates, config=config)
    return _result_payload(case_name="known_synthetic_lag_driver", result=result)


def _build_duplicate_sensor_suppression_case() -> dict[str, object]:
    """Build fixture for duplicate sensor suppression."""
    target = _make_white_noise(n=_DEFAULT_LENGTH, seed=21)
    sensor = _lead_covariate(target, lag=_PRIMARY_LAG, seed=22, noise_scale=0.01)
    covariates = {
        "sensor_a": sensor,
        "sensor_b": sensor.copy(),
    }
    config = LagAwareModMRMRConfig(
        forecast_horizon=1,
        availability_margin=0,
        candidate_lags=[4],
        relevance_scorer=_raw_spearman_spec(),
        redundancy_scorer=_raw_spearman_spec(),
        max_selected_features=2,
    )
    result = run_lag_aware_mod_mrmr(target=target, covariates=covariates, config=config)
    return _result_payload(case_name="duplicate_sensor_suppression", result=result)


def _build_lag_neighbour_duplicate_suppression_case() -> dict[str, object]:
    """Build fixture for lag-neighbour duplicate suppression."""
    target = _make_ar1(n=260, phi=0.92, seed=31)
    covariates = {
        "sensor_series": _lead_covariate(target, lag=_PRIMARY_LAG, seed=32, noise_scale=0.02),
    }
    config = LagAwareModMRMRConfig(
        forecast_horizon=1,
        availability_margin=0,
        candidate_lags=[4, 5, 6],
        relevance_scorer=_raw_spearman_spec(),
        redundancy_scorer=_raw_spearman_spec(),
        max_selected_features=2,
    )
    result = run_lag_aware_mod_mrmr(target=target, covariates=covariates, config=config)
    return _result_payload(case_name="lag_neighbour_duplicate_suppression", result=result)


def _build_target_history_proxy_suppression_case() -> dict[str, object]:
    """Build fixture for target-history proxy suppression."""
    target = _make_ar1(n=260, phi=0.88, seed=41)
    covariates = {
        "leading_signal": _lead_covariate(target, lag=_PRIMARY_LAG, seed=42, noise_scale=0.02),
        "target_proxy": target.copy(),
    }
    config = LagAwareModMRMRConfig(
        forecast_horizon=1,
        availability_margin=0,
        candidate_lags=[4],
        relevance_scorer=_raw_spearman_spec(),
        redundancy_scorer=_raw_spearman_spec(),
        target_lags=[4],
        target_history_scorer=_raw_spearman_spec(),
        max_selected_features=2,
    )
    result = run_lag_aware_mod_mrmr(target=target, covariates=covariates, config=config)
    return _result_payload(case_name="target_history_proxy_suppression", result=result)


def _build_forecast_horizon_legality_case() -> dict[str, object]:
    """Build fixture for forecast-horizon legality blocking."""
    target = _make_white_noise(n=_DEFAULT_LENGTH, seed=51)
    covariates = {
        "driver_signal": _lead_covariate(target, lag=_PRIMARY_LAG, seed=52, noise_scale=0.01),
    }
    config = LagAwareModMRMRConfig(
        forecast_horizon=3,
        availability_margin=1,
        candidate_lags=[1, 2, 4],
        relevance_scorer=_raw_spearman_spec(),
        redundancy_scorer=_raw_spearman_spec(),
        max_selected_features=1,
    )
    result = run_lag_aware_mod_mrmr(target=target, covariates=covariates, config=config)
    return _result_payload(case_name="forecast_horizon_legality", result=result)


def _build_known_future_bypass_case() -> dict[str, object]:
    """Build fixture for known-future bypass and export preservation."""
    target = _make_white_noise(n=_DEFAULT_LENGTH, seed=61)
    covariates = {
        "calendar_flag": _lead_covariate(target, lag=1, seed=62, noise_scale=0.01),
        "measured_signal": _lead_covariate(target, lag=_PRIMARY_LAG, seed=63, noise_scale=0.01),
    }
    config = LagAwareModMRMRConfig(
        forecast_horizon=4,
        availability_margin=0,
        candidate_lags=[1, 4],
        known_future_covariates={"calendar_flag": "calendar"},
        relevance_scorer=_raw_spearman_spec(),
        redundancy_scorer=_raw_spearman_spec(),
        max_selected_features=2,
    )
    result = run_lag_aware_mod_mrmr(target=target, covariates=covariates, config=config)
    return _result_payload(case_name="known_future_bypass", result=result)


def _build_aggregate_redundancy_vs_maximum_case() -> dict[str, object]:
    """Build fixture comparing aggregate and maximum redundancy penalties."""
    lag = 4
    aligned_len = 192
    rng = np.random.default_rng(71)
    u = rng.standard_normal(aligned_len)
    v = rng.standard_normal(aligned_len)
    w = rng.standard_normal(aligned_len)
    target_aligned = u + 0.25 * v + 0.05 * rng.standard_normal(aligned_len)
    target = np.concatenate([rng.standard_normal(lag), target_aligned])

    covariate_a = np.concatenate([u, rng.standard_normal(lag)])
    covariate_b = np.concatenate([v, rng.standard_normal(lag)])
    duplicate_candidate = np.concatenate([u + 0.02 * w, rng.standard_normal(lag)])
    blend_candidate, blend_weights = _resolve_blend_candidate(
        target=target,
        lag=lag,
        u=u,
        v=v,
        w=w,
    )

    comparison = _redundancy_comparison_payload(
        target=target,
        lag=lag,
        covariate_a=covariate_a,
        covariate_b=covariate_b,
        duplicate_candidate=duplicate_candidate,
        blend_candidate=blend_candidate,
    )
    comparison["blend_weights"] = list(blend_weights)
    return comparison


def _resolve_blend_candidate(
    *,
    target: np.ndarray,
    lag: int,
    u: np.ndarray,
    v: np.ndarray,
    w: np.ndarray,
) -> tuple[np.ndarray, tuple[float, float, float]]:
    """Resolve a deterministic blend candidate with diverging penalty winners."""
    for weight_u in (0.35, 0.45, 0.55, 0.65):
        for weight_v in (0.35, 0.45, 0.55, 0.65):
            for weight_w in (0.55, 0.75, 0.95):
                blend = weight_u * u + weight_v * v + weight_w * w
                candidate = np.concatenate([blend, np.zeros(lag)])
                comparison = _redundancy_comparison_payload(
                    target=target,
                    lag=lag,
                    covariate_a=np.concatenate([u, np.zeros(lag)]),
                    covariate_b=np.concatenate([v, np.zeros(lag)]),
                    duplicate_candidate=np.concatenate([u + 0.02 * w, np.zeros(lag)]),
                    blend_candidate=candidate,
                )
                winners = cast(dict[str, str], comparison["winner_by_penalty"])
                if (
                    winners["maximum_redundancy"] == "blend_candidate"
                    and winners["aggregate_mean_redundancy"] == "duplicate_candidate"
                ):
                    return candidate, (weight_u, weight_v, weight_w)

    raise RuntimeError("Failed to construct deterministic aggregate-vs-maximum comparison")


def _redundancy_comparison_payload(
    *,
    target: np.ndarray,
    lag: int,
    covariate_a: np.ndarray,
    covariate_b: np.ndarray,
    duplicate_candidate: np.ndarray,
    blend_candidate: np.ndarray,
) -> dict[str, object]:
    """Compare duplicate-vs-blend candidates under two redundancy penalties."""
    scorer = build_scorer(_raw_spearman_spec())
    prefix_series = {
        "prefix_a": covariate_a,
        "prefix_b": covariate_b,
    }
    candidate_series = {
        "duplicate_candidate": duplicate_candidate,
        "blend_candidate": blend_candidate,
    }

    candidate_scores: dict[str, dict[str, float]] = {}
    for name, series in candidate_series.items():
        relevance = _score_relevance_series(
            scorer=scorer,
            series=series,
            target=target,
            lag=lag,
        )
        redundancies = {
            prefix_name: _score_redundancy_series(
                scorer=scorer,
                left=series,
                right=prefix_series[prefix_name],
                target=target,
                lag=lag,
            )
            for prefix_name in sorted(prefix_series)
        }
        max_redundancy = max(redundancies.values())
        mean_redundancy = sum(redundancies.values()) / len(redundancies)
        candidate_scores[name] = {
            "relevance": relevance,
            "redundancy_to_prefix_a": redundancies["prefix_a"],
            "redundancy_to_prefix_b": redundancies["prefix_b"],
            "score_maximum_redundancy": relevance * (1.0 - max_redundancy),
            "score_aggregate_mean_redundancy": relevance * (1.0 - mean_redundancy),
        }

    winner_maximum = max(
        candidate_scores,
        key=lambda name: (
            candidate_scores[name]["score_maximum_redundancy"],
            candidate_scores[name]["relevance"],
        ),
    )
    winner_aggregate = max(
        candidate_scores,
        key=lambda name: (
            candidate_scores[name]["score_aggregate_mean_redundancy"],
            candidate_scores[name]["relevance"],
        ),
    )
    return {
        "case_name": "aggregate_redundancy_vs_maximum",
        "comparison_lag": lag,
        "selected_prefix": ["prefix_a", "prefix_b"],
        "candidate_scores": candidate_scores,
        "winner_by_penalty": {
            "maximum_redundancy": winner_maximum,
            "aggregate_mean_redundancy": winner_aggregate,
        },
    }


def _score_relevance_series(
    *,
    scorer: PairwiseDependenceScorer,
    series: np.ndarray,
    target: np.ndarray,
    lag: int,
) -> float:
    """Score one lagged candidate against the aligned target window."""
    z_lagged, y_target = build_aligned_pair(target, series, lag=lag)
    score_obj = scorer.score_pair(z_lagged, y_target, random_state=42)
    return float(score_obj.raw_value)


def _score_redundancy_series(
    *,
    scorer: PairwiseDependenceScorer,
    left: np.ndarray,
    right: np.ndarray,
    target: np.ndarray,
    lag: int,
) -> float:
    """Score redundancy between two lag-aligned candidate series."""
    z_left, _ = build_aligned_pair(target, left, lag=lag)
    z_right, _ = build_aligned_pair(target, right, lag=lag)
    min_len = min(len(z_left), len(z_right))
    score_obj = scorer.score_pair(z_left[:min_len], z_right[:min_len], random_state=42)
    return float(score_obj.raw_value)


def build_lag_aware_mod_mrmr_regression_outputs() -> dict[str, dict[str, object]]:
    """Build deterministic outputs for all lag-aware ModMRMR regression cases."""
    return {
        "known_synthetic_lag_driver": _build_known_synthetic_lag_driver_case(),
        "duplicate_sensor_suppression": _build_duplicate_sensor_suppression_case(),
        "lag_neighbour_duplicate_suppression": _build_lag_neighbour_duplicate_suppression_case(),
        "target_history_proxy_suppression": _build_target_history_proxy_suppression_case(),
        "forecast_horizon_legality": _build_forecast_horizon_legality_case(),
        "known_future_bypass": _build_known_future_bypass_case(),
        "aggregate_redundancy_vs_maximum": _build_aggregate_redundancy_vs_maximum_case(),
    }


def write_lag_aware_mod_mrmr_regression_outputs(*, output_dir: Path) -> list[Path]:
    """Write lag-aware ModMRMR regression outputs to JSON files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = build_lag_aware_mod_mrmr_regression_outputs()
    expected_names = {f"{case_name}.json" for case_name in outputs}
    for stale_path in output_dir.glob("*.json"):
        if stale_path.name not in expected_names:
            stale_path.unlink()

    written: list[Path] = []
    for case_name in sorted(outputs):
        path = output_dir / f"{case_name}.json"
        path.write_text(json.dumps(outputs[case_name], indent=2, sort_keys=True) + "\n")
        written.append(path)
    return written


def _compare_json(actual: object, expected: object, *, field_path: str) -> list[str]:
    """Recursively compare JSON-like values with tolerant float handling."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{field_path}: expected object, got {type(actual).__name__}"]
        errors: list[str] = []
        expected_dict = cast(dict[str, object], expected)
        actual_dict = cast(dict[str, object], actual)
        expected_keys = set(expected_dict)
        actual_keys = set(actual_dict)
        for missing_key in sorted(expected_keys - actual_keys):
            errors.append(f"{field_path}: missing key '{missing_key}'")
        for extra_key in sorted(actual_keys - expected_keys):
            errors.append(f"{field_path}: unexpected key '{extra_key}'")
        for key in sorted(expected_keys & actual_keys):
            errors.extend(
                _compare_json(
                    actual_dict[key],
                    expected_dict[key],
                    field_path=f"{field_path}/{key}",
                )
            )
        return errors

    if isinstance(expected, list):
        if not isinstance(actual, list):
            return [f"{field_path}: expected list, got {type(actual).__name__}"]
        errors: list[str] = []
        expected_list = cast(list[object], expected)
        actual_list = cast(list[object], actual)
        if len(actual_list) != len(expected_list):
            return [
                (
                    f"{field_path}: length mismatch (actual={len(actual_list)}, "
                    f"expected={len(expected_list)})"
                )
            ]
        for index, (actual_item, expected_item) in enumerate(
            zip(actual_list, expected_list, strict=True)
        ):
            errors.extend(
                _compare_json(
                    actual_item,
                    expected_item,
                    field_path=f"{field_path}[{index}]",
                )
            )
        return errors

    if isinstance(expected, bool):
        if actual is not expected:
            return [f"{field_path}: bool mismatch (actual={actual!r}, expected={expected!r})"]
        return []

    if isinstance(expected, int):
        if not isinstance(actual, int) or isinstance(actual, bool):
            return [f"{field_path}: expected int, got {type(actual).__name__}"]
        if actual != expected:
            return [f"{field_path}: int mismatch (actual={actual}, expected={expected})"]
        return []

    if isinstance(expected, float):
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            return [f"{field_path}: expected float, got {type(actual).__name__}"]
        if not math.isclose(float(actual), expected, rel_tol=_RTOL, abs_tol=_ATOL):
            return [
                (
                    f"{field_path}: float mismatch (actual={actual}, "
                    f"expected={expected}, atol={_ATOL}, rtol={_RTOL})"
                )
            ]
        return []

    if actual != expected:
        return [f"{field_path}: mismatch (actual={actual!r}, expected={expected!r})"]
    return []


def verify_lag_aware_mod_mrmr_regression_outputs(
    *,
    actual_dir: Path,
    expected_dir: Path,
) -> None:
    """Verify rebuilt lag-aware ModMRMR outputs against frozen expected fixtures."""
    expected_files = sorted(expected_dir.glob("*.json"))
    if not expected_files:
        raise ValueError(f"No expected JSON files found in {expected_dir}")

    errors: list[str] = []
    expected_names = {path.name for path in expected_files}
    actual_names = {path.name for path in actual_dir.glob("*.json")}
    for unexpected_name in sorted(actual_names - expected_names):
        errors.append(f"Unexpected rebuilt output: {unexpected_name}")

    for expected_path in expected_files:
        actual_path = actual_dir / expected_path.name
        if not actual_path.exists():
            errors.append(f"Missing rebuilt output: {actual_path.name}")
            continue

        expected_payload: object = json.loads(expected_path.read_text())
        actual_payload: object = json.loads(actual_path.read_text())
        errors.extend(
            _compare_json(actual_payload, expected_payload, field_path=expected_path.stem)
        )

    if errors:
        error_block = "\n".join(f"- {line}" for line in errors)
        raise ValueError(f"Lag-aware ModMRMR regression verification failed:\n{error_block}")
