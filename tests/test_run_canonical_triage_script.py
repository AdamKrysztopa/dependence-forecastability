"""Focused tests for scripts/run_canonical_triage.py flags and gating behavior."""

from __future__ import annotations

import time
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

import numpy as np

from forecastability.utils.io_models import CanonicalSummaryBundle
from forecastability.utils.types import CanonicalExampleResult, MetricCurve


def _load_script_module() -> ModuleType:
    """Load scripts/run_canonical_triage.py as an importable module.

    Returns:
        Loaded module object.

    Raises:
        RuntimeError: If the module cannot be loaded from disk.
    """
    repo_root = Path(__file__).resolve().parents[1]
    file_path = repo_root / "scripts" / "run_canonical_triage.py"
    spec = spec_from_file_location("run_canonical_triage_script", file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module spec for {file_path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_args_defaults_disable_extensions() -> None:
    """Default script flags should keep mixed bands mode on and extensions off."""
    module = _load_script_module()

    args = module._parse_args([])

    assert args.no_bands is False
    assert args.full_bands is False
    assert args.with_extensions is False


def test_parse_args_allows_with_extensions_flag() -> None:
    """with-extensions flag should be parsed as True when provided."""
    module = _load_script_module()

    args = module._parse_args(["--with-extensions"])

    assert args.no_bands is False
    assert args.with_extensions is True


def test_parse_args_allows_full_bands_flag() -> None:
    """full-bands flag should be parsed as True when provided."""
    module = _load_script_module()

    args = module._parse_args(["--full-bands"])

    assert args.no_bands is False
    assert args.full_bands is True


def test_extensions_enabled_requires_flag_and_bands() -> None:
    """Extensions are enabled only when explicitly requested and bands are active."""
    module = _load_script_module()

    assert module._extensions_enabled(with_extensions=True, skip_bands=False) is True
    assert module._extensions_enabled(with_extensions=False, skip_bands=False) is False
    assert module._extensions_enabled(with_extensions=True, skip_bands=True) is False


def test_skip_bands_policy_defaults_and_overrides() -> None:
    """Default policy should keep bands for core examples and skip them for long finance series."""
    module = _load_script_module()

    assert (
        module._skip_bands_for_dataset(
            "sine_wave",
            skip_bands=False,
            full_bands=False,
        )
        is False
    )
    assert (
        module._skip_bands_for_dataset(
            "bitcoin_returns",
            skip_bands=False,
            full_bands=False,
        )
        is True
    )
    assert (
        module._skip_bands_for_dataset(
            "bitcoin_returns",
            skip_bands=False,
            full_bands=True,
        )
        is False
    )
    assert (
        module._skip_bands_for_dataset(
            "sine_wave",
            skip_bands=True,
            full_bands=True,
        )
        is True
    )


def test_parse_args_accepts_max_workers() -> None:
    """max-workers should be parsed as a positive integer when provided."""
    module = _load_script_module()

    args = module._parse_args(["--max-workers", "2"])

    assert args.max_workers == 2


def _dummy_result(series_name: str, *, peak: float) -> CanonicalExampleResult:
    """Build a lightweight canonical result for runner orchestration tests."""
    ami = np.array([peak, peak * 0.7, peak * 0.4], dtype=float)
    pami = np.array([peak * 0.6, peak * 0.35, peak * 0.2], dtype=float)
    return CanonicalExampleResult(
        series_name=series_name,
        series=np.linspace(0.0, 1.0, 96),
        ami=MetricCurve(
            values=ami,
            significant_lags=np.array([1, 2], dtype=int),
        ),
        pami=MetricCurve(
            values=pami,
            significant_lags=np.array([1], dtype=int),
        ),
        metadata={"seasonal_period": 0},
    )


def test_run_canonical_triage_preserves_summary_order(tmp_path: Path, monkeypatch) -> None:
    """Parallel compute should still write summary artifacts in dataset order."""
    module = _load_script_module()
    dataset_specs = [
        ("alpha", np.arange(96, dtype=float), {"seasonal_period": 0}),
        ("beta", np.arange(96, dtype=float), {"seasonal_period": 0}),
        ("gamma", np.arange(96, dtype=float), {"seasonal_period": 0}),
    ]
    completion_order: list[str] = []
    delays = {"alpha": 0.03, "beta": 0.0, "gamma": 0.0}
    peaks = {"alpha": 0.20, "beta": 0.17, "gamma": 0.04}

    def _fake_run_canonical_example(
        series_name: str,
        series: np.ndarray,
        **_: object,
    ) -> CanonicalExampleResult:
        del series
        time.sleep(delays[series_name])
        completion_order.append(series_name)
        return _dummy_result(series_name, peak=peaks[series_name])

    def _write_panel_plot(_: list[object], *, save_path: Path) -> None:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text("panel-plot", encoding="utf-8")

    monkeypatch.setattr(module, "_load_canonical_datasets", lambda: dataset_specs)
    monkeypatch.setattr(module, "run_canonical_example", _fake_run_canonical_example)
    monkeypatch.setattr(module, "save_all_canonical_plots", lambda result, *, output_dir: {})
    monkeypatch.setattr(module, "save_canonical_result_json", lambda result, *, output_path: None)
    monkeypatch.setattr(module, "save_canonical_markdown", lambda result, *, output_path: None)
    monkeypatch.setattr(module, "plot_canonical_panel_summary", _write_panel_plot)
    monkeypatch.setattr(module, "_log_progress", lambda *args, **kwargs: None)

    output_root = tmp_path / "outputs"
    module.run_canonical_triage(
        skip_bands=True,
        full_bands=False,
        with_extensions=False,
        max_workers=2,
        output_root=output_root,
    )

    assert completion_order[-1] == "alpha"

    bundle = CanonicalSummaryBundle.from_json_file(
        output_root / "json" / "canonical_examples_summary.json"
    )
    assert [payload.series_name for payload in bundle.examples] == [
        "alpha",
        "beta",
        "gamma",
    ]

    panel_report = (output_root / "reports" / "canonical" / "canonical_panel_summary.md").read_text(
        encoding="utf-8"
    )
    assert "## Actionable Recommendations" in panel_report
    assert "Alpha" in panel_report
    assert "Beta" in panel_report
    assert "Gamma" in panel_report
    assert (output_root / "figures" / "canonical" / "canonical_panel_summary.png").exists()


def test_run_canonical_triage_default_mixed_mode_marks_not_computed_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Default mixed mode should skip bands for extended finance series and label outputs."""
    module = _load_script_module()
    dataset_specs = [
        ("sine_wave", np.arange(96, dtype=float), {"seasonal_period": 0}),
        ("bitcoin_returns", np.arange(96, dtype=float), {"seasonal_period": 0}),
    ]
    seen_skip_bands: dict[str, bool] = {}

    def _fake_run_canonical_example(
        series_name: str,
        series: np.ndarray,
        *,
        skip_bands: bool,
        **_: object,
    ) -> CanonicalExampleResult:
        del series
        seen_skip_bands[series_name] = skip_bands
        significant_lags = None if skip_bands else np.array([1, 2], dtype=int)
        return CanonicalExampleResult(
            series_name=series_name,
            series=np.linspace(0.0, 1.0, 96),
            ami=MetricCurve(
                values=np.array([0.3, 0.2, 0.1], dtype=float),
                significant_lags=significant_lags,
            ),
            pami=MetricCurve(
                values=np.array([0.18, 0.12, 0.06], dtype=float),
                significant_lags=significant_lags,
            ),
            metadata={"seasonal_period": 0},
        )

    def _write_panel_plot(_: list[object], *, save_path: Path) -> None:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text("panel-plot", encoding="utf-8")

    monkeypatch.setattr(module, "_load_canonical_datasets", lambda: dataset_specs)
    monkeypatch.setattr(module, "run_canonical_example", _fake_run_canonical_example)
    monkeypatch.setattr(module, "save_all_canonical_plots", lambda result, *, output_dir: {})
    monkeypatch.setattr(module, "plot_canonical_panel_summary", _write_panel_plot)
    monkeypatch.setattr(module, "_log_progress", lambda *args, **kwargs: None)

    output_root = tmp_path / "outputs"
    module.run_canonical_triage(
        skip_bands=False,
        full_bands=False,
        with_extensions=False,
        max_workers=1,
        output_root=output_root,
    )

    assert seen_skip_bands == {
        "sine_wave": False,
        "bitcoin_returns": True,
    }

    bitcoin_payload = (output_root / "json" / "canonical" / "bitcoin_returns.json").read_text(
        encoding="utf-8"
    )
    assert '"ami_significance_status": "not computed"' in bitcoin_payload
    assert '"pami_significance_status": "not computed"' in bitcoin_payload

    bitcoin_report = (output_root / "reports" / "canonical" / "bitcoin_returns.md").read_text(
        encoding="utf-8"
    )
    assert "n_sig_ami: not computed" in bitcoin_report
    assert "n_sig_pami: not computed" in bitcoin_report
    assert "Is it broad or compact? Not assessed (bands not computed)" in bitcoin_report

    panel_report = (output_root / "reports" / "canonical" / "canonical_panel_summary.md").read_text(
        encoding="utf-8"
    )
    assert "Significance entries marked 'not computed'" in panel_report
    assert "| Bitcoin Returns | high | high | 0.600 | not computed | not computed |" in panel_report
