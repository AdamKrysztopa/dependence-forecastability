<!-- type: how-to -->
# Benchmark Fixture Reproducibility Set

This folder contains a tiny deterministic benchmark fixture used by docs and tests.

- Input fixture: `raw_horizon_table.csv`
- Frozen expected outputs: `expected/*.csv`

Rebuild and verify artifact consistency:

```bash
uv run python scripts/rebuild_benchmark_fixture_artifacts.py --verify
```

This command regenerates the summary artifacts (including `benchmark_summary_table.csv`) from
`raw_horizon_table.csv` and checks that they still match frozen expected outputs.
