#!/usr/bin/env bash
set -euo pipefail

AR1_JSON="$(uv run python -c 'import json; from forecastability import generate_ar1; print(json.dumps(generate_ar1(n_samples=300, phi=0.8, random_state=42).tolist()))')"
uv run forecastability triage --series "$AR1_JSON" --goal univariate --max-lag 20 --n-surrogates 99 --random-state 42 --format json
