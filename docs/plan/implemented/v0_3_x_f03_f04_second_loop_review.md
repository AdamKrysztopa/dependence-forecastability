<!-- type: reference -->
# V3-F03 / V3-F04 Second-Loop Review

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-04-17 |
| Scope | Second-loop review of V3-F03 (PCMCI+ adapter) and V3-F04 (PCMCI-AMI-Hybrid), closing V3-F04.2 |
| Related | [../../theory/pcmci_plus.md](../../theory/pcmci_plus.md), [../../implementation_status.md](../../implementation_status.md) |

## Summary verdict

The second-loop statistician audit returned a code-level correctness **PASS** for
V3-F03 and V3-F04. One statistical defect was identified — the default `knn_cmi`
permutation null (`shuffle_scheme="iid"`) over-rejects the true null of conditional
independence on raw autocorrelated series — and is mitigated by the opt-in
`shuffle_scheme="block"` added in V3-F04.2; the default remains i.i.d. for speed
and backward compatibility. Two wording-level issues are closed by this review:
contemporaneous `o-o` adjacency surfaced in `CausalGraphResult.parents` must not be
described as a directed parent, and `PcmciAmiResult.phase1_skeleton` /
`phase2_final` are aliases to the same tigramite output until the adapter is split
into `run_pc_stable` + `run_mci`. Nonlinear-parent recovery on the 8-variable
benchmark is benchmark-specific: at `seed=43, n=1200, max_lag=2, alpha=0.05`,
PCMCI-AMI recovers `driver_nonlin_sq(t-1)` and misses `driver_nonlin_abs(t-1)`.
All comparison scripts are therefore marked as illustrative synthetic evidence.

## Proposal vs implementation boundary

The following table records where the V3-F04 proposal and the shipped V3-F04 code
currently differ. "E" numbering follows the statistician audit Section E.

| # | Item | Proposal | Shipped (as of V3-F04.2) |
|---|---|---|---|
| E1 | Phase 0 screener | Past-window CrossAMI aggregating multiple lags into a single predictive-information score. | Single-lag unconditional MI (CrossMI); diagonal reduces to AMI at lag $h$. |
| E2 | Conditioning-set selection | MI-ranked conditioning sets inside PCMCI+ (condition on highest-MI candidates first). | Tigramite PCMCI+ default conditioning-set selection; no MI-based reordering. |
| E3 | Phase outputs | Distinct `phase1_skeleton` (PC₁ output) and `phase2_final` (MCI output). | Both fields alias the single graph object from `tigramite.run_pcmciplus`. |
| E4 | CI test | Fully non-parametric conditional independence. | Residualised hybrid: `linear_residual` conditioning removal + kNN MI on residuals + shuffle significance. |
| E5 | Null calibration | Time-series-aware null for autocorrelated inputs. | Default `shuffle_scheme="iid"`; opt-in `shuffle_scheme="block"` (Politis–Romano circular blocks, $L=\max(1,\,\operatorname{round}(1.75\,T^{1/3}))$) added in V3-F04.2. |
| E6 | `o-o` semantics | Directed parent claims only in `parents`. | `parents` also contains contemporaneous `o-o` adjacency (CPDAG Markov-equivalence class; unresolved orientation). |
| E7 | Significance knob | Independent PC₁ screening and MCI thresholds. | Single `alpha` knob collapses both; `contemp_collider_rule`, `conflict_resolution`, `fdr_method` not surfaced. |
| E8 | Synergy handling | Multivariate joint-MI scoring to catch synergistic parents. | Pairwise MI only — blind to configurations where $I(A;C)\approx 0,\ I(B;C)\approx 0,\ I(A,B;C)\gg 0$. |
| E9 | Phase 0 threshold | Significance-calibrated threshold. | Heuristic noise floor $\max(\operatorname{median}(\text{MI})\cdot 0.1,\,10^{-3})$. |
| E10 | Ground-truth listing | Include `target(t-1)` self-AR and both nonlinear parents in all benchmark documentation. | Closed by V3-F04.2: six-row truth table now used in `synthetic.py` docstring, theory doc, examples, and implementation status. |

## Pros and cons

### V3-F03 — PCMCI+

| Pros | Cons |
|---|---|
| MCI double conditioning controls for autocorrelation. | Single `alpha` knob conflates PC₁ screening and MCI threshold. |
| Handles lagged and contemporaneous links in one run. | `o-o` adjacency reported inside `CausalGraphResult.parents`. |
| Pluggable CI backends (`parcorr`, `gpdc`, `cmiknn`). | `contemp_collider_rule`, `conflict_resolution`, `fdr_method` not exposed. |
| Established reference implementation. | Global NumPy RNG mutation; single-threaded only. |

### V3-F04 — PCMCI-AMI-Hybrid

| Pros | Cons |
|---|---|
| Phase 0 pruning removes clearly independent pairs before CI testing. | Pairwise MI blind-spot for purely synergistic parents. |
| Residualised kNN CI can recover benchmark-specific nonlinear couplings. | Default i.i.d. shuffle over-rejects on raw autocorrelated data. |
| V3-F04.2: linear-residual vectorisation (QR-projector reuse across permutations). | `phase1_skeleton` / `phase2_final` alias the same tigramite output. |
| V3-F04.2: opt-in time-series-aware `shuffle_scheme="block"`. | "CrossAMI past-window" remains a proposal label, not the shipped path. |

## Acceptance criteria met by V3-F04.2

Documentation outcomes:

- [x] Six-row ground-truth parent table (including `target(t-1)` self-AR at $\beta=0.75$) present in `docs/theory/pcmci_plus.md`.
- [x] "What Phase 0 computes" subsection clarifying single-lag unconditional MI vs Catt's past-window CrossAMI.
- [x] "`o-o` output semantics" subsection flagging adjacency with unresolved orientation.
- [x] "`phase1_skeleton` vs `phase2_final`" subsection stating the alias relationship.
- [x] "Null calibration of `knn_cmi`" subsection documenting default i.i.d. vs opt-in block shuffle.
- [x] "Phase 0 threshold caveat" subsection including the synergy blind-spot.
- [x] Pros/cons tables for V3-F03 and V3-F04 in the theory doc.
- [x] `src/forecastability/utils/synthetic.py` docstring truth listing updated to six rows.
- [x] `docs/implementation_status.md` V3-F04 row marked **Partial / Experimental** and labels example scripts as illustrative synthetic evidence.

Code outcomes:

- [x] Linear-residual null-distribution vectorisation (QR-projector reuse across permutations); comparison script wall-clock ≈ 102.9 s → ≈ 97.9 s.
- [x] Opt-in `shuffle_scheme: Literal["iid", "block"] = "iid"` on `build_knn_cmi_test(...)`, `PcmciAmiAdapter(...)`, and `build_pcmci_ami_hybrid(...)`; block uses Politis–Romano $L=\max(1,\,\operatorname{round}(1.75\,T^{1/3}))$; unsupported values raise `ValueError`.

## Explicit out-of-scope for V3-F04.2

- Making `shuffle_scheme="block"` the default.
- Splitting `phase1_skeleton` and `phase2_final` into distinct outputs via `run_pc_stable` + `run_mci`.
- MI-ranked conditioning-set selection inside PCMCI+.
- Past-window CrossAMI triage in Phase 0.
- Exposing independent `alpha_level` / `contemp_collider_rule` / `conflict_resolution` / `fdr_method` controls.
- Synergy-case (joint-MI) detection in Phase 0.

## Cross-references

- Theory: [../../theory/pcmci_plus.md](../../theory/pcmci_plus.md)
- Status: [../../implementation_status.md](../../implementation_status.md)
- Examples:
  - [../../../examples/covariant_informative/causal_discovery/pcmci_plus_benchmark.py](../../../examples/covariant_informative/causal_discovery/pcmci_plus_benchmark.py)
  - [../../../examples/covariant_informative/causal_discovery/pcmci_ami_hybrid_benchmark.py](../../../examples/covariant_informative/causal_discovery/pcmci_ami_hybrid_benchmark.py)
  - [../../../examples/covariant_informative/causal_discovery/pcmci_plus_vs_pcmci_ami_benchmark.py](../../../examples/covariant_informative/causal_discovery/pcmci_plus_vs_pcmci_ami_benchmark.py)
- Benchmark helper: [../../../examples/covariant_informative/causal_discovery/_benchmark_ground_truth.py](../../../examples/covariant_informative/causal_discovery/_benchmark_ground_truth.py)
