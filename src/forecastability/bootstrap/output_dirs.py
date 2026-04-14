"""Runtime bootstrap: prepare output directories from an OutputConfig."""

from forecastability.utils.config import OutputConfig


def prepare_output_dirs(config: OutputConfig) -> None:
    """Create all output directories defined in *config* if they don't exist.

    This is the only place that performs filesystem side effects for
    output path preparation. Call once at script entry-points (e.g.,
    scripts/run_canonical_examples.py) before writing any artifacts.

    Args:
        config: Validated output configuration.
    """
    for attr in ("figures_dir", "tables_dir", "json_dir", "reports_dir"):
        path = getattr(config, attr, None)
        if path is not None:
            path.mkdir(parents=True, exist_ok=True)
