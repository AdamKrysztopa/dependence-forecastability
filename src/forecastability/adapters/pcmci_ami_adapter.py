"""PCMCI-AMI-Hybrid adapter for causal discovery (V3-F04).

Uses AMI as Phase 0 informational triage to prune weak
(source, lag) candidates before running PCMCI+ on the survivors.
This narrows the candidate set but does not claim a general power gain.

Wraps the optional ``tigramite`` dependency behind the hexagonal
``CausalGraphPort`` contract and maps output to ``CausalGraphResult``.
"""

from __future__ import annotations

import importlib
from typing import Literal

import joblib
import numpy as np

from forecastability.adapters._tigramite_shared import (
    _DIRECTED_LINKS,
    _check_tigramite_available,
)
from forecastability.diagnostics.cmi import compute_conditional_mi_with_backend
from forecastability.utils.types import (
    CausalGraphResult,
    PcmciAmiResult,
    Phase0MiScore,
)

_DEFAULT_THRESHOLD_MULTIPLIER = 0.1
_DEFAULT_THRESHOLD_FLOOR = 0.001


def _compute_auto_threshold(mi_values: list[float]) -> float:
    """Derive a noise-floor threshold from observed MI scores.

    Strategy: ``max(median(scores) * 0.1, 0.001)``.

    This is a data-adaptive heuristic, not a permutation-calibrated threshold.
    The median is driven up by true-signal pairs, so the threshold is only
    meaningful when the majority of candidates have non-negligible MI.
    For small n or sparse causal graphs, the threshold can sit at the KSG
    noise floor (~0.001–0.005 nats at n≈1000, k=8) and will be
    effectively non-selective. Pass an explicit ``ami_threshold`` to
    override when permutation calibration is required.

    Args:
        mi_values: All unconditional MI scores from Phase 0.

    Returns:
        Threshold below which pairs are pruned.
    """
    if not mi_values:
        return _DEFAULT_THRESHOLD_FLOOR
    median_mi = float(np.median(mi_values))
    return max(median_mi * _DEFAULT_THRESHOLD_MULTIPLIER, _DEFAULT_THRESHOLD_FLOOR)


def _compute_single_triplet(
    data: np.ndarray,
    target_idx: int,
    source_idx: int,
    lag: int,
    var_names: list[str],
    *,
    n_timesteps: int,
    min_pairs: int,
    n_neighbors: int,
    random_state: int,
) -> Phase0MiScore | None:
    """Compute MI for a single (target, source, lag) triplet.

    Args:
        data: 2-D array (n_timesteps, n_variables).
        target_idx: Column index of the target variable.
        source_idx: Column index of the source variable.
        lag: Lag to evaluate (>= 1).
        var_names: Variable names matching columns of *data*.
        n_timesteps: Total number of timesteps in *data*.
        min_pairs: Minimum aligned pairs required for MI estimation.
        n_neighbors: kNN neighbor count for MI estimation.
        random_state: Deterministic random seed.

    Returns:
        ``Phase0MiScore`` if enough aligned pairs exist, else ``None``.
    """
    effective_len = n_timesteps - lag
    if effective_len < min_pairs:
        return None
    past = data[:effective_len, source_idx]
    future = data[lag : lag + effective_len, target_idx]
    mi = compute_conditional_mi_with_backend(
        past,
        future,
        conditioning=None,
        n_neighbors=n_neighbors,
        min_pairs=min_pairs,
        random_state=random_state,
    )
    return Phase0MiScore(
        source=var_names[source_idx],
        lag=lag,
        target=var_names[target_idx],
        mi_value=mi,
    )


def _run_phase0(
    data: np.ndarray,
    var_names: list[str],
    *,
    max_lag: int,
    n_neighbors: int,
    min_pairs: int,
    random_state: int,
    ami_threshold: float | None,
    n_jobs: int = 1,
) -> tuple[list[Phase0MiScore], float, int, int]:
    """Phase 0: compute unconditional MI for every (source, lag, target) triplet.

    Args:
        data: 2-D array (n_timesteps, n_variables).
        var_names: Variable names matching columns of *data*.
        max_lag: Maximum lag to consider.
        n_neighbors: kNN neighbor count for MI estimation.
        min_pairs: Minimum aligned pairs for MI estimation.
        random_state: Deterministic random seed.
        ami_threshold: If ``None``, auto-compute from noise floor.
        n_jobs: Number of parallel workers (1 = sequential).

    Returns:
        Tuple of (kept scores, threshold, pruned count, kept count).
    """
    n_vars = len(var_names)
    n_timesteps = data.shape[0]

    triplets = [
        (target_idx, source_idx, lag)
        for target_idx in range(n_vars)
        for source_idx in range(n_vars)
        for lag in range(1, max_lag + 1)
    ]

    raw_results: list[Phase0MiScore | None] = joblib.Parallel(n_jobs=n_jobs, backend="loky")(
        joblib.delayed(_compute_single_triplet)(
            data,
            target_idx,
            source_idx,
            lag,
            var_names,
            n_timesteps=n_timesteps,
            min_pairs=min_pairs,
            n_neighbors=n_neighbors,
            random_state=random_state,
        )
        for target_idx, source_idx, lag in triplets
    )

    all_scores: list[Phase0MiScore] = [r for r in raw_results if r is not None]
    all_mi: list[float] = [s.mi_value for s in all_scores]

    threshold = ami_threshold if ami_threshold is not None else _compute_auto_threshold(all_mi)
    kept = [s for s in all_scores if s.mi_value > threshold]
    pruned_count = len(all_scores) - len(kept)
    return kept, threshold, pruned_count, len(kept)


def _build_link_assumptions(
    kept_scores: list[Phase0MiScore],
    var_names: list[str],
) -> dict[int, dict[tuple[int, int], str]]:
    """Build tigramite ``link_assumptions`` from Phase 0 survivors.

    Converts Phase 0 MI survivors into the ``link_assumptions`` dict
    expected by ``PCMCI.run_pcmciplus``.  Lagged links use ``'-?>'``
    (may or may not exist; if present, directed forward in time).
    Contemporaneous links use ``'o?o'`` (may or may not exist;
    orientation unknown).

    Args:
        kept_scores: Phase 0 MI scores that passed the threshold.
        var_names: Variable names for index lookup.

    Returns:
        Dict ``{target_idx: {(source_idx, -lag): link_type, ...}}``.
    """
    name_to_idx = {name: idx for idx, name in enumerate(var_names)}
    n_vars = len(var_names)
    assumptions: dict[int, dict[tuple[int, int], str]] = {i: {} for i in range(n_vars)}

    for score in kept_scores:
        target_idx = name_to_idx[score.target]
        source_idx = name_to_idx[score.source]
        pair = (source_idx, -score.lag)
        if pair not in assumptions[target_idx]:
            assumptions[target_idx][pair] = "-?>"

    # Include ALL contemporaneous links (lag=0) for every variable pair
    # so PCMCI+ can discover and orient contemporaneous adjacencies.
    # Phase 0 only evaluates lagged pairs (lag >= 1); contemporaneous
    # dependencies require PCMCI+'s MCI phase to resolve properly.
    for target_idx in range(n_vars):
        for source_idx in range(n_vars):
            contemp_pair = (source_idx, 0)
            if contemp_pair not in assumptions[target_idx]:
                assumptions[target_idx][contemp_pair] = "o?o"

    return assumptions


def _run_pcmci_plus(
    data: np.ndarray,
    var_names: list[str],
    *,
    ci_test_name: str,
    ci_test: object,
    max_lag: int,
    alpha: float,
    random_state: int,
    link_assumptions: dict[int, dict[tuple[int, int], str]],
    verbosity: int = 0,
) -> dict[str, object]:
    """Run tigramite PCMCI+ with pre-built link_assumptions.

    Args:
        data: 2-D array (n_timesteps, n_variables).
        var_names: Variable names matching columns of *data*.
        ci_test_name: Name of CI test for metadata.
        ci_test: Instantiated tigramite CI test object.
        max_lag: Maximum lag.
        alpha: Significance level.
        random_state: Deterministic random seed.
        link_assumptions: Pruned link set from Phase 0 in tigramite
            ``link_assumptions`` format.
        verbosity: Tigramite verbosity level (0 = silent).

    Returns:
        Raw tigramite results dict containing 'graph' and 'val_matrix'.
    """
    pp = importlib.import_module("tigramite.data_processing")
    pcmci_module = importlib.import_module("tigramite.pcmci")
    pcmci_cls = pcmci_module.PCMCI

    np.random.seed(random_state)  # noqa: NPY002
    dataframe = pp.DataFrame(data.astype(float, copy=False), var_names=var_names)
    pcmci = pcmci_cls(dataframe=dataframe, cond_ind_test=ci_test, verbosity=verbosity)
    results: dict[str, object] = pcmci.run_pcmciplus(
        tau_min=0,
        tau_max=max_lag,
        pc_alpha=alpha,
        link_assumptions=link_assumptions,
    )
    return results


def _map_results(
    results: dict[str, object],
    var_names: list[str],
    *,
    max_lag: int,
    metadata: dict[str, str | int | float],
) -> CausalGraphResult:
    """Map raw tigramite results to ``CausalGraphResult``.

    Args:
        results: Raw dict from ``run_pcmciplus``.
        var_names: Variable names.
        max_lag: Maximum lag.
        metadata: Metadata to attach.

    Returns:
        Mapped causal graph result.
    """
    graph = np.asarray(results.get("graph"))
    if graph.ndim != 3:
        raise ValueError("PCMCI+ result 'graph' must be a 3-D array")

    n_vars = len(var_names)
    if graph.shape[0] != n_vars or graph.shape[1] != n_vars:
        raise ValueError(
            f"PCMCI+ graph shape {graph.shape[:2]} does not match n_variables={n_vars}."
        )
    tau_max_available = min(max_lag, int(graph.shape[2]) - 1)

    parents = _extract_parents(graph, var_names, tau_max=tau_max_available)
    link_matrix = _compact_link_matrix(graph, n_vars=n_vars, tau_max=tau_max_available)
    val_matrix = _compact_val_matrix(graph, results.get("val_matrix"), n_vars, tau_max_available)

    return CausalGraphResult(
        parents=parents,
        link_matrix=link_matrix,
        val_matrix=val_matrix,
        metadata=metadata,
    )


def _extract_parents(
    graph: np.ndarray,
    var_names: list[str],
    *,
    tau_max: int,
) -> dict[str, list[tuple[str, int]]]:
    """Extract parent dict from the tigramite graph array."""
    parents: dict[str, list[tuple[str, int]]] = {name: [] for name in var_names}
    for source_idx, source_name in enumerate(var_names):
        for target_idx, target_name in enumerate(var_names):
            for lag in range(tau_max + 1):
                link = str(graph[source_idx, target_idx, lag]).strip()
                if link in _DIRECTED_LINKS:
                    parents[target_name].append((source_name, lag))

    for target_name in parents:
        parents[target_name].sort(key=lambda item: (item[1], item[0]))
    return parents


def _compact_link_matrix(
    graph: np.ndarray,
    *,
    n_vars: int,
    tau_max: int,
) -> list[list[str]]:
    """Build a compact link summary matrix."""
    summary: list[list[str]] = []
    for source_idx in range(n_vars):
        row: list[str] = []
        for target_idx in range(n_vars):
            parts: list[str] = []
            for lag in range(tau_max + 1):
                link = str(graph[source_idx, target_idx, lag]).strip()
                if link in _DIRECTED_LINKS:
                    parts.append(f"{lag}:{link}")
            row.append(",".join(parts))
        summary.append(row)
    return summary


def _compact_val_matrix(
    graph: np.ndarray,
    val_matrix_raw: object,
    n_vars: int,
    tau_max: int,
) -> list[list[float]] | None:
    """Build a compact val_matrix summarising strongest test statistics."""
    if val_matrix_raw is None:
        return None
    arr = np.asarray(val_matrix_raw)
    if arr.ndim == 2:
        return arr.astype(float).tolist()
    if arr.ndim != 3:
        return None

    summary: list[list[float]] = []
    for source_idx in range(n_vars):
        row: list[float] = []
        for target_idx in range(n_vars):
            chosen_value = 0.0
            chosen_abs = -1.0
            for lag in range(tau_max + 1):
                link = str(graph[source_idx, target_idx, lag]).strip()
                if link not in _DIRECTED_LINKS:
                    continue
                val = float(arr[source_idx, target_idx, lag])
                if abs(val) > chosen_abs:
                    chosen_abs = abs(val)
                    chosen_value = val
            row.append(chosen_value)
        summary.append(row)
    return summary


class PcmciAmiAdapter:
    """PCMCI-AMI-Hybrid adapter implementing CausalGraphPort.

    Uses AMI as Phase 0 informational triage to prune weak
    (source, lag) candidates before running PCMCI+ on the survivors.
    This can reduce the search space, but the adapter does not assume a
    general improvement in statistical power.

    The default CI test is ``knn_cmi`` — a kNN conditional MI estimator
    with residualization + permutation significance. With the default
    ``linear_residual`` backend, conditioning removal is still an
    approximation rather than fully non-parametric conditioning.

    Phases:
        0. Compute unconditional MI for all (source, lag, target) triplets;
           prune pairs below a noise-floor threshold.
        1. Run PCMCI+ with ``link_assumptions`` built from the Phase 0 survivors.
        2. Map PCMCI+ output (which already performs skeleton + MCI orientation)
           to ``CausalGraphResult``.

    The ``n_permutations`` argument controls the shuffle-test null size of the
    ``knn_cmi`` CI test. The default is 199 and the floor is 99; values below
    99 are rejected at construction time to keep p-values meaningful.
    """

    def __init__(
        self,
        ci_test: Literal["parcorr", "gpdc", "cmiknn", "knn_cmi"] = "knn_cmi",
        *,
        ami_threshold: float | None = None,
        n_neighbors: int = 8,
        min_pairs: int = 50,
        shuffle_scheme: Literal["iid", "block"] = "iid",
        n_permutations: int = 199,
        pcmci_max_lag: int | None = None,
        verbosity: int = 0,
        n_jobs_phase0: int = 1,
    ) -> None:
        from forecastability.diagnostics.knn_cmi_ci_test import _validate_shuffle_scheme

        _validate_shuffle_scheme(shuffle_scheme)
        if n_permutations < 99:
            raise ValueError(
                f"n_permutations must be >= 99 for significance claims; got {n_permutations}"
            )
        _check_tigramite_available()
        self._ci_test_name = ci_test
        self._ami_threshold = ami_threshold
        self._n_neighbors = n_neighbors
        self._min_pairs = min_pairs
        self._shuffle_scheme: Literal["iid", "block"] = shuffle_scheme
        self._n_permutations = n_permutations
        self._pcmci_max_lag = pcmci_max_lag
        self._verbosity = verbosity
        self._n_jobs_phase0 = n_jobs_phase0

    def _build_ci_test(self, *, seed: int = 42) -> object:
        """Instantiate the tigramite conditional-independence test."""
        if self._ci_test_name == "knn_cmi":
            from forecastability.diagnostics.knn_cmi_ci_test import build_knn_cmi_test

            return build_knn_cmi_test(
                n_neighbors=self._n_neighbors,
                n_permutations=self._n_permutations,
                residual_backend="linear_residual",
                seed=seed,
                shuffle_scheme=self._shuffle_scheme,
            )
        if self._ci_test_name == "parcorr":
            module = importlib.import_module("tigramite.independence_tests.parcorr")
            return module.ParCorr(significance="analytic")
        if self._ci_test_name == "gpdc":
            module = importlib.import_module("tigramite.independence_tests.gpdc")
            return module.GPDC(significance="analytic")
        if self._ci_test_name == "cmiknn":
            module = importlib.import_module("tigramite.independence_tests.cmiknn")
            return module.CMIknn(significance="shuffle_test", knn=self._n_neighbors)
        raise ValueError(f"Unsupported ci_test: {self._ci_test_name!r}")

    def discover(
        self,
        data: np.ndarray,
        var_names: list[str],
        *,
        max_lag: int,
        alpha: float = 0.01,
        random_state: int = 42,
    ) -> CausalGraphResult:
        """Run the PCMCI-AMI-Hybrid and return the final causal graph.

        Satisfies the ``CausalGraphPort`` protocol.

        Args:
            data: 2-D array with shape ``(n_timesteps, n_variables)``.
            var_names: Variable names matching columns of *data*.
            max_lag: Maximum lag to consider (>= 1).
            alpha: Significance level for PCMCI+ conditional-independence tests.
            random_state: Deterministic random seed.

        Returns:
            Final causal graph after AMI triage + PCMCI+.
        """
        return self.discover_full(
            data,
            var_names,
            max_lag=max_lag,
            alpha=alpha,
            random_state=random_state,
        ).causal_graph

    def discover_full(
        self,
        data: np.ndarray,
        var_names: list[str],
        *,
        max_lag: int,
        alpha: float = 0.01,
        random_state: int = 42,
    ) -> PcmciAmiResult:
        """Run the full PCMCI-AMI-Hybrid and return all three phases.

        Args:
            data: 2-D array with shape ``(n_timesteps, n_variables)``.
            var_names: Variable names matching columns of *data*.
            max_lag: Maximum lag to consider (>= 1).
            alpha: Significance level for PCMCI+ conditional-independence tests.
            random_state: Deterministic random seed.

        Returns:
            Complete result with Phase 0 MI scores and the final PCMCI+ graph.
        """
        _validate_inputs(data, var_names, max_lag=max_lag, alpha=alpha)

        effective_pcmci_max_lag = (
            self._pcmci_max_lag if self._pcmci_max_lag is not None else max_lag
        )

        # Phase 0 — AMI triage (uses original max_lag to score all candidate lags)
        kept_scores, threshold, pruned_count, kept_count = _run_phase0(
            data,
            var_names,
            max_lag=max_lag,
            n_neighbors=self._n_neighbors,
            min_pairs=self._min_pairs,
            random_state=random_state,
            ami_threshold=self._ami_threshold,
            n_jobs=self._n_jobs_phase0,
        )

        # Filter Phase 0 survivors to effective_pcmci_max_lag before building assumptions
        phase1_scores = [s for s in kept_scores if s.lag <= effective_pcmci_max_lag]
        assumptions = _build_link_assumptions(phase1_scores, var_names)

        # Phases 1+2 — PCMCI+ on pruned candidates using effective_pcmci_max_lag
        results = _run_pcmci_plus(
            data,
            var_names,
            ci_test_name=self._ci_test_name,
            ci_test=self._build_ci_test(seed=random_state),
            max_lag=effective_pcmci_max_lag,
            alpha=alpha,
            random_state=random_state,
            link_assumptions=assumptions,
            verbosity=self._verbosity,
        )

        base_metadata: dict[str, str | int | float] = {
            "method": "pcmci_ami_hybrid",
            "ci_test": self._ci_test_name,
            "alpha": alpha,
            "max_lag": max_lag,
            "pcmci_max_lag": effective_pcmci_max_lag,
            "random_state": random_state,
            "n_variables": len(var_names),
            "n_timesteps": data.shape[0],
            "phase0_pruned": pruned_count,
            "phase0_kept": kept_count,
            "ami_threshold": threshold,
        }

        graph_result = _map_results(
            results,
            var_names,
            max_lag=max_lag,
            metadata=base_metadata,
        )

        return PcmciAmiResult(
            causal_graph=graph_result,
            phase0_mi_scores=kept_scores,
            phase0_pruned_count=pruned_count,
            phase0_kept_count=kept_count,
            phase1_skeleton=graph_result,
            phase2_final=graph_result,
            ami_threshold=threshold,
            metadata=base_metadata,
        )


def _validate_inputs(
    data: np.ndarray,
    var_names: list[str],
    *,
    max_lag: int,
    alpha: float,
) -> None:
    """Validate adapter inputs with clear error messages.

    Args:
        data: Must be 2-D.
        var_names: Must match ``data.shape[1]``.
        max_lag: Must be >= 1.
        alpha: Must be in (0, 1).
    """
    if data.ndim != 2:
        raise ValueError("data must be 2-D with shape (n_timesteps, n_variables)")
    if data.shape[1] != len(var_names):
        raise ValueError("len(var_names) must match data.shape[1]")
    if max_lag < 1:
        raise ValueError("max_lag must be >= 1")
    if not (0.0 < alpha < 1.0):
        raise ValueError("alpha must be in (0, 1)")
