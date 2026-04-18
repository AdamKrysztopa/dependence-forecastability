"""Fingerprint live agent demo (experimental): V3_1-F05.2.

This example demonstrates the optional PydanticAI-powered fingerprint agent.
It runs in **strict mode** (``strict=True``) by default, which means:

- No API key is required.
- The LLM agent step is bypassed.
- Output is deterministic and produced by the A3 interpretation adapter.

This makes the demo safe to run in any CI or offline environment.  To exercise
the live LLM narration path, export a valid ``OPENAI_API_KEY`` or
``ANTHROPIC_API_KEY`` and remove the ``strict=True`` argument.

.. warning::
    The live-agent path is **experimental**.  The narrative produced by the LLM
    is not a quantitative guarantee and may contain inaccuracies.  Always verify
    claims against the deterministic fingerprint fields.

Usage:
    uv run python examples/univariate/agents/fingerprint_live_agent_demo.py

Optional (live narration — requires API key):
    OPENAI_API_KEY=sk-... uv run python examples/univariate/agents/fingerprint_live_agent_demo.py
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Literal

import numpy as np

from forecastability.adapters.llm.fingerprint_agent import (
    FingerprintExplanation,
    pydantic_ai_available,
    run_fingerprint_agent,
)
from forecastability.diagnostics.surrogates import compute_significance_bands
from forecastability.metrics.metrics import compute_ami
from forecastability.utils.synthetic import (
    generate_ar1_monotonic,
    generate_nonlinear_mixed,
    generate_seasonal_periodic,
    generate_white_noise,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_N: int = 500
_SEED: int = 42
_MAX_LAG: int = 24
_N_SURROGATES: int = 99
_AMI_FLOOR: float = 0.01
_NONLINEAR_DEMO_N: int = 700
_NONLINEAR_DEMO_STRENGTH: float = 0.9

_ARCHETYPES: list[tuple[str, np.ndarray]] = []  # populated at runtime

_LINEAR_FAMILIES: frozenset[str] = frozenset(
    {"arima", "ets", "linear_state_space", "dynamic_regression"}
)
_SEASONAL_FAMILIES: frozenset[str] = frozenset(
    {"tbats", "seasonal_state_space", "harmonic_regression", "seasonal_naive"}
)
_NONLINEAR_FAMILIES: frozenset[str] = frozenset(
    {"tree_on_lags", "tcn", "nbeats", "nhits", "nonlinear_tabular"}
)
_FALLBACK_FAMILIES: frozenset[str] = frozenset({"naive", "seasonal_naive", "downscope"})


@dataclass(frozen=True)
class _GatingDiagnostics:
    """Deterministic horizon-gating diagnostics for one archetype run."""

    horizons_above_ami_floor: list[int]
    surrogate_significant_horizons: list[int]
    informative_horizons_intersection: list[int]


@dataclass(frozen=True)
class _LiveRun:
    """Aggregated live-demo outputs for one archetype."""

    explanation: FingerprintExplanation
    gating: _GatingDiagnostics


@dataclass(frozen=True)
class _VerificationIssue:
    """Typed verification issue for mismatch reporting."""

    category: Literal["power_shortfall", "behavioral_contradiction"]
    message: str


def _build_archetypes() -> list[tuple[str, np.ndarray]]:
    """Return ordered (name, series) pairs for the four canonical archetypes.

    Returns:
        List of (name, 1-D numpy array) tuples.
    """
    return [
        ("white_noise", generate_white_noise(n=_N, seed=_SEED)),
        ("ar1_monotonic", generate_ar1_monotonic(n=_N, phi=0.85, seed=_SEED)),
        (
            "seasonal_periodic",
            generate_seasonal_periodic(n=_N, period=12, ar_phi=0.5, seasonal_phi=0.8, seed=_SEED),
        ),
        (
            "nonlinear_mixed",
            generate_nonlinear_mixed(
                n=max(_N, _NONLINEAR_DEMO_N),
                phi=0.6,
                nl_strength=_NONLINEAR_DEMO_STRENGTH,
                seed=_SEED,
            ),
        ),
    ]


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def _verify_explanation(*, name: str, run: _LiveRun) -> None:
    """Verify that the explanation matches expected patterns for the archetype.

    Prints OK / MISMATCH lines so output is easy to scan.

    Args:
        name: Archetype name.
        run: Aggregated archetype run outputs.
    """
    explanation = run.explanation
    issues = _verify_archetype(name=name, run=run)

    if not explanation.narrative or not explanation.narrative.strip():
        issues.append(
            _VerificationIssue(
                category="behavioral_contradiction",
                message="narrative is empty or missing",
            )
        )

    # Invariant: primary_families must not be empty
    if not explanation.primary_families:
        issues.append(
            _VerificationIssue(
                category="behavioral_contradiction",
                message="primary_families is empty",
            )
        )

    if issues:
        for issue in issues:
            tag = "POWER" if issue.category == "power_shortfall" else "CONTRADICTION"
            print(f"  [MISMATCH][{tag}] {name}: {issue.message}")
    else:
        print(f"  [OK]       {name}: explanation fields consistent with expected behaviour")


def _contains_any(families: list[str], allowed: frozenset[str]) -> bool:
    """Return True when at least one family label is in allowed set."""
    return any(f in allowed for f in families)


def _verify_archetype(*, name: str, run: _LiveRun) -> list[_VerificationIssue]:
    """Evaluate archetype-level expectations with issue categorisation."""
    exp = run.explanation
    all_families = list(exp.primary_families)
    gating = run.gating
    issues: list[_VerificationIssue] = []

    if name == "white_noise":
        if exp.information_mass > 0.08:
            issues.append(
                _VerificationIssue(
                    category="behavioral_contradiction",
                    message=(
                        "expected low information_mass for white noise (<= 0.08), "
                        f"got {exp.information_mass:.4f}"
                    ),
                )
            )
        if not _contains_any(all_families, _FALLBACK_FAMILIES):
            issues.append(
                _VerificationIssue(
                    category="behavioral_contradiction",
                    message=f"expected fallback families for white noise, got {all_families}",
                )
            )
        if exp.information_mass > 0.03 and exp.information_structure in {"monotonic", "periodic"}:
            issues.append(
                _VerificationIssue(
                    category="behavioral_contradiction",
                    message=(
                        "structure_not violated for white noise: expected not in "
                        f"['monotonic', 'periodic'], got {exp.information_structure!r}"
                    ),
                )
            )

    if name == "ar1_monotonic":
        if exp.information_structure not in {"none", "monotonic", "mixed"}:
            issues.append(
                _VerificationIssue(
                    category="behavioral_contradiction",
                    message=(
                        "expected structure in ['none', 'monotonic', 'mixed'] for AR(1), "
                        f"got {exp.information_structure!r}"
                    ),
                )
            )
        if exp.information_structure in {"monotonic", "mixed"} and not _contains_any(
            all_families, _LINEAR_FAMILIES
        ):
            issues.append(
                _VerificationIssue(
                    category="behavioral_contradiction",
                    message=f"AR(1) structure implies linear families, got {all_families}",
                )
            )
        if exp.information_structure == "none" and exp.information_mass <= 0.02:
            issues.append(
                _VerificationIssue(
                    category="power_shortfall",
                    message="AR(1) yielded none structure with near-zero mass",
                )
            )

    if name == "seasonal_periodic":
        if exp.information_structure not in {"periodic", "mixed", "monotonic"}:
            issues.append(
                _VerificationIssue(
                    category="behavioral_contradiction",
                    message=(
                        "expected seasonal structure in ['periodic', 'mixed', 'monotonic'], "
                        f"got {exp.information_structure!r}"
                    ),
                )
            )
        if not _contains_any(all_families, _SEASONAL_FAMILIES):
            issues.append(
                _VerificationIssue(
                    category="behavioral_contradiction",
                    message=f"expected seasonal families, got {all_families}",
                )
            )

    if name == "nonlinear_mixed":
        informative_count = len(gating.informative_horizons_intersection)
        if exp.information_mass < 0.02 or informative_count < 2:
            issues.append(
                _VerificationIssue(
                    category="power_shortfall",
                    message=(
                        "nonlinear archetype has weak informative support "
                        f"(mass={exp.information_mass:.4f}, informative_count={informative_count})"
                    ),
                )
            )
        elif exp.nonlinear_share < 0.08 and not _contains_any(all_families, _NONLINEAR_FAMILIES):
            issues.append(
                _VerificationIssue(
                    category="behavioral_contradiction",
                    message=(
                        "nonlinear archetype lacks nonlinear evidence and nonlinear routing "
                        f"(nonlinear_share={exp.nonlinear_share:.4f}, families={all_families})"
                    ),
                )
            )

    return issues


def _compute_gating_diagnostics(series: np.ndarray) -> _GatingDiagnostics:
    """Reconstruct deterministic gate sets for reporting and verification."""
    ami = compute_ami(
        series,
        _MAX_LAG,
        n_neighbors=8,
        min_pairs=30,
        random_state=_SEED,
    )
    _, upper = compute_significance_bands(
        series,
        metric_name="ami",
        max_lag=_MAX_LAG,
        n_surrogates=_N_SURROGATES,
        random_state=_SEED,
        n_jobs=1,
    )
    above = [int(h + 1) for h, v in enumerate(ami) if float(v) >= _AMI_FLOOR]
    significant = [int(h + 1) for h, v in enumerate(ami) if float(v) > float(upper[h])]
    informative = sorted(set(above).intersection(significant))
    return _GatingDiagnostics(
        horizons_above_ami_floor=above,
        surrogate_significant_horizons=significant,
        informative_horizons_intersection=informative,
    )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def _print_explanation(name: str, run: _LiveRun) -> None:
    """Print a formatted explanation report for one archetype.

    Args:
        name: Archetype name.
        run: Aggregated archetype run outputs.
    """
    explanation = run.explanation
    gating = run.gating

    separator = "─" * 68
    print(f"\n{separator}")
    print(f"  ARCHETYPE: {name.upper()}")
    print(separator)
    print(f"  target_name           : {explanation.target_name}")
    print(f"  information_mass      : {explanation.information_mass:.6f}")
    print(f"  information_horizon   : {explanation.information_horizon}")
    print(f"  information_structure : {explanation.information_structure}")
    print(f"  nonlinear_share       : {explanation.nonlinear_share:.6f}")
    print(f"  primary_families      : {explanation.primary_families}")
    print(f"  confidence_label      : {explanation.confidence_label}")
    print("\n  Gating diagnostics:")
    print(f"    horizons_above_floor   : {gating.horizons_above_ami_floor}")
    print(f"    surrogate_significant  : {gating.surrogate_significant_horizons}")
    print(f"    informative_intersect  : {gating.informative_horizons_intersection}")
    print("\n  Narrative:")
    # Wrap narrative at 66 chars for readability
    words = explanation.narrative.split()
    line: list[str] = []
    for word in words:
        line.append(word)
        if sum(len(w) + 1 for w in line) > 64:
            print("    " + " ".join(line[:-1]))
            line = [line[-1]]
    if line:
        print("    " + " ".join(line))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def _run_all_archetypes(*, strict: bool) -> None:
    """Run the fingerprint agent on all four archetypes.

    Args:
        strict: If True, skip the live LLM call and use the deterministic fallback.
    """
    archetypes = _build_archetypes()
    runs: list[tuple[str, _LiveRun]] = []

    for name, series in archetypes:
        print(f"\n  Running fingerprint agent for: {name} (strict={strict}) …")
        explanation = await run_fingerprint_agent(
            series,
            target_name=name,
            max_lag=_MAX_LAG,
            n_surrogates=_N_SURROGATES,
            random_state=_SEED,
            ami_floor=_AMI_FLOOR,
            strict=strict,
        )
        gating = _compute_gating_diagnostics(series)
        runs.append((name, _LiveRun(explanation=explanation, gating=gating)))

    print("\n\n" + "=" * 68)
    print("  FINGERPRINT AGENT RESULTS")
    print("=" * 68)

    for name, run in runs:
        _print_explanation(name, run)

    print("\n\n  ── Verification ──────────────────────────────────────────")
    for name, run in runs:
        _verify_explanation(name=name, run=run)

    print("\n  ── Cross-archetype summary ───────────────────────────────")
    print(
        f"  {'Archetype':<22} {'Structure':<12} {'Mass':>8} {'NL Share':>9} {'Families'}"
    )
    print("  " + "─" * 64)
    for name, run in runs:
        exp = run.explanation
        families = ", ".join(exp.primary_families[:2])
        print(
            f"  {name:<22} {exp.information_structure:<12} "
            f"{exp.information_mass:>8.4f} {exp.nonlinear_share:>9.4f}  {families}"
        )


def main() -> None:
    """Entry point for the fingerprint live agent demo."""
    print("=" * 68)
    print("  FINGERPRINT LIVE AGENT DEMO  (V3_1-F05.2 — EXPERIMENTAL)")
    print("=" * 68)

    import os

    has_key = bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))
    allow_live = os.getenv("FINGERPRINT_LIVE_DEMO_ALLOW_LIVE", "").lower() in {
        "1",
        "true",
        "yes",
    }
    use_strict = True

    if allow_live and has_key and pydantic_ai_available:
        use_strict = False

    if use_strict:
        print("\n  Mode: STRICT (deterministic fallback — no LLM)")
        print(
            "  To opt into live narration, set FINGERPRINT_LIVE_DEMO_ALLOW_LIVE=1 "
            "and export an API key."
        )
    else:
        print("\n  Mode: LIVE (PydanticAI narration)")
        print("\n  *** EXPERIMENTAL — narrative may contain inaccuracies ***")
        print("  Always verify claims against the deterministic fingerprint fields.")

    asyncio.run(_run_all_archetypes(strict=use_strict))

    print("\n" + "=" * 68)
    print("  Demo complete.")
    print("=" * 68)


if __name__ == "__main__":
    main()
