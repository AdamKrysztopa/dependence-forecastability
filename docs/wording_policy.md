<!-- type: reference -->
# Wording Policy

Canonical frozen wording for the AMI → pAMI Forecastability Analysis project.
All docs, surfaces, release notes, and agent outputs must conform to these lines.

---

## Frozen lines

| Line | Canonical text |
|---|---|
| **Product** | "A deterministic forecastability triage toolkit with AMI as the paper-aligned foundation and pAMI as a project extension." |
| **Surface** | "CLI, API, notebooks, MCP, and agents are optional access or narration layers around the same deterministic outputs." |
| **Experimental** | "Largest Lyapunov exponent is experimental and excluded from automated triage decisions." |
| **Leakage** | "In rolling-origin evaluation, diagnostics are computed on train windows only and scoring on post-origin holdout only." |
| **Significance** | "Surrogate significance is optional, conditional on feasible sample size, and requires at least 99 surrogates." |

---

## Stability tiers

Use these exact tier labels — do not invent new gradations.

| Surface | Canonical stability label |
|---|---|
| Deterministic core (`run_triage`, AMI, pAMI) | **stable** |
| CLI / HTTP API | **beta** (until explicitly promoted) |
| MCP server | **experimental** (until explicitly promoted) |
| Agent runtime | **experimental** (until explicitly promoted) |
| Largest Lyapunov exponent (F5) | **experimental — excluded from automated triage** |

---

## Banned claims

Do not write any of the following in docs, release notes, or surface text:

- Agents or MCP compute or validate the science.
- pAMI proves direct causality or equals exact conditional mutual information.
- F5 (Largest Lyapunov exponent) is production-ready or contributes to triage decisions.
- The whole repo is uniformly stable.
- `directness_ratio > 1.0` is positive evidence (it is a warning or anomaly boundary).
- "Surrogates not computed" means "computed, none significant" — these are two distinct outcomes.
- Horizon-level AMI values have been collapsed before triage or interpretation.
- Rolling-origin diagnostics were computed on the full series (they must be train-window-only).
- Fewer than 99 surrogates are sufficient for significance bands.

---

## Notes on specific terms

- **AMI** — horizon-specific, paper-aligned. Never collapse horizons before triage.
- **pAMI** — project extension and approximate direct-dependence diagnostic. Not exact CMI; not causal proof.
- **Blocked result** — a distinct outcome from "low forecastability"; never conflate the two.
- **Significance absent** — always state whether surrogates were not computed (by choice or sample-size constraint) vs computed and showed no significant lags.

> [!IMPORTANT]
> Before publishing any wording that describes AMI, pAMI, or surface stability, check it against this page first.
