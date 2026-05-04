"""Tests for the CLI transport adapter (AGT-009)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest

from forecastability.adapters.cli import (
    _render_extended_markdown,
    _render_markdown,
    _render_scorers_markdown,
    _series_from_json,
    build_parser,
    cmd_extended,
    cmd_list_scorers,
    cmd_triage,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ar1(n: int = 150, *, phi: float = 0.85, seed: int = 42) -> list[float]:
    """Generate a simple AR(1) series."""
    rng = np.random.default_rng(seed)
    ts = np.zeros(n)
    ts[0] = rng.standard_normal()
    for i in range(1, n):
        ts[i] = phi * ts[i - 1] + rng.standard_normal()
    return ts.tolist()


def _make_short(n: int = 20) -> list[float]:
    rng = np.random.default_rng(0)
    return rng.standard_normal(n).tolist()


def _write_csv(tmp_path: Path, series: list[float], col: str = "value") -> Path:
    p = tmp_path / "series.csv"
    with p.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([col])
        for v in series:
            writer.writerow([v])
    return p


# ---------------------------------------------------------------------------
# Parser structure
# ---------------------------------------------------------------------------


class TestBuildParser:
    def test_parser_has_triage_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["triage", "--series", "[1, 2, 3]"])
        assert args.command == "triage"

    def test_parser_has_list_scorers_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["list-scorers"])
        assert args.command == "list-scorers"

    def test_parser_has_extended_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["extended", "--series", "[1, 2, 3]"])
        assert args.command == "extended"

    def test_triage_default_format_is_json(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["triage", "--series", "[1]"])
        assert args.format == "json"

    def test_list_scorers_default_format_is_json(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["list-scorers"])
        assert args.format == "json"

    def test_triage_explicit_markdown_format(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["triage", "--series", "[1]", "--format", "markdown"])
        assert args.format == "markdown"

    def test_triage_default_goal_is_univariate(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["triage", "--series", "[1]"])
        assert args.goal == "univariate"

    def test_triage_max_lag_default(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["triage", "--series", "[1]"])
        assert args.max_lag == 40

    def test_no_subcommand_raises(self) -> None:
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])


# ---------------------------------------------------------------------------
# _series_from_json
# ---------------------------------------------------------------------------


class TestSeriesFromJson:
    def test_valid_array_returns_ndarray(self) -> None:
        result = _series_from_json("[1.0, 2.0, 3.0]")
        assert isinstance(result, np.ndarray)
        np.testing.assert_array_almost_equal(result, [1.0, 2.0, 3.0])

    def test_invalid_json_raises_system_exit(self) -> None:
        with pytest.raises(SystemExit):
            _series_from_json("not_json")

    def test_non_list_raises_system_exit(self) -> None:
        with pytest.raises(SystemExit):
            _series_from_json('{"key": "value"}')


# ---------------------------------------------------------------------------
# cmd_triage via argparse Namespace
# ---------------------------------------------------------------------------


class TestCmdTriageJson:
    def test_ar1_json_series_returns_zero(self, capsys: pytest.CaptureFixture[str]) -> None:
        """AR(1) series via --series → JSON output, no crash."""
        parser = build_parser()
        args = parser.parse_args(["triage", "--series", json.dumps(_make_ar1()), "--max-lag", "20"])
        code = cmd_triage(args)
        captured = capsys.readouterr()
        assert code == 0
        data = json.loads(captured.out)
        assert "blocked" in data
        assert "readiness" in data

    def test_short_series_produces_blocked_result(self, capsys: pytest.CaptureFixture[str]) -> None:
        parser = build_parser()
        args = parser.parse_args(["triage", "--series", json.dumps(_make_short())])
        code = cmd_triage(args)
        captured = capsys.readouterr()
        assert code == 0
        data = json.loads(captured.out)
        assert data["blocked"] is True

    def test_json_output_has_interpretation_for_clear_series(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        parser = build_parser()
        args = parser.parse_args(["triage", "--series", json.dumps(_make_ar1()), "--max-lag", "20"])
        cmd_triage(args)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "interpretation" in data
        assert data["interpretation"]["forecastability_class"] in {"high", "medium", "low"}

    def test_markdown_format_produces_heading(self, capsys: pytest.CaptureFixture[str]) -> None:
        parser = build_parser()
        series_json = json.dumps(_make_ar1())
        args = parser.parse_args(
            ["triage", "--series", series_json, "--max-lag", "20", "--format", "markdown"]
        )
        code = cmd_triage(args)
        captured = capsys.readouterr()
        assert code == 0
        assert "# Forecastability Triage Result" in captured.out

    def test_invalid_goal_returns_nonzero(self, capsys: pytest.CaptureFixture[str]) -> None:
        # bypass argparse choices restriction by setting attribute directly
        import argparse

        ns = argparse.Namespace(
            csv=None,
            series=json.dumps(_make_ar1()),
            col=None,
            exog_csv=None,
            exog_col=None,
            goal="bad_goal",
            max_lag=20,
            n_surrogates=99,
            random_state=42,
            format="json",
        )
        code = cmd_triage(ns)
        assert code == 1


class TestCmdTriageCsv:
    def test_csv_with_default_column(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        csv_path = _write_csv(tmp_path, _make_ar1())
        parser = build_parser()
        args = parser.parse_args(["triage", "--csv", str(csv_path), "--max-lag", "20"])
        code = cmd_triage(args)
        captured = capsys.readouterr()
        assert code == 0
        data = json.loads(captured.out)
        assert "blocked" in data

    def test_csv_with_named_column(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        csv_path = _write_csv(tmp_path, _make_ar1(), col="price")
        parser = build_parser()
        args = parser.parse_args(
            ["triage", "--csv", str(csv_path), "--col", "price", "--max-lag", "20"]
        )
        code = cmd_triage(args)
        assert code == 0

    def test_csv_missing_column_exits(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        csv_path = _write_csv(tmp_path, _make_ar1(), col="value")
        parser = build_parser()
        args = parser.parse_args(
            ["triage", "--csv", str(csv_path), "--col", "nonexistent", "--max-lag", "20"]
        )
        with pytest.raises(SystemExit):
            cmd_triage(args)

    def test_csv_missing_file_exits(self, capsys: pytest.CaptureFixture[str]) -> None:
        import argparse

        ns = argparse.Namespace(
            csv="/nonexistent/path.csv",
            series=None,
            col=None,
            exog_csv=None,
            exog_col=None,
            goal="univariate",
            max_lag=20,
            n_surrogates=99,
            random_state=42,
            format="json",
        )
        with pytest.raises(SystemExit):
            cmd_triage(ns)


class TestCmdExtended:
    def test_json_output_contains_profile(self, capsys: pytest.CaptureFixture[str]) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "extended",
                "--series",
                json.dumps(_make_ar1()),
                "--max-lag",
                "20",
                "--format",
                "json",
            ]
        )
        code = cmd_extended(args)
        captured = capsys.readouterr()
        assert code == 0
        data = json.loads(captured.out)
        assert "fingerprint" in data
        assert "profile" in data

    def test_markdown_output_renders_brief_heading(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "extended",
                "--series",
                json.dumps(_make_ar1()),
                "--max-lag",
                "20",
                "--format",
                "markdown",
            ]
        )
        code = cmd_extended(args)
        captured = capsys.readouterr()
        assert code == 0
        assert "# Extended Forecastability Brief" in captured.out
        assert "Suggested families:" in captured.out

    def test_invalid_extended_input_returns_nonzero(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import argparse

        ns = argparse.Namespace(
            csv=None,
            series=json.dumps(_make_ar1()),
            col=None,
            name=None,
            max_lag=20,
            period=1,
            ordinal_embedding_dimension=3,
            ordinal_delay=1,
            memory_min_scale=None,
            memory_max_scale=None,
            include_ami_geometry=True,
            include_spectral=True,
            include_ordinal=True,
            include_classical=True,
            include_memory=True,
            format="json",
        )
        code = cmd_extended(ns)
        captured = capsys.readouterr()
        assert code == 1
        assert "invalid extended analysis input" in captured.err


# ---------------------------------------------------------------------------
# cmd_list_scorers
# ---------------------------------------------------------------------------


class TestCmdListScorers:
    def test_json_output_is_list(self, capsys: pytest.CaptureFixture[str]) -> None:
        import argparse

        ns = argparse.Namespace(format="json")
        code = cmd_list_scorers(ns)
        captured = capsys.readouterr()
        assert code == 0
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) > 0

    def test_json_output_has_required_keys(self, capsys: pytest.CaptureFixture[str]) -> None:
        import argparse

        ns = argparse.Namespace(format="json")
        cmd_list_scorers(ns)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        for scorer in data:
            assert "name" in scorer
            assert "family" in scorer
            assert "description" in scorer

    def test_mi_scorer_present(self, capsys: pytest.CaptureFixture[str]) -> None:
        import argparse

        ns = argparse.Namespace(format="json")
        cmd_list_scorers(ns)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        names = [s["name"] for s in data]
        assert "mi" in names

    def test_markdown_output_has_table(self, capsys: pytest.CaptureFixture[str]) -> None:
        import argparse

        ns = argparse.Namespace(format="markdown")
        code = cmd_list_scorers(ns)
        captured = capsys.readouterr()
        assert code == 0
        assert "# Available Scorers" in captured.out
        assert "| Name |" in captured.out


# ---------------------------------------------------------------------------
# _render_markdown helpers
# ---------------------------------------------------------------------------


class TestRenderMarkdown:
    def test_blocked_result_contains_caution(self) -> None:
        data = {
            "blocked": True,
            "readiness": {
                "status": "blocked",
                "warnings": [{"code": "TOO_SHORT", "message": "short"}],
            },
        }
        md = _render_markdown(data)
        assert "blocked" in md.lower()
        assert "[!IMPORTANT]" in md

    def test_clear_result_has_interpretation_section(self) -> None:
        data = {
            "blocked": False,
            "readiness": {"status": "clear", "warnings": []},
            "method_plan": {
                "route": "univariate_with_significance",
                "compute_surrogates": True,
                "rationale": "enough data",
                "assumptions": [],
            },
            "interpretation": {
                "forecastability_class": "high",
                "directness_class": "high",
                "modeling_regime": "nonlinear",
                "primary_lags": [1, 2],
                "pattern_class": "A",
            },
            "recommendation": "Use deep AR model.",
        }
        md = _render_markdown(data)
        assert "## Interpretation" in md
        assert "## Recommendation" in md
        assert "high" in md


class TestRenderScorersMarkdown:
    def test_table_contains_mi(self) -> None:
        scorers = [{"name": "mi", "family": "nonlinear", "description": "Mutual info"}]
        md = _render_scorers_markdown(scorers)
        assert "mi" in md
        assert "|" in md


class TestRenderExtendedMarkdown:
    def test_brief_contains_sources_families_and_why(self) -> None:
        data: dict[str, object] = {
            "profile": {
                "signal_strength": "medium",
                "noise_risk": "low",
                "predictability_sources": ["lag_dependence", "seasonality"],
                "recommended_model_families": ["arima", "harmonic_regression"],
                "avoid_model_families": ["tree_on_lags"],
                "explanation": ["AMI-first view: informative lag structure extends to horizon 8."],
            }
        }

        markdown = _render_extended_markdown(data)

        assert "# Extended Forecastability Brief" in markdown
        assert "Detected sources:" in markdown
        assert "Suggested families:" in markdown
        assert "Why:" in markdown
