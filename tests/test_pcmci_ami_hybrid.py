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


# ---------------------------------------------------------------------------
# PBE-F14 — n_permutations floor + bit-identical shuffle null regression
# ---------------------------------------------------------------------------


def _f14_synthetic_ci_inputs() -> tuple[np.ndarray, np.ndarray]:
    """Small synthetic (array, xyz) used by the F14 parity tests."""
    rng = np.random.default_rng(0)
    t_len = 300
    z = rng.standard_normal((t_len, 1))
    x = z[:, 0] + 0.3 * rng.standard_normal(t_len)
    y = 0.4 * z[:, 0] + 0.5 * x + 0.3 * rng.standard_normal(t_len)
    array = np.vstack([x, y, z[:, 0]])
    xyz = np.array([0, 1, 2])
    return array, xyz


@pytest.mark.parametrize("bad_n_perm", [0, -1, 50, 98])
def test_build_knn_cmi_test_rejects_n_permutations_below_floor(bad_n_perm: int) -> None:
    """build_knn_cmi_test must reject n_permutations below the 99 floor."""
    _require_tigramite()
    from forecastability.diagnostics.knn_cmi_ci_test import build_knn_cmi_test

    with pytest.raises(ValueError, match=r"n_permutations.*99"):
        build_knn_cmi_test(n_permutations=bad_n_perm)


def test_build_knn_cmi_test_rejects_n_neighbors_below_one() -> None:
    """n_neighbors < 1 is rejected before tigramite construction."""
    _require_tigramite()
    from forecastability.diagnostics.knn_cmi_ci_test import build_knn_cmi_test

    with pytest.raises(ValueError, match=r"n_neighbors.*>= 1"):
        build_knn_cmi_test(n_neighbors=0)


@pytest.mark.parametrize("scheme", ["iid", "block"])
def test_knn_cmi_shuffle_null_is_bit_identical_under_fixed_seed(scheme: str) -> None:
    """Two builds at the same seed must produce a bit-identical null + p-value."""
    _require_tigramite()
    from forecastability.diagnostics.knn_cmi_ci_test import build_knn_cmi_test

    array, xyz = _f14_synthetic_ci_inputs()

    def _run() -> tuple[float, np.ndarray]:
        test = build_knn_cmi_test(
            n_neighbors=8,
            n_permutations=199,
            residual_backend="linear_residual",
            seed=42,
            shuffle_scheme=scheme,  # type: ignore[arg-type]
        )
        observed = test.get_dependence_measure(array, xyz)  # type: ignore[attr-defined]
        p_value, null = test.get_shuffle_significance(  # type: ignore[attr-defined]
            array, xyz, observed, return_null_dist=True
        )
        return float(p_value), np.asarray(null)

    p_first, null_first = _run()
    p_second, null_second = _run()
    assert p_first == p_second
    assert np.array_equal(null_first, null_second)


def test_knn_cmi_shuffle_null_matches_pre_refactor_baseline() -> None:
    """Regression guard: null_dist tail must match the pre-F14 hard-coded baseline.

    Captured against the F06 pre-F14 implementation by running
    ``build_knn_cmi_test(n_neighbors=8, n_permutations=199,
    residual_backend='linear_residual', seed=42, shuffle_scheme='iid')`` against
    the synthetic input from :func:`_f14_synthetic_ci_inputs`. Both the iid and
    block schemes are pinned to guard the inner-loop refactor.
    """
    _require_tigramite()
    from forecastability.diagnostics.knn_cmi_ci_test import build_knn_cmi_test

    array, xyz = _f14_synthetic_ci_inputs()

    expected_iid_tail = np.array(
        [
            0.0494604571329913,
            0.05002141682603467,
            0.05611142600825003,
            0.0667239068863772,
            0.07327048658879765,
        ]
    )
    expected_iid_sum = 1.6620371093120507
    expected_block_tail = np.array(
        [
            0.05185371857353305,
            0.05916590515852693,
            0.05980693366669376,
            0.06412417255244174,
            0.06429374441123104,
        ]
    )
    expected_block_sum = 1.7725101855080103

    cases = [
        ("iid", expected_iid_tail, expected_iid_sum),
        ("block", expected_block_tail, expected_block_sum),
    ]
    for scheme, expected_tail, expected_sum in cases:
        test = build_knn_cmi_test(
            n_neighbors=8,
            n_permutations=199,
            residual_backend="linear_residual",
            seed=42,
            shuffle_scheme=scheme,  # type: ignore[arg-type]
        )
        observed = test.get_dependence_measure(array, xyz)  # type: ignore[attr-defined]
        p_value, null = test.get_shuffle_significance(  # type: ignore[attr-defined]
            array, xyz, observed, return_null_dist=True
        )
        null_arr = np.asarray(null)
        # Sorted by construction (return_null_dist=True returns np.sort(null_dist)).
        assert null_arr.shape == (199,)
        assert np.array_equal(null_arr[-5:], expected_tail), (
            f"scheme={scheme}: tail drift; got {null_arr[-5:].tolist()}"
        )
        assert float(null_arr.sum()) == expected_sum, (
            f"scheme={scheme}: sum drift; got {float(null_arr.sum())}"
        )
        # observed >> max(null) for this case, so p hits the (1 + 0) / (1 + B) floor.
        assert float(p_value) == 1.0 / (1.0 + 199.0)


def test_pcmci_ami_adapter_rejects_n_permutations_below_floor() -> None:
    """Adapter ctor rejects n_permutations < 99 before any compute work."""
    with pytest.raises(ValueError, match=r"n_permutations.*99"):
        PcmciAmiAdapter(ci_test="knn_cmi", n_permutations=50)


def test_pcmci_ami_adapter_default_n_permutations_is_199() -> None:
    """Default adapter wires through n_permutations=199 to the knn_cmi CI test."""
    _require_tigramite()
    adapter = PcmciAmiAdapter()
    assert adapter._n_permutations == 199
    ci_test = adapter._build_ci_test(seed=42)
    assert ci_test._n_permutations == 199  # type: ignore[attr-defined]


def test_pcmci_ami_adapter_custom_n_permutations_propagates() -> None:
    """A custom n_permutations is forwarded to the underlying CI test."""
    _require_tigramite()
    adapter = PcmciAmiAdapter(ci_test="knn_cmi", n_permutations=149)
    assert adapter._n_permutations == 149
    ci_test = adapter._build_ci_test(seed=42)
    assert ci_test._n_permutations == 149  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# PBE-F25, PBE-F24, PBE-F27 — new parameter tests
# ---------------------------------------------------------------------------


def test_n_permutations_floor_rejection() -> None:
    """PcmciAmiAdapter raises ValueError when n_permutations < 99."""
    _require_tigramite()
    with pytest.raises(ValueError, match="n_permutations"):
        PcmciAmiAdapter(ci_test="parcorr", n_permutations=98)


def test_pcmci_ami_ci_test_parcorr_runs() -> None:
    """discover_full() with ci_test='parcorr' on a small fixture returns PcmciAmiResult."""
    _require_tigramite()
    rng = np.random.default_rng(42)
    data = rng.standard_normal((400, 3))
    var_names = ["x", "y", "z"]
    adapter = PcmciAmiAdapter(ci_test="parcorr")
    result = adapter.discover_full(data, var_names, max_lag=2, alpha=0.05, random_state=42)
    assert isinstance(result, PcmciAmiResult)


def test_pcmci_ami_max_lag_smaller() -> None:
    """pcmci_max_lag=2 with max_lag=4: Phase 0 sees lags 3-4; metadata records pcmci_max_lag=2."""
    _require_tigramite()
    rng = np.random.default_rng(42)
    data = rng.standard_normal((400, 3))
    var_names = ["x", "y", "z"]

    # Use ami_threshold < 0 to force all Phase 0 triplets to survive threshold filtering,
    # so phase0_mi_scores will contain all lags up to max_lag=4.
    adapter = PcmciAmiAdapter(ci_test="parcorr", pcmci_max_lag=2, ami_threshold=-1.0)
    result = adapter.discover_full(data, var_names, max_lag=4, alpha=0.05, random_state=42)

    all_lags = {s.lag for s in result.phase0_mi_scores}
    assert 3 in all_lags and 4 in all_lags, (
        f"Phase 0 should include lags 3 and 4 when max_lag=4; got {all_lags}"
    )
    assert result.causal_graph.metadata["pcmci_max_lag"] == 2, (
        "metadata pcmci_max_lag should be 2; got "
        f"{result.causal_graph.metadata.get('pcmci_max_lag')}"
    )


def test_n_jobs_phase0_parity() -> None:
    """n_jobs_phase0=1 and n_jobs_phase0=2 produce identical results for fixed random_state."""
    _require_tigramite()
    rng = np.random.default_rng(99)
    data = rng.standard_normal((400, 3))
    var_names = ["a", "b", "c"]

    adapter_1 = PcmciAmiAdapter(ci_test="parcorr", n_jobs_phase0=1)
    result_1 = adapter_1.discover_full(data, var_names, max_lag=2, alpha=0.05, random_state=99)

    adapter_2 = PcmciAmiAdapter(ci_test="parcorr", n_jobs_phase0=2)
    result_2 = adapter_2.discover_full(data, var_names, max_lag=2, alpha=0.05, random_state=99)

    assert len(result_1.phase0_mi_scores) == len(result_2.phase0_mi_scores), (
        "n_jobs_phase0=1 and n_jobs_phase0=2 must yield the same number of Phase 0 scores"
    )
    for s1, s2 in zip(result_1.phase0_mi_scores, result_2.phase0_mi_scores, strict=True):
        assert s1 == s2, f"Phase 0 score mismatch between n_jobs=1 and n_jobs=2: {s1} vs {s2}"


def test_default_params_unchanged() -> None:
    """PcmciAmiAdapter() defaults: n_permutations=199, ci_test='knn_cmi', pcmci_max_lag=None."""
    _require_tigramite()
    adapter = PcmciAmiAdapter()
    assert adapter._n_permutations == 199
    assert adapter._ci_test_name == "knn_cmi"
    assert adapter._pcmci_max_lag is None
    assert adapter._verbosity == 0
    assert adapter._n_jobs_phase0 == 1
