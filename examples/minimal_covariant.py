"""Minimal deterministic covariant bundle example."""

from forecastability import generate_covariant_benchmark, run_covariant_analysis

df = generate_covariant_benchmark(n=1200, seed=42)
target = df["target"].to_numpy()
drivers = {name: df[name].to_numpy() for name in df.columns if name != "target"}

bundle = run_covariant_analysis(
    target,
    drivers,
    target_name="target",
    max_lag=5,
    methods=["cross_ami", "cross_pami", "te", "gcmi"],
    n_surrogates=99,
    random_state=42,
)

print(
    {
        "rows": len(bundle.summary_table),
        "active_methods": bundle.metadata.get("active_methods"),
        "has_pcmci": bundle.pcmci_graph is not None,
    }
)
