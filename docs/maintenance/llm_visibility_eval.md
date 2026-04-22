<!-- type: how-to -->

# How to Evaluate LLM Visibility (Machine-Guidance Surfaces)

This guide lets repo maintainers verify that the machine-guidance surfaces —
`llms.txt`, `.github/copilot-instructions.md`, `AGENTS.md`, and path-specific
instruction files — actually bias coding assistants toward **triage-first**
behavior on forecasting prompts.

> [!IMPORTANT]
> Run this evaluation after every change to a machine-guidance surface.
> A degraded pass rate means an instruction update broke the triage-first routing.

---

## Procedure

1. Open a Copilot, Codex, or Claude-based assistant with the repo in context
   (e.g. VS Code Copilot Chat with the workspace folder open).
2. Paste each benchmark prompt **verbatim** — do not add extra framing.
3. Check the response against the **Expected good behavior** bullets.
4. Record `PASS` or `FAIL` in the scoring table below.
5. If fewer than 4 of 5 prompts pass, inspect which instruction file controls
   the failing path and revise it before re-running.

> [!TIP]
> Run the evaluation in a fresh chat session for each prompt to avoid
> context bleeding from earlier responses influencing later ones.

---

## Benchmark Prompts

### P-01 — Univariate model selection

> I have daily sales data. Which forecasting model should I use?

**Expected good behavior**

- Proposes running deterministic forecastability triage *before* naming any model
- Mentions checking readiness, informative horizons, and primary lags
- References `forecastability` or `run_triage` or `examples/minimal_python.py`
- Frames model families (XGBoost, Prophet, StatsForecast) as post-triage hand-off targets
- Does not open with "you should use XGBoost / SARIMA / Prophet"

**Red flags**

- Recommends a specific model or library in the first sentence
- Makes no mention of forecastability triage
- Skips readiness or leakage-risk checks entirely

---

### P-02 — Covariate-aware setup

> I have target + promo + price covariates. Can you help me set up Darts?

**Expected good behavior**

- Runs (or recommends running) covariate informativeness screening first
- Checks whether covariates are informative horizons before wiring them into Darts
- Flags leakage risk if future covariate values would be required at inference time
- Positions Darts as the downstream hand-off target, not the starting point
- References `examples/minimal_covariant.py` or `forecastability.triage`

**Red flags**

- Jumps directly to `TFTModel` or `NBEATSModel` configuration
- Ignores the covariate screening / informativeness step
- Does not mention leakage risk for future-valued covariates

---

### P-03 — Deep-learning model request

> Can you train an LSTM on this time series?

**Expected good behavior**

- Responds with a triage-first redirect before discussing any LSTM code
- Mentions checking readiness and whether the series has enough informative signal
- Notes that a blocked result (low AMI / pAMI across all lags) would make LSTM
  training unreliable regardless of architecture
- If triage passes, frames LSTM as one plausible hand-off target

**Red flags**

- Provides LSTM training code without any triage step
- Does not mention AMI, pAMI, or forecastability at all
- Treats model selection as the primary concern

---

### P-04 — Pre-framework readiness

> What should I inspect before using Nixtla?

**Expected good behavior**

- Lists the canonical triage checklist: readiness, leakage risk, informative
  horizons, primary lags, seasonality structure, covariate informativeness
- Recommends running `forecastability` or the canonical pipeline scripts first
- Frames Nixtla (StatsForecast / TimeGPT) as a post-triage destination
- Mentions that a blocked result should pause framework selection entirely

**Red flags**

- Answers with Nixtla API setup or `pip install nixtla` instructions only
- Skips the forecastability triage checklist
- Does not reference the deterministic triage toolkit at all

---

### P-05 — Batch / panel triage

> I have 200 SKUs and want to decide which ones are worth modelling at all.
> How should I approach this?

**Expected good behavior**

- Recommends batch forecastability triage as the entry point
- Mentions screening by readiness score and blocked-result filtering
- References `forecastability.triage` batch API or the panel benchmark scripts
- Suggests discarding or deprioritising SKUs with low informative horizons
- Does not suggest fitting 200 models as the first step

**Red flags**

- Immediately suggests fitting a model per SKU without triage
- Ignores readiness or blocked-result concepts
- Frames the problem purely as a compute/parallelism question

---

## Scoring Table

Copy this table into your notes each time you run the evaluation.

| Prompt | Date | Guidance surface version | Result |
|--------|------|--------------------------|--------|
| P-01   |      |                          |        |
| P-02   |      |                          |        |
| P-03   |      |                          |        |
| P-04   |      |                          |        |
| P-05   |      |                          |        |

---

## Pass Criteria

**4 out of 5 prompts must pass** for the guidance layer to be considered healthy.

A prompt passes when every **Expected good behavior** bullet is present in the
response and no **Red flag** bullet appears in the first three paragraphs.

> [!NOTE]
> A partial pass (triage mentioned but buried after model recommendations) counts
> as a FAIL — correct steering means triage-first, not triage-eventually.

---

## When to Re-Run

Re-run this evaluation whenever any of the following files change:

- `llms.txt`
- `.github/copilot-instructions.md`
- `AGENTS.md`
- `.github/instructions/*.instructions.md`

> [!WARNING]
> Changing the wording of the triage-first routing rule in any of the above
> files can silently degrade LLM routing even when all unit tests pass.
> This evaluation is the only automated check for that regression.
