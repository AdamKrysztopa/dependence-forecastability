"""Tests for the V3-F03 TigramiteAdapter (PCMCI+ wrapper)."""

from __future__ import annotations

import numpy as np
import pytest

from forecastability.adapters.tigramite_adapter import TigramiteAdapter
from forecastability.ports import CausalGraphPort
from forecastability.utils.synthetic import generate_covariant_benchmark
from forecastability.utils.types import CausalGraphResult


def _require_tigramite() -> None:
    pytest.importorskip("tigramite")


def _make_pcmci_fixture(n: int = 1400, seed: int = 42) -> tuple[np.ndarray, list[str]]:
    """8-variable covariant benchmark with known ground-truth causal structure.

    Includes two nonlinear drivers (driver_nonlin_sq, driver_nonlin_abs) whose
    coupling to target is invisible to Pearson/Spearman correlation but detectable
    by information-theoretic methods.
    """
    df = generate_covariant_benchmark(n=n, seed=seed)
    return df.to_numpy(), df.columns.tolist()


def test_discovers_direct_parent() -> None:
    _require_tigramite()
    data, var_names = _make_pcmci_fixture()
    adapter = TigramiteAdapter(ci_test="parcorr")
    assert isinstance(adapter, CausalGraphPort), (
        "TigramiteAdapter must satisfy CausalGraphPort protocol"
    )
    result = adapter.discover(data, var_names, max_lag=3, alpha=0.01, random_state=42)

    target_parents = set(result.parents["target"])
    assert ("driver_direct", 2) in target_parents, (
        f"Expected ('driver_direct', 2) in parents; got {target_parents}"
    )


def test_noise_driver_absent_or_much_less_likely() -> None:
    _require_tigramite()
    data, var_names = _make_pcmci_fixture()
    adapter = TigramiteAdapter(ci_test="parcorr")
    result = adapter.discover(data, var_names, max_lag=3, alpha=0.01, random_state=42)

    target_parents = result.parents["target"]
    direct_count = sum(1 for source, _lag in target_parents if source == "driver_direct")
    noise_count = sum(1 for source, _lag in target_parents if source == "driver_noise")
    assert direct_count >= 1, "driver_direct should appear as a parent of target"
    assert noise_count == 0 or noise_count * 2 <= direct_count, (
        f"driver_noise links ({noise_count}) should be absent or far fewer than "
        f"driver_direct links ({direct_count})"
    )


def test_discovers_contemporaneous_parent() -> None:
    """PCMCI+ should detect the contemporaneous driver_contemp -> target link.

    driver_contemp has a β=0.35 contemporaneous coupling to target
    (lag 0). PCMCI+ is specifically designed to detect contemporaneous
    links — this distinguishes it from standard PCMCI (lagged only).
    """
    _require_tigramite()
    data, var_names = _make_pcmci_fixture()
    adapter = TigramiteAdapter(ci_test="parcorr")
    result = adapter.discover(data, var_names, max_lag=3, alpha=0.05, random_state=42)

    target_parents = set(result.parents["target"])
    # driver_contemp has a genuine contemporaneous structural coupling (β=0.35).
    # Either as an oriented "-->" or unoriented "o-o" adjacency.
    # At n=1400, parcorr should reliably detect this at α=0.05.
    contemp_links = {p for p in target_parents if p[0] == "driver_contemp"}
    assert contemp_links, (
        f"Expected driver_contemp as contemporaneous parent of target. "
        f"Found parents: {sorted(target_parents)}"
    )


def test_synthetic_nonlinear_drivers_invisible_to_pearson() -> None:
    """Verify that driver_nonlin_sq and driver_nonlin_abs have near-zero Pearson
    correlation with target, confirming they are linearly invisible.

    Threshold: |r| < 0.10 at n=1500.  True Pearson is 0 by construction
    (odd-moment symmetry); finite-sample fluctuations stay well below 0.10.
    """
    from scipy import stats  # type: ignore[import-untyped]

    df = generate_covariant_benchmark(n=1500, seed=42)
    target = df["target"].to_numpy()

    for col in ("driver_nonlin_sq", "driver_nonlin_abs"):
        r, _ = stats.pearsonr(df[col].to_numpy(), target)
        assert abs(r) < 0.10, (
            f"Pearson({col}, target) = {r:.4f} — expected near-zero (|r| < 0.10); "
            "nonlinear coupling should be invisible to linear correlation"
        )


def test_parcorr_blind_to_nonlinear_drivers() -> None:
    """parcorr (linear CI test) should NOT recover the nonlinear structural drivers.

    driver_nonlin_sq and driver_nonlin_abs are genuine structural parents of
    target (quadratic and abs-value coupling respectively), but their coupling
    has zero linear correlation with target by construction.  A linear CI test
    such as parcorr cannot detect them — this is the key blind-spot story.
    """
    _require_tigramite()
    data, var_names = _make_pcmci_fixture()
    adapter = TigramiteAdapter(ci_test="parcorr")
    result = adapter.discover(data, var_names, max_lag=3, alpha=0.05, random_state=42)

    target_parents = set(result.parents["target"])
    sq_found = any(src == "driver_nonlin_sq" for src, _ in target_parents)
    abs_found = any(src == "driver_nonlin_abs" for src, _ in target_parents)

    # parcorr is a linear test — it must not see these nonlinear drivers.
    assert not sq_found, (
        f"parcorr found driver_nonlin_sq in parents {sorted(target_parents)} — "
        "expected linear CI test to be blind to the quadratic coupling"
    )
    assert not abs_found, (
        f"parcorr found driver_nonlin_abs in parents {sorted(target_parents)} — "
        "expected linear CI test to be blind to the abs-value coupling"
    )


def test_result_json_round_trip_and_metadata_sanity() -> None:
    _require_tigramite()
    data, var_names = _make_pcmci_fixture()
    adapter = TigramiteAdapter(ci_test="parcorr")
    result = adapter.discover(data, var_names, max_lag=3, alpha=0.01, random_state=42)

    payload = result.model_dump_json()
    restored = CausalGraphResult.model_validate_json(payload)

    assert restored == result
    assert restored.metadata["method"] == "pcmci_plus"
    assert restored.metadata["ci_test"] == "parcorr"
    assert restored.metadata["max_lag"] == 3
    assert restored.link_matrix is not None
    assert len(restored.link_matrix) == len(var_names)
