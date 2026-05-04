<!-- type: explanation -->
# Classical Structure

The F03 classical structure block is now implemented as a deterministic summary of simple autocorrelation, trend, and optional seasonality structure around an AMI-first workflow.

> [!IMPORTANT]
> The extended fingerprint remains AMI-first. Classical diagnostics explain whether forecastability appears to align with cheap trend, seasonality, and autocorrelation summaries; they do not replace the primary lagged-information analysis.

## What The Current Diagnostic Computes

The implemented service reports five deterministic structure summaries plus a label:

- `acf1`: lag-1 autocorrelation when it can be computed safely
- `acf_decay_rate`: a bounded early-lag decay summary over the first lags up to `max_lag`
- `trend_strength`: variance-explained strength of a least-squares linear trend
- `seasonal_strength`: optional seasonality strength on the detrended series
- `residual_variance_ratio`: the variance remaining after subtracting the fitted deterministic components
- `stationarity_hint`: a conservative label in `{likely_stationary, trend_nonstationary, seasonal, unclear}`

The trend component is a deterministic least-squares line. The seasonality path uses phase means on the detrended series and compares the resulting seasonal template with autocorrelation at the supplied period.

## Seasonality Requires An Explicit Period

> [!IMPORTANT]
> `seasonal_strength` is only computed when `period` is supplied. If `period` is omitted, `seasonal_strength` is intentionally `None`.

This resolved behavior is deliberate:

- the service does not infer a candidate period on its own
- the absence of `period` means the seasonality block is skipped, not guessed
- if fewer than two full seasonal cycles are available, the diagnostic emits a note and leaves `seasonal_strength` unset

That keeps the classical block deterministic and avoids turning a cheap explanatory summary into an undocumented period-search routine.

## How To Read The Result

- high `acf1` with modest trend and no seasonal block often points to short-memory linear dependence
- high `trend_strength` pushes the label toward `trend_nonstationary`
- high `seasonal_strength`, when a valid `period` is supplied, pushes the label toward `seasonal`
- low `acf1`, weak trend, and weak or absent seasonality support `likely_stationary`

These are structure hints, not fitted decomposition outputs. Their role is to explain why the AMI profile may show monotone persistence, repeated peaks, or weak signal.

## Conservative Caveats

- Very short series return an `unclear` summary with `None` fields rather than unstable numeric estimates.
- Constant series also return `None` structure fields and an explicit note.
- `residual_variance_ratio` is only computed when the original variance is safely nonzero.
- The seasonal path is intentionally absent unless the caller provides `period`.

## Non-Goals

- replacing AMI/pAMI or the existing `ForecastabilityProfile`
- claiming that classical structure implies a particular downstream winner
- shipping automatic differencing, decomposition fitting, or framework-specific helpers from the core repo
- inferring seasonality automatically when `period` is omitted
- documenting `run_extended_forecastability_analysis(...)` as an implemented public entry point before that later phase lands
- moving examples or walkthrough notebooks into this repository

## Current Repository Scope

- the stable result model `ClassicalStructureResult`
- the implemented classical diagnostic block used by the extended fingerprint composer
- theory and interpretation guidance for the shipped F03 behavior

F06 and later routing/use-case layers remain outside this page.

Richer walkthroughs and notebooks for classical-structure reading belong in the sibling `forecastability-examples` repository rather than the core repo.