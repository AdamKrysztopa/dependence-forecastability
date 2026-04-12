"""Application service that builds TheoreticalLimitDiagnostics from an AMI curve."""

from __future__ import annotations

import numpy as np

from forecastability.triage.theoretical_limit_diagnostics import TheoreticalLimitDiagnostics

_NON_TRIVIAL_THRESHOLD = 0.01


def _build_ceiling_summary(ami_curve: np.ndarray) -> str:
    """Compose a one-sentence human-readable ceiling summary.

    Args:
        ami_curve: AMI values per horizon (0-indexed).

    Returns:
        Human-readable summary string.
    """
    if ami_curve.size == 0:
        return "No AMI data available — ceiling cannot be determined."
    peak = float(np.max(ami_curve))
    n_non_trivial = int(np.sum(ami_curve > _NON_TRIVIAL_THRESHOLD))
    peak_horizon = int(np.argmax(ami_curve)) + 1
    if n_non_trivial == 0:
        return (
            f"Ceiling is negligible (peak MI={peak:.4f});"
            f" no horizon exceeds {_NON_TRIVIAL_THRESHOLD}."
        )
    return (
        f"Peak MI={peak:.4f} at horizon {peak_horizon}; "
        f"{n_non_trivial} horizon(s) exceed the non-trivial threshold ({_NON_TRIVIAL_THRESHOLD})."
    )


def build_theoretical_limit_diagnostics(
    ami_curve: np.ndarray,
    *,
    compression_suspected: bool = False,
    dpi_suspected: bool = False,
) -> TheoreticalLimitDiagnostics:
    """Build a :class:`TheoreticalLimitDiagnostics` from a raw AMI curve.

    Under log loss, the mutual information at horizon h equals the maximum
    achievable predictive improvement for that horizon.  The AMI curve is
    therefore used directly as the forecastability ceiling.

    Args:
        ami_curve: AMI values per horizon, shape ``(H,)``, 0-indexed.
        compression_suspected: When ``True``, a compression warning is added
            to signal that aggregation or downsampling may have destroyed
            high-frequency information.
        dpi_suspected: When ``True``, a data-processing inequality warning is
            added to signal that the series may have been transformed in a way
            that reduces mutual information.

    Returns:
        A frozen :class:`TheoreticalLimitDiagnostics` instance.
    """
    ceiling_summary = _build_ceiling_summary(ami_curve)

    compression_warning: str | None = None
    if compression_suspected:
        compression_warning = (
            "Compression suspected: aggregation or downsampling may have destroyed "
            "high-frequency information, causing the ceiling to underestimate the "
            "true forecastability of the underlying process."
        )

    dpi_warning: str | None = None
    if dpi_suspected:
        dpi_warning = (
            "Data-processing inequality: the series appears to have been transformed "
            "(e.g. differencing, normalisation, encoding).  Post-transform MI cannot "
            "exceed pre-transform MI, so the ceiling reflects only the transformed signal."
        )

    return TheoreticalLimitDiagnostics(
        forecastability_ceiling_by_horizon=ami_curve.copy(),
        ceiling_summary=ceiling_summary,
        compression_warning=compression_warning,
        dpi_warning=dpi_warning,
        exploitation_ratio_supported=False,
    )
