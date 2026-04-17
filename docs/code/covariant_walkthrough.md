<!-- type: reference -->
# Covariant Walkthrough Notebook

Reference for the V3-F10 live notebook:
[../../notebooks/walkthroughs/01_covariant_informative_showcase.ipynb](../../notebooks/walkthroughs/01_covariant_informative_showcase.ipynb)

_Last verified for V3-F10 on 2026-04-17._

## Purpose

The covariant walkthrough notebook is the story-first companion to
[`scripts/run_showcase_covariant.py`](../../scripts/run_showcase_covariant.py).
It reuses the same synthetic benchmark and the same
`run_covariant_analysis()` facade, but presents the output as a guided
comparison across:

- pairwise lagged dependence (`cross_ami`)
- target-history-conditioned dependence (`cross_pami`)
- directional dependence (`transfer_entropy`)
- copula-based dependence (`gcmi`)
- multivariate causal discovery (`pcmci`, `pcmci_ami`)

The notebook is not the source of analytical logic. It only orchestrates
package APIs, renders figures, and prints deterministic result-driven notes.

## Runtime contract

- Data source: `forecastability.utils.synthetic.generate_covariant_benchmark`
- Main analysis entry point: `forecastability.use_cases.run_covariant_analysis`
- Deterministic interpretation: `forecastability.services.covariant_interpretation_service.interpret_covariant_bundle`
- Notebook-facing plotting/table helpers:
  `forecastability.reporting.covariant_walkthrough`

The benchmark sections reuse one full covariant bundle so the method sections
share exactly the same underlying run. The only auxiliary computations are:

- a monotone-transform sensitivity check for GCMI
- an F09-style directional pair for forward vs reverse TE

## Section map

| Section | Role | Main artifact(s) |
| --- | --- | --- |
| A | Explain why pairwise dependence is insufficient on its own | Markdown only |
| B | Show the synthetic benchmark and ground-truth driver roles | `section_b_*` |
| C | Compare CrossAMI and CrosspAMI | `section_c_*` |
| D | Compare GCMI against CrossAMI and show monotone-transform stability | `section_d_*` |
| E | Show TE on the benchmark and on a directional pair | `section_e_*` |
| F | Show PCMCI+ selected parents | `section_f_*` |
| G | Show PCMCI-AMI pruning and final parents | `section_g_*` |
| H | Show the unified ranked table and deterministic driver roles | `section_h_*` |
| Limitation | Reproduce the conditioning-scope table and point to v0.3.1 | `section_limitation_*` |

## Stable artifact paths

The notebook writes stable artifacts under:

- `outputs/notebooks/walkthroughs/01_covariant_informative_showcase/figures/`
- `outputs/notebooks/walkthroughs/01_covariant_informative_showcase/tables/`

Representative files:

- `section_shared_full_summary.csv`
- `section_h_driver_roles.csv`
- `section_limitation_conditioning_scope.csv`
- `section_c_cross_ami_heatmap.png`
- `section_g_phase0_overview.png`

## Notebook invariants

- The benchmark narrative must stay aligned with `generate_covariant_benchmark()`.
- The dedicated limitation section must remain titled:
  `Known limitation: exogenous autohistory is not conditioned out in CrossMI/pCrossAMI/TE—see v0.3.1`
- Benchmark computations must flow through `run_covariant_analysis()`.
- The notebook contract is checked by
  [../../scripts/check_notebook_contract.py](../../scripts/check_notebook_contract.py).

## Related references

- [covariant_showcase.md](covariant_showcase.md)
- [../theory/covariant_informative_walkthrough.md](../theory/covariant_informative_walkthrough.md)
- [../theory/covariant_summary_table.md](../theory/covariant_summary_table.md)
- [../theory/covariant_role_assignment.md](../theory/covariant_role_assignment.md)
