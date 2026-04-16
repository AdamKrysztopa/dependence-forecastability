"""Tigramite adapter for PCMCI+ causal discovery (V3-F03).

Wraps the optional ``tigramite`` dependency behind the hexagonal
``CausalGraphPort`` contract and maps output to ``CausalGraphResult``.
"""

from __future__ import annotations

import importlib
from typing import Literal

import numpy as np

from forecastability.utils.types import CausalGraphResult

# "-->": directed link (lagged or oriented contemporaneous)
# "o->": directed, uncertain tail — used by LPCMCI; included for forward compatibility
# "o-o": unoriented contemporaneous adjacency — PCMCI+ specific (Markov equivalent)
_DIRECTED_LINKS = {"-->", "o->", "o-o"}


def _check_tigramite_available() -> None:
    """Raise a clear error when the optional tigramite dependency is missing."""
    try:
        importlib.import_module("tigramite")
    except ImportError as exc:
        raise ImportError(
            "tigramite is required for PCMCI+ causal discovery. "
            "Install with `uv sync --extra causal` or `pip install tigramite`."
        ) from exc


class TigramiteAdapter:
    """Adapter wrapping tigramite PCMCI+ behind the CausalGraphPort contract."""

    def __init__(self, ci_test: Literal["parcorr", "gpdc", "cmiknn"] = "parcorr") -> None:
        _check_tigramite_available()
        self._ci_test_name = ci_test

    def _build_ci_test(self) -> object:
        if self._ci_test_name == "parcorr":
            module = importlib.import_module("tigramite.independence_tests.parcorr")
            parcorr_cls = module.ParCorr

            return parcorr_cls(significance="analytic")
        if self._ci_test_name == "gpdc":
            module = importlib.import_module("tigramite.independence_tests.gpdc")
            gpdc_cls = module.GPDC

            return gpdc_cls(significance="analytic")
        if self._ci_test_name == "cmiknn":
            module = importlib.import_module("tigramite.independence_tests.cmiknn")
            cmiknn_cls = module.CMIknn

            return cmiknn_cls(significance="shuffle_test", knn=8)
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
        """Run PCMCI+ and map results to ``CausalGraphResult``."""
        _check_tigramite_available()
        pp = importlib.import_module("tigramite.data_processing")
        pcmci_module = importlib.import_module("tigramite.pcmci")
        pcmci_cls = pcmci_module.PCMCI

        if data.ndim != 2:
            raise ValueError("data must be 2-D with shape (n_timesteps, n_variables)")
        if data.shape[1] != len(var_names):
            raise ValueError("len(var_names) must match data.shape[1]")
        if max_lag < 0:
            raise ValueError("max_lag must be >= 0")
        if not (0.0 < alpha < 1.0):
            raise ValueError("alpha must be in (0, 1)")

        # NOTE: tigramite uses the global NumPy legacy RNG internally.
        # np.random.seed() is called here to ensure reproducibility.
        # In parallel/concurrent usage, this global state mutation may
        # cause non-deterministic results. Use single-threaded execution
        # if exact reproducibility is required.
        np.random.seed(random_state)
        dataframe = pp.DataFrame(data.astype(float, copy=False), var_names=var_names)
        pcmci = pcmci_cls(dataframe=dataframe, cond_ind_test=self._build_ci_test(), verbosity=0)
        results = pcmci.run_pcmciplus(tau_min=0, tau_max=max_lag, pc_alpha=alpha)

        return self._map_results(
            results=results,
            var_names=var_names,
            max_lag=max_lag,
            alpha=alpha,
            random_state=random_state,
            n_timesteps=data.shape[0],
        )

    def _map_results(
        self,
        *,
        results: dict[str, object],
        var_names: list[str],
        max_lag: int,
        alpha: float,
        random_state: int,
        n_timesteps: int,
    ) -> CausalGraphResult:
        graph = np.asarray(results.get("graph"))
        if graph.ndim != 3:
            raise ValueError("PCMCI+ result 'graph' must be a 3-D array")

        n_vars = len(var_names)
        if graph.shape[0] != n_vars or graph.shape[1] != n_vars:
            raise ValueError(
                f"PCMCI+ graph shape {graph.shape[:2]} does not match "
                f"n_variables={n_vars}. Possible tigramite API version mismatch "
                f"or incorrect data ordering."
            )
        tau_max_available = min(max_lag, int(graph.shape[2]) - 1)
        parents: dict[str, list[tuple[str, int]]] = {name: [] for name in var_names}

        for source_idx, source_name in enumerate(var_names):
            for target_idx, target_name in enumerate(var_names):
                for lag in range(tau_max_available + 1):
                    link = str(graph[source_idx, target_idx, lag]).strip()
                    # "o-o" denotes an unoriented contemporaneous adjacency in PCMCI+:
                    # both directions are consistent with the data (Markov equivalence
                    # class). Treating the source as a parent is conservative but correct.
                    if link in _DIRECTED_LINKS:
                        parents[target_name].append((source_name, lag))

        for target_name in parents:
            parents[target_name].sort(key=lambda item: (item[1], item[0]))

        link_matrix = self._compact_link_matrix(
            graph=graph,
            n_vars=n_vars,
            tau_max=tau_max_available,
        )
        val_matrix = self._compact_val_matrix(
            graph=graph,
            val_matrix=results.get("val_matrix"),
            n_vars=n_vars,
            tau_max=tau_max_available,
        )

        return CausalGraphResult(
            parents=parents,
            link_matrix=link_matrix,
            val_matrix=val_matrix,
            metadata={
                "method": "pcmci_plus",
                "ci_test": self._ci_test_name,
                "alpha": alpha,
                "max_lag": max_lag,
                "random_state": random_state,
                "n_variables": n_vars,
                "n_timesteps": n_timesteps,
            },
        )

    def _compact_link_matrix(
        self,
        *,
        graph: np.ndarray,
        n_vars: int,
        tau_max: int,
    ) -> list[list[str]]:
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
        self,
        *,
        graph: np.ndarray,
        val_matrix: object,
        n_vars: int,
        tau_max: int,
    ) -> list[list[float]] | None:
        if val_matrix is None:
            return None

        arr = np.asarray(val_matrix)
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
