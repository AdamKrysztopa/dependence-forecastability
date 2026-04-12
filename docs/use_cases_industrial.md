<!-- type: how-to -->
# Industrial Use Cases

Concise scenarios for manufacturing, reliability, and predictive maintenance (PdM) teams that want a dependence-first decision path before full model development.

## Scenario Matrix

| Scenario | Input signal type | Recommended path | Expected output | Typical next decision |
|---|---|---|---|---|
| Predictability alarm on rolling windows | Single sensor or KPI stream segmented into fixed rolling windows | Run deterministic triage per window (`run_triage()`), track AMI AUC, pAMI AUC, and `directness_ratio` over time | Time-ordered predictability profile with shifts in class/ratio | Escalate windows with abrupt degradation for root-cause review or temporary fallback policies |
| Horizon-aware maintenance signals | Condition-monitoring series (vibration, temperature, pressure, cycle-time drift) with maintenance-relevant lead times | Use AMI/pAMI horizon curves to identify lag bands that stay significant near target action horizons | Horizon-band map of informative lags and directness strength | Choose monitoring horizon and retraining cadence aligned to actionable lead time |
| Driver screening for exogenous forecasting | Target demand/throughput series plus candidate external drivers (weather, upstream load, line states) | Run exogenous analysis (CrossAMI + pCrossAMI) to rank candidate drivers by robust lead-lag signal | Ranked driver list and lag-specific relevance evidence | Keep top drivers for feature set prototyping; drop low-signal drivers early |
| Signal readiness before model development | New or newly instrumented stream with uncertain quality or structure | Start with triage readiness gate, then AMI/pAMI only if checks pass | Readiness status plus initial forecastability/directness classification | Proceed to model benchmark only for ready signals; route failed signals to data-quality remediation |
| Post-maintenance regime comparison | Matched pre-maintenance and post-maintenance windows of the same process signal | Run the same AMI/pAMI configuration on both regimes and compare class, AUC, and `directness_ratio` deltas | Regime comparison snapshot showing structural dependence change | Confirm whether intervention improved direct predictable structure; decide whether to keep new regime |

## Practical Notes

- Keep windowing and `max_lag` configuration constant when comparing periods.
- Use the same random state and significance settings for fair ranking between assets.
- Treat results as screening diagnostics that feed, not replace, forecast backtests.
