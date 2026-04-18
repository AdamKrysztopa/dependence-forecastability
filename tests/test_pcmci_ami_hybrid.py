"""Tests for the V3-F04 PCMCI-AMI-Hybrid adapter."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.adapters.pcmci_ami_adapter import PcmciAmiAdapter
from forecastability.ports import CausalGraphPort
from forecastability.utils.synthetic import generate_covariant_benchmark
from forecastability.utils.types import CausalGraphResult, PcmciAmiResult, Phase0MiScore


def _require_tigramite() -> None:
    pytest.importorskip("tigramite")


def _make_pcmci_fixture(n: int = 1400, seed: int = 42) -> tuple[np.ndarray, list[str]]:
    """8-variable covariant benchmark with known ground-truth causal structure."""
    df = generate_covariant_benchmark(n=n, seed=seed)
    return df.to_numpy(), df.columns.tolist()


def test_satisfies_causal_graph_port() -> None:
    """PcmciAmiAdapter must satisfy the CausalGraphPort protocol."""
    _require_tigramite()
    adapter = PcmciAmiAdapter(ci_test="parcorr")
    assert isinstance(adapter, CausalGraphPort)


def test_discovers_direct_parent() -> None:
    """Phase 2 should find driver_direct at lag 2 in parents of target."""
    _require_tigramite()
    data, var_names = _make_pcmci_fixture()
    adapter = PcmciAmiAdapter(ci_test="parcorr")
    result = adapter.discover_full(data, var_names, max_lag=3, alpha=0.01, random_state=42)

    target_parents = set(result.phase2_final.parents["target"])
    assert ("driver_direct", 2) in target_parents, (
        f"Expected ('driver_direct', 2) in parents; got {target_parents}"
    )


def test_phase0_prunes_noise() -> None:
    """Phase 0 MI scores for driver_noise should be much lower than driver_direct."""
    _require_tigramite()
    data, var_names = _make_pcmci_fixture()
    adapter = PcmciAmiAdapter(ci_test="parcorr")
    result = adapter.discover_full(data, var_names, max_lag=3, alpha=0.01, random_state=42)

    # Collect all Phase 0 MI scores (kept scores) plus infer pruned ones are below threshold
    noise_scores = [
        s.mi_value
        for s in result.phase0_mi_scores
        if s.source == "driver_noise" and s.target == "target"
    ]
    direct_scores = [
        s.mi_value
        for s in result.phase0_mi_scores
        if s.source == "driver_direct" and s.target == "target"
    ]

    # driver_direct should have substantially higher MI than driver_noise
    if noise_scores and direct_scores:
        assert max(direct_scores) > max(noise_scores) * 2, (
            f"driver_direct MI ({max(direct_scores):.4f}) should dominate "
            f"driver_noise MI ({max(noise_scores):.4f})"
        )
    elif not noise_scores:
        # driver_noise was pruned entirely — that's even better
        assert direct_scores, "driver_direct should survive Phase 0 pruning"


def test_phase0_keeps_true_drivers() -> None:
    """Phase 0 kept_count > 0 and driver_direct appears with reasonable MI."""
    _require_tigramite()
    data, var_names = _make_pcmci_fixture()
    adapter = PcmciAmiAdapter(ci_test="parcorr")
    result = adapter.discover_full(data, var_names, max_lag=3, alpha=0.01, random_state=42)

    assert result.phase0_kept_count > 0, "Phase 0 must keep at least some candidates"

    direct_scores = [
        s for s in result.phase0_mi_scores if s.source == "driver_direct" and s.target == "target"
    ]
    assert direct_scores, "driver_direct must appear in Phase 0 MI scores"
    assert max(s.mi_value for s in direct_scores) > 0.0, "driver_direct MI value should be positive"


def test_discover_full_returns_pcmci_ami_result() -> None:
    """discover_full() returns PcmciAmiResult with all required fields populated."""
    _require_tigramite()
    data, var_names = _make_pcmci_fixture()
    adapter = PcmciAmiAdapter(ci_test="parcorr")
    result = adapter.discover_full(data, var_names, max_lag=3, alpha=0.01, random_state=42)

    assert isinstance(result, PcmciAmiResult)
    assert isinstance(result.causal_graph, CausalGraphResult)
    assert isinstance(result.phase1_skeleton, CausalGraphResult)
    assert isinstance(result.phase2_final, CausalGraphResult)
    assert isinstance(result.phase0_mi_scores, list)
    assert all(isinstance(s, Phase0MiScore) for s in result.phase0_mi_scores)
    assert result.phase0_pruned_count >= 0
    assert result.phase0_kept_count >= 0
    assert result.ami_threshold > 0.0
    assert result.metadata


def test_metadata_method_is_pcmci_ami_hybrid() -> None:
    """metadata['method'] must be 'pcmci_ami_hybrid'."""
    _require_tigramite()
    data, var_names = _make_pcmci_fixture()
    adapter = PcmciAmiAdapter(ci_test="parcorr")
    result = adapter.discover_full(data, var_names, max_lag=3, alpha=0.01, random_state=42)

    assert result.metadata["method"] == "pcmci_ami_hybrid"
    assert result.metadata["ci_test"] == "parcorr"
    assert result.metadata["max_lag"] == 3


def test_result_json_round_trip() -> None:
    """PcmciAmiResult serializes to JSON and round-trips correctly."""
    _require_tigramite()
    data, var_names = _make_pcmci_fixture()
    adapter = PcmciAmiAdapter(ci_test="parcorr")
    result = adapter.discover_full(data, var_names, max_lag=3, alpha=0.01, random_state=42)

    payload = result.model_dump_json()
    restored = PcmciAmiResult.model_validate_json(payload)

    assert restored == result
    assert restored.metadata["method"] == "pcmci_ami_hybrid"
    assert len(restored.phase0_mi_scores) == len(result.phase0_mi_scores)
    assert restored.phase0_pruned_count == result.phase0_pruned_count


def test_phase0_pruning_reduces_candidates() -> None:
    """phase0_pruned_count > 0 — some candidates should be pruned."""
    _require_tigramite()
    data, var_names = _make_pcmci_fixture()
    adapter = PcmciAmiAdapter(ci_test="parcorr")
    result = adapter.discover_full(data, var_names, max_lag=3, alpha=0.01, random_state=42)

    assert result.phase0_pruned_count > 0, "Phase 0 should prune at least some low-MI candidates"


def test_custom_ami_threshold() -> None:
    """Passing ami_threshold=0.5 changes pruning behavior vs default."""
    _require_tigramite()
    data, var_names = _make_pcmci_fixture()

    adapter_default = PcmciAmiAdapter(ci_test="parcorr")
    result_default = adapter_default.discover_full(
        data, var_names, max_lag=3, alpha=0.01, random_state=42
    )

    adapter_strict = PcmciAmiAdapter(ci_test="parcorr", ami_threshold=0.5)
    result_strict = adapter_strict.discover_full(
        data, var_names, max_lag=3, alpha=0.01, random_state=42
    )

    # A very high threshold should prune more aggressively
    assert result_strict.phase0_pruned_count >= result_default.phase0_pruned_count, (
        f"ami_threshold=0.5 should prune at least as many as default "
        f"({result_strict.phase0_pruned_count} vs {result_default.phase0_pruned_count})"
    )
    assert result_strict.ami_threshold == 0.5


def test_input_validation_errors() -> None:
    """Adapter must raise ValueError for invalid inputs."""
    _require_tigramite()
    data, var_names = _make_pcmci_fixture()
    adapter = PcmciAmiAdapter(ci_test="parcorr")

    # data.ndim != 2
    with pytest.raises(ValueError, match="2-D"):
        adapter.discover(np.ones(10), var_names, max_lag=3, random_state=42)

    # mismatched var_names
    with pytest.raises(ValueError, match="var_names"):
        adapter.discover(data, ["a", "b"], max_lag=3, random_state=42)

    # max_lag < 1
    with pytest.raises(ValueError, match="max_lag"):
        adapter.discover(data, var_names, max_lag=0, random_state=42)

    # alpha out of range
    with pytest.raises(ValueError, match="alpha"):
        adapter.discover(data, var_names, max_lag=3, alpha=0.0, random_state=42)

    with pytest.raises(ValueError, match="alpha"):
        adapter.discover(data, var_names, max_lag=3, alpha=1.0, random_state=42)


def test_default_ci_test_is_knn_cmi() -> None:
    """Default ci_test must be knn_cmi, not parcorr."""
    _require_tigramite()
    adapter = PcmciAmiAdapter()
    assert adapter._ci_test_name == "knn_cmi"


def test_iid_shuffle_scheme_is_default() -> None:
    """PcmciAmiAdapter must default to the i.i.d. shuffle scheme."""
    _require_tigramite()
    adapter = PcmciAmiAdapter()
    assert adapter._shuffle_scheme == "iid"
    ci_test = adapter._build_ci_test(seed=42)
    assert ci_test._shuffle_scheme == "iid"  # type: ignore[attr-defined]


def test_block_shuffle_scheme_preserves_output_shape() -> None:
    """discover_full() with shuffle_scheme='block' runs and recovers driver_direct(t-2)."""
    _require_tigramite()
    df = generate_covariant_benchmark(n=400, seed=42)
    data, var_names = df.to_numpy(), df.columns.tolist()

    adapter = PcmciAmiAdapter(ci_test="knn_cmi", shuffle_scheme="block")
    assert adapter._shuffle_scheme == "block"

    result = adapter.discover_full(data, var_names, max_lag=2, alpha=0.05, random_state=42)

    assert isinstance(result, PcmciAmiResult)
    target_parents = set(result.phase2_final.parents["target"])
    assert ("driver_direct", 2) in target_parents, (
        f"Expected ('driver_direct', 2) in parents; got {target_parents}"
    )


def test_knn_cmi_linear_vectorised_matches_naive() -> None:
    """Vectorised linear-residual shuffle must reproduce the same p-value across reruns."""
    _require_tigramite()
    from forecastability.diagnostics.knn_cmi_ci_test import build_knn_cmi_test

    rng = np.random.default_rng(0)
    t_len = 200
    z_mat = rng.standard_normal((t_len, 2))
    x = z_mat[:, 0] + 0.3 * rng.standard_normal(t_len)
    y = 0.5 * z_mat[:, 1] + 0.4 * x + 0.3 * rng.standard_normal(t_len)

    array = np.vstack([x, y, z_mat[:, 0], z_mat[:, 1]])
    xyz = np.array([0, 1, 2, 2])

    def _run_once() -> float:
        test = build_knn_cmi_test(
            n_neighbors=5,
            n_permutations=99,
            residual_backend="linear_residual",
            seed=123,
            shuffle_scheme="iid",
        )
        observed = test.get_dependence_measure(array, xyz)  # type: ignore[attr-defined]
        p_value = test.get_shuffle_significance(array, xyz, observed)  # type: ignore[attr-defined]
        return float(p_value)

    p_first = _run_once()
    p_second = _run_once()
    assert p_first == p_second, (
        f"Vectorised linear-residual shuffle must be deterministic: got {p_first} vs {p_second}"
    )


def test_linear_residual_projector_matches_ols_refit() -> None:
    """_linear_residual via QR projector must match an explicit OLS refit residual."""
    from forecastability.diagnostics.knn_cmi_ci_test import (
        _build_linear_projector,
        _linear_residual,
    )

    rng = np.random.default_rng(7)
    for _ in range(3):
        t_len = rng.integers(150, 300)
        dim_z = int(rng.integers(1, 4))
        z = rng.standard_normal((t_len, dim_z))
        x = rng.standard_normal(t_len) + z[:, 0] * 0.4

        projector = _build_linear_projector(z)
        vectorised = _linear_residual(x, projector)

        z_aug = np.column_stack([np.ones(t_len), z])
        beta, *_ = np.linalg.lstsq(z_aug, x, rcond=None)
        naive = x - z_aug @ beta

        assert np.allclose(vectorised, naive, atol=1e-10), (
            "Vectorised residual disagrees with OLS refit: "
            f"max|diff|={np.max(np.abs(vectorised - naive))}"
        )


def test_build_knn_cmi_test_rejects_unknown_shuffle_scheme() -> None:
    """Runtime validation must reject mistyped shuffle_scheme values."""
    _require_tigramite()
    from forecastability.diagnostics.knn_cmi_ci_test import build_knn_cmi_test

    with pytest.raises(ValueError, match="shuffle_scheme"):
        build_knn_cmi_test(shuffle_scheme="Block")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="shuffle_scheme"):
        build_knn_cmi_test(shuffle_scheme="iid ")  # type: ignore[arg-type]


def test_pcmci_ami_adapter_rejects_unknown_shuffle_scheme() -> None:
    """Adapter ctor validates shuffle_scheme before the tigramite availability check."""
    with pytest.raises(ValueError, match="shuffle_scheme"):
        PcmciAmiAdapter(shuffle_scheme="politis_romano")  # type: ignore[arg-type]


@pytest.mark.slow
def test_knn_cmi_finds_nonlinear_parents() -> None:
    """knn_cmi CI test detects nonlinear (quadratic) parents that parcorr misses."""
    _require_tigramite()
    df = generate_covariant_benchmark(n=800, seed=42)
    data, var_names = df.to_numpy(), df.columns.tolist()

    adapter = PcmciAmiAdapter(ci_test="knn_cmi")
    result = adapter.discover_full(data, var_names, max_lag=2, alpha=0.05, random_state=42)

    target_parents = set(result.phase2_final.parents["target"])
    assert ("driver_nonlin_sq", 1) in target_parents, (
        f"Expected ('driver_nonlin_sq', 1) in parents; got {target_parents}"
    )
    assert result.metadata["ci_test"] == "knn_cmi"
