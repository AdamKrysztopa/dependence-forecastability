<!-- type: reference -->
# Should Have

These items are important and high-value, but they do not outrank paper-baseline parity or the core extension studies.

## 1. Frequency-wise extension report

Goal:
- Add a compact reporting layer that summarizes extension findings by frequency regime.

Acceptance criteria:
- Produces a report section or artifact per frequency group.
- Separates forecastability findings from exploitability findings.
- Makes AMI baseline and pAMI extension conclusions easy to compare within each frequency.

## 2. Extension ablation pack

Goal:
- Provide a reproducible study bundle for testing how extension conclusions change with lag cap, surrogate count, and scorer choice.

Acceptance criteria:
- Includes one reproducible configuration surface for ablations.
- Reports which conclusions are invariant and which are tuning-sensitive.
- Keeps benchmark comparisons frequency-aware rather than pooled into one global claim.
