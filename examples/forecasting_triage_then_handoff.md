Use deterministic triage first.

If the result is blocked or weak, do data and readiness cleanup first and prefer simple baselines over heavier model search.

If the result is structured, use the detected lags, seasonality clues, and covariate signal to configure downstream forecasting tools.

This package is the triage layer before hand-off, not a model-fitting library.