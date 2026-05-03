"""Focused integration tests for the covariant orchestration facade."""

from __future__ import annotations

import importlib
from collections import defaultdict
from collections.abc import Callable

import numpy as np
import pandas as pd
import pytest

from forecastability.use_cases.run_covariant_analysis import run_covariant_analysis
from forecastability.utils.synthetic import generate_covariant_benchmark
from forecastability.utils.types import CausalGraphResult, PcmciAmiResult, Phase0MiScore

covariant_module = importlib.import_module("forecastability.use_cases.run_covariant_analysis")


def _make_stub_graph(
    *,
    var_names: list[str],
    target_name: str,
    lagged_links: list[tuple[str, int, str]],
    method: str,
) -> CausalGraphResult:
    parents = {name: [] for name in var_names}
    link_matrix = [["" for _ in var_names] for _ in var_names]
    target_index = var_names.index(target_name)

    for source_name, lag, link in lagged_links:
        parents[target_name].append((source_name, lag))
        source_index = var_names.index(source_name)
        link_matrix[source_index][target_index] = f"{lag}:{link}"

    return CausalGraphResult(
        parents=parents,
        link_matrix=link_matrix,
        metadata={"method": method, "max_lag": 3},
    )


class _StubPcmciPort:
    def discover(
        self,
        data: object,
        var_names: list[str],
        *,
        max_lag: int,
        alpha: float = 0.01,
        random_state: int = 42,
    ) -> CausalGraphResult:
        del data, max_lag, alpha, random_state
        return _make_stub_graph(
            var_names=var_names,
            target_name="target",
            lagged_links=[("driver_direct", 2, "-->"), ("driver_mediated", 1, "-->")],
            method="pcmci_plus",
        )


class _StubPcmciAmiPort:
    def discover(
        self,
        data: object,
        var_names: list[str],
        *,
        max_lag: int,
        alpha: float = 0.01,
        random_state: int = 42,
    ) -> CausalGraphResult:
        del data, max_lag, alpha, random_state
        return _make_stub_graph(
            var_names=var_names,
            target_name="target",
            lagged_links=[("driver_direct", 2, "-->"), ("driver_mediated", 1, "-->")],
            method="pcmci_ami_hybrid",
        )

    def discover_full(
        self,
        data: object,
        var_names: list[str],
        *,
        max_lag: int,
        alpha: float = 0.01,
        random_state: int = 42,
    ) -> PcmciAmiResult:
        del data, max_lag, alpha, random_state
        graph = _make_stub_graph(
            var_names=var_names,
            target_name="target",
            lagged_links=[("driver_direct", 2, "-->"), ("driver_mediated", 1, "-->")],
            method="pcmci_ami_hybrid",
        )
        return PcmciAmiResult(
            causal_graph=graph,
            phase0_mi_scores=[
                Phase0MiScore(source="driver_direct", lag=2, target="target", mi_value=0.8),
                Phase0MiScore(source="driver_mediated", lag=1, target="target", mi_value=0.5),
            ],
            phase0_pruned_count=4,
            phase0_kept_count=2,
            phase1_skeleton=graph,
            phase2_final=graph,
            ami_threshold=0.05,
            metadata={"method": "pcmci_ami_hybrid", "max_lag": 3},
        )


class _ImportErrorPcmciPort:
    def discover(
        self,
        data: object,
        var_names: list[str],
        *,
        max_lag: int,
        alpha: float = 0.01,
        random_state: int = 42,
    ) -> CausalGraphResult:
        del data, var_names, max_lag, alpha, random_state
        raise ImportError("submodule moved")


class _ImportErrorPcmciAmiPort:
    def discover(
        self,
        data: object,
        var_names: list[str],
        *,
        max_lag: int,
        alpha: float = 0.01,
        random_state: int = 42,
    ) -> CausalGraphResult:
        del data, var_names, max_lag, alpha, random_state
        raise ImportError("submodule moved")

    def discover_full(
        self,
        data: object,
        var_names: list[str],
        *,
        max_lag: int,
        alpha: float = 0.01,
        random_state: int = 42,
    ) -> PcmciAmiResult:
        del data, var_names, max_lag, alpha, random_state
        raise ImportError("submodule moved")


@pytest.fixture
def benchmark_df() -> pd.DataFrame:
    return generate_covariant_benchmark(n=900, seed=42)


def test_bundle_has_one_row_per_driver_lag_for_non_optional_methods(
    benchmark_df: pd.DataFrame,
) -> None:
    drivers = {
        name: benchmark_df[name].to_numpy()
        for name in ("driver_direct", "driver_mediated", "driver_noise")
    }

    result = run_covariant_analysis(
        benchmark_df["target"].to_numpy(),
        drivers,
        max_lag=3,
        methods=["cross_ami", "cross_pami", "te", "gcmi"],
        random_state=42,
    )

    assert len(result.summary_table) == len(drivers) * 3
    assert len(result.te_results or []) == len(drivers) * 3
    assert len(result.gcmi_results or []) == len(drivers) * 3
    assert result.pcmci_graph is None
    assert result.pcmci_ami_result is None


def test_lagged_exog_bundle_is_opt_in_on_covariant_facade(
    benchmark_df: pd.DataFrame,
) -> None:
    """Phase 2 lagged-exog output should be attached only when explicitly enabled."""
    drivers = {"driver_direct": benchmark_df["driver_direct"].to_numpy()}

    baseline = run_covariant_analysis(
        benchmark_df["target"].to_numpy(),
        drivers,
        max_lag=2,
        methods=["te"],
        n_surrogates=99,
        random_state=42,
    )
    assert baseline.lagged_exog is None

    with_lagged = run_covariant_analysis(
        benchmark_df["target"].to_numpy(),
        drivers,
        max_lag=2,
        methods=["te"],
        n_surrogates=99,
        random_state=42,
        include_lagged_exog_triage=True,
    )
    assert with_lagged.lagged_exog is not None
    assert all(row.lag >= 1 for row in with_lagged.lagged_exog.selected_lags)
    lag0_rows = [row for row in with_lagged.lagged_exog.profile_rows if row.lag == 0]
    assert len(lag0_rows) == 1
    assert lag0_rows[0].tensor_role == "diagnostic"


@pytest.mark.parametrize(
    ("methods", "requested_field", "unrequested_field", "requested_conditioning", "has_disclaimer"),
    [
        (["cross_ami"], "cross_ami", "cross_pami", "none", False),
        (["cross_pami"], "cross_pami", "cross_ami", "target_only", True),
    ],
)
def test_requested_cross_method_only_populates_its_own_summary_column(
    benchmark_df: pd.DataFrame,
    methods: list[str],
    requested_field: str,
    unrequested_field: str,
    requested_conditioning: str,
    has_disclaimer: bool,
) -> None:
    drivers = {"driver_direct": benchmark_df["driver_direct"].to_numpy()}

    result = run_covariant_analysis(
        benchmark_df["target"].to_numpy(),
        drivers,
        max_lag=3,
        methods=methods,
        random_state=42,
    )

    assert len(result.summary_table) == 3
    assert all(getattr(row, requested_field) is not None for row in result.summary_table)
    assert all(getattr(row, unrequested_field) is None for row in result.summary_table)
    assert all(
        getattr(row.lagged_exog_conditioning, requested_field) == requested_conditioning
        for row in result.summary_table
    )
    assert all(
        getattr(row.lagged_exog_conditioning, unrequested_field) is None
        for row in result.summary_table
    )
    if has_disclaimer:
        assert result.metadata["contains_target_only_methods"] == 1
        assert "conditioning_scope_disclaimer" in result.metadata
    else:
        assert "contains_target_only_methods" not in result.metadata
        assert "conditioning_scope_disclaimer" not in result.metadata


@pytest.mark.parametrize(
    ("methods", "expected_calls"),
    [
        (["cross_ami"], {"raw": 1, "partial": 0, "significance": 1}),
        (["cross_pami"], {"raw": 0, "partial": 1, "significance": 0}),
        (["cross_ami", "cross_pami"], {"raw": 1, "partial": 1, "significance": 1}),
    ],
)
def test_cross_method_subset_skips_unrequested_curve_work(
    monkeypatch: pytest.MonkeyPatch,
    methods: list[str],
    expected_calls: dict[str, int],
) -> None:
    calls = {"raw": 0, "partial": 0, "significance": 0}

    def _raw_curve(*args: object, **kwargs: object) -> np.ndarray:
        del args, kwargs
        calls["raw"] += 1
        return np.array([0.10, 0.20])

    def _partial_curve(*args: object, **kwargs: object) -> np.ndarray:
        del args, kwargs
        calls["partial"] += 1
        return np.array([0.05, 0.07])

    def _significance_bands(*args: object, **kwargs: object) -> tuple[np.ndarray, np.ndarray]:
        del args, kwargs
        calls["significance"] += 1
        return np.array([0.0, 0.0]), np.array([0.15, 0.25])

    monkeypatch.setattr(covariant_module, "compute_exog_raw_curve", _raw_curve)
    monkeypatch.setattr(covariant_module, "compute_exog_partial_curve", _partial_curve)
    monkeypatch.setattr(covariant_module, "compute_significance_bands_generic", _significance_bands)

    target = np.arange(12, dtype=float)
    drivers = {"driver": target + 1.0}

    result = run_covariant_analysis(
        target,
        drivers,
        max_lag=2,
        methods=methods,
        n_surrogates=99,
        random_state=42,
    )

    assert calls == expected_calls
    assert len(result.summary_table) == 2


def test_lagged_exog_conditioning_metadata_is_truthful(
    benchmark_df: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(covariant_module, "build_pcmci_plus", lambda **_: _StubPcmciPort())
    monkeypatch.setattr(
        covariant_module,
        "build_pcmci_ami_hybrid",
        lambda **_: _StubPcmciAmiPort(),
    )
    drivers = {
        name: benchmark_df[name].to_numpy()
        for name in ("driver_direct", "driver_mediated", "driver_noise")
    }

    result = run_covariant_analysis(
        benchmark_df["target"].to_numpy(),
        drivers,
        max_lag=3,
        methods=["cross_ami", "cross_pami", "te", "gcmi", "pcmci", "pcmci_ami"],
        random_state=42,
    )

    direct_lag2 = next(
        row for row in result.summary_table if row.driver == "driver_direct" and row.lag == 2
    )
    assert direct_lag2.lagged_exog_conditioning.cross_ami == "none"
    assert direct_lag2.lagged_exog_conditioning.cross_pami == "target_only"
    assert direct_lag2.lagged_exog_conditioning.transfer_entropy == "target_only"
    assert direct_lag2.lagged_exog_conditioning.gcmi == "none"
    assert direct_lag2.lagged_exog_conditioning.pcmci == "full_mci"
    assert direct_lag2.lagged_exog_conditioning.pcmci_ami == "full_mci"
    assert direct_lag2.pcmci_link == "-->"
    assert direct_lag2.pcmci_ami_parent is True
    assert all(item.lagged_exog_conditioning == "target_only" for item in result.te_results or [])
    assert all(item.lagged_exog_conditioning == "none" for item in result.gcmi_results or [])
    assert result.pcmci_graph is not None
    assert result.pcmci_graph.lagged_exog_conditioning == "full_mci"
    assert result.pcmci_ami_result is not None
    assert result.pcmci_ami_result.lagged_exog_conditioning == "full_mci"
    assert "conditioning_scope_disclaimer" in result.metadata
    disclaimer = str(result.metadata["conditioning_scope_disclaimer"])
    assert "CrossMI and GCMI rows are unconditioned pairwise signals (`none`)" in disclaimer
    assert "pCrossAMI and TE rows are `target_only`" in disclaimer
    assert "only PCMCI+ and PCMCI-AMI are `full_mci`" in disclaimer
    assert result.metadata["conditioning_scope_forward_link"] == (
        "docs/plan/v0_3_2_lagged_exogenous_triage_ultimate_plan.md"
    )


def test_optional_tigramite_methods_are_skipped_when_unavailable(
    benchmark_df: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_import_error(**_: object) -> object:
        raise ImportError("tigramite unavailable")

    monkeypatch.setattr(covariant_module, "build_pcmci_plus", _raise_import_error)
    monkeypatch.setattr(covariant_module, "build_pcmci_ami_hybrid", _raise_import_error)
    drivers = {"driver_direct": benchmark_df["driver_direct"].to_numpy()}

    result = run_covariant_analysis(
        benchmark_df["target"].to_numpy(),
        drivers,
        max_lag=3,
        methods=["cross_ami", "pcmci", "pcmci_ami"],
        random_state=42,
    )

    assert len(result.summary_table) == 3
    assert result.pcmci_graph is None
    assert result.pcmci_ami_result is None
    assert result.metadata["skipped_optional_methods"] == "pcmci,pcmci_ami"


@pytest.mark.parametrize(
    ("method_name", "builder_name"),
    [("pcmci", "build_pcmci_plus"), ("pcmci_ami", "build_pcmci_ami_hybrid")],
)
def test_optional_only_requests_keep_driver_lag_grid_when_unavailable(
    benchmark_df: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    builder_name: str,
) -> None:
    def _raise_import_error(**_: object) -> object:
        raise ImportError("tigramite unavailable")

    monkeypatch.setattr(covariant_module, builder_name, _raise_import_error)
    drivers = {"driver_direct": benchmark_df["driver_direct"].to_numpy()}

    result = run_covariant_analysis(
        benchmark_df["target"].to_numpy(),
        drivers,
        max_lag=3,
        methods=[method_name],
        random_state=42,
    )

    assert len(result.summary_table) == 3
    assert result.metadata["active_methods"] == ""
    assert result.metadata["skipped_optional_methods"] == method_name
    assert all(row.cross_ami is None for row in result.summary_table)
    assert all(row.cross_pami is None for row in result.summary_table)
    assert all(row.transfer_entropy is None for row in result.summary_table)
    assert all(row.gcmi is None for row in result.summary_table)
    assert all(row.pcmci_link is None for row in result.summary_table)
    assert all(row.pcmci_ami_parent is None for row in result.summary_table)


@pytest.mark.parametrize(
    ("method_name", "builder_name", "factory"),
    [
        ("pcmci", "build_pcmci_plus", lambda: _ImportErrorPcmciPort()),
        ("pcmci_ami", "build_pcmci_ami_hybrid", lambda: _ImportErrorPcmciAmiPort()),
    ],
)
def test_execution_time_import_error_from_optional_adapter_is_not_swallowed(
    benchmark_df: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    builder_name: str,
    factory: Callable[[], object],
) -> None:
    monkeypatch.setattr(covariant_module, builder_name, lambda **_: factory())
    drivers = {"driver_direct": benchmark_df["driver_direct"].to_numpy()}

    with pytest.raises(ImportError, match="submodule moved"):
        run_covariant_analysis(
            benchmark_df["target"].to_numpy(),
            drivers,
            max_lag=3,
            methods=[method_name],
            random_state=42,
        )


def test_direct_and_mediated_drivers_surface_above_noise_on_synthetic_benchmark(
    benchmark_df: pd.DataFrame,
) -> None:
    drivers = {
        name: benchmark_df[name].to_numpy()
        for name in ("driver_direct", "driver_mediated", "driver_noise")
    }
    result = run_covariant_analysis(
        benchmark_df["target"].to_numpy(),
        drivers,
        max_lag=3,
        methods=["cross_ami", "cross_pami", "te", "gcmi"],
        random_state=42,
    )

    maxima: dict[str, dict[str, float]] = defaultdict(dict)
    for row in result.summary_table:
        for method_name, field_name in (
            ("cross_ami", "cross_ami"),
            ("cross_pami", "cross_pami"),
            ("te", "transfer_entropy"),
            ("gcmi", "gcmi"),
        ):
            value = getattr(row, field_name)
            if value is None:
                continue
            current = maxima[method_name].get(row.driver, float("-inf"))
            maxima[method_name][row.driver] = max(current, value)

    assert maxima["cross_ami"]["driver_direct"] > maxima["cross_ami"]["driver_noise"]
    assert maxima["cross_ami"]["driver_mediated"] > maxima["cross_ami"]["driver_noise"]
    assert maxima["gcmi"]["driver_direct"] > maxima["gcmi"]["driver_noise"]
    assert maxima["gcmi"]["driver_mediated"] > maxima["gcmi"]["driver_noise"]


def test_rejects_unknown_methods() -> None:
    benchmark_df = generate_covariant_benchmark(n=200, seed=7)
    with pytest.raises(ValueError, match="Unknown methods"):
        run_covariant_analysis(
            target=benchmark_df["target"].to_numpy(),
            drivers={"driver_direct": benchmark_df["driver_direct"].to_numpy()},
            methods=["magic_method"],
        )


def test_rejects_low_surrogates(benchmark_df: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="n_surrogates must be >= 99"):
        run_covariant_analysis(
            benchmark_df["target"].to_numpy(),
            {"driver_direct": benchmark_df["driver_direct"].to_numpy()},
            n_surrogates=98,
        )


def test_significance_populated_when_cross_ami_requested(
    benchmark_df: pd.DataFrame,
) -> None:
    """Every row has significance tag when cross_ami is active."""
    drivers = {"driver_direct": benchmark_df["driver_direct"].to_numpy()}
    result = run_covariant_analysis(
        benchmark_df["target"].to_numpy(),
        drivers,
        max_lag=3,
        methods=["cross_ami"],
        n_surrogates=99,
        random_state=42,
    )
    assert all(row.significance in ("above_band", "below_band") for row in result.summary_table)


def test_significance_none_when_cross_ami_not_requested(
    benchmark_df: pd.DataFrame,
) -> None:
    drivers = {"driver_direct": benchmark_df["driver_direct"].to_numpy()}
    result = run_covariant_analysis(
        benchmark_df["target"].to_numpy(),
        drivers,
        max_lag=3,
        methods=["te"],
        n_surrogates=99,
        random_state=42,
    )
    assert all(row.significance is None for row in result.summary_table)


def test_rank_is_always_populated(benchmark_df: pd.DataFrame) -> None:
    """Rank field is always populated with a valid positive integer."""
    drivers = {
        name: benchmark_df[name].to_numpy()
        for name in ("driver_direct", "driver_mediated", "driver_noise")
    }
    result = run_covariant_analysis(
        benchmark_df["target"].to_numpy(),
        drivers,
        max_lag=3,
        methods=["cross_ami", "te", "gcmi"],
        n_surrogates=99,
        random_state=42,
    )
    ranks = [row.rank for row in result.summary_table]
    assert all(r is not None and r >= 1 for r in ranks)
    assert sorted(ranks) == list(range(1, len(result.summary_table) + 1))


def test_interpretation_tag_populated_when_cross_ami_requested(
    benchmark_df: pd.DataFrame,
) -> None:
    drivers = {"driver_direct": benchmark_df["driver_direct"].to_numpy()}
    result = run_covariant_analysis(
        benchmark_df["target"].to_numpy(),
        drivers,
        max_lag=3,
        methods=["cross_ami"],
        n_surrogates=99,
        random_state=42,
    )
    valid_tags = {
        "causal_confirmed",
        "probably_mediated",
        "directional_informative",
        "pairwise_informative",
        "noise_or_weak",
    }
    assert all(row.interpretation_tag in valid_tags for row in result.summary_table)


def test_rank_ordering_consistent_with_primary_score(benchmark_df: pd.DataFrame) -> None:
    """Row with highest cross_ami has rank 1."""
    drivers = {
        name: benchmark_df[name].to_numpy()
        for name in ("driver_direct", "driver_mediated", "driver_noise")
    }
    result = run_covariant_analysis(
        benchmark_df["target"].to_numpy(),
        drivers,
        max_lag=3,
        methods=["cross_ami"],
        n_surrogates=99,
        random_state=42,
    )
    rank1_row = next(r for r in result.summary_table if r.rank == 1)
    best_ami = max(r.cross_ami for r in result.summary_table if r.cross_ami is not None)
    assert rank1_row.cross_ami == best_ami


# ---------------------------------------------------------------------------
# PBE-F25 — new run_covariant_analysis parameter tests
# ---------------------------------------------------------------------------


def test_run_covariant_pcmci_ami_n_permutations_below_floor(
    benchmark_df: pd.DataFrame,
) -> None:
    """run_covariant_analysis raises ValueError when pcmci_ami_n_permutations < 99."""
    drivers = {"driver_direct": benchmark_df["driver_direct"].to_numpy()}
    with pytest.raises(ValueError, match="pcmci_ami_n_permutations"):
        run_covariant_analysis(
            benchmark_df["target"].to_numpy(),
            drivers,
            max_lag=3,
            methods=["pcmci_ami"],
            pcmci_ami_n_permutations=98,
        )


def test_run_covariant_pcmci_ami_ci_test_param_accepted(
    benchmark_df: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """pcmci_ami_ci_test='parcorr' is accepted by run_covariant_analysis without error."""

    class _MinimalPcmciAmiPort:
        def discover(
            self, data: object, var_names: list[str], **_: object
        ) -> CausalGraphResult:
            parents = {name: [] for name in var_names}
            link_matrix = [["" for _ in var_names] for _ in var_names]
            return CausalGraphResult(
                parents=parents, link_matrix=link_matrix, metadata={"method": "pcmci_ami_hybrid"}
            )

        def discover_full(
            self, data: object, var_names: list[str], **_: object
        ) -> PcmciAmiResult:
            graph = self.discover(data, var_names)
            return PcmciAmiResult(
                causal_graph=graph,
                phase0_mi_scores=[],
                phase0_pruned_count=0,
                phase0_kept_count=0,
                phase1_skeleton=graph,
                phase2_final=graph,
                ami_threshold=0.05,
                metadata={"method": "pcmci_ami_hybrid"},
            )

    monkeypatch.setattr(
        covariant_module, "build_pcmci_ami_hybrid", lambda **_: _MinimalPcmciAmiPort()
    )
    drivers = {"driver_direct": benchmark_df["driver_direct"].to_numpy()[:100]}
    result = run_covariant_analysis(
        benchmark_df["target"].to_numpy()[:100],
        drivers,
        max_lag=2,
        methods=["pcmci_ami"],
        pcmci_ami_ci_test="parcorr",
        n_surrogates=99,
        random_state=42,
    )
    assert result.pcmci_ami_result is not None
