"""Executable Phase 0 tests for extended diagnostic service scaffolds."""

from __future__ import annotations

import re
from collections.abc import Callable

import numpy as np
import pytest

from forecastability.services.classical_structure_service import compute_classical_structure
from forecastability.services.extended_fingerprint_service import (
    build_extended_forecastability_fingerprint,
)
from forecastability.services.memory_structure_service import compute_memory_structure
from forecastability.services.ordinal_complexity_service import compute_ordinal_complexity
from forecastability.services.spectral_forecastability_service import (
    compute_spectral_forecastability,
)


@pytest.mark.parametrize(
    ("invoke", "expected_message"),
    [
        (
            lambda: compute_spectral_forecastability(np.arange(8, dtype=float)),
            "Phase 0 scaffold only: compute_spectral_forecastability() is not implemented yet.",
        ),
        (
            lambda: compute_ordinal_complexity(np.arange(8, dtype=float)),
            "Phase 0 scaffold only: compute_ordinal_complexity() is not implemented yet.",
        ),
        (
            lambda: compute_classical_structure(np.arange(8, dtype=float)),
            "Phase 0 scaffold only: compute_classical_structure() is not implemented yet.",
        ),
        (
            lambda: compute_memory_structure(np.arange(8, dtype=float)),
            "Phase 0 scaffold only: compute_memory_structure() is not implemented yet.",
        ),
        (
            lambda: build_extended_forecastability_fingerprint(np.arange(8, dtype=float)),
            (
                "Phase 0 scaffold only: build_extended_forecastability_fingerprint() "
                "is not implemented yet."
            ),
        ),
    ],
)
def test_phase0_scaffold_functions_raise_clear_not_implemented(
    invoke: Callable[[], object],
    expected_message: str,
) -> None:
    """Each Phase 0 scaffold should execute and fail with a clear scaffold message."""
    with pytest.raises(NotImplementedError, match=re.escape(expected_message)):
        invoke()
