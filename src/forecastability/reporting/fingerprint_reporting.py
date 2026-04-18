"""Fingerprint rendering helpers — V3_1-F05.

Compact rendering surface for :class:`FingerprintBundle` results: markdown
summaries, summary rows for tabular display, and JSON serialisation.
All functions are pure renderers — no scientific computation.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from pathlib import Path

from forecastability.utils.types import FingerprintBundle

_logger = logging.getLogger(__name__)

_SEPARATOR = "\n---\n"


def build_fingerprint_markdown(bundle: FingerprintBundle) -> str:
    """Build a markdown summary for a single :class:`FingerprintBundle`.

    Args:
        bundle: The fingerprint bundle to render.

    Returns:
        Markdown-formatted string summarising fingerprint and routing.
    """
    fp = bundle.fingerprint
    rec = bundle.recommendation

    if fp.directness_ratio is not None:
        dr_str = f"{fp.directness_ratio:.4f}"
    else:
        dr_str = "N/A"

    horizons = fp.informative_horizons
    if len(horizons) > 10:
        horizons_str = ", ".join(str(h) for h in horizons[:10]) + ", ..."
    else:
        horizons_str = ", ".join(str(h) for h in horizons) if horizons else "none"

    primary_str = ", ".join(rec.primary_families) if rec.primary_families else "none"
    secondary_str = ", ".join(rec.secondary_families) if rec.secondary_families else "none"
    cautions_str = ", ".join(rec.caution_flags) if rec.caution_flags else "none"

    rationale_lines = "\n".join(f"- {r}" for r in rec.rationale) if rec.rationale else "- (none)"

    profile_lines = "\n".join(f"- {k}: {v}" for k, v in bundle.profile_summary.items())

    return f"""# {bundle.target_name}

## Fingerprint
- information_mass: {fp.information_mass:.4f}
- information_horizon: {fp.information_horizon}
- information_structure: {fp.information_structure}
- nonlinear_share: {fp.nonlinear_share:.4f}
- directness_ratio: {dr_str}
- informative_horizons: [{horizons_str}]

## Routing Recommendation
- confidence: {rec.confidence_label}
- primary_families: {primary_str}
- secondary_families: {secondary_str}
- caution_flags: {cautions_str}

### Rationale
{rationale_lines}

## Profile Summary
{profile_lines}
"""


def build_fingerprint_panel_markdown(bundles: Sequence[FingerprintBundle]) -> str:
    """Build a combined markdown report for multiple bundles.

    Args:
        bundles: Sequence of :class:`FingerprintBundle` objects to render.

    Returns:
        Markdown string with each bundle separated by a horizontal rule.
    """
    if not bundles:
        return "# Fingerprint Panel\n\n_No bundles available._\n"
    return _SEPARATOR.join(build_fingerprint_markdown(b) for b in bundles)


def build_fingerprint_summary_row(bundle: FingerprintBundle) -> dict[str, str | int | float]:
    """Build a compact flat dictionary row for tabular display.

    Suitable for constructing a pandas DataFrame from a list of bundles.

    Args:
        bundle: The fingerprint bundle to summarise.

    Returns:
        Dictionary with scalar fields from fingerprint and recommendation.
    """
    fp = bundle.fingerprint
    rec = bundle.recommendation
    return {
        "target_name": bundle.target_name,
        "information_mass": fp.information_mass,
        "information_horizon": fp.information_horizon,
        "information_structure": fp.information_structure,
        "nonlinear_share": fp.nonlinear_share,
        "directness_ratio": (
            fp.directness_ratio if fp.directness_ratio is not None else float("nan")
        ),
        "confidence": rec.confidence_label,
        "primary_families": ", ".join(rec.primary_families),
        "n_cautions": len(rec.caution_flags),
    }


def save_fingerprint_bundle_json(
    bundle: FingerprintBundle,
    *,
    output_path: Path,
) -> None:
    """Serialise a :class:`FingerprintBundle` to JSON at *output_path*.

    Parent directories are created automatically.

    Args:
        bundle: The fingerprint bundle to serialise.
        output_path: Destination file path for the JSON output.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = bundle.model_dump()
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _logger.debug("Saved fingerprint bundle JSON to %s", output_path)
