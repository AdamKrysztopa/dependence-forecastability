<!-- type: explanation -->
# Canonical Forecastability Notebook: Durable Summary

## Purpose

Summarize the core univariate AMI to pAMI story from the canonical notebook in one maintainable page that can be read without opening Jupyter.

Scope covered:
- horizon-specific AMI and pAMI behavior,
- forecastability class outcomes,
- directness interpretation for model-family triage.

## Key Figure

![Sine-wave AMI and pAMI overlay](../../outputs/figures/canonical/sine_wave_overlay.png)

Figure source: [../../outputs/figures/canonical/sine_wave_overlay.png](../../outputs/figures/canonical/sine_wave_overlay.png)

Why this figure matters: the sine-wave case shows a high AMI profile with much lower pAMI after conditioning, which demonstrates mediated dependence and motivates compact structured models.

## Key Result

From [../../outputs/json/canonical_examples_summary.json](../../outputs/json/canonical_examples_summary.json):

- Forecastability class split across 8 canonical series is 2 high, 1 medium, 5 low.
- Sine wave: AUC AMI = 145.05, AUC pAMI = 2.28, directness ratio = 0.0157.
- AirPassengers: AUC AMI = 57.71, AUC pAMI = 5.73, directness ratio = 0.0993.
- Simulated stock returns remain low forecastability (AUC AMI = 0.8879).

These outcomes preserve the notebook-level interpretation while making the decision signal immediately visible in docs.

## Takeaways

- Use AMI first for overall forecastability screening at each horizon.
- Use pAMI to separate direct lag signal from mediated lag chains.
- Prioritize compact structured models when AMI is high but directness is low.
- Keep notebooks as deep evidence and reproducible context, not as the only explanation layer.

## Notebook For Full Detail

- Full walkthrough: [../../notebooks/walkthroughs/01_canonical_forecastability.ipynb](../../notebooks/walkthroughs/01_canonical_forecastability.ipynb)
