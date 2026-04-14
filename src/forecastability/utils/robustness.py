"""pAMI robustness study: backend comparison and sample-size stress tests."""

from __future__ import annotations

import logging

import numpy as np
from scipy.stats import spearmanr

from forecastability.pipeline.pipeline import run_canonical_example
from forecastability.utils.aggregation import summarize_canonical_result
from forecastability.utils.config import RobustnessStudyConfig
from forecastability.utils.types import (
    BackendComparisonEntry,
    BackendComparisonResult,
    RobustnessStudyResult,
    SampleSizeStressEntry,
    SampleSizeStressResult,
)

_logger = logging.getLogger(__name__)


def _adaptive_lag_caps(
    n: int,
    *,
    max_lag_ami: int,
    max_lag_pami: int,
) -> tuple[int, int]:
    """Compute safe lag caps given series length."""
    return min(max_lag_ami, n - 31), min(max_lag_pami, n - 51)


def _build_entry(
    *,
    series_name: str,
    ts: np.ndarray,
    backend: str,
    max_lag_ami: int,
    max_lag_pami: int,
    n_neighbors: int,
    n_surrogates: int,
    alpha: float,
    random_state: int,
    skip_bands: bool,
) -> BackendComparisonEntry:
    """Run one backend and return a comparison entry."""
    result = run_canonical_example(
        series_name,
        ts,
        max_lag_ami=max_lag_ami,
        max_lag_pami=max_lag_pami,
        n_neighbors=n_neighbors,
        n_surrogates=n_surrogates,
        alpha=alpha,
        random_state=random_state,
        pami_backend=backend,
        skip_bands=skip_bands,
    )
    summary = summarize_canonical_result(result)
    warning = summary.directness_ratio > 1.0
    return BackendComparisonEntry(
        backend=backend,
        n_sig_ami=summary.n_sig_ami,
        n_sig_pami=summary.n_sig_pami,
        directness_ratio=summary.directness_ratio,
        auc_ami=summary.auc_ami,
        auc_pami=summary.auc_pami,
        pami_values=result.pami.values.tolist(),
        directness_ratio_warning=warning,
    )


def run_backend_comparison(
    *,
    series_name: str,
    ts: np.ndarray,
    max_lag_ami: int,
    max_lag_pami: int,
    backends: list[str],
    n_neighbors: int,
    n_surrogates: int,
    alpha: float,
    random_state: int,
    rank_stability_threshold: float = 0.8,
    directness_stability_threshold: float = 0.15,
) -> BackendComparisonResult:
    """Compare pAMI across backends for one series.

    Args:
        series_name: Identifier for the series.
        ts: Univariate time series values.
        max_lag_ami: Maximum lag for AMI curves.
        max_lag_pami: Maximum lag for pAMI curves.
        backends: List of pAMI backend names to compare.
        n_neighbors: Number of neighbors for kNN MI estimation.
        n_surrogates: Number of surrogates for significance estimation.
        alpha: Significance level.
        random_state: Seed for deterministic execution.
        rank_stability_threshold: Minimum Spearman rho for lag ranking stability.
        directness_stability_threshold: Maximum directness_ratio range for stability.

    Returns:
        BackendComparisonResult with entries per backend and stability flags.
    """
    safe_ami, safe_pami = _adaptive_lag_caps(
        len(ts), max_lag_ami=max_lag_ami, max_lag_pami=max_lag_pami
    )
    entries = [
        _build_entry(
            series_name=series_name,
            ts=ts,
            backend=b,
            max_lag_ami=safe_ami,
            max_lag_pami=safe_pami,
            n_neighbors=n_neighbors,
            n_surrogates=n_surrogates,
            alpha=alpha,
            random_state=random_state,
            skip_bands=True,
        )
        for b in backends
    ]
    return _assemble_backend_result(
        series_name=series_name,
        entries=entries,
        rank_stability_threshold=rank_stability_threshold,
        directness_stability_threshold=directness_stability_threshold,
    )


def _assemble_backend_result(
    *,
    series_name: str,
    entries: list[BackendComparisonEntry],
    rank_stability_threshold: float = 0.8,
    directness_stability_threshold: float = 0.15,
) -> BackendComparisonResult:
    """Compute stability flags from backend entries."""
    enriched_entries, has_linear_baseline = _attach_linear_baseline_deltas(entries)
    warnings: list[str] = []
    if not has_linear_baseline:
        warnings.append(
            f"{series_name}: linear_residual baseline missing; delta_vs_linear fields are null"
        )
    for e in enriched_entries:
        if e.directness_ratio_warning:
            warnings.append(
                f"{series_name}/{e.backend}: directness_ratio={e.directness_ratio:.3f} > 1.0"
            )

    pami_arrays = [np.asarray(e.pami_values) for e in enriched_entries]
    min_len = min(a.size for a in pami_arrays)
    trimmed = [a[:min_len] for a in pami_arrays]

    rank_corr = _pairwise_rank_correlation(trimmed)
    dr_values = [e.directness_ratio for e in enriched_entries]
    dr_range = max(dr_values) - min(dr_values)

    return BackendComparisonResult(
        series_name=series_name,
        entries=enriched_entries,
        rank_correlation=rank_corr,
        directness_ratio_range=dr_range,
        lag_ranking_stable=rank_corr >= rank_stability_threshold,
        directness_ratio_stable=dr_range < directness_stability_threshold,
        warnings=warnings,
    )


def _attach_linear_baseline_deltas(
    entries: list[BackendComparisonEntry],
) -> tuple[list[BackendComparisonEntry], bool]:
    """Attach per-backend deltas against the linear residual baseline."""
    baseline = next((entry for entry in entries if entry.backend == "linear_residual"), None)
    if baseline is None:
        return entries, False

    enriched: list[BackendComparisonEntry] = []
    for entry in entries:
        enriched.append(
            entry.model_copy(
                update={
                    "auc_pami_delta_vs_linear": float(entry.auc_pami - baseline.auc_pami),
                    "directness_ratio_delta_vs_linear": float(
                        entry.directness_ratio - baseline.directness_ratio
                    ),
                    "n_sig_pami_delta_vs_linear": int(entry.n_sig_pami - baseline.n_sig_pami),
                }
            )
        )
    return enriched, True


def _pairwise_rank_correlation(arrays: list[np.ndarray]) -> float:
    """Mean pairwise Spearman correlation across arrays."""
    if len(arrays) < 2:
        return 1.0
    correlations: list[float] = []
    for i in range(len(arrays)):
        for j in range(i + 1, len(arrays)):
            if np.std(arrays[i]) == 0.0 or np.std(arrays[j]) == 0.0:
                correlations.append(0.0)
                continue
            rho, _ = spearmanr(arrays[i], arrays[j])
            correlations.append(float(np.nan_to_num(rho, nan=0.0)))
    return float(np.mean(correlations))


def run_sample_size_stress(
    *,
    series_name: str,
    ts: np.ndarray,
    fractions: list[float],
    max_lag_ami: int,
    max_lag_pami: int,
    n_neighbors: int,
    n_surrogates: int,
    alpha: float,
    random_state: int,
    min_series_length: int = 100,
    directness_stability_threshold: float = 0.15,
) -> SampleSizeStressResult:
    """Test pAMI stability under sample-size reduction.

    Args:
        series_name: Identifier for the series.
        ts: Univariate time series values.
        fractions: Fractions of series length to test.
        max_lag_ami: Maximum lag for AMI curves.
        max_lag_pami: Maximum lag for pAMI curves.
        n_neighbors: Number of neighbors for kNN MI estimation.
        n_surrogates: Number of surrogates for significance estimation.
        alpha: Significance level.
        random_state: Seed for deterministic execution.
        min_series_length: Minimum length to include a fraction.
        directness_stability_threshold: Maximum directness_ratio range for stability.

    Returns:
        SampleSizeStressResult with entries per fraction and stability flags.
    """
    entries: list[SampleSizeStressEntry] = []
    warnings: list[str] = []
    n_full = len(ts)

    for frac in sorted(fractions):
        n_obs = int(n_full * frac)
        if n_obs < min_series_length:
            warnings.append(
                f"{series_name}: fraction={frac} gives n={n_obs} < {min_series_length}, skipped"
            )
            continue
        entry = _stress_entry(
            series_name=series_name,
            ts=ts[:n_obs],
            fraction=frac,
            max_lag_ami=max_lag_ami,
            max_lag_pami=max_lag_pami,
            n_neighbors=n_neighbors,
            n_surrogates=n_surrogates,
            alpha=alpha,
            random_state=random_state,
            skip_bands=(frac < 1.0),
        )
        entries.append(entry)

    dr_stable = _directness_ratios_stable(entries, threshold=directness_stability_threshold)
    return SampleSizeStressResult(
        series_name=series_name,
        entries=entries,
        directness_ratio_stable=dr_stable,
        warnings=warnings,
    )


def _stress_entry(
    *,
    series_name: str,
    ts: np.ndarray,
    fraction: float,
    max_lag_ami: int,
    max_lag_pami: int,
    n_neighbors: int,
    n_surrogates: int,
    alpha: float,
    random_state: int,
    skip_bands: bool,
) -> SampleSizeStressEntry:
    """Build a single stress-test entry."""
    safe_ami, safe_pami = _adaptive_lag_caps(
        len(ts), max_lag_ami=max_lag_ami, max_lag_pami=max_lag_pami
    )
    result = run_canonical_example(
        series_name,
        ts,
        max_lag_ami=safe_ami,
        max_lag_pami=safe_pami,
        n_neighbors=n_neighbors,
        n_surrogates=n_surrogates,
        alpha=alpha,
        random_state=random_state,
        skip_bands=skip_bands,
    )
    summary = summarize_canonical_result(result)
    warning = summary.directness_ratio > 1.0
    return SampleSizeStressEntry(
        fraction=fraction,
        n_observations=len(ts),
        directness_ratio=summary.directness_ratio,
        auc_ami=summary.auc_ami,
        auc_pami=summary.auc_pami,
        n_sig_ami=summary.n_sig_ami,
        n_sig_pami=summary.n_sig_pami,
        directness_ratio_warning=warning,
    )


def _directness_ratios_stable(
    entries: list[SampleSizeStressEntry],
    *,
    threshold: float = 0.15,
) -> bool:
    """Check whether directness ratios are stable across entries."""
    if len(entries) < 2:
        return True
    dr_values = [e.directness_ratio for e in entries]
    return (max(dr_values) - min(dr_values)) < threshold


def run_robustness_study(
    datasets: list[tuple[str, np.ndarray]],
    *,
    config: RobustnessStudyConfig,
) -> RobustnessStudyResult:
    """Run the full robustness study across all datasets.

    Args:
        datasets: List of (series_name, time_series_array) tuples.
        config: Study configuration.

    Returns:
        RobustnessStudyResult with backend comparisons, stress tests,
        exclusions, overall stability verdict, and narrative summary.
    """
    backend_results: list[BackendComparisonResult] = []
    stress_results: list[SampleSizeStressResult] = []
    excluded: list[str] = []

    for name, ts in datasets:
        if len(ts) < config.min_series_length:
            excluded.append(name)
            _logger.info("Excluding %s: length %d < %d", name, len(ts), config.min_series_length)
            continue

        bc = run_backend_comparison(
            series_name=name,
            ts=ts,
            max_lag_ami=config.max_lag_ami,
            max_lag_pami=config.max_lag_pami,
            backends=config.backends,
            n_neighbors=config.n_neighbors,
            n_surrogates=config.n_surrogates,
            alpha=config.alpha,
            random_state=config.random_state,
            rank_stability_threshold=config.rank_stability_threshold,
            directness_stability_threshold=config.directness_stability_threshold,
        )
        backend_results.append(bc)

        ss = run_sample_size_stress(
            series_name=name,
            ts=ts,
            fractions=config.sample_fractions,
            max_lag_ami=config.max_lag_ami,
            max_lag_pami=config.max_lag_pami,
            n_neighbors=config.n_neighbors,
            n_surrogates=config.n_surrogates,
            alpha=config.alpha,
            random_state=config.random_state,
            min_series_length=config.min_series_length,
            directness_stability_threshold=config.directness_stability_threshold,
        )
        stress_results.append(ss)

    overall = _compute_overall_stability(backend_results, stress_results)
    narrative = _build_narrative(backend_results, stress_results, excluded)

    return RobustnessStudyResult(
        backend_comparisons=backend_results,
        sample_size_tests=stress_results,
        excluded_series=excluded,
        overall_stable=overall,
        summary_narrative=narrative,
    )


def _compute_overall_stability(
    backend_results: list[BackendComparisonResult],
    stress_results: list[SampleSizeStressResult],
) -> bool:
    """All series must pass both backend and stress stability checks."""
    if not backend_results:
        return True
    bc_ok = all(r.lag_ranking_stable and r.directness_ratio_stable for r in backend_results)
    ss_ok = all(r.directness_ratio_stable for r in stress_results)
    return bc_ok and ss_ok


def _build_narrative(
    backend_results: list[BackendComparisonResult],
    stress_results: list[SampleSizeStressResult],
    excluded: list[str],
) -> str:
    """Build a human-readable summary narrative."""
    n_bc = len(backend_results)
    n_bc_stable = sum(
        1 for r in backend_results if r.lag_ranking_stable and r.directness_ratio_stable
    )
    n_ss = len(stress_results)
    n_ss_stable = sum(1 for r in stress_results if r.directness_ratio_stable)

    parts = [
        f"Backend comparison: {n_bc_stable}/{n_bc} series stable.",
        f"Sample-size stress: {n_ss_stable}/{n_ss} series stable.",
    ]
    if excluded:
        parts.append(f"Excluded series (too short): {', '.join(excluded)}.")

    warn_series = [r.series_name for r in backend_results if r.warnings]
    if warn_series:
        parts.append(
            f"directness_ratio > 1.0 warnings in: {', '.join(warn_series)}. "
            "This is a numerical artifact, not a scientific conclusion."
        )
    return " ".join(parts)
