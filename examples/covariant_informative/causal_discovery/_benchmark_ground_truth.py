"""Ground-truth tables and recovery-summary helpers for the covariant benchmark.

Private helper module used by the causal-discovery example scripts under
``examples/covariant_informative/causal_discovery``. The tables here mirror
the structural parents of ``target`` in
``forecastability.utils.synthetic.generate_covariant_benchmark`` and provide a
consistent recovery-summary printout across the three benchmark scripts.

This module is intentionally not exported from ``forecastability`` — it lives
next to the example scripts and is imported via a path-local ``sys.path``
insertion by each script.
"""

from __future__ import annotations

# Ground-truth structural parents of ``target`` in the covariant benchmark.
# Fields: (driver_name, lag, coefficient, mechanism)
GROUND_TRUTH_PARENTS: tuple[tuple[str, int, float, str], ...] = (
    ("target", 1, 0.75, "linear self-AR"),
    ("driver_direct", 2, 0.80, "linear lagged"),
    ("driver_mediated", 1, 0.50, "linear lagged"),
    ("driver_contemp", 0, 0.35, "linear contemporaneous"),
    ("driver_nonlin_sq", 1, 0.40, "quadratic (Pearson \u2248 0)"),
    ("driver_nonlin_abs", 1, 0.35, "absolute value (Pearson \u2248 0)"),
)

_GROUND_TRUTH_SET: frozenset[tuple[str, int]] = frozenset(
    (name, lag) for name, lag, _, _ in GROUND_TRUTH_PARENTS
)
_TARGET_NAME = "target"


def _format_parent(parent: tuple[str, int]) -> str:
    """Return ``name(t-lag)`` or ``name(t)`` when lag is 0."""
    source, lag = parent
    return f"{source}(t-{lag})" if lag > 0 else f"{source}(t)"


def print_ground_truth_table() -> None:
    """Print the full ground-truth parent table of ``target``."""
    print("Ground-truth parents of `target` (covariant benchmark):")
    print(f"  {'Parent':<22s} {'Lag':>3s} {'Coef':>6s}  Mechanism")
    print(f"  {'-' * 22} {'-' * 3} {'-' * 6}  {'-' * 28}")
    for name, lag, coef, kind in GROUND_TRUTH_PARENTS:
        print(f"  {name:<22s} {lag:>3d} {coef:>6.2f}  {kind}")
    print()


def summarize_recovery(
    *,
    method_label: str,
    recovered_parents: list[tuple[str, int]],
) -> str:
    """Build a per-ground-truth-parent recovery table for a method.

    Args:
        method_label: Human-readable label for the method column.
        recovered_parents: ``(driver_name, lag)`` tuples discovered by the
            method as parents of ``target``.

    Returns:
        A multi-line string. Each ground-truth parent is marked ``✓`` or ``✗``,
        followed by a trailing ``False positives:`` row that lists parents not
        in the ground-truth set. Self-lags ``(target, lag > 1)`` are reported
        as non-structural self-lag false positives.
    """
    recovered_set = {(name, lag) for name, lag in recovered_parents}

    lines: list[str] = []
    lines.append(f"Recovery summary — {method_label}:")
    lines.append(f"  {'Parent':<24s} {'Mechanism':<30s} Recovered")
    lines.append(f"  {'-' * 24} {'-' * 30} ---------")
    for name, lag, _coef, kind in GROUND_TRUTH_PARENTS:
        hit = (name, lag) in recovered_set
        mark = "\u2713" if hit else "\u2717"
        lines.append(f"  {_format_parent((name, lag)):<24s} {kind:<30s} {mark}")

    false_positives: list[tuple[str, int]] = []
    non_structural_self_lags: list[tuple[str, int]] = []
    for parent in sorted(recovered_set):
        if parent in _GROUND_TRUTH_SET:
            continue
        if parent[0] == _TARGET_NAME and parent[1] > 1:
            non_structural_self_lags.append(parent)
        else:
            false_positives.append(parent)

    if false_positives:
        rendered = ", ".join(_format_parent(p) for p in false_positives)
        lines.append(f"  False positives: {rendered}")
    else:
        lines.append("  False positives: (none)")

    if non_structural_self_lags:
        rendered = ", ".join(_format_parent(p) for p in non_structural_self_lags)
        lines.append(f"  Non-structural self-lag(s) (AR(1) has only lag-1 self-link): {rendered}")

    return "\n".join(lines)
