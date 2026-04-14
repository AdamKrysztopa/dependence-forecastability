<!-- type: explanation -->
# Air Passengers Showcase Notebook

## Purpose

Provide a story-first notebook surface that markets the package around one
recognizable series. The goal is not to teach implementation internals; it is
to help a user quickly see the breadth of the toolkit and why the outputs are
useful.

## What The Notebook Shows

The notebook walks through 13 sections on the classic Air Passengers series:

1. **Data & seasonal profile** — load the series, visualise trend and seasonality.
2. **One-line triage** — `run_triage` produces a complete forecastability verdict in one call.
3. **Six diagnostics (F1–F6) + dashboard** — stationarity, autocorrelation, noise-floor, entropy, Lyapunov exponent, and spectral dominant-period, each with interpretive narrative, unified in a diagnostic dashboard.
4. **Scorer registry** — exercise four registered scorers (AMI, pAMI, CMI, spectral).
5. **Canonical AMI / pAMI** — surrogate-based significance bands and mediated decomposition of the dependence profile.
6. **Robustness study** — backend comparison (KSG vs permutation) and sample-size stress test.
7. **Rolling-origin evaluation** — map dependence metrics to realised sMAPE across expanding windows.
8. **Batch triage** — portfolio of five series with comparative ranking.
9. **Interpretation patterns A–E** — translate AMI/pAMI shapes into modelling-regime recommendations.
10. **Exogenous driver screening** — deterministic stub demonstrating the screening interface.
11. **Agent serialisation** — round-trip the triage result through the JSON bundle contract.
12. **Report generation** — produce a canonical Markdown report from the result object.
13. **Summary & surface map** — 12 key findings plus the five product surfaces (Python API, CLI, Dashboard, MCP server, PydanticAI agent).

## Positioning

- This is the first-stop showcase notebook for a new user.
- Runtime ownership still lives in `src/forecastability/`.
- Deep method details remain in `notebooks/triage/`.

## Notebook For Full Detail

- Showcase notebook: [../../notebooks/walkthroughs/00_air_passengers_showcase.ipynb](../../notebooks/walkthroughs/00_air_passengers_showcase.ipynb)
