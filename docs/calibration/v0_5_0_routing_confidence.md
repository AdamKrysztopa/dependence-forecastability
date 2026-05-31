# Routing-Confidence Calibration — v0.5.0

**Document type:** Calibration methodology and audit record  
**Feature:** RVH-F08  
**Script:** `scripts/run_routing_confidence_calibration.py`  
**Audit artifact:** `docs/calibration/v0_5_0_routing_confidence_audit.json`  
**Last updated:** 2026-05-24

---

## Purpose

The triage recommendation service (`services/recommendation_service.py`) assigns
a confidence label (`HIGH`, `MEDIUM`, `LOW`) to each forecastability run based on
the peak of the raw AMI curve.  Before v0.5.0, the thresholds that determine these
labels were hand-picked heuristics with no quantitative precision guarantee.

RVH-F08 introduces:

1. A calibration script that measures the actual precision of each confidence label
   against a synthetic ground-truth suite.
2. A committed audit JSON artifact that records what precision was achieved at the
   current thresholds.
3. This document, which explains the methodology and its limitations honestly.

The word **"calibrated"** appears in `recommendation_service.py` only in the audit
artifact and this document — not in any public docstring where thresholds were not
actually fitted against a precision target.

---

## Synthetic archetype suite

The calibration uses 10 synthetic archetypes, each with a ground-truth
confidence label derived from domain knowledge:

| Archetype | Ground truth | Rationale |
|---|---|---|
| White noise | LOW | No predictable structure; baseline |
| AR(1) φ=0.3 | MEDIUM | Weak linear structure |
| AR(1) φ=0.8 | HIGH | Strong linear structure, clear AMI peak |
| AR(2) φ=[0.6, 0.3] | HIGH | Multi-lag linear structure |
| Sine + AR(1) | HIGH | Periodic structure |
| Logistic map r=3.9 | HIGH | Deterministic chaos, high AMI at lag 1 |
| Random walk | HIGH | Unit root — lag-1 dominance |
| Seasonal AR(1) period=12 | HIGH | Clear seasonal structure |
| MA(1) θ=0.5 | MEDIUM | Short memory, moderate AMI |
| Heavy-noise AR(1) φ=0.1 | LOW | Near-white-noise |

Each archetype is instantiated with 100 independent noise replicates (N=400 observations each)
using `numpy.random.default_rng` seeded deterministically.

---

## Precision definition

For a confidence label L:

```text
Precision(L) = TP(L) / (TP(L) + FP(L))
```

where TP(L) = runs labelled L with ground-truth L, and FP(L) = runs labelled L with
a different ground-truth.

Precision is the fraction of runs *assigned label L* that are actually correct.
It does not measure recall (the fraction of correct-L runs that are identified).

---

## Threshold fitting methodology

The current thresholds are **hand-picked heuristics**:

```python
_TRIAGE_THRESHOLDS = {
    "nonlinear": (0.15, 0.05),  # (high_threshold, medium_threshold)
    ...
}
```

These values were chosen so that:
- White noise (AMI peak ≈ 0.02) → LOW
- AR(1) φ=0.8 (AMI peak ≈ 0.38) → HIGH

The calibration script measures achieved precision at these existing thresholds
and reports whether they meet the precision targets:
- HIGH target: ≥ 90% precision
- MEDIUM target: ≥ 75% precision

A true threshold-sweep calibration (selecting the smallest threshold that achieves
the target precision) is deferred to v0.5.1, when the calibration script will store
raw AMI peaks per run and sweep thresholds without re-running triage.

---

## Limitations and honesty notes

1. **In-sample calibration**: All 1000 runs (10 archetypes × 100 replicates) are
   used for both measurement and reporting. No hold-out set is used. Generalisation
   to real-world series is not guaranteed.

2. **10 archetypes is not comprehensive**: The suite covers the most common DGP
   families but misses heavy-tailed noise, structural breaks, and multivariate
   interactions. A future v0.5.1 audit would add ≥ 5 additional archetypes.

3. **AMI estimator change**: v0.5.0 changes the default AMI estimator from KSG-I
   to KSG-II. The calibration is run against the v0.5.0 KSG-II default. If
   `estimator='ksg1_sklearn'` is used, the precision figures do not apply.

4. **Series length**: All archetypes use N=400. Performance on shorter series
   (N < 200) is unknown and likely worse.

5. **The thresholds in `_TRIAGE_THRESHOLDS` are NOT updated by this script**.
   They remain hand-picked. The audit JSON documents the gap between the current
   thresholds and the precision target, giving the maintainer a quantitative signal
   for manual adjustment.

---

## CI integration

The audit JSON is committed as `docs/calibration/v0_5_0_routing_confidence_audit.json`.
It is not enforced by CI (see Open Question 6 in the release plan): a future calibration
regression would surface as a warning in the PR diff, not a CI failure.

To regenerate the audit:

```bash
uv run python scripts/run_routing_confidence_calibration.py
```

Expected wall-clock time: 10–30 minutes on a standard developer machine (1000 triage runs,
n_surrogates=99 each).

---

## Reading the audit JSON

```json
{
  "version": "0.5.0",
  "n_archetypes": 10,
  "n_noise_replicates": 100,
  "thresholds": [
    {
      "label": "high",
      "threshold": 0.15,
      "achieved_precision": 0.XXX,
      "target_precision": 0.90,
      "n_samples": NNN
    },
    ...
  ],
  "audit_timestamp": "2026-05-24T...",
  "notes": "..."
}
```

- `achieved_precision`: fraction of HIGH-labelled runs that are truly HIGH
- `target_precision`: the precision floor the calibration aims for
- `n_samples`: total number of runs assigned this label across all archetypes
