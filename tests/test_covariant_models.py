"""Tests for V3-F00 covariant result models and V3-F05 CausalGraphPort.

Acceptance criteria (Phase 0):
- All new models importable from forecastability.utils.types
- All new models importable from forecastability (top-level)
- CausalGraphPort importable from forecastability.ports and forecastability
- isinstance check passes for a conformant object
- Round-trip: construct → model_dump() → reconstruct
- Frozen models reject mutation
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Import acceptance
# ---------------------------------------------------------------------------


def test_imports_from_utils_types() -> None:
    from forecastability.utils.types import (  # noqa: F401
        CausalGraphResult,
        CovariantAnalysisBundle,
        CovariantMethodConditioning,
        CovariantSummaryRow,
        GcmiResult,
        PcmciAmiResult,
        Phase0MiScore,
        TransferEntropyResult,
    )


def test_imports_from_top_level() -> None:
    from forecastability import (  # noqa: F401
        CausalGraphResult,
        CovariantAnalysisBundle,
        CovariantSummaryRow,
        GcmiResult,
        PcmciAmiResult,
        Phase0MiScore,
        TransferEntropyResult,
    )


def test_causal_graph_port_importable_from_ports() -> None:
    from forecastability.ports import CausalGraphPort  # noqa: F401


def test_causal_graph_port_not_in_top_level_public_api() -> None:
    """CausalGraphPort is an adapter interface, not a user-facing type.

    Ports are implementation contracts — they live in forecastability.ports,
    not in the top-level forecastability package.
    """
    import forecastability

    assert not hasattr(forecastability, "CausalGraphPort"), (
        "CausalGraphPort must not be in the top-level public API — it is an adapter interface"
    )


# ---------------------------------------------------------------------------
# isinstance runtime check for CausalGraphPort
# ---------------------------------------------------------------------------


def test_causal_graph_port_isinstance() -> None:
    import numpy as np

    from forecastability.ports import CausalGraphPort
    from forecastability.utils.types import CausalGraphResult

    class _ConformantAdapter:
        def discover(
            self,
            data: np.ndarray,
            var_names: list[str],
            *,
            max_lag: int,
            alpha: float = 0.01,
            random_state: int = 42,
        ) -> CausalGraphResult:
            return CausalGraphResult(parents={})

    assert isinstance(_ConformantAdapter(), CausalGraphPort)


def test_causal_graph_port_isinstance_fails_for_non_conformant() -> None:
    from forecastability.ports import CausalGraphPort

    class _BadAdapter:
        def run(self) -> None: ...

    assert not isinstance(_BadAdapter(), CausalGraphPort)


# ---------------------------------------------------------------------------
# CovariantSummaryRow round-trip
# ---------------------------------------------------------------------------


def test_covariant_summary_row_round_trip() -> None:
    from forecastability.utils.types import CovariantMethodConditioning, CovariantSummaryRow

    row = CovariantSummaryRow(
        target="temp",
        driver="humidity",
        lag=3,
        cross_ami=0.12,
        cross_pami=0.08,
        significance="above_band",
        rank=1,
        interpretation_tag="direct_driver",
        lagged_exog_conditioning=CovariantMethodConditioning(
            cross_ami="none",
            cross_pami="target_only",
        ),
    )
    dumped = row.model_dump()
    assert dumped["target"] == "temp"
    assert dumped["driver"] == "humidity"
    assert dumped["lag"] == 3
    assert dumped["transfer_entropy"] is None
    assert dumped["lagged_exog_conditioning"]["cross_ami"] == "none"
    reconstructed = CovariantSummaryRow(**dumped)
    assert reconstructed == row


def test_covariant_summary_row_all_optional_none() -> None:
    from forecastability.utils.types import CovariantSummaryRow

    row = CovariantSummaryRow(target="x", driver="y", lag=1)
    assert row.cross_ami is None
    assert row.cross_pami is None
    assert row.transfer_entropy is None
    assert row.gcmi is None
    assert row.pcmci_link is None
    assert row.pcmci_ami_parent is None
    assert row.significance is None
    assert row.rank is None
    assert row.interpretation_tag is None
    assert row.lagged_exog_conditioning.cross_ami is None
    assert row.lagged_exog_conditioning.pcmci is None


# ---------------------------------------------------------------------------
# TransferEntropyResult round-trip
# ---------------------------------------------------------------------------


def test_transfer_entropy_result_round_trip() -> None:
    from forecastability.utils.types import TransferEntropyResult

    te = TransferEntropyResult(
        source="x",
        target="y",
        lag=2,
        te_value=0.45,
        p_value=0.03,
        significant=True,
    )
    dumped = te.model_dump()
    assert dumped["te_value"] == pytest.approx(0.45)
    assert dumped["lagged_exog_conditioning"] == "target_only"
    reconstructed = TransferEntropyResult(**dumped)
    assert reconstructed == te


# ---------------------------------------------------------------------------
# GcmiResult round-trip
# ---------------------------------------------------------------------------


def test_gcmi_result_round_trip() -> None:
    from forecastability.utils.types import GcmiResult

    gcmi = GcmiResult(source="a", target="b", lag=1, gcmi_value=0.33)
    dumped = gcmi.model_dump()
    assert dumped["gcmi_value"] == pytest.approx(0.33)
    assert dumped["lagged_exog_conditioning"] == "none"
    reconstructed = GcmiResult(**dumped)
    assert reconstructed == gcmi


# ---------------------------------------------------------------------------
# CausalGraphResult round-trip with non-empty parents
# ---------------------------------------------------------------------------


def test_causal_graph_result_round_trip() -> None:
    from forecastability.utils.types import CausalGraphResult

    result = CausalGraphResult(
        parents={"y": [("x", 1), ("z", 2)]},
        link_matrix=[["-->", ""], ["", "-->"]],
        val_matrix=[[0.95, 0.0], [0.0, 0.88]],
        metadata={"alpha": 0.01, "method": "pcmci_plus"},
    )
    dumped = result.model_dump()
    assert dumped["parents"]["y"] == [("x", 1), ("z", 2)]
    assert dumped["lagged_exog_conditioning"] == "full_mci"
    reconstructed = CausalGraphResult(**dumped)
    assert reconstructed == result


def test_causal_graph_result_empty_parents() -> None:
    from forecastability.utils.types import CausalGraphResult

    result = CausalGraphResult(parents={})
    assert result.parents == {}
    assert result.link_matrix is None
    assert result.val_matrix is None


# ---------------------------------------------------------------------------
# Phase0MiScore round-trip
# ---------------------------------------------------------------------------


def test_phase0_mi_score_round_trip() -> None:
    from forecastability.utils.types import Phase0MiScore

    score = Phase0MiScore(source="x", lag=3, target="y", mi_value=0.22)
    dumped = score.model_dump()
    assert dumped["mi_value"] == pytest.approx(0.22)
    reconstructed = Phase0MiScore(**dumped)
    assert reconstructed == score


# ---------------------------------------------------------------------------
# PcmciAmiResult round-trip
# ---------------------------------------------------------------------------


def test_pcmci_ami_result_round_trip() -> None:
    from forecastability.utils.types import CausalGraphResult, PcmciAmiResult, Phase0MiScore

    empty_graph = CausalGraphResult(parents={})
    result = PcmciAmiResult(
        causal_graph=empty_graph,
        phase0_mi_scores=[Phase0MiScore(source="x", lag=1, target="y", mi_value=0.1)],
        phase0_pruned_count=5,
        phase0_kept_count=3,
        phase1_skeleton=empty_graph,
        phase2_final=empty_graph,
        ami_threshold=0.05,
    )
    dumped = result.model_dump()
    assert dumped["phase0_pruned_count"] == 5
    assert dumped["phase0_kept_count"] == 3
    assert len(dumped["phase0_mi_scores"]) == 1
    assert dumped["phase0_mi_scores"][0]["source"] == "x"
    assert dumped["lagged_exog_conditioning"] == "full_mci"
    reconstructed = PcmciAmiResult(**dumped)
    assert reconstructed == result


# ---------------------------------------------------------------------------
# CovariantAnalysisBundle — all optionals None
# ---------------------------------------------------------------------------


def test_covariant_analysis_bundle_minimal() -> None:
    from forecastability.utils.types import CovariantAnalysisBundle

    bundle = CovariantAnalysisBundle(
        summary_table=[],
        target_name="target",
        driver_names=["d1", "d2"],
        horizons=[1, 2, 3],
    )
    assert bundle.te_results is None
    assert bundle.gcmi_results is None
    assert bundle.pcmci_graph is None
    assert bundle.pcmci_ami_result is None
    assert bundle.metadata == {}


def test_covariant_analysis_bundle_round_trip() -> None:
    from forecastability.utils.types import (
        CausalGraphResult,
        CovariantAnalysisBundle,
        CovariantSummaryRow,
        GcmiResult,
        TransferEntropyResult,
    )

    row = CovariantSummaryRow(target="t", driver="d", lag=1, cross_ami=0.5)
    te = TransferEntropyResult(source="d", target="t", lag=1, te_value=0.3)
    gcmi = GcmiResult(source="d", target="t", lag=1, gcmi_value=0.25)
    graph = CausalGraphResult(parents={"t": [("d", 1)]})

    bundle = CovariantAnalysisBundle(
        summary_table=[row],
        te_results=[te],
        gcmi_results=[gcmi],
        pcmci_graph=graph,
        target_name="t",
        driver_names=["d"],
        horizons=[1],
    )
    dumped = bundle.model_dump()
    assert len(dumped["summary_table"]) == 1
    assert len(dumped["te_results"]) == 1
    reconstructed = CovariantAnalysisBundle(**dumped)
    assert reconstructed == bundle


# ---------------------------------------------------------------------------
# Frozen models reject mutation
# ---------------------------------------------------------------------------


def test_covariant_summary_row_is_frozen() -> None:
    from forecastability.utils.types import CovariantSummaryRow

    row = CovariantSummaryRow(target="x", driver="y", lag=1)
    with pytest.raises(ValidationError):
        row.lag = 99


def test_causal_graph_result_is_frozen() -> None:
    from forecastability.utils.types import CausalGraphResult

    result = CausalGraphResult(parents={})
    with pytest.raises(ValidationError):
        result.parents = {"z": []}


def test_pcmci_ami_result_is_frozen() -> None:
    from forecastability.utils.types import CausalGraphResult, PcmciAmiResult

    empty_graph = CausalGraphResult(parents={})
    result = PcmciAmiResult(
        causal_graph=empty_graph,
        phase0_mi_scores=[],
        phase0_pruned_count=0,
        phase0_kept_count=0,
        phase1_skeleton=empty_graph,
        phase2_final=empty_graph,
        ami_threshold=0.05,
    )
    with pytest.raises(ValidationError):
        result.ami_threshold = 0.99
