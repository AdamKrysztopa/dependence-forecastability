<!-- type: explanation -->
# Spectral Forecastability

The F01 spectral forecastability block is now implemented as a deterministic, AMI-adjacent summary of how concentrated a univariate series is in frequency space.

> [!IMPORTANT]
> The extended fingerprint remains AMI-first. Spectral diagnostics explain whether periodic or frequency-concentrated structure may be contributing to forecastability; they do not replace lagged-information analysis from [../theory/ami_information_geometry.md](../theory/ami_information_geometry.md).

## What The Current Diagnostic Computes

For a finite univariate series, the current diagnostic computes a normalized power spectral density, keeps only positive-frequency bins, and derives five bounded outputs:

- `spectral_entropy`: normalized spectral entropy on $[0, 1]$
- `spectral_predictability`: the complement of entropy, also on $[0, 1]$
- `spectral_concentration`: how strongly the dominant positive-frequency bin rises above a uniform baseline
- `dominant_periods`: the strongest unique inverse-frequency periods, reported in sample counts
- `periodicity_hint`: a conservative label in `{none, weak, moderate, strong}`

The entropy and predictability scores are related by:

$$
H_{spec} = \frac{-\sum_k p_k \log p_k}{\log K},
\qquad
P_{spec} = 1 - H_{spec}
$$

where $p_k$ is the normalized positive-frequency spectral mass and $K$ is the number of positive-frequency bins retained after normalization.

The current implementation supports deterministic detrending modes `linear` and `none`. Because no sampling interval is supplied, `dominant_periods` are reported in numbers of samples rather than calendar or physical time units.

## Relation To AMI Information Geometry

AMI information geometry and spectral forecastability answer different questions:

- AMI information geometry works in the lag domain and asks where predictive dependence survives correction and thresholding.
- Spectral forecastability works in the frequency domain and asks whether the series energy is diffuse or concentrated.
- Repeated AMI peaks and strong spectral concentration often support the same periodic interpretation, but they are not interchangeable diagnostics.

That separation is intentional. AMI remains the primary evidence for informative horizons. The spectral block adds explanatory context about whether a periodic or narrow-band mechanism may be helping to produce those horizons.

## Conservative Caveats

The implemented diagnostic is explicitly conservative in low-information or ambiguous settings.

- Very short series return a degenerate summary with `spectral_entropy = 1.0`, `spectral_predictability = 0.0`, `spectral_concentration = 0.0`, `periodicity_hint = none`, and an explanatory note.
- Constant series return the same conservative shape rather than a misleading pseudo-periodic answer.
- Strong low-frequency concentration can reflect trend contamination rather than stable periodic structure. In that case the diagnostic emits a note and downgrades the periodicity hint.
- When a non-`none` periodicity hint is paired with extracted periods, the notes remind the reader that periods are expressed in sample counts only.

## What This Block Is Good For

- explaining why a series with periodic AMI structure may also look concentrated in frequency space
- separating clean periodic signals from diffuse, noise-like spectra in a deterministic triage workflow
- adding a cheap secondary structure summary inside `ExtendedForecastabilityFingerprint.spectral`

## Non-Goals

- replacing AMI or pAMI as the primary lagged-information evidence
- inferring a physical sampling interval or calendar-aware seasonality unit
- proving that a particular seasonal model will win downstream
- turning the core package into a generic feature-extraction or model-selection zoo
- documenting `run_extended_forecastability_analysis(...)` as an available public workflow before that later-phase use case exists

## Current Repository Scope

- the stable result model `SpectralForecastabilityResult`
- the implemented spectral block used by the extended fingerprint composer
- theory and interpretation guidance for the shipped F01 behavior

F06 and later routing/use-case layers remain outside this page.

Richer walkthroughs and notebooks for this surface belong in the sibling `forecastability-examples` repository rather than the core repo.